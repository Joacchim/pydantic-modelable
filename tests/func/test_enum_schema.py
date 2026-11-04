"""Functional tests for the pydantic schemas of ModelableStrEnum."""

from typing import Annotated, Any, Literal

import aenum
import pytest
from pydantic import BaseModel, Field, ValidationError

from pydantic_modelable import Modelable, ModelableEnumMixin, ModelableStrEnum


def _make_shapes(*kinds: Literal['circle', 'square']) -> tuple[type[BaseModel], type[ModelableStrEnum]]:
    """Build a fresh Modelable setup, then declare the requested extensions in order.

    Each test gets its own classes: extensions registered by one test must not
    leak into another.
    """

    class Shape(Modelable, discriminator='kind'):
        pass

    @Shape.extends_enum
    class ShapeKind(ModelableStrEnum):
        pass

    # Rewriting this union on each extension is what rebuilds ShapeFilter.
    @Shape.extends_union('shape')
    class Drawing(BaseModel):
        shape: Shape

    @Shape.rebuilds_model()
    class ShapeFilter(BaseModel):
        kind: Annotated[ShapeKind | None, Field(strict=False)] = None

    for kind in kinds:
        if kind == 'circle':

            class Circle(Shape):
                kind: Literal['circle'] = 'circle'

        if kind == 'square':

            class Square(Shape):
                kind: Literal['square'] = 'square'

    return ShapeFilter, ShapeKind


def _validated_kind(model: type[BaseModel], kind: str) -> Any:
    return model.model_validate({'kind': kind}).model_dump()['kind']


def test_enum_field_rejects_values_before_any_extension() -> None:
    """A model can hold the enum before any value exists, and rejects everything."""
    shape_filter, _ = _make_shapes()

    with pytest.raises(ValidationError):
        _validated_kind(shape_filter, 'circle')


def test_enum_field_accepts_the_first_extension_alone() -> None:
    """The model is rebuilt before the enum gets the first value, and still accepts it."""
    shape_filter, shape_kind = _make_shapes('circle')

    assert _validated_kind(shape_filter, 'circle') is shape_kind('circle')
    with pytest.raises(ValidationError):
        _validated_kind(shape_filter, 'triangle')


def test_enum_field_accepts_later_extensions() -> None:
    """Each further extension adds a value accepted by the rebuilt model."""
    shape_filter, shape_kind = _make_shapes('circle', 'square')

    assert _validated_kind(shape_filter, 'circle') is shape_kind('circle')
    assert _validated_kind(shape_filter, 'square') is shape_kind('square')
    with pytest.raises(ValidationError):
        _validated_kind(shape_filter, 'triangle')


def test_enum_schema_kwargs_set_the_json_schema() -> None:
    """The schema_title and schema_description subclass parameters reach the JSON schema."""

    class Kinds(ModelableStrEnum, schema_title='Shape kinds', schema_description='Kind of a shape'):
        pass

    class Holder(BaseModel):
        kind: Kinds | None = None

    schema = Holder.model_json_schema()['properties']['kind']['anyOf'][0]

    assert schema['title'] == 'Shape kinds'
    assert schema['description'] == 'Kind of a shape'


def test_enum_schema_defaults_without_kwargs() -> None:
    """Without subclass parameters, the schema title and description default to values derived from the class name."""

    class Bare(ModelableStrEnum):
        pass

    assert Bare.__schema_title__ == 'Bare'
    assert Bare.__schema_description__ == 'Extensible enum for Bare'


def test_enum_schema_class_attributes_on_a_hand_written_enum() -> None:
    """An enum spelled out with the mixin takes its schema title and description from class attributes."""

    class Kinds(ModelableEnumMixin, str, aenum.Enum):  # type: ignore[misc]
        __schema_title__ = 'Shape kinds'
        __schema_description__ = 'Kind of a shape'

    assert Kinds.__schema_title__ == 'Shape kinds'
    assert Kinds.__schema_description__ == 'Kind of a shape'
