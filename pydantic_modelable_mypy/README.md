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
