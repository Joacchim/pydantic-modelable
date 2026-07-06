# Changelog

## In development:

### Improvements:

 - The registration decorators (`as_attribute`, `extends_union`,
   `extends_enum`, `rebuilds_model`, on both `Modelable` and
   `ModelableForwarder`) are now identity-preserving: the decorated class keeps
   its own type instead of being erased to `type[BaseModel]` /
   `type[aenum.Enum]`, removing the need for `# type: ignore` at decoration
   sites.

### Features:

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
