"""Typing errors around `Modelable.as_attribute`.

`as_attribute` registers the decorated model as a new field on the target
`Modelable`. At runtime the field exists; statically it does not. This surfaces
as two distinct `mypy --strict` errors, both fixed by the plugin:

 - `[attr-defined]` when *reading* the injected attribute (field injection);
 - `[call-arg]` when *constructing* the target with the injected keyword — the
   target's `__init__` is synthesized (via pydantic's `dataclass_transform`)
   before the extension's decorator is seen, so the field is absent from it; a
   constructor signature hook adds it back as an accepted keyword.
"""
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

_READ_ERROR = '"Shelter" has no attribute "welcome_desk"'
_CONSTRUCT_ERROR = 'Unexpected keyword argument "welcome_desk" for "Shelter"'


def test_as_attribute_read_errors_without_plugin(run_mypy: RunMypy) -> None:
    """Baseline: reading the injected attribute is an error without the plugin.

    This is the canonical weakness we are fixing: the field is added at runtime
    by the decorator, so mypy has no way to know `Shelter` gained it.
    """
    result = run_mypy(AS_ATTRIBUTE_SNIPPET, plugin=False)
    assert result.has_error(_READ_ERROR), result.output


def test_as_attribute_read_ok_with_plugin(run_mypy: RunMypy) -> None:
    """With the plugin, the injected attribute is known and typed as the model."""
    result = run_mypy(AS_ATTRIBUTE_SNIPPET, plugin=True)
    assert not result.has_error(_READ_ERROR), result.output
    assert 'Revealed type is "snippet.WelcomeDesk"' in result.output, result.output


def test_as_attribute_construct_errors_without_plugin(run_mypy: RunMypy) -> None:
    """Baseline: constructing the target with the injected keyword errors."""
    result = run_mypy(AS_ATTRIBUTE_SNIPPET, plugin=False)
    assert result.has_error(_CONSTRUCT_ERROR), result.output


def test_as_attribute_construct_ok_with_plugin(run_mypy: RunMypy) -> None:
    """With the plugin, the injected field is accepted as a constructor keyword."""
    result = run_mypy(AS_ATTRIBUTE_SNIPPET, plugin=True)
    assert not result.has_error(_CONSTRUCT_ERROR), result.output


def test_as_attribute_snippet_fully_clean_with_plugin(run_mypy: RunMypy) -> None:
    """With the plugin, the whole extension snippet type-checks with no errors."""
    result = run_mypy(AS_ATTRIBUTE_SNIPPET, plugin=True)
    assert result.errors == 0, result.output


# The model genuinely gains `welcome_desk`, but a plain function returning it
# must not: the constructor signature hook must be scoped to constructors, not
# leaked onto arbitrary callables whose return type is the extended model.
FUNCTION_RETURNING_TARGET_SNIPPET = """
from pydantic import BaseModel
from pydantic_modelable import Modelable


class Shelter(Modelable):
    pass


@Shelter.as_attribute('welcome_desk')
class WelcomeDesk(BaseModel):
    name: str


def make() -> Shelter:
    return Shelter(welcome_desk=WelcomeDesk(name='front'))


make(welcome_desk=WelcomeDesk(name='leak'))
"""


def test_injected_keyword_not_leaked_to_plain_functions(run_mypy: RunMypy) -> None:
    """The keyword widening is scoped to constructors, not any Modelable-returning call."""
    result = run_mypy(FUNCTION_RETURNING_TARGET_SNIPPET, plugin=True)
    # The constructor call inside `make` is fine; the call to `make` itself is not.
    assert result.has_error('Unexpected keyword argument "welcome_desk" for "make"'), result.output


# A plain (non-optional, no default_factory) registration: the field is required
# at runtime, so omitting it from the constructor must be an error.
REQUIRED_OMITTED_SNIPPET = """
from pydantic import BaseModel
from pydantic_modelable import Modelable


class Shelter(Modelable):
    pass


@Shelter.as_attribute('welcome_desk')
class WelcomeDesk(BaseModel):
    name: str


Shelter()
"""


def test_as_attribute_required_field_omitted_errors(run_mypy: RunMypy) -> None:
    """A required injected field must be flagged as missing, matching pydantic."""
    result = run_mypy(REQUIRED_OMITTED_SNIPPET, plugin=True)
    assert result.has_error('Missing named argument "welcome_desk"'), result.output


# With a default_factory, the field is optional at construction: omitting it is
# fine, and the read type stays the (non-widened) model type.
DEFAULT_FACTORY_SNIPPET = """
from pydantic import BaseModel
from pydantic_modelable import Modelable


class Shelter(Modelable):
    pass


@Shelter.as_attribute('welcome_desk', default_factory=lambda: WelcomeDesk(name='d'))
class WelcomeDesk(BaseModel):
    name: str


shelter = Shelter()
reveal_type(shelter.welcome_desk)
"""


def test_as_attribute_default_factory_field_is_optional(run_mypy: RunMypy) -> None:
    """A default_factory makes the field non-required; the read type is the model."""
    result = run_mypy(DEFAULT_FACTORY_SNIPPET, plugin=True)
    assert result.errors == 0, result.output
    assert 'Revealed type is "snippet.WelcomeDesk"' in result.output, result.output


# `optional=True` widens the field type to `Model | None` but does not add a
# default: the field is still required, and now accepts None.
OPTIONAL_SNIPPET = """
from pydantic import BaseModel
from pydantic_modelable import Modelable


class Shelter(Modelable):
    pass


@Shelter.as_attribute('welcome_desk', optional=True)
class WelcomeDesk(BaseModel):
    name: str


shelter = Shelter(welcome_desk=None)
reveal_type(shelter.welcome_desk)
"""


def test_as_attribute_optional_widens_type_but_stays_required(run_mypy: RunMypy) -> None:
    """`optional=True` accepts None and widens the read type, remaining required."""
    ok = run_mypy(OPTIONAL_SNIPPET, plugin=True)
    assert ok.errors == 0, ok.output
    assert 'Revealed type is "snippet.WelcomeDesk | None"' in ok.output, ok.output

    omitted = run_mypy(OPTIONAL_SNIPPET.replace('Shelter(welcome_desk=None)', 'Shelter()'), plugin=True)
    assert omitted.has_error('Missing named argument "welcome_desk"'), omitted.output
