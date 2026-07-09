"""Extension module contributing the `temperature` alternative."""
from typing import Literal

from union_core import Feed


class Temperature(Feed):
    """A temperature reading alternative of the Feed union."""

    kind: Literal['temperature'] = 'temperature'
    celsius: float = 0.0
