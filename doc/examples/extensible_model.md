# Defining Extensible models with pydantic-modelable

The general usage of pydantic is to use the `pydantic.BaseModel` to represent
some structured data. One common use within this category could be the
representation of a Configuration file's internal structure and fields,
thus expressing the expected data. This can be used for this, though this
documents take a more general approach in what it will describe.

The following shows how `pydantic-modelable` allows defining a model that can
be extended by third-party code, in order to build, dynamically a complete
model that includes late additions.

## Defining an extensible Model in your core project

As an example, we'll define an animal "shelter" project, defining the
"architecture" of the shelter, represented through an extensible pydantic
Model, using the `pydantic-modelable` module.

As such, we'll define a base model `Shelter`, which defines the basic
facilities available in the shelter:
 - An administrative office to welcome visitors
 - A `Sheltered` submodel, describing the various available wings, dedicated to
   specific animals

```py
from pydantic import BaseModel
from pydantic_modelable import Modelable


class GeneralSection(BaseModel):
    species: str
    capacity: int
    occupants: int


class Sections(Modelable):
    dogs: GeneralSection


class AdministrativeOffice(BaseModel):
    ...

class Shelter(Modelable):
    admin_office: AdministrativeOffice = AdministrativeOffice()
    sections: Sections
```

| :memo: | Nothing prevents us from defining multiple extensible models, based on what we want to allow extensions for |
|--------|:------------------------------------------------------------------------------------------------------------|


## Using the extensible type in another module or a third party

As we've defined two extensible models, we'll be defining two extensions, one
for each "feature" addition.

### Adding facilities to the Shelter

For this first extension, we want to add some new facility to the Shelter: a
Welcome desk to offer a pleasant entry point for visitors willing to adopt one
of the sheltered animals.

The first step is to import the shelter's initial model, and make use of the
`Modelable`'s `as_attribute` decorator to decorate your extension's model:

```py
from pydantic import BaseModel
from shelter import Shelter

class Worker(BaseModel):
    name: str

@Shelter.as_attribute('welcome_desk')
class WelcomeDesk(BaseModel):
    worker: Worker
    office_hours: list[tuple[int,int]]
```

By decorating our `WelcomeDesk` as the example shows, it will be added into the
`Shelter` model under the attrbute name `welcome_desk`, thus extending the
model, along with all the related pydantic facilities (schemas, validators,
etc).

| :memo: | The `as_attribute` decorator offers multiple parameters to tune the behavior of the registered attribute |
|--------|:---------------------------------------------------------------------------------------------------------|


### Adding a new Section to the shelter

As a second extension, we will be adding a new animal section to the shelter: A
`cats` section.

Very similarly to the previous extension, we'll import the `Sections` model,
and use it to decorate our new one. That being said, the `shelter` module
already offers some basic common general definition of a section, so we might
want to reuse it:

```py
from pydantic import BaseModel
from shelter import GeneralSection, Sections


@Sections.as_attribute(
    'cats',
    default_factory=lambda: CatsSection(species='cats', capacity=40, occupants=5, caretaker='James'),
)
class CatsSection(GeneralSection):
    caretaker: str
```

Here, we've defined a default_factory to ensure that by default, the new
`CatsSection` will be instanciated with specific values, as any default value
would do by declaring them in front of the attribute declaration.

## Actual form of the modules (once extensions are loaded)

With the shelter module loaded, along with both extensions, the original
`Shelter` and `Sections` models would be altered to look as if we'd written the
following, in a single module:

```py
from pydantic import BaseModel
from pydantic_modelable import Modelable


class GeneralSection(BaseModel):
    species: str
    capacity: int
    occupants: int


class CatsSection(GeneralSection):
    caretaker: str


class Sections(Modelable):
    dogs: GeneralSection
    cats: CatsSection = CatsSection(species='cats', capacity=40, occupants=5, caretaker='James')


class AdministrativeOffice(BaseModel):
    ...


class Worker(BaseModel):
    name: str


class WelcomeDesk(BaseModel):
    worker: Worker
    office_hours: list[tuple[int,int]]


class Shelter(Modelable):
    admin_office: AdministrativeOffice = AdministrativeOffice()
    sections: Sections
    welcome_desk: WelcomeDesk
```
