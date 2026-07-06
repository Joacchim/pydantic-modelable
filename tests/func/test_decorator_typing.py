"""Typing regression tests for the identity-preserving registration decorators.

These tests carry no runtime assertions: the guarantee is that the decorated
class keeps its own type rather than being erased to `type[BaseModel]` /
`type[aenum.Enum]`. `assert_type` is verified by `mypy --strict` (run as the
`typecheck` tox env over `tests/`); at runtime the calls are no-ops.
"""
import aenum
from pydantic import BaseModel
from typing_extensions import assert_type

from pydantic_modelable import Modelable, ModelableForwarder
from pydantic_modelable.mixins import ModelableEnumMixin


class Shelter(Modelable, discriminator='kind'):
    """Extensible model used as the decorators' registration target."""


class ShelterForwarder(ModelableForwarder, forwards_to=Shelter):
    """Registration proxy delegating to `Shelter`."""


class ExtensibleEnum(ModelableEnumMixin, str, aenum.Enum):  # type: ignore
    """Extensible enum base for the `extends_enum` test."""


def test_as_attribute_preserves_type() -> None:
    """`as_attribute` returns the decorated class, not `type[BaseModel]`."""
    @Shelter.as_attribute('welcome_desk')
    class WelcomeDesk(BaseModel):
        name: str

    assert_type(WelcomeDesk, type[WelcomeDesk])


def test_extends_union_preserves_type() -> None:
    """`extends_union` returns the decorated class, not `type[BaseModel]`."""
    @Shelter.extends_union('sub')
    class SubModel(BaseModel):
        kind: str

    assert_type(SubModel, type[SubModel])


def test_rebuilds_model_preserves_type() -> None:
    """`rebuilds_model` returns the decorated class, not `type[BaseModel]`."""
    @Shelter.rebuilds_model()
    class Container(BaseModel):
        shelter: Shelter

    assert_type(Container, type[Container])


def test_extends_enum_preserves_type() -> None:
    """`extends_enum` returns the decorated enum, not `type[aenum.Enum]`."""
    @Shelter.extends_enum
    class ExtEnum(ExtensibleEnum):
        """Enum registered as an extension of `Shelter`'s discriminator."""

    assert_type(ExtEnum, type[ExtEnum])


def test_forwarder_preserves_type() -> None:
    """Forwarded decorators preserve the decorated class's type too."""
    @ShelterForwarder.as_attribute('via_forwarder')
    class ViaForwarder(BaseModel):
        x: int

    assert_type(ViaForwarder, type[ViaForwarder])
