"""A mypy plugin for pydantic-modelable.

`pydantic_modelable` extends pydantic models at runtime: decorating a class
with `Modelable.as_attribute`, `extends_union` or `extends_enum` mutates a
*different*, pre-existing model. The static type system cannot express such a
cross-class mutation, so `mypy --strict` reports the extended fields as unknown
attributes.

This package ships a mypy plugin that observes those decorators during analysis
and teaches the type-checker about the fields they add to the target model.

Enable it in your mypy configuration:

```ini
[mypy]
plugins = pydantic_modelable_mypy.plugin
```
"""

from .plugin import ModelablePlugin, plugin

__all__ = [
    'ModelablePlugin',
    'plugin',
]
