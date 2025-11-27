"""Example module using pydantic_modelable to create extensible models."""

from typing import Any

import aenum
from pydantic import BaseModel

from pydantic_modelable import Modelable, ModelableEnumMixin, PluginLoader


class BaseDiscriminated(Modelable, discriminator='mtype'):
    """Example base model to be extended for a discriminated union."""


@BaseDiscriminated.extends_union('item')
class AutoExtensibleContainer(BaseModel):
    """Example model which will contain a discriminated union of the children of BaseDiscriminated."""

    id: int
    # Will be overridden by the extend_union hook
    item: BaseDiscriminated


# Type hinting must be ignored here due to aenum being untyped :(
@BaseDiscriminated.extends_enum
class AutoExtensibleEnum(ModelableEnumMixin, str, aenum.Enum):  # type: ignore
    """Example Enum to be 'redefined' through extending BaseDiscriminated."""


loader = PluginLoader[Any]('core')
loader.load()
