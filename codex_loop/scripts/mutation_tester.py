"""
mutation_tester.py — Seeded defect / mutation testing framework for Loop Engine.

Plants known defects in a test project, runs the Loop review chain,
and verifies that defects are detected and blocked.

Usage:
    python mutation_tester.py --project-root <path> --seed-defects <count>
    python mutation_tester.py --verify-results --reviewer-output <json_file>
"""
import argparse
import json
import sys
from dataclasses import dataclass, field

# Known defect types that can be seeded
DEFECT_TYPES = {
    "hardcoded_secret": {
        "description": "Hardcoded API key or password in source code",
        "severity": "P0",
        "type": "security",
        "fr_ref": "FR-SEC-03",
    },
    "sql_injection": {
        "description": "SQL query built via string concatenation",
        "severity": "P0",
        "type": "security",
        "fr_ref": "FR-SEC-02",
    },
    "missing_validation": {
        "description": "User input not validated before use",
        "severity": "P1",
        "type": "security",
        "fr_ref": "FR-SEC-01",
    },
    "missing_auth_check": {
        "description": "Endpoint without authentication check",
        "severity": "P1",
        "type": "security",
        "fr_ref": "FR-SEC-04",
    },
    "architecture_violation": {
        "description": "Code bypasses required abstraction layer",
        "severity": "P1",
        "type": "architecture",
        "fr_ref": "ARCH-DB-01",
    },
    "weak_hashing": {
        "description": "Using fast hash (SHA256/MD5) for passwords",
        "severity": "P2",
        "type": "security",
        "fr_ref": "FR-SEC-01",
    },
    "none_bypass": {
        "description": "Using os.environ.get() resulting in None comparison bypass",
        "severity": "P2",
        "type": "security",
        "fr_ref": "FR-SEC-04",
    },
}


@dataclass
class MutationResult:
    """Result of a single mutation test."""
    defect_type: str
    seeded: bool = False
    detected: bool = False
    reviewer_finding_id: str | None = None
    reviewer_severity: str | None = None

    @property
    def passed(self) -> bool:
        """Mutation test passes when seeded defect IS detected."""
        return self.seeded and self.detected

    @property
    def false_negative(self) -> bool:
        """Seeded defect was NOT detected by reviewer."""
        return self.seeded and not self.detected


@dataclass
class MutationSuite:
    """Collection of mutation test results."""
    results: list[MutationResult] = field(default_factory=list)

    @property
    def total(self) -> int:
        return len(self.results)

    @property
    def passed(self) -> int:
        return sum(1 for r in self.results if r.passed)

    @property
    def false_negatives(self) -> int:
        return sum(1 for r in self.results if r.false_negative)

    @property
    def detection_rate(self) -> float:
        seeded = sum(1 for r in self.results if r.seeded)
        if seeded == 0:
            return 1.0
        return self.passed / seeded

    def summary(self) -> dict:
        return {
            "total_mutations": self.total,
            "seeded_defects": sum(1 for r in self.results if r.seeded),
            "detected": self.passed,
            "false_negatives": self.false_negatives,
            "detection_rate": f"{self.detection_rate:.0%}",
            "verdict": "PASS" if self.detection_rate >= 0.9 else "BLOCKED",
        }


def parse_reviewer_output(json_path: str) -> dict:
    """Parse the structured JSON output from an independent reviewer."""
    with open(json_path, "r", encoding="utf-8") as f:
        return json.load(f)


def match_defects_to_findings(
    seeded_defects: list[str],
    reviewer_output: dict,
) -> MutationSuite:
    """Match seeded defect types to reviewer findings."""
    suite = MutationSuite()
    findings = reviewer_output.get("findings", [])

    for defect_type in seeded_defects:
        defect_info = DEFECT_TYPES.get(defect_type, {})
        result = MutationResult(defect_type=defect_type, seeded=True)

        # Try to match against reviewer findings
        for finding in findings:
            title_lower = finding.get("title", "").lower()
            defect_info.get("description", "").lower()

            if defect_type == "hardcoded_secret" and ("api key" in title_lower or "hardcoded" in title_lower):
                result.detected = True
                result.reviewer_finding_id = finding.get("id")
                result.reviewer_severity = finding.get("severity")
                break
            elif defect_type == "sql_injection" and "sql injection" in title_lower:
                result.detected = True
                result.reviewer_finding_id = finding.get("id")
                result.reviewer_severity = finding.get("severity")
                break
            elif defect_type == "missing_validation" and ("input validation" in title_lower or "validate" in title_lower):
                result.detected = True
                result.reviewer_finding_id = finding.get("id")
                result.reviewer_severity = finding.get("severity")
                break
            elif defect_type in title_lower.replace(" ", "_"):
                result.detected = True
                result.reviewer_finding_id = finding.get("id")
                result.reviewer_severity = finding.get("severity")
                break

        suite.results.append(result)

    return suite


def main():
    parser = argparse.ArgumentParser(description="Loop Engine Mutation Tester")
    sub = parser.add_subparsers(dest="command")

    verify = sub.add_parser("verify", help="Verify reviewer output against seeded defects")
    verify.add_argument("--reviewer-output", required=True, help="Path to reviewer JSON output")
    verify.add_argument("--seeded", nargs="+", required=True, help="List of seeded defect types")

    sub.add_parser("list-defects", help="List available defect types")

    args = parser.parse_args()

    if args.command == "list-defects":
        print(json.dumps(DEFECT_TYPES, indent=2, ensure_ascii=False))
    elif args.command == "verify":
        reviewer = parse_reviewer_output(args.reviewer_output)
        suite = match_defects_to_findings(args.seeded, reviewer)
        print(json.dumps(suite.summary(), indent=2, ensure_ascii=False))

        if suite.detection_rate < 0.9:
            print(f"\n[BLOCKED] Detection rate {suite.detection_rate:.0%} below 90% threshold")
            sys.exit(2)
        else:
            print(f"\n[PASS] Detection rate {suite.detection_rate:.0%} meets threshold")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
