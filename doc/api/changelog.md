# Changelog

## In development:

## version 0.1.0:

### Features:

 - `pydantic.BaseModel` extension by allowing to inject new attributes
 - Dynamic extension-based Enums & Discriminated Unions definitions, using
   `pydantic_modelable.model.Modelable` as a base for the extensible model, and
   `pydantic_modelable.mixins.ModelableEnumMixin` as a base for the extensible
   enum type.
 - Ability to load a module's extensions using
   `pydantic_modelable.loader.PluginLoader`.
