"""Typing errors around `Modelable.extends_union`.

`extends_union('attr')` rewrites the decorated model's `attr` field into a
discriminated union of the base `Modelable`'s subtypes. Statically the field
keeps its declared (base) type, so mypy sees neither the discriminator nor any
subtype-specific field. The plugin types the field as the union of the base's
subtypes, restoring discriminated-union narrowing.
"""
from .conftest import RunMypy, RunMypyIncremental, RunMypyPackage

EXTENDS_UNION_SNIPPET = """
from typing import Literal

from pydantic import BaseModel
from pydantic_modelable import Modelable


class BaseDiscriminated(Modelable, discriminator='mtype'):
    pass


class ExtensionOne(BaseDiscriminated):
    mtype: Literal['one'] = 'one'
    value: str = 'x'


class ExtensionTwo(BaseDiscriminated):
    mtype: Literal['two'] = 'two'
    count: int = 0


@BaseDiscriminated.extends_union('item')
class Container(BaseModel):
    id: int
    item: BaseDiscriminated


c = Container(id=1, item=ExtensionOne(value='hi'))
reveal_type(c.item)
if c.item.mtype == 'one':
    print(c.item.value)
"""


def test_extends_union_errors_without_plugin(run_mypy: RunMypy) -> None:
    """Baseline: the field is the abstract base, so subtype access is an error."""
    result = run_mypy(EXTENDS_UNION_SNIPPET, plugin=False)
    assert result.has_error('"BaseDiscriminated" has no attribute "mtype"'), result.output
    assert result.has_error('"BaseDiscriminated" has no attribute "value"'), result.output


def test_extends_union_read_ok_with_plugin(run_mypy: RunMypy) -> None:
    """With the plugin, the field is the union of subtypes and narrows correctly."""
    result = run_mypy(EXTENDS_UNION_SNIPPET, plugin=True)
    assert result.errors == 0, result.output
    assert 'Revealed type is "snippet.ExtensionOne | snippet.ExtensionTwo"' in result.output, result.output


# Cross-module: base + container in one module, each subtype in its own module,
# consumer in a fourth. The union alternatives are only discoverable once every
# module has been analysed — the real aggregation ordering.
_UNION_FIXTURES = ('union_core.py', 'union_temp.py', 'union_switch.py', 'union_app.py')


def test_extends_union_crossmodule_errors_without_plugin(run_mypy_package: RunMypyPackage) -> None:
    """Baseline: without the plugin, the consumer cannot see the discriminator/fields."""
    result = run_mypy_package(*_UNION_FIXTURES, plugin=False)
    assert result.has_error('"Feed" has no attribute "kind"'), result.output
    assert result.has_error('"Feed" has no attribute "celsius"'), result.output


def test_extends_union_crossmodule_ok_with_plugin(run_mypy_package: RunMypyPackage) -> None:
    """With the plugin, the union aggregates subtypes across modules and narrows."""
    result = run_mypy_package(*_UNION_FIXTURES, plugin=True)
    assert result.errors == 0, result.output


# Construction with a bare base is runtime-invalid (fails pydantic's discriminated
# validation); the plugin narrows the constructor keyword to the union so mypy
# rejects it, while accepting a genuine subtype.
CONSTRUCTOR_SNIPPET = """
from typing import Literal

from pydantic import BaseModel
from pydantic_modelable import Modelable


class BaseDiscriminated(Modelable, discriminator='mtype'):
    pass


class ExtensionOne(BaseDiscriminated):
    mtype: Literal['one'] = 'one'
    value: str = 'x'


@BaseDiscriminated.extends_union('item')
class Container(BaseModel):
    id: int
    item: BaseDiscriminated


good = Container(id=1, item=ExtensionOne(value='hi'))
bad = Container(id=1, item=BaseDiscriminated())
"""

_BASE_ARG_ERROR = 'has incompatible type "BaseDiscriminated"'


def test_extends_union_constructor_accepts_bare_base_without_plugin(run_mypy: RunMypy) -> None:
    """Baseline: without the plugin the field is the base, so a bare base is accepted."""
    result = run_mypy(CONSTRUCTOR_SNIPPET, plugin=False)
    assert not result.has_error(_BASE_ARG_ERROR), result.output


def test_extends_union_constructor_narrowed_with_plugin(run_mypy: RunMypy) -> None:
    """With the plugin, the constructor keyword is the union: bare base rejected, subtype ok."""
    result = run_mypy(CONSTRUCTOR_SNIPPET, plugin=True)
    assert result.has_error(_BASE_ARG_ERROR), result.output
    assert result.errors == 1, result.output


def test_extends_union_incremental_survives_consumer_edit(run_mypy_incremental: RunMypyIncremental) -> None:
    """Editing only the consumer must not collapse the union on the incremental pass.

    On the second pass the subtype modules are served from cache (their semantic
    analysis, hence the in-memory registry, is skipped), so the union can only
    survive via the module-graph scan.
    """
    first, second = run_mypy_incremental(*_UNION_FIXTURES, touch='union_app.py')
    assert first.errors == 0, first.output
    assert second.errors == 0, second.output


def test_extends_union_incremental_survives_subtype_edit(run_mypy_incremental: RunMypyIncremental) -> None:
    """Editing a subtype module keeps the union intact on the incremental pass."""
    first, second = run_mypy_incremental(*_UNION_FIXTURES, touch='union_switch.py')
    assert first.errors == 0, first.output
    assert second.errors == 0, second.output
