"""Shared harness for running mypy over code snippets, with or without the plugin.

Each test provides a snippet of code that exercises `pydantic_modelable`, runs
`mypy --strict` over it, and asserts on the resulting diagnostics. Toggling the
plugin lets a single snippet both *reproduce* an error (plugin off) and *verify
the fix* (plugin on).
"""
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from textwrap import dedent

import pytest
from mypy import api

# The runtime library is installed editable in the test env (a PEP 660 import
# hook mypy's own module finder does not follow), so point mypy at its source
# tree directly. In a normal wheel install this is unnecessary.
_REPO_ROOT = Path(__file__).resolve().parents[2]

# Snippets refer to a Modelable subtype defined in the snippet itself; aenum is
# untyped, so it is silenced to keep diagnostics focused on the plugin's domain.
_CONFIG_TEMPLATE = f"""\
[mypy]
strict = True
mypy_path = {_REPO_ROOT}
{{plugins}}
[mypy-aenum.*]
ignore_missing_imports = True
"""


@dataclass
class MypyResult:
    """Outcome of a mypy run over a snippet."""

    output: str
    errors: int
    exit_status: int

    def error_lines(self) -> list[str]:
        """Return only the diagnostic lines flagged as errors."""
        return [line for line in self.output.splitlines() if ': error:' in line]

    def has_error(self, needle: str) -> bool:
        """Whether any error line contains `needle`."""
        return any(needle in line for line in self.error_lines())


RunMypy = Callable[..., MypyResult]


@pytest.fixture
def run_mypy(tmp_path: Path) -> RunMypy:
    """Return a callable running `mypy --strict` over a snippet.

    The callable accepts the snippet source and a `plugin` flag (default
    `True`) selecting whether the `pydantic_modelable_mypy` plugin is enabled.
    """

    def _run(code: str, *, plugin: bool = True) -> MypyResult:
        source = tmp_path / 'snippet.py'
        source.write_text(dedent(code))

        plugins = 'plugins = pydantic_modelable_mypy.plugin' if plugin else ''
        config = tmp_path / 'mypy.ini'
        config.write_text(_CONFIG_TEMPLATE.format(plugins=plugins))

        stdout, _stderr, exit_status = api.run(
            ['--config-file', str(config), '--no-incremental', str(source)],
        )
        errors = sum(1 for line in stdout.splitlines() if ': error:' in line)
        return MypyResult(output=stdout, errors=errors, exit_status=exit_status)

    return _run
