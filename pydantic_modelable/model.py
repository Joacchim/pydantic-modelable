"""Base models for pydantic_modelable."""

import enum
from collections.abc import Callable, Sequence
from typing import Annotated, Any, ClassVar, TypeVar, Union, cast

import aenum
from pydantic import BaseModel, Field, Tag
from pydantic.fields import FieldInfo

from .mixins import ModelableEnumMixin

T = TypeVar('T', bound='type[aenum.Enum]|tuple[str,type[BaseModel]]')


class DefaultDiscriminatorPolicy(enum.Enum):
    """Describes the method used to determine a Discriminator's default value.

    NONE: No default will be setup in the discriminated union
    FIRST_REGISTERED: The first Modelable extension registered will be used as
    the default
    LAST_REGISTERED: The last Modelable extension registered will be used as
    the default
    PREDETERMINED: The base Modelable type provides a hard-coded default
    value on initialization.

    Usage examples:
    ```py
    # To use the first extension to MyExtensible ever loaded, provide the enum value:
    class MyExtensible(
        Modelable,
        discriminator='attr',
        discriminator_default_policy=DefaultDiscriminatorPolicy.FIRST_REGISTERED,
    ):
        ...

    # To use the last extension to MyExtensible loaded before instanciation, provide the enum value:
    class MyExtensible(
        Modelable,
        discriminator='attr',
        discriminator_default_policy=DefaultDiscriminatorPolicy.LAST_REGISTERED,
    ):
        ...

    # To use a pre-determined value, as a hard-coded default, provide a string:
    class MyExtensible(Modelable, discriminator='attr', discriminator_default_policy='default'):
        ...
    ```
    """

    NONE = 0
    FIRST_REGISTERED = 1
    LAST_REGISTERED = 2
    PREDETERMINED = 3


_DefaultDiscriminatorConfig = tuple[DefaultDiscriminatorPolicy,str|None]

class Modelable(BaseModel):
    """Inherit from this class to define extensible pydantic_modelable models.

    Comes with all utilities to register other models as related models to be
    updated with each loaded extensions of the class derivating this one.
    """

    # set of types directly derivating Model
    __discriminator__: ClassVar[dict[type['Modelable'], tuple[str,_DefaultDiscriminatorConfig] | None]] = {}
    __subtypes__: ClassVar[dict[type['Modelable'], list[type['Modelable']]]] = {}

    # maps subtypes to the types registered as "Users" of the derivated Model
    __feat_unions__: ClassVar[dict[type['Modelable'], set[tuple[str, type[BaseModel]]]]] = {}
    __feat_enums__: ClassVar[dict[type['Modelable'], set[type[aenum.Enum]]]] = {}

    @classmethod
    def _parent_modelable(cls) -> type['Modelable']:
        return cls.mro()[1]

    @classmethod
    def __init_subclass__(
        cls,
        discriminator: str | None = None,
        discriminator_default_policy: str | DefaultDiscriminatorPolicy = DefaultDiscriminatorPolicy.NONE,
        **kwargs: Any,
    ) -> None:
        """Initialize the pydantic_modelable.Modelable internal class data for subclasses.

        It currently mostly records the subclass parameters into itself,
        guaranteeing that the __pydantic_init_subclass__ function has all
        required pieces of information to do its job properly.
        """
        super().__init_subclass__(**kwargs)
        base = cls.mro()[1]
        # Here, we only record the discriminator and the subtype for the sake of it.
        if base not in cls.__subtypes__.keys():
            policy = discriminator_default_policy
            policy_param: str | None = None
            if isinstance(policy, str):
                policy_param = policy
                policy = DefaultDiscriminatorPolicy.PREDETERMINED
            cls.__discriminator__[cls] = None if discriminator is None else (discriminator, (policy, policy_param))
            cls.__subtypes__[cls] = []
            cls.__feat_enums__[cls] = set()
            cls.__feat_unions__[cls] = set()
        else:
            cls.__subtypes__[base].append(cls)

    @classmethod
    def _set_field_on_model(
        cls,
        model: type[BaseModel],
        name: str,
        # Actually an Annotated[] specialized type, which can only be determined at runtime.
        # Using `Any` for simplification
        annotation: Any,
        # Likewise, Callable return type can only be specified at runtime.
        default_factory: Callable[[], BaseModel|None] | None = None,
    ) -> None:
        """Inspired heavily by what is done inside `ModelMetaclass.__new__`.

        May be incomplete!
        """
        # The following setp seems kind-of duplicated, but complies with what mypy can handle.
        field_info = FieldInfo(annotation=annotation)
        if default_factory is not None:
            field_info = FieldInfo(annotation=annotation, default_factory=default_factory)
        model.model_fields.update({name: field_info})
        model.model_rebuild(force=True)

    @classmethod
    def _extend_pydantic_enum(cls, subtype: type['Modelable'], enum_type: type[aenum.Enum]) -> None:
        """Extend an enum with the value provided by `subtype`."""
        # Defensive-coding/mypy: expresses our assumption that calling this code means we _HAVE_ a discriminator
        discriminator_config = cls.__discriminator__[cls]
        assert discriminator_config is not None
        discriminator_key, _ = discriminator_config
        assert discriminator_key is not None # for mypy
        discriminator = subtype.model_fields[discriminator_key]
        annotation = discriminator.annotation
        assert annotation is not None # for mypy
        discriminator_values = annotation.__args__
        # Normalize discriminator_values into a sequence for unified handling
        if not isinstance(discriminator_values, Sequence):
            discriminator_values = [discriminator_values]
        for value in discriminator_values:
            enum_type._add_choice(value)

    @classmethod
    def _extend_pydantic_union(cls, _: type['Modelable'], union_spec: tuple[str, type[BaseModel]]) -> None:
        """Rewrites a model's discriminated union field with the available subtypes."""
        # TODO(joa) Features to add:
        #  - Ordering of model rebuilding after adding a new alternative for discriminated unions (after X ?)

        # Defensive-coding/mypy: expresses our assumption that calling this code means we _HAVE_ a discriminator
        discriminator_config = cls.__discriminator__[cls]
        assert discriminator_config is not None

        attr_name, union_type = union_spec
        discriminator_key, (default_policy, default_tag) = discriminator_config
        alternatives = cls.__subtypes__[cls]

        #
        # Prepare Optional default value for discriminated union
        #
        def _resolve_discriminator_defaults() -> tuple[str | None, type[Modelable] | None]:
            nonlocal default_policy
            nonlocal default_tag
            def _get_tag(item: type[Modelable]) -> str:
                item_discriminator = item.model_fields[discriminator_key]
                # NOTE(david): Make mypy happy
                assert item_discriminator.annotation is not None
                return cast(str, item_discriminator.annotation.__args__[0])

            default_type: type[Modelable] | None
            match default_policy:
                case DefaultDiscriminatorPolicy.FIRST_REGISTERED:
                    default_type = alternatives[0]
                    default_tag = _get_tag(default_type)
                case DefaultDiscriminatorPolicy.LAST_REGISTERED:
                    default_type = alternatives[-1]
                    default_tag = _get_tag(default_type)
                case DefaultDiscriminatorPolicy.PREDETERMINED:
                    for alt in alternatives:
                        alt_discriminator = alt.model_fields[discriminator_key]
                        assert alt_discriminator.annotation is not None
                        if default_tag in alt_discriminator.annotation.__args__:
                            default_type = alt
                            break
                    else:
                        # Here, we failed to find the specified default to be loaded.
                        # As we're possibly in an extension's
                        # `__pydantic_init_subclass__`'s routine, it is
                        # possible it hasn't been loaded yet.
                        # As such, we cannot "fail" or raise here, as we "hope"
                        # that the default will somehow be loaded later on, and
                        # then properly set into the discriminated union field
                        # parameters.
                        default_tag, default_type = None, None
                case DefaultDiscriminatorPolicy.NONE:
                    default_tag, default_type = None, None

            return default_tag, default_type

        default_factory: Callable[[], Modelable] | None = None
        default_tag, default_type = _resolve_discriminator_defaults()
        if default_type is not None:
            # Set the specified default. it MUST be instanciable without args
            # for the model not to fail to instanciate by default
            def _default_factory() -> Modelable:
                return default_type(**{discriminator_key: default_tag})
            default_factory = _default_factory

        field_args: dict[str, Any] = {}
        # discriminated union only works with at least 2 distinct values
        # -> First extension is the de-facto only choice, so no discriminator value can be set.
        if len(alternatives) >= 2:
            field_args.update({'discriminator': discriminator_key})

        # Prepare annotations for the updated field
        # ruff: noqa: UP007
        holder_annotation = Annotated[  # type: ignore[valid-type]
            Union[tuple(
                Annotated[alternative, Tag(t)]
                for alternative in alternatives
                # Hard to properly help mypy understand `annotation` can't be None
                for t in alternative.model_fields[discriminator_key].annotation.__args__  # type: ignore
            )],
            # Set the first loaded subtype as default. it MUST be instanciable without args
            Field(**field_args),
        ]

        cls._set_field_on_model(
            union_type,
            attr_name,
            holder_annotation,
            default_factory,
        )

    @classmethod
    def _update_related_models_with_subtype(cls) -> None:
        """Update all registered related union & enum types with newly loaded extension."""
        parent_modelable = cls._parent_modelable()
        for union_spec in cls.__feat_unions__[parent_modelable]:
            parent_modelable._extend_pydantic_union(cls, union_spec)
        for enum_type in cls.__feat_enums__[parent_modelable]:
            parent_modelable._extend_pydantic_enum(cls, enum_type)

    @classmethod
    def __pydantic_init_subclass__(cls, **kwargs: Any) -> None:
        """Initialize pydantic-related information for a subclass.

        The initialization is done after calling pydantic's metaclass/basemodel
        subclass init.
        """
        super().__pydantic_init_subclass__()

        # Skip all, if we're handling a direct child of Modelable
        if cls in cls.__subtypes__.keys():
            return

        cls._update_related_models_with_subtype()

    @classmethod
    def _register_item(
        cls,
        collection: set[T],
        item_type: T,
        method: Callable[[type['Modelable'], T], None],
    ) -> T:
        collection |= {item_type}
        for subtype in cls.__subtypes__[cls]:
            method(subtype, item_type)
        return item_type

    @classmethod
    def extends_enum(cls, decorable: type[aenum.Enum]) -> type[aenum.Enum]:
        """Decorate String Enum classes based on aenum.Enum.

        Register the decorated class as an Enum to be extended with the
        discriminating literal from all the child Classes of the one
        inheriting `Modelable`.

        Only works in conjunction with inheriting `Modelable` with the
        `discriminator` keyword argument defined, hinting at which Literal
        field should be use as the discrimnator value.
        """
        if not all(t in decorable.mro() for t in [aenum.Enum, ModelableEnumMixin]):
            raise TypeError(
                'Unable to extend any other enum type than an aenum.Enum, including the ModelableEnumMixin.'
            )
        return cls._register_item(cls.__feat_enums__[cls], decorable, cls._extend_pydantic_enum)

    @classmethod
    def extends_union(cls, attr_name: str) -> Callable[[type[BaseModel]], type[BaseModel]]:
        """Decorate pydantic.BaseModel classes.

        The decorated class, must be a `pydantic.BaseModel`. It should contain
        a field, that the decorator rewrites as a discriminated Union. The
        discriminated union thus configured is made up of all the subclasses of
        the class inheriting `Modelable`.

        The parameter `attr_name` tells the decorator what attribute from the
        decorated model should be overwritten as a Discriminated Union field,
        and its initial type annotation will not be accounted for.
        """

        def _wrapper(decorable: type[BaseModel]) -> type[BaseModel]:
            if not isinstance(decorable, type) or BaseModel not in decorable.mro():
                raise TypeError('Unable to extend any other model type than a descendant of pydantic.BaseModel.')
            return cls._register_item(cls.__feat_unions__[cls], (attr_name, decorable), cls._extend_pydantic_union)[1]

        return _wrapper

    @classmethod
    def as_attribute(
        cls,
        attr_name: str,
        optional: bool = False,
        default_factory: Callable[[], BaseModel|None] | None = None,
    ) -> Callable[[type[BaseModel]], type[BaseModel]]:
        """Register a custom pydantic.BaseModel-based class an an attribute.

        The attribute to be registered is controlled by the decorator's
        parameters:

         - `name`: name of the attribute to be registered in the decorating
           class
         - `default_factory`: Optional callable which takes no parameters, and
           returns a valid instance of the decorated model. Used to provide
           valid defaults when necessary/useful.
        """
        def _wrapper(decorable: type[BaseModel]) -> type[BaseModel]:
            if not isinstance(decorable, type) or BaseModel not in decorable.mro():
                raise TypeError(
                    'Unable to use a custom model type not descending from pydantic.BaseModel as an attribute.'
                )
            if optional:
                cls._set_field_on_model(cls, attr_name, decorable|None, default_factory)
            else:
                cls._set_field_on_model(cls, attr_name, decorable, default_factory)
            return decorable

        return _wrapper
