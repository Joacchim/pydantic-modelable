"""Core module: an extensible discriminated base and an extensible enum over it.

`Palette`'s members are the discriminator values of `Swatch`'s subtypes, added
at runtime by `extends_enum` and (for full runs) resolved by the plugin.
"""
from pydantic_modelable import Modelable, ModelableStrEnum


class Swatch(Modelable, discriminator='kind'):
    """Extensible discriminated base."""


@Swatch.extends_enum
class Palette(ModelableStrEnum):
    """Enum of every registered Swatch's discriminator value."""
