"""
auto_mutation.py — Automated mutation testing for Loop Engine.

Injects known defects into code, runs the review chain, and verifies
detection. Fully automated: inject → test → review → report.

Usage:
    python auto_mutation.py --project-root <path> --source <file>
    python auto_mutation.py --list-defects
"""
import argparse
import hashlib
import json
import random
import sys
import tempfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

# Mutations that can be injected into source code
MUTATIONS = {
    "hardcoded_secret": {
        "description": "Inject a hardcoded API key",
        "severity": "P0",
        "inject": lambda lines: _inject_at_line(lines, 10, 'API_KEY = "sk-deadbeef1234567890abcdef"'),
    },
    "sql_injection": {
        "description": "Replace parameterized query with string concatenation",
        "severity": "P0",
        "inject": lambda lines: _replace_pattern(lines, "cursor.execute(", 'cursor.execute(f"'),
    },
    "missing_auth_check": {
        "description": "Remove authentication check from a function",
        "severity": "P1",
        "inject": lambda lines: _remove_lines_containing(lines, "token", "auth", "permission"),
    },
    "broad_exception": {
        "description": "Replace specific exception with bare except",
        "severity": "P1",
        "inject": lambda lines: _replace_pattern(lines, "except ValueError:", "except:"),
    },
    "weak_hash": {
        "description": "Replace secure hash with MD5",
        "severity": "P2",
        "inject": lambda lines: _replace_pattern(lines, "sha256", "md5"),
    },
}


def _inject_at_line(lines: list[str], target_line: int, code: str) -> list[str]:
    result = lines[:]
    if target_line < len(result):
        result.insert(target_line, code + "\n")
    return result


def _replace_pattern(lines: list[str], old: str, new: str) -> list[str]:
    return [line.replace(old, new) if old in line else line for line in lines]


def _remove_lines_containing(lines: list[str], *keywords: str) -> list[str]:
    return [line for line in lines if not any(kw in line.lower() for kw in keywords)]


@dataclass
class MutationRun:
    mutation_id: str
    original_hash: str
    mutated_hash: str
    expected_severity: str


@dataclass
class MutationReport:
    runs: list[MutationRun] = field(default_factory=list)
    detected: list[str] = field(default_factory=list)
    missed: list[str] = field(default_factory=list)

    @property
    def total(self) -> int: return len(self.runs)
    @property
    def detection_rate(self) -> float:
        return len(self.detected) / max(self.total, 1)


def inject_all(source_path: Path, output_dir: Path) -> list[MutationRun]:
    """Inject all mutations into copies of the source file."""
    original = source_path.read_text(encoding="utf-8")
    original_hash = hashlib.sha256(original.encode()).hexdigest()
    lines = original.splitlines(keepends=True)
    runs = []

    output_dir.mkdir(parents=True, exist_ok=True)
    for mutation_id, mutation in MUTATIONS.items():
        mutated_lines = mutation["inject"](list(lines))
        mutated_code = "".join(mutated_lines)
        mutated_hash = hashlib.sha256(mutated_code.encode()).hexdigest()

        if mutated_hash == original_hash:
            continue  # Mutation had no effect

        out_path = output_dir / f"mutated_{mutation_id}.py"
        out_path.write_text(mutated_code, encoding="utf-8")

        runs.append(MutationRun(
            mutation_id=mutation_id,
            original_hash=original_hash,
            mutated_hash=mutated_hash,
            expected_severity=MUTATIONS[mutation_id]["severity"],
        ))

    return runs


def verify_detection(reviewer_findings: list[dict], runs: list[MutationRun]) -> MutationReport:
    """Match reviewer findings against injected mutations."""
    report = MutationReport(runs=runs)
    finding_texts = [f.get("title", "").lower() for f in reviewer_findings]

    for run in runs:
        mutation = MUTATIONS.get(run.mutation_id, {})
        desc = mutation.get("description", "").lower()
        severity = mutation.get("severity", "")

        detected = any(
            run.mutation_id in title or desc.split()[0] in title
            for title in finding_texts
        )
        if detected:
            report.detected.append(run.mutation_id)
        else:
            report.missed.append(run.mutation_id)

    return report


def main():
    parser = argparse.ArgumentParser(description="Automated Mutation Tester")
    sub = parser.add_subparsers(dest="command")

    inject = sub.add_parser("inject", help="Inject mutations into source")
    inject.add_argument("--source", required=True)
    inject.add_argument("--output-dir", default=".ai/evidence/mutations")

    verify = sub.add_parser("verify", help="Verify reviewer detected mutations")
    verify.add_argument("--reviewer-output", required=True, help="JSON from reviewer")
    verify.add_argument("--mutation-dir", default=".ai/evidence/mutations")

    list_cmd = sub.add_parser("list-defects")

    args = parser.parse_args()

    if args.command == "inject":
        source = Path(args.source)
        output = Path(args.output_dir)
        runs = inject_all(source, output)
        print(json.dumps({
            "total_mutations": len(runs),
            "mutations": [
                {"id": r.mutation_id, "severity": MUTATIONS[r.mutation_id]["severity"]}
                for r in runs
            ],
        }, indent=2, ensure_ascii=False))

    elif args.command == "verify":
        with open(args.reviewer_output, "r", encoding="utf-8") as f:
            reviewer = json.load(f)
        findings = reviewer.get("findings", [])
        # Rebuild runs from mutation dir
        mutation_dir = Path(args.mutation_dir)
        if mutation_dir.exists():
            runs = [MutationRun(
                mutation_id=p.stem.replace("mutated_", ""),
                original_hash="",
                mutated_hash=hashlib.sha256(p.read_bytes()).hexdigest(),
                expected_severity="unknown",
            ) for p in sorted(mutation_dir.glob("mutated_*.py"))]
        else:
            runs = []
        report = verify_detection(findings, runs)
        print(json.dumps({
            "total": report.total,
            "detected": len(report.detected),
            "missed": len(report.missed),
            "detection_rate": f"{report.detection_rate:.0%}",
            "detected_list": report.detected,
            "missed_list": report.missed,
            "verdict": "PASS" if report.detection_rate >= 0.8 else "BLOCKED",
        }, indent=2, ensure_ascii=False))

    elif args.command == "list-defects":
        print(json.dumps({
            mid: {"description": m["description"], "severity": m["severity"]}
            for mid, m in MUTATIONS.items()
        }, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
