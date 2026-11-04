# Static typing

`pydantic-modelable` alters pydantic models at runtime: an extension adds a
field, a discriminated-union alternative, or an enum value to a model it does
not own. The static type system has no way to express a decorator on one class
re-typing a *different*, pre-existing class, so a plain type-checker reports the
added members as unknown attributes.

Two layers address this.

## Any type-checker

These work with any PEP 561 type-checker, without extra tooling:

- **Identity-preserving decorators.** `as_attribute`, `extends_union`,
  `extends_enum` and `rebuilds_model` return the class they decorate unchanged,
  so the decorated class keeps its own type (no erasure to `type[BaseModel]`).
- **`ModelableStrEnum`.** Inherit `pydantic_modelable.ModelableStrEnum` for an
  extensible string enum instead of spelling out `(ModelableEnumMixin, str,
  aenum.Enum)`. It is the `aenum`-based enum at runtime but is seen as a
  standard `enum.Enum` by type-checkers, so subclasses are understood as enums
  — iterable, constructible, membership-testable — with no `# type: ignore`.

```py
from pydantic_modelable import Modelable, ModelableStrEnum


class Animal(Modelable, discriminator='species'):
    ...


@Animal.extends_enum
class Species(ModelableStrEnum):
    ...
```

## mypy plugin

The runtime extensions of the *models* themselves (the fields and union members
an extension injects into another model) are understood by mypy through the
companion `pydantic-modelable-mypy` distribution.

Install it alongside `pydantic-modelable` and enable the plugin:

```ini
[mypy]
plugins = pydantic_modelable_mypy.plugin
```

It covers:

- `as_attribute` — the injected field is known for both attribute access and
  construction (as a keyword argument, required unless a `default_factory` is
  given).
- `extends_union` — the field is typed as the discriminated union of the base's
  subtypes (reads and construction), including subtypes declared in other
  modules, on full and incremental runs.
- `extends_enum` — the discriminator values injected as enum members are
  resolved by name (`Species.dog`).
- `ModelableForwarder` — a decorator applied through a forwarder is resolved
  through the `forwards_to` chain (including chained forwarders) to the target
  `Modelable` and handled as above.

## Remaining limitations

- The plugin is **mypy-specific**. Other checkers (e.g. pyright) benefit only
  from the "any type-checker" layer above.
- Members an extension **creates** on another model — `as_attribute` fields and
  `extends_enum` enum values (`Species.dog`) — resolve on full runs but not on
  incremental / daemon runs (e.g. an editor using the mypy daemon), where the
  extension modules are served from cache and a clean run is needed. This is
  inherent: such a member must physically *exist* on the target for mypy to
  resolve it (pydantic models expose no `__getattr__` to type-checkers, by
  design, so there is no hook to resolve it lazily), and the cross-module
  injection that adds it is not replayed from the cache.
- `extends_union` is **not** affected: it retypes a field the model already
  declares, which mypy always sees, so it works in every mode — as does
  `ModelableStrEnum`'s enum behaviour (iteration, membership, construction,
  `.value`).
