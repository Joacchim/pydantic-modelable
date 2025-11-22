"""Example module of an discriminated union extension of a core module relying on pydantic_modelable."""

from typing import Literal

from core import BaseDiscriminated


class ExtensionTwo(BaseDiscriminated):
    """Example extension of an extensible discriminated union."""

    mtype: Literal['two'] = 'two'
    value: int = 34
