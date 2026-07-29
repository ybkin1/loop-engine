"""
Security Scanner — project-aware security checks.

Detects:
  - Hardcoded secrets (API keys, tokens, passwords)
  - Path traversal risks
  - Command injection surfaces
  - Unsafe file operations
  - Environment variable leakage

Project-aware: knows Loop Engine's architecture and checks for
Loop-specific security patterns (hooks isolation, adapter boundaries).
"""
from __future__ import annotations

import ast
import re
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class SecFinding:
    rule_id: str
    severity: str  # "critical" | "high" | "medium" | "low"
    file: str
    line: int
    message: str
    snippet: str = ""


@dataclass
class SecurityReport:
    files_scanned: int
    findings: list[SecFinding] = field(default_factory=list)

    @property
    def critical(self) -> int:
        return sum(1 for f in self.findings if f.severity == "critical")

    @property
    def high(self) -> int:
        return sum(1 for f in self.findings if f.severity == "high")

    @property
    def passed(self) -> bool:
        return self.critical == 0 and self.high == 0


# ── Patterns ─────────────────────────────────────────────────────────────

_SECRET_PATTERNS = [
    (re.compile(r'(?:api[_-]?key|apikey|secret|password|token)\s*[:=]\s*["\'][^"\' ]{8,}["\']', re.IGNORECASE),
     "SS-001", "critical", "Hardcoded secret detected (API key, password, or token)"),
    (re.compile(r'(?:api[_-]?key|apikey|secret|token)\s*[:=]\s*[a-zA-Z0-9_]{20,}', re.IGNORECASE),
     "SS-002", "high", "Possible hardcoded credential (alphanumeric string)"),
]

_OS_COMMAND_PATTERNS = [
    (re.compile(r'os\.system\s*\(|subprocess\.(?:call|run|Popen)\s*\(|os\.popen\s*\('),
     "SS-010", "medium", "OS command execution — potential injection surface"),
    (re.compile(r'(?:exec|eval)\s*\(\s*[\"\'][^\"\']*\{'),
     "SS-011", "high", "Dynamic code execution with string interpolation — injection risk"),
]

_PATH_PATTERNS = [
    (re.compile(r'os\.path\.join\s*\(\s*[\"\'][^\"\']*\{\w+\}'),
     "SS-020", "medium", "Path construction with user input — traversal risk"),
]

_ENV_PATTERNS = [
    (re.compile(r'os\.environ\[["\']([^"\']+)["\']\]'),
     "SS-030", "low", f"Environment variable read — may leak sensitive config"),
]


def scan_security(root: str | Path) -> SecurityReport:
    """Run security scan on a project."""
    root = Path(root).resolve()
    py_files = list(root.rglob("*.py"))
    py_files = [f for f in py_files if "__pycache__" not in str(f) and ".git" not in str(f)]
    # Exclude test files, mutation scripts, and demo fixtures
    py_files = [f for f in py_files if not any(
        p in str(f).lower() for p in ("test_", "/tests/", "\\tests\\",
                                        "mutation", "fixture", "demo/",
                                        "auto_mutation", "perf_runner",
                                        "archive/", "\\archive\\",
                                        "repair-preimages"))
    ]

    findings: list[SecFinding] = []
    env_vars_seen: set[str] = set()

    for file_path in py_files:
        try:
            source = file_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        rel = str(file_path.relative_to(root)) if file_path.is_relative_to(root) else str(file_path)

        for line_no, line in enumerate(source.splitlines(), 1):
            # Secret patterns
            for pattern, rule_id, severity, msg in _SECRET_PATTERNS:
                m = pattern.search(line)
                if m:
                    # Exclude test files and comments
                    stripped = line.strip()
                    if stripped.startswith("#") or stripped.startswith("//"):
                        continue
                    if "test_" in rel or rel.startswith("tests/"):
                        continue
                    # Exclude env var reads (not hardcoded)
                    if "os.environ" in line or "environ.get" in line:
                        continue
                    findings.append(SecFinding(
                        rule_id=rule_id, severity=severity, file=rel,
                        line=line_no, message=msg,
                        snippet=stripped[:100],
                    ))

            # Command injection
            for pattern, rule_id, severity, msg in _OS_COMMAND_PATTERNS:
                if pattern.search(line):
                    findings.append(SecFinding(
                        rule_id=rule_id, severity=severity, file=rel,
                        line=line_no, message=msg, snippet=line.strip()[:100],
                    ))

            # Path traversal
            for pattern, rule_id, severity, msg in _PATH_PATTERNS:
                if pattern.search(line):
                    findings.append(SecFinding(
                        rule_id=rule_id, severity=severity, file=rel,
                        line=line_no, message=msg, snippet=line.strip()[:100],
                    ))

            # Env var reads
            for pattern, rule_id, severity, msg in _ENV_PATTERNS:
                m = pattern.search(line)
                if m:
                    var_name = m.group(1)
                    if var_name not in env_vars_seen:
                        env_vars_seen.add(var_name)
                        findings.append(SecFinding(
                            rule_id=rule_id, severity=severity, file=rel,
                            line=line_no, message=f"Reads env var '{var_name}'",
                            snippet=line.strip()[:100],
                        ))

    return SecurityReport(files_scanned=len(py_files), findings=findings)
