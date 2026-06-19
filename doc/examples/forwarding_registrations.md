# Forwarding registrations to another Modelable

The `Modelable` decorators (`as_attribute`, `extends_union`, `extends_enum`,
`rebuilds_model`) all act on the `Modelable` subclass they are called on. To
use them, the registering code must import that target model directly.

A `ModelableForwarder` lifts that requirement. It is a registration proxy:
every decorator invoked on it is delegated, unchanged, to a target `Modelable`,
so the target behaves exactly as if it had been decorated directly. This lets
a module register onto a core model it never imports, by going through a
forwarder that sits closer to it in the dependency graph.

## Defining an extensible Model in your core project

Picking up the animal "shelter" project from the other How-Tos, we'll start
with a `shelter` module exposing a `Shelter` model to be extended:

```py
from pydantic_modelable import Modelable


class Shelter(Modelable):
    ...
```

## Exposing a forwarder from an extension

We'll now write a `clinic` extension, importing the `shelter` module to add a
veterinary `Clinic` facility to the `Shelter`. On top of that, the `clinic`
extension wants to let further extensions attach their own equipment to the
`Shelter`, **without forcing them to depend on the core `shelter` module**. To
that end, it exposes a forwarder bound to `Shelter`:

```py
from pydantic import BaseModel
from pydantic_modelable import ModelableForwarder
from shelter import Shelter


@Shelter.as_attribute('clinic')
class Clinic(BaseModel):
    veterinary: str


class ClinicForwarder(ModelableForwarder, forwards_to=Shelter):
    ...
```

## Registering through the forwarder from a third party

A further `xray` extension can now equip the shelter with an imaging room. It
only depends on the `clinic` extension, and never imports the core `shelter`
module. Decorating through `ClinicForwarder` lands the field on `Shelter` just
as if `Shelter.as_attribute` had been used:

```py
from pydantic import BaseModel
from clinic import ClinicForwarder


@ClinicForwarder.as_attribute('xray')
class XRayRoom(BaseModel):
    model: str
```

| :memo: | The same holds for `extends_union`, `extends_enum` and `rebuilds_model`: the forwarder exposes the full `Modelable` registration surface. |
|--------|:----------------------------------------------------------------------------------------------------------------------------------------|

## Chaining forwarders

A forwarder's `forwards_to` target may itself be another `ModelableForwarder`.
Registrations are then delegated down the chain until a concrete `Modelable` is
reached, so each intermediate layer can expose its own forwarder without
knowing the final target:

```py
class ClinicForwarder(ModelableForwarder, forwards_to=Shelter):
    ...


class ImagingForwarder(ModelableForwarder, forwards_to=ClinicForwarder):
    ...


# Still lands on `Shelter`:
@ImagingForwarder.as_attribute('xray')
class XRayRoom(BaseModel):
    model: str
```

## Actual form of the modules (once extensions are loaded)

Once the `shelter` module is loaded along with both the `clinic` and `xray`
extensions, the `Shelter` model would be equivalent at runtime to the following
"hardcoded-style" definition:

```py
from pydantic import BaseModel
from pydantic_modelable import Modelable


class Clinic(BaseModel):
    veterinary: str


class XRayRoom(BaseModel):
    model: str


class Shelter(Modelable):
    clinic: Clinic
    xray: XRayRoom
```
