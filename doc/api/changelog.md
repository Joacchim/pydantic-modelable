# Changelog

## In development:

### Fixes:

 - A model holding a `ModelableStrEnum` field can be declared before any
   extension is loaded. It used to fail at class creation with a pydantic
   `SchemaError`. Until the first value exists the field rejects every input,
   and a model rebuilt while the first extension registers still accepts its
   value.
 - The `schema_title` / `schema_description` subclass parameters of
   `ModelableStrEnum` now reach the JSON schema. `aenum` does not forward class
   keywords to `__init_subclass__`, so they were silently ignored. An enum
   spelled out as `(ModelableEnumMixin, str, aenum.Enum)` can set
   `__schema_title__` / `__schema_description__` as class attributes instead.

### Improvements:

 - The registration decorators (`as_attribute`, `extends_union`,
   `extends_enum`, `rebuilds_model`, on both `Modelable` and
   `ModelableForwarder`) are now identity-preserving: the decorated class keeps
   its own type instead of being erased to `type[BaseModel]` /
   `type[aenum.Enum]`, removing the need for `# type: ignore` at decoration
   sites.

### Features:

 - `pydantic-modelable-mypy`, a companion (separately-installed) mypy plugin
   that teaches the type-checker about the runtime extensions: `as_attribute`
   fields, `extends_union` discriminated unions, `extends_enum` enum members,
   and the same through a `ModelableForwarder`. See the Static typing guide.
 - `pydantic_modelable.ModelableStrEnum`, a base class for extensible string
   enums. It is an `aenum`-based str Enum at runtime (extended in place by
   `extends_enum`) but is seen as a standard `enum.Enum` by type-checkers, so
   subclasses are recognised as enums without the `# type: ignore` that
   `aenum`'s untyped base previously required under strict settings.
 - `pydantic_modelable.forwarder.ModelableForwarder`, a registration proxy that
   delegates the `Modelable` decorators (`as_attribute`, `extends_union`,
   `extends_enum`, `rebuilds_model`) to a target `Modelable`, letting a module
   register onto a model it never imports. Forwarders can be chained.

## version 0.1.0:

### Features:

 - `pydantic.BaseModel` extension by allowing to inject new attributes
 - Dynamic extension-based Enums & Discriminated Unions definitions, using
   `pydantic_modelable.model.Modelable` as a base for the extensible model, and
   `pydantic_modelable.mixins.ModelableEnumMixin` as a base for the extensible
   enum type.
 - Ability to load a module's extensions using
   `pydantic_modelable.loader.PluginLoader`.
