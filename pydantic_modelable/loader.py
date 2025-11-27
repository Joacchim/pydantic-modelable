"""Extension loading utilities, to support pydantic_modelable usage."""

from collections.abc import Mapping
from importlib.metadata import (  # type: ignore
    PackageNotFoundError,
    import_module,
    packages_distributions,
    requires,
)
from typing import Generic, TypeVar, cast

LoadedEntry = TypeVar('LoadedEntry')


class PluginLoader(Generic[LoadedEntry]):
    """A Python package dynamic loader utility, tracking what modules where loaded.

    The PluginLoader class is generic to allow enforcing type-hints over the
    loaded modules or attributes.
    It keeps a dict of the loaded modules, to facilitate various uses:
     - generic usage of the loaded modules/module-attributes
     - debugging purposes

    The provided type should ideally be a typing.Protocol based type, ensuring
    the loaded modules and/or attributes are loosely tied to the type-hint.
    """

    def __init__(self, root_module_name: str = 'pydantic-modelable', load_attribute: str|None = None) -> None:
        """Instanciate and Configure a PluginLoader object.

        root_module_name: Optional name of the python module to load dependants
                          for. Defaults to pydantic_modelable.
        load_attribute: Optional attribute name, for situations where the
                        wanted item is an attribute of the module, and not the
                        whole module.
        depend_on: Name of the module we're looking up the dependants for
        """
        self._depend_on = root_module_name
        self._load_attr = load_attribute
        self._plugins: dict[str, LoadedEntry] = {}

    def __str__(self) -> str:
        """Represent the PluginLoader as a string."""
        return f'{self.__class__.__name__}<load_attribute={self._load_attr},{",".join(self._plugins.keys())}>'

    def _load_modules(self, module_names: list[str]) -> None:
        """Load a list of modules fomr their names, to record them into the object's state."""
        for name in module_names:
            # Import them, an record their `.cli_root` attribute as the subcommand_object
            module = import_module(name)
            self._plugins[name] = cast(
                LoadedEntry,
                module if self._load_attr is None else getattr(module, self._load_attr),
            )

    @staticmethod
    def _find_dependants(pkg_dist: Mapping[str, list[str]], pkg_name: str) -> list[str]:
        reqs = []
        try:
            reqs = requires(pkg_name) or []
        except PackageNotFoundError:
            reqs = [
                d for dep in pkg_dist[pkg_name]
                for d in PluginLoader._find_dependants(pkg_dist, dep)
            ]
        return reqs

    def _lookup_dependants(self) -> list[str]:
        """Return the list of module names of the python packages depending on `depend_on`."""
        # Keep all forms of names to hint the dependency
        # (since dashes and underscores are interchangeable in pypi package names)
        dependency_names = {
            self._depend_on,
            self._depend_on.replace('-', '_'),
            self._depend_on.replace('_', '-'),
        }
        packages = packages_distributions()
        dependants = [
            package_name
            for package_name in packages
            # Find those that depend, directly or indirectly on the specified module
            if any(
                any(spec.startswith(name) for name in dependency_names)
                for spec in self._find_dependants(packages, package_name)
            )
        ]

        return dependants

    def load(self) -> None:
        """Load all the modules depending (directly or indirectly) on `depend_on`."""
        self._load_modules(self._lookup_dependants())

    def loaded(self) -> dict[str, LoadedEntry]:
        """Return a shallow copy of the loaded modules dict.

        The shallow copy aims to reduce risk of the calling code altering the
        object's internal state.
        """
        return dict(self._plugins.items())
