"""Functional tests for pydantic_modelable based extension mechanism."""

import typing

import aenum
import core
import ext1
import ext2


def test_extended_enum() -> None:
    """Tests that an enum is properly extended."""
    assert len(list(typing.cast(aenum.Enum, core.AutoExtensibleEnum))) == 2
    assert ext1.ExtensionOne().mtype in typing.cast(aenum.Enum, core.AutoExtensibleEnum)
    assert ext2.ExtensionTwo().mtype in typing.cast(aenum.Enum, core.AutoExtensibleEnum)


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
    assert ext1.ExtensionOne in types
    assert ext2.ExtensionTwo in types
    # Ensure all expected discriminator literals (tags) are set
    tags = [annotation.__metadata__[0].tag for annotation in typing_args]
    assert ext1.ExtensionOne().mtype in tags
    assert ext2.ExtensionTwo().mtype in tags
