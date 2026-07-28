"""
security_scan.py — Basic security scanning for Loop Engine projects.

Checks for: hardcoded secrets, dangerous patterns, missing input validation,
insecure configurations. Script-based, no external tools required.

Usage:
    python security_scan.py --project-root <path>
    python security_scan.py --project-root <path> --json
"""
import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

# Patterns to detect in source code
SECRET_PATTERNS = [
    (r'(?:api_key|apikey|API_KEY|secret|password|token)\s*=\s*["\'][A-Za-z0-9_\-]{20,}["\']',
     "P0", "Hardcoded secret/API key"),
    (r'-----BEGIN (?:RSA |EC )?PRIVATE KEY-----',
     "P0", "Hardcoded private key"),
    (r'(?:password|passwd|pwd)\s*=\s*["\'][^"\']+["\']',
     "P1", "Hardcoded password (may be test-only)"),
]

SQL_PATTERNS = [
    (r'(?:execute|cursor\.execute)\s*\(\s*f["\']', "P0", "SQL injection: f-string in execute()"),
    (r'(?:execute|cursor\.execute)\s*\(\s*["\'].*%\s*\(', "P1", "SQL injection: %-formatting in execute()"),
    (r'(?:execute|cursor\.execute)\s*\(\s*["\'].*\+', "P1", "SQL injection: string concatenation in execute()"),
]

SECURITY_ANTI_PATTERNS = [
    (r'except\s*:', "P1", "Bare except clause"),
    (r'os\.system\s*\(', "P1", "Unsafe os.system() call"),
    (r'subprocess\.(?:call|run|Popen)\s*\(\s*[^,)]*\bshell\s*=\s*True',
     "P1", "subprocess with shell=True"),
    (r'pickle\.(?:load|loads)\s*\(', "P1", "Unsafe pickle deserialization"),
    (r'eval\s*\(', "P0", "Dangerous eval() call"),
    (r'exec\s*\(', "P0", "Dangerous exec() call"),
]


@dataclass
class SecurityFinding:
    file: str
    line: int
    severity: str
    category: str
    description: str
    code_snippet: str


def scan_file(file_path: Path, project_root: Path) -> list[SecurityFinding]:
    """Scan a single file for security issues."""
    findings = []
    try:
        lines = file_path.read_text(encoding="utf-8").splitlines()
    except Exception:
        return findings

    rel_path = str(file_path.relative_to(project_root)).replace("\\", "/")

    all_patterns = [
        ("secret", SECRET_PATTERNS),
        ("sql_injection", SQL_PATTERNS),
        ("anti_pattern", SECURITY_ANTI_PATTERNS),
    ]

    for i, line in enumerate(lines, 1):
        for category, patterns in all_patterns:
            for pattern, severity, desc in patterns:
                if re.search(pattern, line, re.IGNORECASE):
                    # Skip lines inside comments or docstrings that mention the issue
                    stripped = line.strip()
                    if stripped.startswith("#") or stripped.startswith('"""') or stripped.startswith("'''"):
                        if "SEEDED DEFECT" in stripped.upper() or "test" in rel_path.lower():
                            continue  # Known test fixtures
                    findings.append(SecurityFinding(
                        file=rel_path, line=i, severity=severity,
                        category=category, description=desc,
                        code_snippet=stripped[:120],
                    ))

    return findings


def scan_project(project_root: Path, exclude_dirs: list[str] | None = None) -> list[SecurityFinding]:
    """Scan entire project for security issues."""
    if exclude_dirs is None:
        exclude_dirs = ["archive", ".git", "__pycache__", ".pytest_cache", "lab", "seeded_defects"]

    findings = []
    for py_file in project_root.rglob("*.py"):
        if any(excl in str(py_file) for excl in exclude_dirs):
            continue
        findings.extend(scan_file(py_file, project_root))

    return findings


def main():
    parser = argparse.ArgumentParser(description="Loop Engine Security Scanner")
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    root = Path(args.project_root).resolve()
    findings = scan_project(root)

    p0 = [f for f in findings if f.severity == "P0"]
    p1 = [f for f in findings if f.severity == "P1"]

    if args.json:
        print(json.dumps({
            "total": len(findings),
            "P0_count": len(p0),
            "P1_count": len(p1),
            "verdict": "BLOCKED" if p0 else "PASS",
            "findings": [
                {"file": f.file, "line": f.line, "severity": f.severity,
                 "category": f.category, "description": f.description}
                for f in findings
            ],
        }, indent=2, ensure_ascii=False))
    else:
        print(f"Files scanned: {len({f.file for f in findings})}")
        print(f"Findings: {len(findings)} (P0: {len(p0)}, P1: {len(p1)})")
        for f in p0:
            print(f"  P0 {f.file}:{f.line} — {f.description}")
        for f in p1[:5]:
            print(f"  P1 {f.file}:{f.line} — {f.description}")
        if len(p1) > 5:
            print(f"  ... and {len(p1) - 5} more P1 findings")

    sys.exit(2 if p0 else 0)


if __name__ == "__main__":
    main()
