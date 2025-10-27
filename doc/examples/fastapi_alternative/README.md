# Injecting an alternative into a discriminated union

## Special case of a pydantic-based API framework: FastAPI

### Injecting a FastAPI-compatible model into a Discriminated union

In the core service you want to make extensible:

```py
from pydantic import BaseModel
import pydantic_modelable as modelable


class ThingBase(
    BaseModel,
    metaclass=modelable.Modelable,
    discriminator='my_discriminator',
):
    """Base class for all `Thing` models.

    Implementing any `Thing` model by inheriting this base will automatically
    register it as a fully-featured "Thing", with its discriminator value
    registered in all relevant FastAPI models.
    """
    # Default value, automatically removed upon initializing first subclass
    my_discriminator: Literal['none']
    ...


class ThingContainer(BaseModel):
    """A Pydantic-based model, for use in FastAPI

    It contains an 'item' field, which is in reality a DiscriminatedUnion,
    where all items are children classes of `ThingBase`.

    The way it is currently written only shows the "invalid default", which
    will be overwritten by pydantic_modelable, upon loading any of the children
    classes of `ThingBase`. As such, the final model, once every extension is
    loaded, will include all extensions of the `ThingBase` as discriminated
    alternatives for the `item` field.
    """
    @ThingBase.discriminated_union
    item: Union[ThingBase]
    ...
```

In any extending module:

```py
from core import ThingBase


class AwesomeThing(ThingBase):
    my_discriminator: Literal['awesome']
    ...


class ShinyThing(ThingBase):
    my_discriminator: Literal['shiny']
    ...
```

Then, you need to make sure that your core service loads its extensions. Either
you can handle manually, or you can use an utility from `pydantic_modelable`,
which inspects installed python modules, and loads the ones that depend on your
core module:

```py
from pydantic_modelable import load_dependencies

# Imports for your core service

if __name__ == "__main__":
    load_dependencies('core-service')
    main()
```

### Updating an extensible Enum for precision on the OpenAPI specification

Reusing our earlier example, the `pydantic_modelable.Modelable` metaclass,
along with an extensible enum model provide the way to have an Enum being
defined by loaded Modelable items:

```py
import pydantic_modelable as modelable

from code.models import ThingBase

@ThingBase.discriminator_enum
class DiscriminatorEnum(modelable.StrEnum):
    """StrEnum that will hold all the valid, loaded values for any model based on `ThingBase`

    This enum can be used in any API model that could benefit from fully
    specifying available discriminator values for `Thing` models.
    """
```
