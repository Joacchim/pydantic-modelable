# pydantic-modelable

A set of utilities around pydantic that allows to create extensible pydantic
models, with little code, in an aim to have models extended by third-party
python code.


## Features

Using `pydantic` for type modelisation and validation has become a very common
practice. That being said, some advanced uses are not natively supported,
although the pydantic types are extremely flexible, such as dynamic
extensibility of the models.

It can be very useful to define extensible models relying on this mechanism,
and `pydantic_modelable`, as it may provide the following benefits:
 - Reduction of code maintenance (defining an "extension" registers it
   automatically wherever the base was setup)
 - Easy extension of a core library's models and features through the loading
   of extension modules
 - Automatically updated Model schemas for inclusion in any schema-based
   tooling or framework (ex: FastAPI's OpenAPI Schema generation tooling)

With a few additional parameters to your model's constructor, inheriting from
`pydantic_modelable.Modelable`, you can thus configure specific behaviors for
your extensible model:
 - discriminated union: `discriminator=attr_name`

You can then register other models into your base model using decorators
embedded into your base model by the `pydantic_modelable.Modelable` class:
 - `extends_enum`
 - `extends_union(dicriminated_union_attr_name: str)`
 - `as_attribute(attr_name: str, optional: bool, default_factory: Callable[[], BaseModel])`


## Static typing

Because the models are altered at runtime, a plain type-checker cannot, on its
own, see the fields, union members or enum values an extension adds.
`pydantic-modelable` closes most of that gap:

 - **Any type-checker.** The registration decorators are identity-preserving —
   decorating a class returns that same class, so its type is never erased. And
   `pydantic_modelable.ModelableStrEnum` is a typed base for extensible string
   enums: inherit it instead of spelling out the `aenum` bases and subclasses
   are understood as ordinary enums, with no `# type: ignore`.
 - **mypy.** Install the companion `pydantic-modelable-mypy` distribution and
   enable its plugin:

   ```ini
   [mypy]
   plugins = pydantic_modelable_mypy.plugin
   ```

   It teaches mypy about the runtime extensions — `as_attribute` fields,
   `extends_union` discriminated unions, `extends_enum` enum members — including
   when they are registered through a `ModelableForwarder`.

### Remaining limitations

 - The plugin is mypy-specific; other checkers (e.g. pyright) see only what the
   "any type-checker" support above provides.
 - Members an extension *creates* on another model — `as_attribute` fields and
   `extends_enum` enum values — resolve on full runs but not on incremental /
   daemon runs (e.g. an editor using the mypy daemon), where the extension
   modules come from cache and a clean run is needed. Such a member must
   physically exist on the target for mypy to resolve it, and the cross-module
   injection that adds it is not replayed from the cache.
 - `extends_union` is *not* affected — it retypes a field the model already
   declares, so it works in every mode, as does `ModelableStrEnum`'s enum
   behaviour (iteration, membership, construction, `.value`).
