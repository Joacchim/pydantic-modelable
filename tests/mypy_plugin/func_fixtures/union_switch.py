"""Extension module contributing the `switch` alternative."""
from typing import Literal

from union_core import Feed


class Switch(Feed):
    """A switch-state alternative of the Feed union."""

    kind: Literal['switch'] = 'switch'
    on: bool = False
