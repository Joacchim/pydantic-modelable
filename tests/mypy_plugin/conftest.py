"""Shared harness for running mypy over code snippets, with or without the plugin.

Each test provides a snippet of code that exercises `pydantic_modelable`, runs
`mypy --strict` over it, and asserts on the resulting diagnostics. Toggling the
plugin lets a single snippet both *reproduce* an error (plugin off) and *verify
the fix* (plugin on).
"""
import os
import shutil
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

# Multi-module fixture packages for the cross-module functional test.
_FUNC_FIXTURES = Path(__file__).resolve().parent / 'func_fixtures'

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
RunMypyPackage = Callable[..., MypyResult]
RunMypyIncremental = Callable[..., tuple[MypyResult, MypyResult]]


@pytest.fixture
def run_mypy_incremental(tmp_path: Path) -> RunMypyIncremental:
    """Run `mypy` over fixture modules twice, with a persistent cache and an edit between.

    Simulates the incremental / daemon workflow: the first pass populates the
    cache, then `touch` is edited and the second pass reuses the cache for the
    unchanged modules. Each `api.run` builds a fresh plugin instance, so the
    second pass genuinely relies on cache-backed discovery, not the first pass's
    in-memory state. Returns both results.
    """

    def _run(*modules: str, touch: str, plugin: bool = True) -> tuple[MypyResult, MypyResult]:
        for module in modules:
            shutil.copy(_FUNC_FIXTURES / module, tmp_path / module)
        plugins = 'plugins = pydantic_modelable_mypy.plugin' if plugin else ''
        search_path = os.pathsep.join((str(_REPO_ROOT), str(tmp_path)))
        config = tmp_path / 'mypy.ini'
        config.write_text(
            '[mypy]\n'
            'strict = True\n'
            f'mypy_path = {search_path}\n'
            f'cache_dir = {tmp_path / ".mypy_cache"}\n'
            f'{plugins}\n'
            '[mypy-aenum.*]\n'
            'ignore_missing_imports = True\n'
        )
        targets = [str(tmp_path / module) for module in modules]

        def _once() -> MypyResult:
            stdout, _stderr, exit_status = api.run(['--config-file', str(config), *targets])
            errors = sum(1 for line in stdout.splitlines() if ': error:' in line)
            return MypyResult(output=stdout, errors=errors, exit_status=exit_status)

        first = _once()
        touched = tmp_path / touch
        touched.write_text(f'{touched.read_text()}\n# incremental edit\n')
        second = _once()
        return first, second

    return _run


@pytest.fixture
def run_mypy_package(tmp_path: Path) -> RunMypyPackage:
    """Return a callable running `mypy --strict` over cross-module fixture files.

    Named modules are copied out of `func_fixtures/` into an isolated directory
    that belongs to no package, which is placed on `mypy_path` so the fixtures
    import one another by module name (as separately-installed packages would)
    without the surrounding `tests` package shadowing their module paths.
    """

    def _run(*modules: str, plugin: bool = True) -> MypyResult:
        for module in modules:
            shutil.copy(_FUNC_FIXTURES / module, tmp_path / module)
        plugins = 'plugins = pydantic_modelable_mypy.plugin' if plugin else ''
        search_path = os.pathsep.join((str(_REPO_ROOT), str(tmp_path)))
        config = tmp_path / 'mypy.ini'
        config.write_text(
            '[mypy]\n'
            'strict = True\n'
            f'mypy_path = {search_path}\n'
            f'{plugins}\n'
            '[mypy-aenum.*]\n'
            'ignore_missing_imports = True\n'
        )
        targets = [str(tmp_path / module) for module in modules]
        stdout, _stderr, exit_status = api.run(
            ['--config-file', str(config), '--no-incremental', *targets],
        )
        errors = sum(1 for line in stdout.splitlines() if ': error:' in line)
        return MypyResult(output=stdout, errors=errors, exit_status=exit_status)

    return _run


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
