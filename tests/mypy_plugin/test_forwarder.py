"""Decorators applied through a `ModelableForwarder`.

A forwarder delegates the registration decorators to its `forwards_to` target
(a `Modelable`, or a further forwarder). The plugin resolves the decorator's
receiver through the forwarder chain to the target `Modelable` and then applies
the same handling as for a direct decorator.
"""
from .conftest import RunMypy

_AS_ATTRIBUTE = """
from pydantic import BaseModel
from pydantic_modelable import Modelable, ModelableForwarder


class Profile(Modelable):
    pass


class ProfileForwarder(ModelableForwarder, forwards_to=Profile):
    pass


@ProfileForwarder.as_attribute('indirect')
class Indirect(BaseModel):
    name: str


p = Profile(indirect=Indirect(name='x'))
reveal_type(p.indirect)
"""


def test_forwarded_as_attribute_errors_without_plugin(run_mypy: RunMypy) -> None:
    """Baseline: the forwarded attribute is invisible without the plugin."""
    result = run_mypy(_AS_ATTRIBUTE, plugin=False)
    assert result.has_error('"Profile" has no attribute "indirect"'), result.output


def test_forwarded_as_attribute_ok_with_plugin(run_mypy: RunMypy) -> None:
    """With the plugin, a forwarded `as_attribute` lands on the target model."""
    result = run_mypy(_AS_ATTRIBUTE, plugin=True)
    assert result.errors == 0, result.output
    assert 'Revealed type is "snippet.Indirect"' in result.output, result.output


_EXTENDS_UNION = """
from typing import Literal

from pydantic import BaseModel
from pydantic_modelable import Modelable, ModelableForwarder


class Base(Modelable, discriminator='mtype'):
    pass


class Fwd(ModelableForwarder, forwards_to=Base):
    pass


class One(Base):
    mtype: Literal['one'] = 'one'
    value: str = 'x'


@Fwd.extends_union('item')
class Container(BaseModel):
    id: int
    item: Base


c = Container(id=1, item=One(value='hi'))
if c.item.mtype == 'one':
    print(c.item.value)
"""


def test_forwarded_extends_union_ok_with_plugin(run_mypy: RunMypy) -> None:
    """With the plugin, a forwarded `extends_union` types the field as the union."""
    result = run_mypy(_EXTENDS_UNION, plugin=True)
    assert result.errors == 0, result.output


_EXTENDS_ENUM = """
from typing import Literal

from pydantic_modelable import Modelable, ModelableForwarder, ModelableStrEnum


class Base(Modelable, discriminator='mtype'):
    pass


class Fwd(ModelableForwarder, forwards_to=Base):
    pass


class One(Base):
    mtype: Literal['one'] = 'one'


@Fwd.extends_enum
class Kinds(ModelableStrEnum):
    pass


reveal_type(Kinds.one)
"""


def test_forwarded_extends_enum_ok_with_plugin(run_mypy: RunMypy) -> None:
    """With the plugin, a forwarded `extends_enum` resolves the injected member."""
    result = run_mypy(_EXTENDS_ENUM, plugin=True)
    assert result.errors == 0, result.output
    assert 'Revealed type is "snippet.Kinds"' in result.output, result.output


_CHAINED = """
from pydantic import BaseModel
from pydantic_modelable import Modelable, ModelableForwarder


class Profile(Modelable):
    pass


class Fwd1(ModelableForwarder, forwards_to=Profile):
    pass


class Fwd2(ModelableForwarder, forwards_to=Fwd1):
    pass


@Fwd2.as_attribute('deep')
class Deep(BaseModel):
    x: int


p = Profile(deep=Deep(x=1))
reveal_type(p.deep)
"""


def test_chained_forwarder_resolves_to_target_with_plugin(run_mypy: RunMypy) -> None:
    """A chain of forwarders is followed to the ultimate `Modelable`."""
    result = run_mypy(_CHAINED, plugin=True)
    assert result.errors == 0, result.output
    assert 'Revealed type is "snippet.Deep"' in result.output, result.output
