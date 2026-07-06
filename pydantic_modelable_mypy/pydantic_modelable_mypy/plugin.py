"""The mypy plugin entrypoint for pydantic-modelable.

The plugin is intentionally introduced as a no-op skeleton: it registers a
valid mypy entrypoint but installs no hooks yet. Each class of typing error
raised by `pydantic_modelable`'s runtime model extension is then addressed
iteratively, one hook at a time, each backed by a reproduction test.
"""

from mypy.plugin import Plugin


class ModelablePlugin(Plugin):
    """Teach mypy about the models `pydantic_modelable` extends at runtime.

    No hooks are wired yet; capabilities are added incrementally, each paired
    with a test that first reproduces the error the hook is meant to fix.
    """


def plugin(version: str) -> type[Plugin]:
    """Return the plugin class for mypy to instantiate.

    This is the entrypoint mypy looks up from the `plugins` configuration key.
    The `version` argument is mypy's own version string, which a plugin may use
    to guard against incompatible internal APIs.
    """
    return ModelablePlugin
