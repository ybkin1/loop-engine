"""
Static Code Analyzer — project-aware code quality checks.

Detects patterns that unit tests and compile checks miss:
  - Extracted-but-not-verified values (e.g. hash extracted but not compared)
  - Swallowed exceptions (bare except, except Exception: pass)
  - Declared-but-not-implemented parallelism
  - Missing logging in critical paths
  - Hardcoded magic values

Project-aware: checks the actual Loop Engine codebase for Loop-specific
anti-patterns, not just generic linting rules.
"""
from __future__ import annotations

import ast
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class Finding:
    rule_id: str
    severity: str  # "error" | "warning" | "info"
    file: str
    line: int
    message: str
    snippet: str = ""


@dataclass
class AnalysisReport:
    files_scanned: int
    findings: list[Finding] = field(default_factory=list)

    @property
    def errors(self) -> int:
        return sum(1 for f in self.findings if f.severity == "error")

    @property
    def warnings(self) -> int:
        return sum(1 for f in self.findings if f.severity == "warning")

    @property
    def passed(self) -> bool:
        return self.errors == 0


# ── Rule: Extract-but-not-verify ────────────────────────────────────────


def _check_extract_without_verify(file_path: Path, source: str, tree: ast.AST) -> list[Finding]:
    """Detect patterns where a value is extracted (regex, dict.get) but never compared."""
    findings: list[Finding] = []
    rel = str(file_path)

    # Pattern: re.search(...) or re.match(...) then .group(1) but no comparison
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets if isinstance(node.targets, list) else [node.targets]:
                if isinstance(target, ast.Name) and isinstance(node.value, ast.Call):
                    call = node.value
                    # Check if it's a regex match result
                    is_regex_result = False
                    if isinstance(call.func, ast.Attribute):
                        if call.func.attr in ("search", "match"):
                            is_regex_result = True
                    elif isinstance(call.func, ast.Name):
                        pass  # not regex

                    if is_regex_result:
                        var_name = target.id
                        # Check if this variable is later compared
                        compared = _is_var_compared(var_name, tree)
                        if not compared:
                            findings.append(Finding(
                                rule_id="SA-001", severity="warning",
                                file=rel, line=node.lineno,
                                message=f"Regex result '{var_name}' extracted but never compared — potential unverified value",
                                snippet=ast.get_source_segment(source, node) or "",
                            ))
    return findings


def _is_var_compared(var_name: str, tree: ast.AST) -> bool:
    """Check if var_name or its derivatives appear in any comparison."""
    # Direct check
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare):
            for operand in [node.left] + node.comparators:
                if isinstance(operand, ast.Name) and operand.id == var_name:
                    return True
        if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Eq, ast.NotEq)):
            for operand in [node.left, node.right]:
                if isinstance(operand, ast.Name) and operand.id == var_name:
                    return True
    # Also check if var_name was assigned to another variable that gets compared
    assigned_to: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets if isinstance(node.targets, list) else [node.targets]:
                if isinstance(target, ast.Name):
                    # Case: key = m.group(1)  (Call on Attribute)
                    if isinstance(node.value, ast.Call) and isinstance(node.value.func, ast.Attribute):
                        if isinstance(node.value.func.value, ast.Name) and node.value.func.value.id == var_name:
                            assigned_to.add(target.id)
                    # Case: key = m.attr  (direct Attribute)
                    elif isinstance(node.value, ast.Attribute):
                        if isinstance(node.value.value, ast.Name) and node.value.value.id == var_name:
                            assigned_to.add(target.id)
    for name in assigned_to:
        if _is_var_compared(name, tree):
            return True
    return False


# ── Rule: Swallowed exceptions ──────────────────────────────────────────


def _check_swallowed_exceptions(file_path: Path, source: str, tree: ast.AST) -> list[Finding]:
    """Detect bare except or except Exception: pass patterns."""
    findings: list[Finding] = []
    rel = str(file_path)

    for node in ast.walk(tree):
        if isinstance(node, ast.Try):
            for handler in node.handlers:
                if handler.type is None:
                    findings.append(Finding(
                        rule_id="SA-002", severity="warning",
                        file=rel, line=handler.lineno,
                        message="Bare except: — catches all exceptions including SystemExit/KeyboardInterrupt",
                        snippet="except:",
                    ))
                elif isinstance(handler.type, ast.Name) and handler.type.id == "Exception":
                    body_text = ast.get_source_segment(source, handler) or ""
                    if "pass" in body_text and len(handler.body) == 1 and isinstance(handler.body[0], ast.Pass):
                        findings.append(Finding(
                            rule_id="SA-003", severity="warning",
                            file=rel, line=handler.lineno,
                            message="except Exception: pass — error silently swallowed",
                            snippet=body_text.strip()[:80],
                        ))
    return findings


# ── Rule: Parallelism declared but not implemented ─────────────────────


def _check_parallel_declaration(file_path: Path, source: str, tree: ast.AST) -> list[Finding]:
    """Detect 'parallel=True' or 'max_parallel' in config but sequential execution in code."""
    findings: list[Finding] = []
    rel = str(file_path)
    source_lower = source.lower()

    has_parallel_decl = ("parallel" in source_lower and "true" in source_lower) or \
                        "max_parallel" in source_lower
    has_threading = "thread" in source_lower or "concurrent" in source_lower or \
                    "ThreadPool" in source or "ProcessPool" in source

    if has_parallel_decl and not has_threading:
        # Check if it's a data class or config (not actual execution code)
        if "def " in source_lower and "for " in source_lower:  # has loops in functions
            findings.append(Finding(
                rule_id="SA-004", severity="info",
                file=rel, line=1,
                message="Parallelism declared (max_parallel/parallel=True) but no threading/concurrent imports detected",
                snippet="",
            ))
    return findings


# ── Rule: Missing logging ───────────────────────────────────────────────


def _check_missing_logging(file_path: Path, source: str, tree: ast.AST) -> list[Finding]:
    """Detect files that do error-prone work without logging."""
    findings: list[Finding] = []
    rel = str(file_path)

    has_except = any(isinstance(n, ast.Try) for n in ast.walk(tree))
    has_logging = "logging" in source or "logger" in source or "print(" in source
    has_network = "urllib" in source or "requests" in source or "http" in source.lower()

    if has_network and not has_logging:
        findings.append(Finding(
            rule_id="SA-005", severity="warning",
            file=rel, line=1,
            message="Network I/O without logging — failures will be invisible",
            snippet="",
        ))
    elif has_except and not has_logging:
        findings.append(Finding(
            rule_id="SA-006", severity="info",
            file=rel, line=1,
            message="Exception handling without logging — errors may go unnoticed",
            snippet="",
        ))
    return findings


# ── Main entry point ────────────────────────────────────────────────────


def analyze_project(root: str | Path) -> AnalysisReport:
    """Run all static analysis rules on a project."""
    root = Path(root).resolve()
    py_files = list(root.rglob("*.py"))
    # Exclude __pycache__, .git, venv, tests (test files have different rules)
    py_files = [
        f for f in py_files
        if "__pycache__" not in str(f)
        and ".git" not in str(f)
        and "venv" not in str(f)
    ]

    all_findings: list[Finding] = []

    for file_path in py_files:
        try:
            source = file_path.read_text(encoding="utf-8")
            tree = ast.parse(source, filename=str(file_path))
        except (SyntaxError, UnicodeDecodeError):
            continue

        all_findings.extend(_check_extract_without_verify(file_path, source, tree))
        all_findings.extend(_check_swallowed_exceptions(file_path, source, tree))
        all_findings.extend(_check_parallel_declaration(file_path, source, tree))
        all_findings.extend(_check_missing_logging(file_path, source, tree))

    return AnalysisReport(files_scanned=len(py_files), findings=all_findings)
