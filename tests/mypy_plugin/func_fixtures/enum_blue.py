"""Extension contributing the `blue` swatch."""
from typing import Literal

from enum_core import Swatch


class Blue(Swatch):
    """A blue swatch."""

    kind: Literal['blue'] = 'blue'
