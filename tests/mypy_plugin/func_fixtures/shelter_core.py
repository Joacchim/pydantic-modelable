"""Core module of the cross-module functional fixture: the extensible model."""
from pydantic_modelable import Modelable


class Shelter(Modelable):
    """Extensible shelter model, extended by a sibling module."""
