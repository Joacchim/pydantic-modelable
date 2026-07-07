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

## Limitation (`extends_enum` member names)

Enum member access on an unknown name offers no plugin hook, so injected member
names can only be resolved from subtypes discovered during analysis. This is
reliable on **full (non-incremental) runs** (e.g. CI with `mypy` fresh, or
`--no-incremental`). On **incremental / daemon** runs, subtypes served from
cache are not re-analysed, so member-name access (`Palette.red`) may report an
unknown attribute until a clean run. Everything else `ModelableStrEnum` provides
— iteration, membership, construction, `.value` — works in all modes, as does
all of `as_attribute` and `extends_union`.
