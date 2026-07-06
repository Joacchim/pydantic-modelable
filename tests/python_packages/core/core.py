"""Example module using pydantic_modelable to create extensible models."""

from typing import Any

from pydantic import BaseModel

from pydantic_modelable import Modelable, ModelableStrEnum, PluginLoader


class BaseDiscriminated(Modelable, discriminator='mtype'):
    """Example base model to be extended for a discriminated union."""


@BaseDiscriminated.extends_union('item')
class AutoExtensibleContainer(BaseModel):
    """Example model which will contain a discriminated union of the children of BaseDiscriminated."""

    id: int
    # Will be overridden by the extend_union hook
    item: BaseDiscriminated


@BaseDiscriminated.extends_enum
class AutoExtensibleEnum(ModelableStrEnum):
    """Example Enum to be 'redefined' through extending BaseDiscriminated."""


loader = PluginLoader[Any]('core')
loader.load()
