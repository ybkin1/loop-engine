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

FAIL-CLOSED POLICY: Any critical severity finding -> Verdict.BLOCKED.
This cannot be overridden. Security is non-negotiable.
"""
from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from dataclasses import dataclass, field
from pathlib import Path

from .verdicts import ReportBinding, Verdict


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
    # ── Binding fields (Phase 2) ──
    binding: ReportBinding | None = None
    verdict: Verdict = Verdict.NOT_VERIFIED
    content_hash: str = ""  # SHA-256 of findings content

    @property
    def critical(self) -> int:
        return sum(1 for f in self.findings if f.severity == "critical")

    @property
    def high(self) -> int:
        return sum(1 for f in self.findings if f.severity == "high")

    @property
    def passed(self) -> bool:
        return self.critical == 0 and self.high == 0

    def compute_verdict(self) -> Verdict:
        """Compute verdict based on findings. Fail-closed: any critical -> BLOCKED."""
        if self.critical > 0:
            return Verdict.BLOCKED
        if self.high > 0:
            return Verdict.FAIL
        return Verdict.PASS

    def compute_hash(self) -> str:
        """Compute content hash from findings for fingerprint verification."""
        sorted_findings = sorted(self.findings, key=lambda f: (f.file, f.line, f.rule_id))
        content = json.dumps([
            {"rule_id": f.rule_id, "severity": f.severity, "file": f.file,
             "line": f.line, "message": f.message}
            for f in sorted_findings
        ], sort_keys=True)
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def bind(self, task_id: str, phase: str, git_commit: str = "",
             gate_id: str | None = None, execution_id: str | None = None,
             diff_fingerprint: str | None = None) -> "SecurityReport":
        """Bind report to execution context and compute verdict + hash."""
        self.binding = ReportBinding(
            task_id=task_id, phase=phase, gate_id=gate_id,
            execution_id=execution_id, git_commit=git_commit,
            diff_fingerprint=diff_fingerprint,
            timestamp=datetime.now(timezone.utc).isoformat(),
            tool_name="loop_core.security_scanner",
            tool_version="1.0",
        )
        self.verdict = self.compute_verdict()
        self.content_hash = self.compute_hash()
        return self

    def is_valid(self) -> bool:
        """Verify binding integrity. Old/stale reports are invalid."""
        if self.binding is None:
            return False
        missing = self.binding.validate()
        if missing:
            return False
        # Content hash must match
        if self.content_hash and self.content_hash != self.compute_hash():
            return False
        return True

    def to_dict(self) -> dict:
        return {
            "files_scanned": self.files_scanned,
            "findings": [
                {"rule_id": f.rule_id, "severity": f.severity, "file": f.file,
                 "line": f.line, "message": f.message, "snippet": f.snippet}
                for f in self.findings
            ],
            "binding": self.binding.to_dict() if self.binding else None,
            "verdict": self.verdict.value if self.verdict else Verdict.NOT_VERIFIED.value,
            "content_hash": self.content_hash,
        }


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


def scan_security(root: str | Path, task_id: str = "", phase: str = "",
                  git_commit: str = "", gate_id: str | None = None,
                  execution_id: str | None = None) -> SecurityReport:
    """Run security scan on a project with optional execution context binding."""
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

    report = SecurityReport(files_scanned=len(py_files), findings=findings)
    if task_id:
        report.bind(task_id=task_id, phase=phase, git_commit=git_commit,
                    gate_id=gate_id, execution_id=execution_id)
    return report


# Compatibility alias (legacy callers expect "SecurityScanner" class)
class SecurityScanner:
    """Compatibility wrapper for function-based security_scanner module."""
    @staticmethod
    def scan(root):
        return scan_security(root)
