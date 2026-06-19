"""Forwarding proxy for pydantic_modelable.Modelable registration decorators."""

from collections.abc import Callable
from typing import TYPE_CHECKING, Any, ClassVar

import aenum
from pydantic import BaseModel

if TYPE_CHECKING:
    from .model import Modelable


class ModelableForwarder:
    """Forward `Modelable` registration decorators to another `Modelable`.

    A `ModelableForwarder` is a registration proxy: every decorator invoked on
    it is delegated, unchanged, to a target `Modelable`. The target then
    behaves exactly as if it had been decorated directly, so a third-party
    module can register attributes, unions or enums onto a core model it never
    imports, by going through a forwarder instead.

    Bind a forwarder to its target by subclassing with the `forwards_to`
    keyword:
    ```py
    from pydantic import BaseModel
    from pydantic_modelable import Modelable, ModelableForwarder

    class Profile(Modelable):
        ...

    class ExtensionForwarder(ModelableForwarder, forwards_to=Profile):
        ...

    # Lands on `Profile` as if `@Profile.as_attribute('indirect')` was used:
    @ExtensionForwarder.as_attribute('indirect')
    class IndirectExtension(BaseModel):
        ...
    ```

    The target may itself be another `ModelableForwarder`, in which case
    forwarders are chained until a concrete `Modelable` is reached.
    """

    # The Modelable (or further forwarder) every decorator is delegated to.
    __forwards_to__: ClassVar['type[Modelable] | type[ModelableForwarder]']

    def __init_subclass__(
        cls,
        forwards_to: 'type[Modelable] | type[ModelableForwarder]',
        **kwargs: Any,
    ) -> None:
        """Bind the forwarder subclass to its target `Modelable` (or forwarder).

        The `forwards_to` keyword is required: a forwarder with no target has
        nothing to delegate to.
        """
        super().__init_subclass__(**kwargs)
        cls.__forwards_to__ = forwards_to

    @classmethod
    def as_attribute(
        cls,
        attr_name: str,
        optional: bool = False,
        default_factory: Callable[[], BaseModel | None] | None = None,
    ) -> Callable[[type[BaseModel]], type[BaseModel]]:
        """Forward `Modelable.as_attribute` to the target."""
        return cls.__forwards_to__.as_attribute(attr_name, optional, default_factory)

    @classmethod
    def extends_union(cls, attr_name: str) -> Callable[[type[BaseModel]], type[BaseModel]]:
        """Forward `Modelable.extends_union` to the target."""
        return cls.__forwards_to__.extends_union(attr_name)

    @classmethod
    def extends_enum(cls, decorable: type[aenum.Enum]) -> type[aenum.Enum]:
        """Forward `Modelable.extends_enum` to the target."""
        return cls.__forwards_to__.extends_enum(decorable)

    @classmethod
    def rebuilds_model(cls) -> Callable[[type[BaseModel]], type[BaseModel]]:
        """Forward `Modelable.rebuilds_model` to the target."""
        return cls.__forwards_to__.rebuilds_model()
