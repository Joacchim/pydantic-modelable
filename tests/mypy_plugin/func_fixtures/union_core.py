"""Core module: an extensible discriminated-union base and its container.

`Feed` is the extensible base; `Envelope.payload` is rewritten into a
discriminated union of `Feed`'s subtypes, which live in sibling modules.
"""
from pydantic import BaseModel

from pydantic_modelable import Modelable


class Feed(Modelable, discriminator='kind'):
    """Extensible discriminated base, extended by sibling modules."""


@Feed.extends_union('payload')
class Envelope(BaseModel):
    """Container whose `payload` becomes a discriminated union of Feed subtypes."""

    seq: int
    payload: Feed
