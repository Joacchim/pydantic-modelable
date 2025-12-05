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


## Limitations

As pydantic-modelable relies on altering the pydantic models at runtime, the
type-checking tools are usually not able to understand that the model was
extended and its type signature was changed. This, sadly, often leads to an
extensive use of `#type: ignore` directives in the code relating to the use
of the extended models.
