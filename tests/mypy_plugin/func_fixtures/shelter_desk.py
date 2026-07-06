"""Extension module: registers a welcome desk onto the core `Shelter`.

The decorated class lives here, in a different module from `Shelter` itself —
this is what exercises the plugin's cross-module ordering: `Shelter` is fully
analysed before mypy ever sees this decorator.
"""
from pydantic import BaseModel
from shelter_core import Shelter


@Shelter.as_attribute('welcome_desk')
class WelcomeDesk(BaseModel):
    """Facility grafted onto `Shelter` as the `welcome_desk` field."""

    name: str
