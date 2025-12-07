# Loading a library's extensions easily

As `pydantic-modelable` aims to facilitate writing an extensible code base, it
is a matter of course that the extensions to this might come in the form of
third-party plugins.

To clarify the terms for this document, we'll call `framework` the module
relying on `pydantic-modelable` to create an extension mechanism. Similarly,
we'll call `extensions` the third-party modules importing the `framework`, and
extending it.

This documentation section will describe how the
`pydantic_modelable.loader.PluginLoader` utlity can be used to quickly setup
automatic loading of the `extensions` for a given `framework`.

## Setting up the PluginLoader

### Example context

To provide a more concrete example, we'll assume our `framework` module is
called `shelter`, adn represents an animal shelter. While various `extensions`
exist for it, we will setup automatic loading of the installed `extensions`,
so that we only need to install them to ensure the `shelter` is effectively
extended at runtime.

The `PluginLoader` class is relatively simple to use, as it merely requires a
loaded item type, and a few initialization parameters, relating to what should
be extended from the `framework` module, as the [API doc](../api/loader.md)
describes it. Note, though, that it stores whatever it loads internally,
enabling us to retrieve these entries and manipulate them as we wish.


### Using the `PluginLoader` class

Thus, we can instanciate our own loader, and invoke its `load()` method to
actually load the installed `extensions`:

```py
from typing import Any
from pydantic_modelable import PluginLoader

# We load full modules, so Any is our best type fit.
loader = PluginLoader[Any](root_module_name='shelter')
loader.load()
```

With that, the `PluginLoader` will load all modules that depend (directly or
indirectly) on the `shelter` module.


### Accessing the loaded `extensions` from the `PluginLoader` object

To facilitate accessing the loaded `extensions` modules, the `PluginLoader`
keeps the loaded references internally. The `loaded` property yields a shallow
copy of the internal loaded objects dictionary, so that one can iterate over
it.

Picking up from our previous example, we could show all loaded `extensions`:

```py
for name, module in loader.loaded:
    print(f'Shelter loaded extension {name}')
```

### Loading an attribute

The `PluginLoader`'s `load_attribute` initialization parameter may be specified
to ensure that we load a specific attribute of the `extension` modules. In that
case, the stored loaded objects are actually the attributes of the loaded
module, and not the `extension` modules themselves.

Of course, this implies that all `extension` modules _MUST_ provide the
specified `attribute`, with the expected type. We'll consider that this
constraint is part of the documentation covered by our `framework` module,
`shelter`.

Additionally, when specifying the `load_attribute`, the `PluginLoader` will
only keep the specified attribute in its loaded object map. Thus, iterating
over those will only yield the desired attribute, and not the whole module.
With this comes the possibility to refine the type hint we used to instanciate
our `PluginLoader` object. Assuming we want to load a type attribute named
`Species`, based on our `shelter`'s module `Animal` type, we could rewrite the
loader instanciation:

```py
from typing import Any
from pydantic_modelable import PluginLoader

from shelter import Animal

# We load full modules, so Any is our best type fit.
loader = PluginLoader[Animal](root_module_name='shelter', load_attribute='Species')
loader.load()
```
