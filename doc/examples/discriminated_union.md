# Defining Extensible pydantic discriminated unions with pydantic-modelable

In a context of `pydantic` validated data, `discriminated unions` is a very
practical feature, allowing to determine a sub-element's type based on one of
its inner values.

The following section shows how `pydantic-modelable` allows extending types to
aggregate extensions under `discriminated unions`.


## Defining an extensible Model in your core project

As an example, we'll define an animal "shelter" project, defining the
"architecture" of the shelter, represented through pydantic Models, extended
using the `pydantic-modelable` module.

As such, we'll define here:
 - A base model `Animal`, which defines the discriminator and can be inherited
   to extend the list of sheltered animals species
 - A container model, using a discriminated union over concrete `Animal`
   species (initial setup may seem invalid, and will be completed by the
   extension mechanism)
 - An `AnimalSpecies` Enum that lists all the available discriminator values
   for `Animal`

```py
import aenum
from typing import Literal

from pydantic_modelable import Modelable, ModelableEnumMixin


# Modelable requires the `discriminator` parameter to be set for its subclass init,
# thus informing it of which field to use as the discriminator for all the models
# it will update for you.
class Animal(Modelable, discriminator='species'):
    # The discriminator value from the base type is not used by Modelable, but
    # will be necessary for typechecking your final code.
    species: Literal['']
    # Add whatever common logic you need here.
    ...


# Use the Modelable decorator to automatically rewrite the `animal` discriminated union
@Animal.extends_union('animal')
class ShelterRoom(BaseModel):
    # Type hint will be overriden with the specification of the discriminated Union
    # by the Animal decorator hook
    animal: Animal


@Animal.extends_enum
class AnimalSpecies(ModelableEnumMixin, str, aenum.Enum):
    ...


class Shelter(BaseModel):
    rooms: list[ShelterRoom|None]
```

| :memo: | You can specify the default-value behavior for discriminated unions using the `discriminator_default_policy` subclass constructor parameter. See the API Documentation for more details.  |
|--------|:------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|

| :memo::exclamation: | Currently, only aenum-based str Enums are supported for the `extends_enum` decorator |
|---------------------|:-------------------------------------------------------------------------------------|

## Using the extensible type in another module or a third party

Now, assuming you are writing a core library to be extended by others, they
will need to use your base type, simply inheriting it for their own specialized
models:

```py
from typing import Literal

from shelter.models import Animal


class Dog(Animal):
    species: Literal['dog'] = 'dog'
```

Then, yet another third-party could provide another animal type:

```py
from typing import Literal

from shelter.models import Animal


class Cat(Animal):
    species: Literal['cat'] = 'cat'
```

## Actual form of the modules (once extensions are loaded)

To use these additional `Animal` definitions your shelter module, one would
only need to load them into python.

| :memo::exclamation: | Currently, `pydantic-modelable` does not offer any way to automatically load the extensions |
|---------------------|:--------------------------------------------------------------------------------------------|

Once the `shelter` is loaded along with the two extensions modules previously
described, the `ShelterRoom` and `AnimalSpecies` models would be equivalent at
runtime to the following "hardcoded-style" definitions (this can be checked by
dumping their json schema, for instance):

```py
from enum import Enom
from pydantic import BaseModel, Field

class ShelterRoom(BaseModel):
    animal: Dog|Cat = Field(discriminator='species')

class AnimalSpecies(str, aenum.Enum):
    dog = 'dog'
    cat = 'cat'
```
