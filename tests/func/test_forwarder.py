"""Tests for ModelableForwarder, delegating Modelable registration to a target."""

import typing
from typing import Literal, cast

import aenum
from pydantic import BaseModel

from pydantic_modelable import Modelable, ModelableEnumMixin, ModelableForwarder


def test_forward_as_attribute() -> None:
    """An attribute registered through a forwarder lands on the target Modelable."""

    class Profile(Modelable): ...

    class ExtensionForwarder(ModelableForwarder, forwards_to=Profile): ...

    @ExtensionForwarder.as_attribute('indirect')
    class IndirectExtension(BaseModel):
        subname: str

    Profile.model_rebuild(force=True)

    profile = Profile(**{'indirect': {'subname': 'forwarded'}})
    assert getattr(getattr(profile, 'indirect'), 'subname') == 'forwarded'


def test_forward_chained() -> None:
    """A forwarder may target another forwarder, chaining down to the Modelable."""

    class Root(Modelable): ...

    class MidForwarder(ModelableForwarder, forwards_to=Root): ...

    class LeafForwarder(ModelableForwarder, forwards_to=MidForwarder): ...

    @LeafForwarder.as_attribute('deep')
    class Deep(BaseModel):
        value: int = 3

    Root.model_rebuild(force=True)

    root = Root(**{'deep': {'value': 7}})
    assert getattr(getattr(root, 'deep'), 'value') == 7


def test_forward_extends_union() -> None:
    """A discriminated union registered through a forwarder is built from the target's subtypes."""

    class Base(Modelable, discriminator='key'): ...

    class BaseForwarder(ModelableForwarder, forwards_to=Base): ...

    @BaseForwarder.extends_union('item')
    class Container(BaseModel):
        item: None = None  # Overridden by the forwarded extends_union hook

    class One(Base):
        key: Literal['one'] = 'one'

    class Two(Base):
        key: Literal['two'] = 'two'

    item_annotation = Container.model_fields['item'].annotation
    assert item_annotation is not None
    union_arg = item_annotation.__args__[0]
    assert typing.get_origin(union_arg) is typing.Union
    members = [arg.__args__[0] for arg in typing.get_args(union_arg)]
    assert One in members
    assert Two in members

    container = Container.model_validate({'item': {'key': 'two'}})
    assert getattr(getattr(container, 'item'), 'key') == 'two'


def test_forward_extends_enum() -> None:
    """An enum extended through a forwarder collects the target's discriminator values."""

    class Base(Modelable, discriminator='mtype'): ...

    class BaseForwarder(ModelableForwarder, forwards_to=Base): ...

    @BaseForwarder.extends_enum
    class ForwardedEnum(ModelableEnumMixin, str, aenum.Enum):  # type: ignore[misc]
        ...

    class One(Base):
        mtype: Literal['one'] = 'one'

    class Two(Base):
        mtype: Literal['two'] = 'two'

    assert len(list(cast(aenum.Enum, ForwardedEnum))) == 2


def test_forward_rebuilds_model() -> None:
    """A rebuildable registered through a forwarder is recorded on the target Modelable."""

    class Base(Modelable): ...

    class BaseForwarder(ModelableForwarder, forwards_to=Base): ...

    @BaseForwarder.rebuilds_model()
    class Container(BaseModel): ...

    assert Container in Base.__feat_rebuild__[Base]
