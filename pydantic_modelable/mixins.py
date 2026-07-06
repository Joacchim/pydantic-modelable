"""Mixins classes for using pydantic_modelable."""

from typing import TYPE_CHECKING, Any, ClassVar, cast

import aenum
from pydantic import (
    GetCoreSchemaHandler,
    GetJsonSchemaHandler,
)
from pydantic.json_schema import JsonSchemaValue
from pydantic_core import CoreSchema, core_schema


class ModelableEnumMixin:
    """A mixin allowing to define an extensible `aenum`-based StrEnum.

    It must be used to define an enum that can be extended using the class
    decorator `pydantic_modelable.model.Modelable.extend_enum()`.

    Prefer inheriting `pydantic_modelable.ModelableStrEnum`, which bundles this
    mixin with the correct enum bases and stays type-checker friendly. Subclass
    parameters customise the generated json_schema so the extended enum fulfils
    its role when included in a pydantic-based API:
    ```py
    from pydantic_modelable import ModelableStrEnum

    class MyExtensibleEnum(
        ModelableStrEnum,
        schema_title='MyExtensibleEnum',
        schema_description='This is my Enum',
    ):
        ...
    ```
    """

    __schema_title__: ClassVar[str] = ''
    __schema_description__: ClassVar[str] = ''

    __setup__: ClassVar[bool] = False

    def __init_subclass__(cls, schema_title: str = '', schema_description: str = '', **kwargs: Any) -> None:
        """Initialize the ModelableEnumMixin with subclass custom parameters.

        Keyword parameters are used to customize the Schema model to be
        generated:

         - `schema_title`: The title of the model's generated schema
         - `schema_description`: The description of the model's generated schema
        """
        super().__init_subclass__(**kwargs)
        cls.__schema_title__ = schema_title if schema_title else f'{cls.__name__}'
        cls.__schema_description__ = schema_description if schema_description else f'Extensible enum for {cls.__name__}'

    @classmethod
    def _add_choice(cls, choice: str) -> None:
        """Add a new option into the Enum."""
        # Ensure `_pydantic_modelable_invalid_` member does not remain
        if not cls.__setup__:
            # Field comes from aenum.Enum, so type-checking does not complain
            # if we cast to that type, given we "ignore" that typing import
            cast(aenum.Enum, cls)._member_names_ = []
            cls.__setup__ = True
        # Now we can extend the list of available values
        aenum.extend_enum(cls, choice, choice)

    @classmethod
    def __get_pydantic_core_schema__(cls, source: type[Any], handler: GetCoreSchemaHandler) -> core_schema.CoreSchema:
        """Redefine the pydantic core schema using the dynamically injected Enum values."""
        return core_schema.enum_schema(
            cls,
            # We need to provide at least one "choice" for an enum schema.
            # Additionally, mypy complains on the Type having no "__iter__"
            # attribute but it works nonetheless
            (['none'] if not cls.__setup__ else list(cls._member_map_.values())),  # type: ignore
            sub_type='str',
            strict=True,
        )

    @classmethod
    def __get_pydantic_json_schema__(
        cls,
        _core_schema: CoreSchema,
        _handler: GetJsonSchemaHandler,
    ) -> JsonSchemaValue:
        """Redefine the pydantic JSON schema using the dynamically injected Enum values."""
        return {
            # NOTE(joa) aenum is not type-hinted: mypy can't find __iter__ for aenum.Enum
            'enum': [m.name for m in cls],  # type: ignore
            'type': 'string',
            'title': cls.__schema_title__,
            'description': cls.__schema_description__,
        }


# `aenum` ships no type information, so `aenum.Enum` is `Any` to a type checker.
# Presenting the standard-library `enum.Enum` as the base *for type-checking
# only* lets checkers recognise subclasses as real enums (iterable,
# constructible, no "cannot subclass Any" under strict), while the runtime keeps
# the `aenum` base that `extends_enum` needs to inject members dynamically. Both
# bases yield the same MRO (`ModelableEnumMixin`, `str`, an `Enum`).
if TYPE_CHECKING:
    import enum

    _StrEnumImpl = enum.Enum
else:
    _StrEnumImpl = aenum.Enum


class ModelableStrEnum(ModelableEnumMixin, str, _StrEnumImpl):
    """Base class for extensible string enums.

    Inherit from this rather than spelling out
    `(ModelableEnumMixin, str, aenum.Enum)`. At runtime it is exactly that — an
    empty `aenum` string enum, extended in place by
    `pydantic_modelable.Modelable.extends_enum` — but type checkers see a
    standard `enum.Enum`, so subclasses are understood as enums without an
    `aenum`-induced `# type: ignore`.

    The `schema_title` / `schema_description` subclass keyword arguments provided
    by `ModelableEnumMixin` are accepted as usual.
    """

