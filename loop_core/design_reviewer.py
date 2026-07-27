"""
Design Reviewer — automated architecture and design checks.

Detects:
  - Host-specific imports in loop_core (boundary violation)
  - Interface compliance gaps (abstract methods not implemented)
  - Dead code and unused imports
  - Missing docstrings for public modules
  - Architecture pattern violations

Project-aware: knows Loop Engine's architecture contract (loop_core
must be host-independent, hooks/ owns ZCode specifics, tools/ implements
HostAdapter).
"""
from __future__ import annotations

import ast
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class DesignFinding:
    rule_id: str
    severity: str
    file: str
    line: int
    message: str
    snippet: str = ""


@dataclass
class DesignReport:
    files_scanned: int
    findings: list[DesignFinding] = field(default_factory=list)

    @property
    def errors(self) -> int:
        return sum(1 for f in self.findings if f.severity == "error")

    @property
    def passed(self) -> bool:
        return self.errors == 0


# ── Rule: Host-specific imports in loop_core ───────────────────────────


_HOST_PATTERNS = [
    (re.compile(r'(?:from|import)\s+zcode', re.IGNORECASE), "zcode"),
    (re.compile(r'(?:from|import)\s+claude', re.IGNORECASE), "claude"),
    (re.compile(r'(?:from|import)\s+qoder', re.IGNORECASE), "qoder"),
    (re.compile(r'(?:from|import)\s+codex', re.IGNORECASE), "codex"),
]

_HOST_PATH_PATTERNS = [
    re.compile(r'["\']\.zcode/', re.IGNORECASE),
    re.compile(r'["\']\.claude/', re.IGNORECASE),
]


def _check_host_leaks(file_path: Path, source: str) -> list[DesignFinding]:
    """Detect host-specific code in loop_core/."""
    findings: list[DesignFinding] = []
    rel = str(file_path)

    if "loop_core" not in rel.replace("\\", "/"):
        return findings

    for line_no, line in enumerate(source.splitlines(), 1):
        stripped = line.strip()
        if stripped.startswith("#") or stripped.startswith('"""') or stripped.startswith("'''"):
            continue

        for pattern, host_name in _HOST_PATTERNS:
            if pattern.search(line):
                # Skip comments, docstrings, and attributions
                if stripped.startswith("#") or stripped.startswith('"""') or stripped.startswith("'''"):
                    continue
                if stripped.startswith("*") or stripped.startswith("//"):
                    continue
                if "e.g." in stripped.lower() or "example" in stripped.lower():
                    continue
                if any(word in stripped.lower() for word in (
                    "adapted from", "pattern from", "absorbs concepts from",
                    "credit", "source:", "supports", "from qoder", "from zcode",
                )):
                    continue
                findings.append(DesignFinding(
                    rule_id="DR-001", severity="error",
                    file=rel, line=line_no,
                    message=f"Host-specific import '{host_name}' in loop_core/ — violates host-independence",
                    snippet=stripped[:100],
                ))

        for pattern in _HOST_PATH_PATTERNS:
            if pattern.search(line) and not stripped.startswith("#"):
                findings.append(DesignFinding(
                    rule_id="DR-002", severity="error",
                    file=rel, line=line_no,
                    message="Host-specific path in loop_core/ — use HostAdapter injection",
                    snippet=stripped[:100],
                ))

    return findings


# ── Rule: Public API without docstring ──────────────────────────────────


def _check_public_api_docs(file_path: Path, source: str, tree: ast.AST) -> list[DesignFinding]:
    """Detect public functions/classes without docstrings."""
    findings: list[DesignFinding] = []
    rel = str(file_path)

    # Skip test files and __init__.py
    if "test_" in rel or rel.endswith("__init__.py"):
        return findings

    for node in ast.iter_child_nodes(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            # Skip private names
            if node.name.startswith("_"):
                continue
            # Check for docstring
            if not (node.body and isinstance(node.body[0], ast.Expr) and
                    isinstance(node.body[0].value, (ast.Constant, ast.Str))):
                findings.append(DesignFinding(
                    rule_id="DR-010", severity="warning",
                    file=rel, line=node.lineno,
                    message=f"Public {type(node).__name__[:-3].lower()} '{node.name}' has no docstring",
                    snippet=node.name,
                ))
    return findings


# ── Rule: Dead imports ──────────────────────────────────────────────────


def _check_dead_imports(file_path: Path, source: str, tree: ast.AST) -> list[DesignFinding]:
    """Detect unused imports."""
    findings: list[DesignFinding] = []
    rel = str(file_path)

    imports: dict[str, int] = {}

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                name = alias.asname or alias.name
                imports[name] = node.lineno
        elif isinstance(node, ast.ImportFrom):
            for alias in node.names:
                if alias.name == "*":
                    continue
                name = alias.asname or alias.name
                imports[name] = node.lineno

    # Check usage
    for name, line_no in imports.items():
        if name.startswith("_"):
            continue
        # Simple check: does the name appear elsewhere in source?
        # (This is approximate; proper dead-import detection needs more analysis)
        count = source.count(name)
        if count <= 1:  # Only appears in import statement
            findings.append(DesignFinding(
                rule_id="DR-011", severity="info",
                file=rel, line=line_no,
                message=f"Import '{name}' may be unused (appears only once)",
                snippet=name,
            ))

    return findings


# ── Rule: Complexity hotspots ───────────────────────────────────────────


def _check_complexity(file_path: Path, source: str, tree: ast.AST) -> list[DesignFinding]:
    """Detect overly complex functions."""
    findings: list[DesignFinding] = []
    rel = str(file_path)

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            # Count lines
            if node.end_lineno and node.lineno:
                lines = node.end_lineno - node.lineno + 1
                if lines > 80:
                    # Count branches (if/for/while/except)
                    branches = sum(1 for n in ast.walk(node)
                                   if isinstance(n, (ast.If, ast.For, ast.While, ast.ExceptHandler)))
                    if branches > 15:
                        findings.append(DesignFinding(
                            rule_id="DR-020", severity="warning",
                            file=rel, line=node.lineno,
                            message=f"Function '{node.name}' is {lines} lines with ~{branches} branches — consider splitting",
                            snippet=f"def {node.name}(...):",
                        ))

    return findings


# ── Main entry point ────────────────────────────────────────────────────


def review_design(root: str | Path) -> DesignReport:
    """Run all design review rules on a project."""
    root = Path(root).resolve()
    py_files = list(root.rglob("*.py"))
    py_files = [f for f in py_files if "__pycache__" not in str(f) and ".git" not in str(f)]

    all_findings: list[DesignFinding] = []

    for file_path in py_files:
        try:
            source = file_path.read_text(encoding="utf-8")
            tree = ast.parse(source, filename=str(file_path))
        except (SyntaxError, UnicodeDecodeError):
            continue

        all_findings.extend(_check_host_leaks(file_path, source))
        all_findings.extend(_check_public_api_docs(file_path, source, tree))
        all_findings.extend(_check_dead_imports(file_path, source, tree))
        all_findings.extend(_check_complexity(file_path, source, tree))

    return DesignReport(files_scanned=len(py_files), findings=all_findings)
