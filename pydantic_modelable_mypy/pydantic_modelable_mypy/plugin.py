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
from mypy.options import Options
from mypy.plugin import (
    AttributeContext,
    ClassDefContext,
    FunctionSigContext,
    Plugin,
    SemanticAnalyzerPluginInterface,
)
from mypy.plugins.common import add_attribute_to_class
from mypy.types import (
    CallableType,
    FunctionLike,
    Instance,
    LiteralType,
    NoneType,
    ProperType,
    Type,
    UnionType,
    get_proper_type,
)

# The base every extensible model derives from; used to filter our decorators
# apart from any unrelated method that happens to be named `as_attribute`.
MODELABLE_FULLNAME = 'pydantic_modelable.model.Modelable'

_AS_ATTRIBUTE = 'as_attribute'
_EXTENDS_UNION = 'extends_union'
_EXTENDS_ENUM = 'extends_enum'

# Parameters of `Modelable.as_attribute`, after the bound `cls`, in order.
_AS_ATTRIBUTE_PARAMS = ('attr_name', 'optional', 'default_factory')

# Metadata persisted in mypy's cache, so the information survives incremental /
# daemon runs where the module that recorded it is not re-analysed.
_METADATA_KEY = 'pydantic_modelable'
# On a target `TypeInfo`: {attr_name: required} injected by `as_attribute`.
_INJECTED_ATTRS = 'injected_attrs'
# On a container `TypeInfo`: {attr_name: base_fullname} for `extends_union`.
_UNION_FIELDS = 'union_fields'
# On an extensible base `TypeInfo`: the discriminator field name.
_DISCRIMINATOR = 'discriminator'


class ModelablePlugin(Plugin):
    """Teach mypy about the models `pydantic_modelable` extends at runtime."""

    def __init__(self, options: Options) -> None:
        """Initialise the per-run caches."""
        super().__init__(options)
        # Subtypes discovered during semantic analysis (`get_base_class_hook`).
        # Reliable for a full run — where module trees may be freed before the
        # check phase, defeating the module scan — but empty for classes loaded
        # from cache on an incremental run.
        self._union_subtypes: dict[str, list[str]] = {}
        # Same-run supplement to the container's persisted `union_fields`
        # metadata: covers containers decorated this run before their cache
        # exists. Keyed by 'Container.attr' fullname -> base fullname.
        self._union_fields: dict[str, str] = {}
        # Extensible base fullname -> its discriminator field name, captured
        # from the base's `discriminator=` class keyword.
        self._discriminators: dict[str, str] = {}
        # Extensible base fullname -> the extensible enum TypeInfos registered
        # onto it. Subtypes analysed after the enum push their discriminator
        # values into these (the enum's module is analysed before its subtypes',
        # so the enum TypeInfo already exists when a subtype is seen).
        self._enum_bases: dict[str, list[TypeInfo]] = {}

    def get_class_decorator_hook_2(self, fullname: str) -> Callable[[ClassDefContext], bool] | None:
        """Dispatch class-decorator analysis for the registration decorators.

        mypy keys this on the decorator's fullname. The decorators are
        classmethods inherited from `Modelable`, so `@Shelter.as_attribute(...)`
        resolves to `Modelable.as_attribute` regardless of the subclass.
        """
        name = fullname.rsplit('.', 1)[-1]
        if name == _AS_ATTRIBUTE:
            return _as_attribute_hook
        if name == _EXTENDS_UNION:
            return self._record_union_field
        if name == _EXTENDS_ENUM:
            return self._extend_enum_hook
        return None

    def get_base_class_hook(self, fullname: str) -> Callable[[ClassDefContext], None] | None:
        """Record subclasses of an extensible `Modelable` base during analysis.

        mypy keys this on the base's fullname, which may be a re-export path
        (e.g. `pydantic_modelable.Modelable`), so we resolve it to a `TypeInfo`
        and compare its canonical fullname. When the base is `Modelable` itself,
        the class being defined is an extensible base and we capture its
        discriminator for `extends_enum`. When the base is a proper `Modelable`
        subclass, the class is one of its union alternatives; recording it here
        keeps full runs reliable, since the check-time module scan cannot see
        trees mypy has freed.
        """
        symbol = self.lookup_fully_qualified(fullname)
        if symbol is None or not isinstance(symbol.node, TypeInfo):
            return None
        base_info = symbol.node
        if base_info.fullname == MODELABLE_FULLNAME:
            return self._capture_discriminator
        if not base_info.has_base(MODELABLE_FULLNAME):
            return None
        base_fullname = base_info.fullname

        def _register(ctx: ClassDefContext) -> None:
            subtypes = self._union_subtypes.setdefault(base_fullname, [])
            subtype = ctx.cls.info.fullname
            if subtype not in subtypes:
                subtypes.append(subtype)
            # Push this subtype's discriminator values into any enum already
            # registered for the base (covers subtypes — incl. cross-module —
            # defined after the enum).
            discriminator = self._discriminator_of(base_fullname)
            if discriminator is not None:
                for enum_info in self._enum_bases.get(base_fullname, []):
                    self._add_enum_members(ctx.api, enum_info, ctx.cls.info, discriminator)

        return _register

    def get_attribute_hook(self, fullname: str) -> Callable[[AttributeContext], Type] | None:
        """Type an `extends_union` field as the union of its base's subtypes."""
        base_fullname = self._union_field_base(fullname)
        if base_fullname is None:
            return None

        def _typed(ctx: AttributeContext) -> Type:
            union = self._build_union(base_fullname)
            return union if union is not None else ctx.default_attr_type

        return _typed

    def get_function_signature_hook(self, fullname: str) -> Callable[[FunctionSigContext], FunctionLike] | None:
        """Adjust constructor signatures of extended models.

        Two adjustments, both keyed on the callee (constructor) fullname:

         - `as_attribute` injects fields whose keyword the synthesized pydantic
           `__init__` does not know about; we append them.
         - `extends_union` rewrites a declared field into a discriminated union;
           we narrow that field's constructor keyword to the union so a bare
           base instance is rejected, matching runtime validation.

        Offered only for `Modelable` subclasses or classes carrying union
        fields, so unrelated callables are left untouched.
        """
        symbol = self.lookup_fully_qualified(fullname)
        if symbol is None or not isinstance(symbol.node, TypeInfo):
            return None
        if symbol.node.has_base(MODELABLE_FULLNAME) or self._union_fields_of(symbol.node):
            return self._constructor_sig_hook
        return None

    def _record_union_field(self, ctx: ClassDefContext) -> bool:
        """Record that `@Base.extends_union('attr')` makes `attr` a discriminated union.

        The field keeps its declared type; the union is resolved lazily at use
        (read site and constructor) once every subtype is known. The mapping is
        stored on the container's own (persisted) metadata plus the same-run
        registry.
        """
        reason = ctx.reason
        if not isinstance(reason, CallExpr):
            return False
        callee = reason.callee
        if not isinstance(callee, MemberExpr) or callee.name != _EXTENDS_UNION:
            return True
        base = callee.expr
        if not (isinstance(base, RefExpr) and isinstance(base.node, TypeInfo)):
            return False
        if not base.node.has_base(MODELABLE_FULLNAME):
            return True
        attr_name: str | None = None
        for name, arg in zip(reason.arg_names, reason.args, strict=True):
            if isinstance(arg, StrExpr) and name in (None, 'attr_name'):
                attr_name = arg.value
                break
        if attr_name is None:
            return True
        container = ctx.cls.info
        container.metadata.setdefault(_METADATA_KEY, {}).setdefault(_UNION_FIELDS, {})[attr_name] = base.node.fullname
        self._union_fields[f'{container.fullname}.{attr_name}'] = base.node.fullname
        return True

    def _capture_discriminator(self, ctx: ClassDefContext) -> None:
        """Record the `discriminator=` keyword of an extensible base being defined."""
        discriminator = ctx.cls.keywords.get(_DISCRIMINATOR)
        if not isinstance(discriminator, StrExpr):
            return
        base = ctx.cls.info
        self._discriminators[base.fullname] = discriminator.value
        base.metadata.setdefault(_METADATA_KEY, {})[_DISCRIMINATOR] = discriminator.value

    def _discriminator_of(self, base_fullname: str) -> str | None:
        """Return the discriminator field name of an extensible base, or None."""
        cached = self._discriminators.get(base_fullname)
        if cached is not None:
            return cached
        symbol = self.lookup_fully_qualified(base_fullname)
        if symbol is None or not isinstance(symbol.node, TypeInfo):
            return None
        value: str | None = symbol.node.metadata.get(_METADATA_KEY, {}).get(_DISCRIMINATOR)
        return value

    def _extend_enum_hook(self, ctx: ClassDefContext) -> bool:
        """Inject the discriminator literals of a base's subtypes as enum members.

        `@Base.extends_enum` adds, at runtime, one member per discriminator value
        of every `Base` subtype. We mirror that on the decorated enum's TypeInfo
        so member access (`Species.one`) resolves.
        """
        reason = ctx.reason
        if not isinstance(reason, MemberExpr) or reason.name != _EXTENDS_ENUM:
            return True
        base_expr = reason.expr
        if not (isinstance(base_expr, RefExpr) and isinstance(base_expr.node, TypeInfo)):
            return False
        base = base_expr.node
        if not base.has_base(MODELABLE_FULLNAME):
            return True
        discriminator = self._discriminator_of(base.fullname)
        if discriminator is None:
            return True
        enum_info = ctx.cls.info
        # Register so subtypes analysed later push their values into this enum.
        enums = self._enum_bases.setdefault(base.fullname, [])
        if enum_info not in enums:
            enums.append(enum_info)
        # Inject members for subtypes already known (defined before the enum, or
        # loaded from cache on an incremental run).
        for subtype_fullname in self._subtypes_of(base.fullname):
            symbol = self.lookup_fully_qualified(subtype_fullname)
            if symbol is not None and isinstance(symbol.node, TypeInfo):
                self._add_enum_members(ctx.api, enum_info, symbol.node, discriminator)
        return True

    def _add_enum_members(
        self,
        api: SemanticAnalyzerPluginInterface,
        enum_info: TypeInfo,
        subtype: TypeInfo,
        discriminator: str,
    ) -> None:
        """Add `subtype`'s discriminator literal(s) as members of `enum_info`."""
        field = subtype.get(discriminator)
        if field is None or not isinstance(field.node, Var) or field.node.type is None:
            return
        for value in _literal_str_values(field.node.type):
            if value not in enum_info.names:
                add_attribute_to_class(api, enum_info.defn, value, Instance(enum_info, []))

    def _subtypes_of(self, base_fullname: str) -> list[str]:
        """Direct subclasses of an extensible base: registry + module-graph scan.

        The semantic-analysis registry (`_union_subtypes`) covers classes
        analysed this run; the module-graph scan covers classes loaded from
        cache on incremental runs (where semanal, hence the registry, is
        skipped). Merged, de-duplicated by fullname, registry order first.

        Deliberately not memoised: an early call (e.g. during incremental SCC
        processing, before the registry is complete) would otherwise cache an
        incomplete result. Only invoked for genuine union-field accesses.
        """
        ordered: list[str] = []
        seen: set[str] = set()
        for name in self._union_subtypes.get(base_fullname, []):
            if name not in seen:
                seen.add(name)
                ordered.append(name)
        for module in (self._modules or {}).values():
            for symbol in module.names.values():
                node = symbol.node
                if (
                    isinstance(node, TypeInfo)
                    and node.fullname not in seen
                    and any(base.type.fullname == base_fullname for base in node.bases)
                ):
                    seen.add(node.fullname)
                    ordered.append(node.fullname)
        return ordered

    def _union_field_base(self, attr_fullname: str) -> str | None:
        """Return the extensible base for a `Container.attr` fullname, or None."""
        base = self._union_fields.get(attr_fullname)
        if base is not None:
            return base
        cls_fullname, _, attr = attr_fullname.rpartition('.')
        if not attr:
            return None
        symbol = self.lookup_fully_qualified(cls_fullname)
        if symbol is None or not isinstance(symbol.node, TypeInfo):
            return None
        fields: dict[str, str] = symbol.node.metadata.get(_METADATA_KEY, {}).get(_UNION_FIELDS, {})
        return fields.get(attr)

    def _union_fields_of(self, info: TypeInfo) -> dict[str, str]:
        """Return the `extends_union` fields declared on `info`: {attr: base_fullname}."""
        fields: dict[str, str] = dict(info.metadata.get(_METADATA_KEY, {}).get(_UNION_FIELDS, {}))
        prefix = f'{info.fullname}.'
        for key, base in self._union_fields.items():
            if key.startswith(prefix):
                fields[key[len(prefix):]] = base
        return fields

    def _build_union(self, base_fullname: str) -> Type | None:
        """Build the discriminated union of a base's subtypes, or None if none resolve."""
        instances: list[Instance] = []
        for subtype in self._subtypes_of(base_fullname):
            symbol = self.lookup_fully_qualified(subtype)
            if symbol is not None and isinstance(symbol.node, TypeInfo):
                instances.append(Instance(symbol.node, []))
        if not instances:
            return None
        return UnionType.make_union(instances)

    def _constructor_sig_hook(self, ctx: FunctionSigContext) -> FunctionLike:
        """Narrow `extends_union` fields and append `as_attribute` fields on a constructor."""
        signature = ctx.default_signature
        if not isinstance(signature, CallableType):
            return signature
        ret_type = get_proper_type(signature.ret_type)
        if not isinstance(ret_type, Instance):
            return signature
        info = ret_type.type

        arg_types = list(signature.arg_types)
        arg_kinds = list(signature.arg_kinds)
        arg_names = list(signature.arg_names)

        # extends_union: narrow the declared field's keyword to the union.
        for attr, base_fullname in self._union_fields_of(info).items():
            if attr not in arg_names:
                continue
            union = self._build_union(base_fullname)
            if union is not None:
                arg_types[arg_names.index(attr)] = union

        # as_attribute: append injected fields, unless the constructor already
        # accepts arbitrary keywords (inserting named args after `**kwargs` would
        # be ill-formed).
        if ARG_STAR2 not in arg_kinds:
            existing = set(arg_names)
            for name, (typ, required) in _injected_fields(info).items():
                if name in existing:
                    continue
                arg_types.append(typ)
                arg_kinds.append(ARG_NAMED if required else ARG_NAMED_OPT)
                arg_names.append(name)

        return signature.copy_modified(arg_types=arg_types, arg_kinds=arg_kinds, arg_names=arg_names)


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


def _literal_str_values(typ: Type) -> list[str]:
    """Extract the string values of a `Literal[...]` type (a union yields several)."""
    proper = get_proper_type(typ)
    if isinstance(proper, UnionType):
        values: list[str] = []
        for item in proper.items:
            values.extend(_literal_str_values(item))
        return values
    if isinstance(proper, LiteralType) and isinstance(proper.value, str):
        return [proper.value]
    # A field declared as a value (`mtype: Literal['one'] = 'one'`) may present
    # as its fallback instance carrying the literal in `last_known_value`.
    if isinstance(proper, Instance) and proper.last_known_value is not None:
        return _literal_str_values(proper.last_known_value)
    return []


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


def plugin(version: str) -> type[Plugin]:
    """Return the plugin class for mypy to instantiate.

    This is the entrypoint mypy looks up from the `plugins` configuration key.
    The `version` argument is mypy's own version string, which a plugin may use
    to guard against incompatible internal APIs.
    """
    return ModelablePlugin
