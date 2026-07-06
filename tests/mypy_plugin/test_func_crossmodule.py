"""Functional cross-module test for the plugin.

Mirrors the runtime `tests/func` style of the runtime library, but for typing:
a core module defines an extensible `Shelter`, a sibling module registers a
field onto it with `as_attribute`, and a consumer module both constructs the
model with the injected keyword and reads the injected attribute. The extension
lives in a different module from the model, so the field is registered only
after `Shelter` is fully analysed — the real ordering the plugin must survive.
"""
from .conftest import RunMypyPackage

_FIXTURES = ('shelter_core.py', 'shelter_desk.py', 'shelter_app.py')


def test_crossmodule_extension_errors_without_plugin(run_mypy_package: RunMypyPackage) -> None:
    """Baseline: without the plugin, the consumer cannot see the cross-module field."""
    result = run_mypy_package(*_FIXTURES, plugin=False)
    assert result.has_error('Unexpected keyword argument "welcome_desk" for "Shelter"'), result.output
    assert result.has_error('"Shelter" has no attribute "welcome_desk"'), result.output


def test_crossmodule_extension_ok_with_plugin(run_mypy_package: RunMypyPackage) -> None:
    """With the plugin, the whole multi-module program type-checks cleanly.

    The consumer constructs `Shelter(welcome_desk=...)` and reads
    `shelter.welcome_desk` into a `WelcomeDesk`-annotated variable, both across
    the module boundary.
    """
    result = run_mypy_package(*_FIXTURES, plugin=True)
    assert result.errors == 0, result.output
