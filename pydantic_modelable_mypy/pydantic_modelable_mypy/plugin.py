"""The mypy plugin entrypoint for pydantic-modelable.

`pydantic_modelable`'s registration decorators mutate a *different*, pre-existing
model at runtime, which the static type system cannot express. This plugin
observes those decorators during semantic analysis and injects the corresponding
members into the target model's `TypeInfo`, so `mypy --strict` sees the extended
model as its runtime shape.

Capabilities are added one decorator at a time; each is backed by a test that
first reproduces the error it fixes.
"""

from collections.abc import Callable

from mypy.nodes import (
    ARG_NAMED,
    ARG_NAMED_OPT,
    ARG_STAR2,
    CallExpr,
    Expression,
    MemberExpr,
    NameExpr,
    RefExpr,
    StrExpr,
    TypeInfo,
    Var,
)
from mypy.plugin import ClassDefContext, FunctionSigContext, Plugin
from mypy.plugins.common import add_attribute_to_class
from mypy.types import CallableType, FunctionLike, Instance, NoneType, ProperType, Type, UnionType, get_proper_type

# The base every extensible model derives from; used to filter our decorators
# apart from any unrelated method that happens to be named `as_attribute`.
MODELABLE_FULLNAME = 'pydantic_modelable.model.Modelable'

_AS_ATTRIBUTE = 'as_attribute'

# Parameters of `Modelable.as_attribute`, after the bound `cls`, in order.
_AS_ATTRIBUTE_PARAMS = ('attr_name', 'optional', 'default_factory')

# Metadata (persisted in mypy's cache) recording, per target `TypeInfo`, the
# fields we injected and whether each is required at construction — so the
# constructor signature hook can rediscover them on incremental runs without
# re-observing the decorator.
_METADATA_KEY = 'pydantic_modelable'
_INJECTED_ATTRS = 'injected_attrs'


class ModelablePlugin(Plugin):
    """Teach mypy about the models `pydantic_modelable` extends at runtime."""

    def get_class_decorator_hook_2(self, fullname: str) -> Callable[[ClassDefContext], bool] | None:
        """Dispatch class-decorator analysis for the registration decorators.

        mypy keys this on the decorator's fullname. `as_attribute` is a
        classmethod inherited from `Modelable`, so a `@Shelter.as_attribute(...)`
        decorator resolves to `Modelable.as_attribute` regardless of the subclass.
        """
        if fullname.rsplit('.', 1)[-1] == _AS_ATTRIBUTE:
            return _as_attribute_hook
        return None

    def get_function_signature_hook(self, fullname: str) -> Callable[[FunctionSigContext], FunctionLike] | None:
        """Adjust constructor signatures of extended models to accept injected fields.

        The target's `__init__` is synthesized (pydantic `dataclass_transform`)
        before the extension's decorator is analysed, so injected fields are
        absent from it. Rather than re-synthesize `__init__` — which fights that
        ordering — we widen the signature mypy checks each call against.

        mypy keys this on the callee's fullname; for `Shelter(...)` that is the
        class fullname. We offer the hook only when the fullname resolves to a
        `Modelable` subclass, so a plain function returning a `Modelable` is left
        untouched.
        """
        symbol = self.lookup_fully_qualified(fullname)
        if symbol is not None and isinstance(symbol.node, TypeInfo) and symbol.node.has_base(MODELABLE_FULLNAME):
            return _constructor_sig_hook
        return None


def _record_injected(info: TypeInfo, attr_name: str, *, required: bool) -> None:
    """Note, in persisted metadata, the field we injected onto `info`."""
    data = info.metadata.setdefault(_METADATA_KEY, {})
    attrs = data.setdefault(_INJECTED_ATTRS, {})
    attrs[attr_name] = required


def _injected_fields(info: TypeInfo) -> dict[str, tuple[Type, bool]]:
    """Fields injected onto `info` (or a base), mapping name -> (type, required)."""
    fields: dict[str, tuple[Type, bool]] = {}
    for base in info.mro:
        attrs = base.metadata.get(_METADATA_KEY, {}).get(_INJECTED_ATTRS, {})
        for name, required in attrs.items():
            symbol = info.get(name)
            if symbol is not None and isinstance(symbol.node, Var) and symbol.node.type is not None:
                fields[name] = (symbol.node.type, required)
    return fields


def _resolve_target(ctx: ClassDefContext) -> TypeInfo | None:
    """Resolve the `Modelable` subclass a decorator is registering onto.

    For `@Shelter.as_attribute('welcome_desk')`, that is `Shelter` — the object
    the decorator method is bound to, not the decorated class.
    """
    reason = ctx.reason
    if not isinstance(reason, CallExpr):
        return None
    callee = reason.callee
    if not isinstance(callee, MemberExpr) or callee.name != _AS_ATTRIBUTE:
        return None
    target = callee.expr
    if isinstance(target, RefExpr) and isinstance(target.node, TypeInfo):
        return target.node
    return None


def _bind_arguments(reason: CallExpr) -> dict[str, Expression]:
    """Map a decorator call's positional/keyword args to parameter names.

    `as_attribute` is called as a bound classmethod (`Shelter.as_attribute(...)`),
    so positional arguments align with `_AS_ATTRIBUTE_PARAMS` directly.
    """
    bound: dict[str, Expression] = {}
    position = 0
    for name, arg in zip(reason.arg_names, reason.args, strict=True):
        if name is None:
            if position < len(_AS_ATTRIBUTE_PARAMS):
                bound[_AS_ATTRIBUTE_PARAMS[position]] = arg
            position += 1
        else:
            bound[name] = arg
    return bound


def _is_true(expr: object) -> bool:
    """Whether a call argument is the literal `True`."""
    return isinstance(expr, NameExpr) and expr.fullname == 'builtins.True'


def _is_none(expr: object) -> bool:
    """Whether a call argument is the literal `None`."""
    return isinstance(expr, NameExpr) and expr.fullname == 'builtins.None'


def _as_attribute_hook(ctx: ClassDefContext) -> bool:
    """Inject the field `Modelable.as_attribute` adds onto its target model.

    Returns whether analysis is complete: if the target model is not resolvable
    yet, we return `False` so mypy re-runs us on a later pass.
    """
    target = _resolve_target(ctx)
    if target is None:
        return False
    # Only act on our own decorator; a same-named method elsewhere is not ours.
    if not target.has_base(MODELABLE_FULLNAME):
        return True

    reason = ctx.reason
    assert isinstance(reason, CallExpr)

    bound = _bind_arguments(reason)
    attr_name_expr = bound.get('attr_name')
    if not isinstance(attr_name_expr, StrExpr):
        return True
    attr_name = attr_name_expr.value

    # `optional=True` widens the field type; it does not supply a default. A
    # field is required at construction unless a `default_factory` is given.
    optional = _is_true(bound.get('optional'))
    factory = bound.get('default_factory')
    required = factory is None or _is_none(factory)

    attr_type: ProperType = Instance(ctx.cls.info, [])
    if optional:
        attr_type = UnionType([attr_type, NoneType()])

    add_attribute_to_class(ctx.api, target.defn, attr_name, attr_type)
    _record_injected(target, attr_name, required=required)
    return True


def _constructor_sig_hook(ctx: FunctionSigContext) -> FunctionLike:
    """Append injected fields as accepted keyword arguments to a constructor."""
    signature = ctx.default_signature
    if not isinstance(signature, CallableType):
        return signature
    # A `**kwargs`-accepting constructor already takes any keyword; nothing to do
    # (and inserting named args after `**kwargs` would be ill-formed).
    if ARG_STAR2 in signature.arg_kinds:
        return signature
    ret_type = get_proper_type(signature.ret_type)
    if not isinstance(ret_type, Instance):
        return signature

    existing = set(signature.arg_names)
    extra = {name: field for name, field in _injected_fields(ret_type.type).items() if name not in existing}
    if not extra:
        return signature

    arg_types = list(signature.arg_types)
    arg_kinds = list(signature.arg_kinds)
    arg_names = list(signature.arg_names)
    for name, (typ, required) in extra.items():
        arg_types.append(typ)
        arg_kinds.append(ARG_NAMED if required else ARG_NAMED_OPT)
        arg_names.append(name)
    return signature.copy_modified(arg_types=arg_types, arg_kinds=arg_kinds, arg_names=arg_names)


def plugin(version: str) -> type[Plugin]:
    """Return the plugin class for mypy to instantiate.

    This is the entrypoint mypy looks up from the `plugins` configuration key.
    The `version` argument is mypy's own version string, which a plugin may use
    to guard against incompatible internal APIs.
    """
    return ModelablePlugin
