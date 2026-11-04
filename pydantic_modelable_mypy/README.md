# pydantic-modelable-mypy

A [mypy](https://mypy-lang.org/) plugin that teaches the type-checker about the
model extensions `pydantic_modelable` performs at runtime.

## Why

`pydantic_modelable` lets a class decorate a *different*, pre-existing model to
add fields, union members or enum values to it. A decorator cannot re-type a
third class in the standard type system, so `mypy --strict` reports the added
fields as unknown attributes. This plugin observes those decorators and injects
the corresponding members into the target model during analysis.

## Usage

Install alongside `pydantic-modelable` and enable the plugin in your mypy
configuration:

```ini
[mypy]
plugins = pydantic_modelable_mypy.plugin
```

## What it covers

- `as_attribute` — the injected field is known for reads and construction.
- `extends_union` — the field is typed as the discriminated union of the base's
  subtypes (reads and construction), including subtypes defined in other
  modules, on full and incremental runs.
- `extends_enum` — the discriminator values injected as enum members are
  resolved by name (`Palette.red`).
- `ModelableForwarder` — decorators applied through a forwarder
  (`@Fwd.as_attribute(...)`) are resolved through the `forwards_to` chain
  (including chained forwarders) to the target `Modelable` and handled as above.

## Limitation (incremental / daemon runs)

`as_attribute` fields and `extends_enum` enum values are *created* on a model
that does not declare them, so mypy can only resolve them once the extension's
injection has run. That happens on **full runs** (e.g. CI, or
`--no-incremental`) but not on **incremental / daemon** runs, where the
extension modules are served from cache and not re-analysed — attribute /
member access then reports an unknown attribute until a clean run. (A pydantic
model exposes no `__getattr__` to type-checkers, by design, so there is no hook
to resolve such a member lazily.)

`extends_union` is unaffected — it retypes a field the model already declares —
as is `ModelableStrEnum`'s enum behaviour (iteration, membership, construction,
`.value`), which all work in every mode.
