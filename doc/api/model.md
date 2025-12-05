# Models

::: pydantic_modelable.model.DefaultDiscriminatorPolicy
    handler: python
    options:
      members:
        - NONE
        - FIRST_REGISTERED
        - LAST_REGISTERED
        - PREDETERMINED
      show_root_heading: true
      show_source: false

::: pydantic_modelable.model.Modelable
    handler: python
    options:
      members:
        - extends_enum
        - extends_union
        - as_attribute
      show_root_heading: true
      show_source: false
