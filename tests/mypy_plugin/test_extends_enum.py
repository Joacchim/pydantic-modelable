"""Member-name resolution for `Modelable.extends_enum`.

`ModelableStrEnum` already makes an extended enum a real enum (iterable,
constructible, membership). This closes the last gap: `extends_enum` injects one
member per discriminator value of the base's subtypes at runtime, and the plugin
mirrors those as static members so name access (`Palette.red`) resolves.

Limitation: members are injected during analysis and enum member access offers
no use-site hook for a missing name, so — unlike `extends_union` — this cannot
be recovered on incremental / daemon runs where the relevant modules are served
from cache. It is reliable under full (non-incremental) runs, which is what the
harness (and CI) use.
"""
from .conftest import RunMypy, RunMypyPackage

ENUM_SNIPPET = """
from typing import Literal

from pydantic_modelable import Modelable, ModelableStrEnum


class Base(Modelable, discriminator='mtype'):
    pass


class One(Base):
    mtype: Literal['one'] = 'one'


class Two(Base):
    mtype: Literal['two'] = 'two'


@Base.extends_enum
class Species(ModelableStrEnum):
    pass


reveal_type(Species.one)
reveal_type(Species.two)
missing = Species.three
"""


def test_extends_enum_member_access_errors_without_plugin(run_mypy: RunMypy) -> None:
    """Baseline: without the plugin the dynamically-added members are unknown."""
    result = run_mypy(ENUM_SNIPPET, plugin=False)
    assert result.has_error('"type[Species]" has no attribute "one"'), result.output


def test_extends_enum_member_access_ok_with_plugin(run_mypy: RunMypy) -> None:
    """With the plugin, injected members resolve; a genuine non-member still errors."""
    result = run_mypy(ENUM_SNIPPET, plugin=True)
    assert not result.has_error('has no attribute "one"'), result.output
    assert not result.has_error('has no attribute "two"'), result.output
    assert result.output.count('Revealed type is "snippet.Species"') == 2, result.output
    # A value no subtype contributes is still correctly rejected.
    assert result.has_error('"type[Species]" has no attribute "three"'), result.output


# Cross-module: base + enum in one module, each subtype in its own, consumer in
# a fourth — the members come from the sibling modules.
_ENUM_FIXTURES = ('enum_core.py', 'enum_red.py', 'enum_blue.py', 'enum_app.py')


def test_extends_enum_crossmodule_errors_without_plugin(run_mypy_package: RunMypyPackage) -> None:
    """Baseline: the consumer cannot see the cross-module members without the plugin."""
    result = run_mypy_package(*_ENUM_FIXTURES, plugin=False)
    assert result.has_error('"type[Palette]" has no attribute "red"'), result.output


def test_extends_enum_crossmodule_ok_with_plugin(run_mypy_package: RunMypyPackage) -> None:
    """With the plugin (full run), members contributed by sibling modules resolve."""
    result = run_mypy_package(*_ENUM_FIXTURES, plugin=True)
    assert result.errors == 0, result.output
