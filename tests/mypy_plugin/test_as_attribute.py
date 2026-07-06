"""Typing errors around `Modelable.as_attribute`.

`as_attribute` registers the decorated model as a new field on the target
`Modelable`. At runtime the field exists; statically it does not, so reading it
trips `mypy --strict`. These tests pin the baseline error and the fix.
"""
import pytest

from .conftest import RunMypy

# A minimal extension: `WelcomeDesk` is grafted onto `Shelter` as `welcome_desk`.
AS_ATTRIBUTE_SNIPPET = """
from pydantic import BaseModel
from pydantic_modelable import Modelable


class Shelter(Modelable):
    pass


@Shelter.as_attribute('welcome_desk')
class WelcomeDesk(BaseModel):
    name: str


shelter = Shelter(welcome_desk=WelcomeDesk(name='front'))
reveal_type(shelter.welcome_desk)
"""


def test_as_attribute_read_errors_without_plugin(run_mypy: RunMypy) -> None:
    """Baseline: reading the injected attribute is an error without the plugin.

    This is the canonical weakness we are fixing: the field is added at runtime
    by the decorator, so mypy has no way to know `Shelter` gained it.
    """
    result = run_mypy(AS_ATTRIBUTE_SNIPPET, plugin=False)
    assert result.has_error('"Shelter" has no attribute "welcome_desk"'), result.output


@pytest.mark.xfail(reason='as_attribute hook not implemented yet', strict=True)
def test_as_attribute_read_ok_with_plugin(run_mypy: RunMypy) -> None:
    """Target: with the plugin, the injected attribute is known and typed."""
    result = run_mypy(AS_ATTRIBUTE_SNIPPET, plugin=True)
    assert not result.has_error('has no attribute "welcome_desk"'), result.output
    assert result.has_error('') is False or 'WelcomeDesk' in result.output
