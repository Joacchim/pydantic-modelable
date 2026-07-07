"""Extension contributing the `red` swatch."""
from typing import Literal

from enum_core import Swatch


class Red(Swatch):
    """A red swatch."""

    kind: Literal['red'] = 'red'
