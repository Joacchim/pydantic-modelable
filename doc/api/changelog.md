# Changelog

## In development:

### Features:

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
