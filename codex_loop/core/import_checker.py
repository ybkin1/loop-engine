"""
AST-based import scanner for import真实性校验 (Import Authenticity Verification).

Scans all .py files in specified directories, extracts import statements,
and cross-references them against declared dependencies to detect
undeclared third-party imports (C9-import-not-declared).

Part of the Loop Core Hard Constraints system (C9).
"""
from __future__ import annotations

import ast
import logging
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)

# ── Stdlib module name set ─────────────────────────────────────────────────
# Use Python's built-in sys.stdlib_module_names (available 3.10+) for exact
# accuracy, with a minimal fallback for older Python versions.
try:
    _STDLIB_MODULES: frozenset[str] = sys.stdlib_module_names  # type: ignore[attr-defined]
except AttributeError:
    # Fallback: core modules present since Python 3.10
    _STDLIB_MODULES = frozenset({
        "abc", "aifc", "argparse", "array", "ast", "asynchat", "asyncio",
        "asyncore", "atexit", "audioop", "base64", "bdb", "binascii", "binhex",
        "bisect", "builtins", "bz2", "calendar", "cgi", "cgitb", "chunk", "cmath",
        "cmd", "code", "codecs", "codeop", "collections", "colorsys", "compileall",
        "concurrent", "configparser", "contextlib", "contextvars", "copy", "copyreg",
        "cProfile", "crypt", "csv", "ctypes", "curses", "dataclasses", "datetime",
        "dbm", "decimal", "difflib", "dis", "distutils", "doctest", "email",
        "encodings", "enum", "errno", "faulthandler", "fcntl", "filecmp",
        "fileinput", "fnmatch", "fractions", "ftplib", "functools", "gc", "getopt",
        "getpass", "gettext", "glob", "graphlib", "grp", "gzip", "hashlib",
        "heapq", "hmac", "html", "http", "idlelib", "imaplib", "imghdr", "imp",
        "importlib", "inspect", "io", "ipaddress", "itertools", "json", "keyword",
        "lib2to3", "linecache", "locale", "logging", "lzma", "mailbox", "mailcap",
        "marshal", "math", "mimetypes", "mmap", "modulefinder", "multiprocessing",
        "netrc", "nis", "nntplib", "numbers", "operator", "optparse", "os",
        "ossaudiodev", "pathlib", "pdb", "pickle", "pickletools", "pipes", "pkgutil",
        "platform", "plistlib", "poplib", "posix", "posixpath", "pprint", "profile",
        "pstats", "pty", "pwd", "py_compile", "pyclbr", "pydoc", "queue", "quopri",
        "random", "re", "readline", "reprlib", "resource", "rlcompleter", "runpy",
        "sched", "secrets", "select", "selectors", "shelve", "shlex", "shutil",
        "signal", "site", "smtpd", "smtplib", "sndhdr", "socket", "socketserver",
        "sqlite3", "ssl", "stat", "statistics", "string", "stringprep", "struct",
        "subprocess", "sunau", "symtable", "sys", "sysconfig", "syslog", "tabnanny",
        "tarfile", "telnetlib", "tempfile", "termios", "test", "textwrap",
        "threading", "time", "timeit", "tkinter", "token", "tokenize", "trace",
        "traceback", "tracemalloc", "tty", "turtle", "turtledemo", "types",
        "typing", "unicodedata", "unittest", "urllib", "uu", "uuid", "venv",
        "warnings", "wave", "weakref", "webbrowser", "winreg", "winsound", "wsgiref",
        "xdrlib", "xml", "xmlrpc", "zipapp", "zipfile", "zipimport", "zlib",
        "_thread", "__future__", "__main__",
    })


# ── Data Classes ────────────────────────────────────────────────────────────


@dataclass
class ImportViolation:
    """A single import that is not present in declared dependencies.

    Attributes:
        file_path: Absolute or relative path to the .py file containing the import.
        line_number: 1-based line number of the import statement.
        import_name: The full dotted import name (e.g., 'numpy.linalg').
        declared: Whether the top-level package was found in declared dependencies.
        is_stdlib: Whether the top-level module is in the Python standard library.
        is_relative: Whether this is a relative import (always valid).
    """
    file_path: str
    line_number: int
    import_name: str
    declared: bool = False
    is_stdlib: bool = False
    is_relative: bool = False


@dataclass
class ImportCheckResult:
    """Aggregate result of import validation.

    Attributes:
        violations: All ImportViolation objects found (undeclared third-party imports).
        total_files_scanned: Number of .py files that were scanned.
        total_imports_checked: Total number of import statements evaluated.
        warnings: Advisory messages (e.g., missing dependency files).
    """
    violations: list[ImportViolation] = field(default_factory=list)
    total_files_scanned: int = 0
    total_imports_checked: int = 0
    warnings: list[str] = field(default_factory=list)


# ── ImportChecker ───────────────────────────────────────────────────────────


class ImportChecker:
    """AST-based scanner that validates imports against declared dependencies.

    Cross-references every ``import X`` and ``from X import Y`` statement
    in project source files against dependency declarations found in
    ``pyproject.toml`` and ``requirements.txt``.

    Rules:
        - Stdlib imports (os, sys, pathlib, …) are always valid.
        - Relative imports (``from .module import X``) are always valid.
        - Project-local imports (top-level matches a directory in scan_paths)
          are always valid.
        - All other third-party imports MUST appear in declared dependencies.

    Usage::

        checker = ImportChecker()
        result = checker.check_directory(
            root=Path("/project"),
            scan_paths=[Path("/project/src")],
        )
        for v in result.violations:
            print(f"{v.file_path}:{v.line_number} — {v.import_name} undeclared")
    """

    # ── Dependency Collection ────────────────────────────────────────────

    @staticmethod
    def _parse_dependencies_from_pyproject(pyproject_path: Path) -> set[str]:
        """Extract dependency package names from a PEP 621 pyproject.toml.

        Tries tomllib (3.11+), then tomli (backport), then falls back to a
        simple line-based parser for the ``[project]`` dependencies table.
        Returns a set of normalized (lowercase) package names.
        """
        deps: set[str] = set()

        # Strategy 1: Use a proper TOML parser if available
        toml_data = ImportChecker._load_toml(pyproject_path)
        if toml_data is not None:
            try:
                project = toml_data.get("project", {}) if isinstance(toml_data, dict) else {}

                # Core dependencies: "pkg>=1.0" -> "pkg"
                for dep_line in project.get("dependencies", []):
                    name = ImportChecker._extract_package_name(dep_line)
                    if name:
                        deps.add(name)

                # Optional dependency groups
                opt_deps = project.get("optional-dependencies", {})
                if isinstance(opt_deps, dict):
                    for _group, dep_list in opt_deps.items():
                        if isinstance(dep_list, list):
                            for dep_line in dep_list:
                                name = ImportChecker._extract_package_name(dep_line)
                                if name:
                                    deps.add(name)

                # Build-system requires
                build = toml_data.get("build-system", {})
                if isinstance(build, dict):
                    for dep_line in build.get("requires", []):
                        name = ImportChecker._extract_package_name(dep_line)
                        if name:
                            deps.add(name)

                return deps
            except Exception:
                logger.debug("Error traversing TOML data from %s", pyproject_path, exc_info=True)

        return deps

    @staticmethod
    def _load_toml(path: Path) -> dict | None:
        """Load a TOML file using the best available parser.

        Returns None if no parser is available or parsing fails.
        """
        try:
            import tomllib  # Python 3.11+
            with open(path, "rb") as f:
                return tomllib.load(f)
        except (ImportError, FileNotFoundError):
            pass

        try:
            import tomli  # Backport
            with open(path, "rb") as f:
                return tomli.load(f)
        except (ImportError, FileNotFoundError):
            pass

        return None

    @staticmethod
    def _parse_dependencies_from_requirements(requirements_path: Path) -> set[str]:
        """Extract dependency package names from a pip requirements.txt file.

        Handles:
            - Plain packages: ``PyYAML>=6.0``
            - Comments: ``# this is a comment``
            - Options: ``-r other.txt``, ``--index-url ...``
            - Extras: ``pkg[extra]>=1.0``
        """
        deps: set[str] = set()
        try:
            with open(requirements_path, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    # Skip empty, comments, and pip options
                    if not line or line.startswith("#") or line.startswith("-"):
                        continue
                    name = ImportChecker._extract_package_name(line)
                    if name:
                        deps.add(name)
        except FileNotFoundError:
            pass
        except Exception:
            logger.debug("Failed to parse requirements.txt", exc_info=True)

        return deps

    @staticmethod
    def _extract_package_name(dep_line: str) -> str | None:
        """Extract the package name from a PEP 508 dependency specification.

        Examples:
            ``"PyYAML>=6.0"`` -> ``"pyyaml"``
            ``"pytest-cov>=4.0"`` -> ``"pytest-cov"``
            ``"mypy>=1.0; python_version>='3.10'"`` -> ``"mypy"``
            ``"requests[security]>=2.28"`` -> ``"requests"``
        """
        dep_line = dep_line.strip()
        if not dep_line:
            return None

        # Match a valid package name: starts with letter/digit, contains
        # letters, digits, dots, hyphens, underscores. Stop at the first
        # character that cannot be part of a package name (space, operator,
        # semicolon, bracket, comma).
        match = re.match(r'^([a-zA-Z0-9][a-zA-Z0-9._-]*)', dep_line)
        if match:
            return match.group(1).lower()
        return None

    @staticmethod
    def _collect_declared_deps(root: Path) -> set[str]:
        """Collect all declared dependencies from pyproject.toml and requirements.txt."""
        root = Path(root)
        deps: set[str] = set()

        pyproject = root / "pyproject.toml"
        if pyproject.exists():
            deps.update(ImportChecker._parse_dependencies_from_pyproject(pyproject))

        requirements = root / "requirements.txt"
        if requirements.exists():
            deps.update(ImportChecker._parse_dependencies_from_requirements(requirements))

        return deps

    # ── Module Classification ────────────────────────────────────────────

    @staticmethod
    def _get_top_level_module(import_name: str) -> str:
        """Return the top-level module name from a dotted import.

        Examples:
            ``"os.path"`` -> ``"os"``
            ``"loop_core.hard_constraints"`` -> ``"loop_core"``
            ``"yaml"`` -> ``"yaml"``
        """
        return import_name.split(".")[0]

    @staticmethod
    def _is_stdlib_module(module_name: str) -> bool:
        """Check if a top-level module name is in the Python standard library."""
        return module_name in _STDLIB_MODULES

    @staticmethod
    def _is_project_local_module(
        top_level_name: str, root: Path, scan_paths: list[Path],
    ) -> bool:
        """Check if a top-level module name corresponds to a local project package.

        A module is considered project-local if any of these exist directly
        under the project root or a scan path:
            - ``<name>/`` directory (with or without __init__.py)
            - ``<name>.py`` file
        """
        # Normalize to match file-system names
        normalized = top_level_name.lower()

        def _exists_as_local(base: Path) -> bool:
            # Check as a package directory (namespace or regular)
            pkg_dir = base / top_level_name
            if pkg_dir.is_dir():
                # Has __init__.py or is a namespace package with any .py files
                if (pkg_dir / "__init__.py").exists():
                    return True
                # Check if it's a namespace package (has any .py file inside)
                for _child in pkg_dir.iterdir():
                    if _child.suffix == ".py":
                        return True
                    if _child.is_dir() and not _child.name.startswith("."):
                        return True  # nested package, likely a real package
                return False
            # Check as a single-file module
            mod_file = base / f"{top_level_name}.py"
            if mod_file.is_file():
                return True
            return False

        # Also try lowercase variants (some packages differ in case)
        def _exists_as_local_lower(base: Path) -> bool:
            if _exists_as_local(base):
                return True
            # Try case-insensitive match
            try:
                for child in base.iterdir():
                    if child.name.lower() == normalized:
                        if child.is_dir():
                            return True
                        if child.is_file() and child.suffix == ".py":
                            return True
            except OSError:
                pass
            return False

        for scan_path in scan_paths:
            if _exists_as_local_lower(scan_path):
                return True

        # Also check root
        if _exists_as_local_lower(root):
            return True

        return False

    # ── File Scanning ────────────────────────────────────────────────────

    @staticmethod
    def _scan_file(
        file_path: Path,
        declared_deps: set[str],
        root: Path,
        scan_paths: list[Path],
    ) -> tuple[list[ImportViolation], int]:
        """Scan a single Python file for import violations.

        Returns:
            Tuple of (violations, total_imports_checked).
        """
        violations: list[ImportViolation] = []
        imports_checked = 0

        try:
            with open(file_path, encoding="utf-8") as f:
                source = f.read()
        except (OSError, UnicodeDecodeError):
            return violations, 0

        try:
            tree = ast.parse(source, filename=str(file_path))
        except SyntaxError:
            return violations, 0

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports_checked += 1
                    name = alias.name
                    top_level = ImportChecker._get_top_level_module(name)

                    # Relative imports via `import .name` — extremely rare, skip
                    if name.startswith("."):
                        continue

                    # Stdlib imports are always valid
                    if ImportChecker._is_stdlib_module(top_level):
                        continue

                    # Project-local imports are always valid
                    if ImportChecker._is_project_local_module(top_level, root, scan_paths):
                        continue

                    # Check against declared dependencies (case-insensitive)
                    declared = top_level.lower() in declared_deps
                    if not declared:
                        violations.append(ImportViolation(
                            file_path=str(file_path),
                            line_number=node.lineno,
                            import_name=name,
                            declared=False,
                            is_stdlib=False,
                            is_relative=False,
                        ))

            elif isinstance(node, ast.ImportFrom):
                module = node.module

                # Relative imports (from . import X, from ..sibling import Y)
                if module is None or module.startswith("."):
                    continue  # always valid

                imports_checked += 1
                top_level = ImportChecker._get_top_level_module(module)

                # Stdlib imports are always valid
                if ImportChecker._is_stdlib_module(top_level):
                    continue

                # Project-local imports are always valid
                if ImportChecker._is_project_local_module(top_level, root, scan_paths):
                    continue

                # Check against declared dependencies (case-insensitive)
                declared = top_level.lower() in declared_deps
                if not declared:
                    violations.append(ImportViolation(
                        file_path=str(file_path),
                        line_number=node.lineno,
                        import_name=module,
                        declared=False,
                        is_stdlib=False,
                        is_relative=False,
                    ))

        return violations, imports_checked

    # ── Public API ───────────────────────────────────────────────────────

    @staticmethod
    def check_directory(
        root: Path,
        scan_paths: list[Path] | None = None,
        declared_deps: set[str] | None = None,
    ) -> ImportCheckResult:
        """Check all .py files in the specified directories for import violations.

        Args:
            root: Project root directory (used to locate pyproject.toml and
                  requirements.txt, and as a fallback for project-local detection).
            scan_paths: Directories to scan for .py files. If None, scans ``root``.
            declared_deps: Pre-computed set of declared dependency names (lowercase).
                  If None, auto-detected from pyproject.toml + requirements.txt.

        Returns:
            ImportCheckResult with violations, scan counts, and warnings.
        """
        if declared_deps is None:
            declared_deps = ImportChecker._collect_declared_deps(root)

        # Normalize to Path objects
        root = Path(root)
        if scan_paths is None:
            scan_paths = [root]
        else:
            scan_paths = [Path(p) for p in scan_paths]

        all_violations: list[ImportViolation] = []
        total_files = 0
        total_imports = 0
        warnings: list[str] = []

        # Warn if no dependency files were found
        pyproject = root / "pyproject.toml"
        requirements = root / "requirements.txt"
        if not pyproject.exists() and not requirements.exists():
            msg = (
                "No pyproject.toml or requirements.txt found in project root. "
                "All third-party imports will be flagged as undeclared. "
                f"Root: {root}"
            )
            logger.warning(msg)
            warnings.append(msg)

        for scan_path in scan_paths:
            if not scan_path.exists():
                logger.warning("Scan path does not exist: %s", scan_path)
                continue

            for dirpath, dirnames, filenames in os.walk(scan_path):
                # Skip hidden directories and Python cache directories
                dirnames[:] = [
                    d for d in dirnames
                    if not d.startswith(".") and d != "__pycache__"
                ]

                for filename in filenames:
                    if filename.endswith(".py"):
                        total_files += 1
                        file_path = Path(dirpath) / filename
                        file_violations, file_imports = ImportChecker._scan_file(
                            file_path, declared_deps, root, scan_paths,
                        )
                        all_violations.extend(file_violations)
                        total_imports += file_imports

        return ImportCheckResult(
            violations=all_violations,
            total_files_scanned=total_files,
            total_imports_checked=total_imports,
            warnings=warnings,
        )
