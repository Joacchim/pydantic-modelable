"""Functional tests for pydantic_modelable based extension mechanism."""

import typing
from typing import Any, Literal

import aenum
import core
import pytest
from pydantic import BaseModel

from pydantic_modelable import DefaultDiscriminatorPolicy, Modelable, PluginLoader


@pytest.mark.parametrize('module,expected',
    (
        (None, {'core'}),
        ('core', {'ext1', 'ext2'}),
    ),
    ids=['not-specified', 'core'],
)
def test_plugin_loader_lookup_dependants(module: str | None, expected: set[str]) -> None:
    """Test PluginLoader._lookup_dependants internal function."""
    loader: PluginLoader[Any]
    if module is not None:
        loader = PluginLoader[Any](module)
    else:
        loader = PluginLoader[Any]()
    assert set(loader._lookup_dependants()) == expected


def test_core_loaded_plugins() -> None:
    """Test PluginLoader._lookup_dependants internal function."""
    assert set(core.loader.loaded().keys()) == {'ext1', 'ext2'}


def test_extended_enum() -> None:
    """Tests that an enum is properly extended."""
    assert len(list(typing.cast(aenum.Enum, core.AutoExtensibleEnum))) == 2
    assert core.loader.loaded()['ext1'].ExtensionOne().mtype in typing.cast(aenum.Enum, core.AutoExtensibleEnum)
    assert core.loader.loaded()['ext2'].ExtensionTwo().mtype in typing.cast(aenum.Enum, core.AutoExtensibleEnum)


def test_extended_union() -> None:
    """Tests that a discriminated union field is properly updated."""
    item_annotations = core.AutoExtensibleContainer.model_fields['item'].annotation
    assert item_annotations is not None
    annotation_args = item_annotations.__args__
    # Inspect the field's annotation
    assert len(annotation_args) == 1
    assert typing.get_origin(annotation_args[0]) is typing.Union
    typing_args = typing.get_args(annotation_args[0])
    assert len(typing_args) == 2
    # Ensure all expected types are set
    types = [annotation.__args__[0] for annotation in typing_args]
    assert core.loader.loaded()['ext1'].ExtensionOne in types
    assert core.loader.loaded()['ext2'].ExtensionTwo in types
    # Ensure all expected discriminator literals (tags) are set
    tags = [annotation.__metadata__[0].tag for annotation in typing_args]
    assert core.loader.loaded()['ext1'].ExtensionOne().mtype in tags
    assert core.loader.loaded()['ext2'].ExtensionTwo().mtype in tags


@pytest.mark.parametrize('behavior',
    list(DefaultDiscriminatorPolicy),
    ids=[e.name.lower() for e in DefaultDiscriminatorPolicy],
)
def test_extended_union_default(behavior: str) -> None:
    """Validate the default-value behavior of an extended discriminated enum."""
    policy_value = behavior
    match behavior:
        case DefaultDiscriminatorPolicy.FIRST_REGISTERED:
            expected_tag = 'one'
        case DefaultDiscriminatorPolicy.LAST_REGISTERED:
            expected_tag = 'three'
        case DefaultDiscriminatorPolicy.PREDETERMINED:
            expected_tag = policy_value = 'two'

    class Base(Modelable, discriminator='key', discriminator_default_policy=policy_value):
        ...

    @Base.extends_union('item')
    class Container(BaseModel):
        item: None = None  # Represent default value for mypy

    class B1(Base):
        key: Literal['one']
    class B2(Base):
        key: Literal['two']
    class B3(Base):
        key: Literal['three']

    match behavior:
        case DefaultDiscriminatorPolicy.NONE:
            with pytest.raises(ValueError):
                Container()
        case _:
            obj = Container()
            assert obj.item is not None
            assert obj.item.key == expected_tag
