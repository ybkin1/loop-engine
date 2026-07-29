"""
subagent_evidence_verifier.py — Verify that review evidence came from an
independent sub-agent session, not from main-session role-playing.

T-0067: Gate_guard uses this to enforce quality-gate evidence authenticity.
"""

import hashlib
import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# Patterns that indicate simulated/fake evidence
SIMULATION_MARKERS = [
    "Simulated output",
    "simulated output",
    "No issues found",
    "no defects found",
    "no vulnerabilities found",
    "All tests pass",
]

# Minimum required fields for valid sub-agent evidence
REQUIRED_EVIDENCE_FIELDS = [
    "reviewer_session_id",
    "verdict",
    "findings",
]


def _hash_file(path: Path) -> str:
    """SHA256 hash of a file's content."""
    if not path.exists():
        return ""
    return hashlib.sha256(path.read_bytes()).hexdigest()[:16]


def is_simulated(content: dict) -> bool:
    """Detect if review output looks like simulated/fabricated evidence.

    Returns True if the content matches known simulation patterns.
    """
    summary = str(content.get("summary", ""))
    for marker in SIMULATION_MARKERS:
        if marker.lower() in summary.lower():
            logger.warning("Simulation marker detected: '%s' in summary", marker)
            return True

    # Check for suspiciously empty findings
    findings = content.get("findings", [])
    if isinstance(findings, list) and len(findings) == 0:
        verdict = content.get("verdict", "")
        if verdict == "PASS":
            logger.warning("Suspicious: PASS verdict with empty findings list")
            return True

    return False


def has_valid_session_id(content: dict) -> bool:
    """Verify that the review evidence contains a valid session ID."""
    session_id = content.get("reviewer_session_id", "")
    if not session_id:
        logger.warning("Missing reviewer_session_id")
        return False

    # Session ID should be non-trivial (not empty, not "unknown")
    if session_id.lower() in ("", "unknown", "none", "null", "n/a"):
        return False

    return True


def is_independent_session(content: dict, main_session_id: str = "") -> bool:
    """Verify that reviewer session differs from developer session."""
    reviewer = content.get("reviewer_session_id", "")
    developer = content.get("developer_session_id", "")

    if not reviewer:
        return False

    if reviewer == developer:
        logger.warning("SELF_REVIEW: reviewer_session_id == developer_session_id")
        return False

    if main_session_id and reviewer == main_session_id:
        logger.warning("SELF_REVIEW: reviewer_session_id matches main session")
        return False

    return True


def has_required_fields(content: dict) -> tuple[bool, list[str]]:
    """Check that all required evidence fields are present and non-empty."""
    missing = []
    for field in REQUIRED_EVIDENCE_FIELDS:
        if field not in content or not content[field]:
            missing.append(field)
    return len(missing) == 0, missing


def verify_review_evidence(
    evidence_path: str,
    main_session_id: str = "",
    expected_files: list[str] | None = None,
) -> dict:
    """Complete evidence verification for a quality-gate review.

    Args:
        evidence_path: Path to the review evidence JSON file
        main_session_id: Current main session ID (to detect self-review)
        expected_files: List of files that should have been reviewed

    Returns:
        {"valid": bool, "reason": str, "checks": {...}}
    """
    path = Path(evidence_path)
    checks = {
        "file_exists": False,
        "valid_json": False,
        "not_simulated": False,
        "has_session_id": False,
        "independent_session": False,
        "required_fields": False,
        "files_covered": False,
    }

    if not path.exists():
        return {"valid": False, "reason": f"Evidence file not found: {evidence_path}", "checks": checks}
    checks["file_exists"] = True

    try:
        content = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, Exception) as e:
        return {"valid": False, "reason": f"Invalid JSON: {e}", "checks": checks}
    checks["valid_json"] = True

    # 1. Anti-simulation
    if is_simulated(content):
        return {"valid": False, "reason": "Evidence appears to be simulated/fabricated", "checks": checks}
    checks["not_simulated"] = True

    # 2. Session ID
    if not has_valid_session_id(content):
        return {"valid": False, "reason": "Missing or invalid reviewer_session_id", "checks": checks}
    checks["has_session_id"] = True

    # 3. Independence
    if not is_independent_session(content, main_session_id):
        return {"valid": False, "reason": "Reviewer session is not independent (self-review detected)", "checks": checks}
    checks["independent_session"] = True

    # 4. Required fields
    ok, missing = has_required_fields(content)
    if not ok:
        return {"valid": False, "reason": f"Missing required fields: {missing}", "checks": checks}
    checks["required_fields"] = True

    # 5. File coverage (if expected files provided)
    if expected_files:
        reviewed = set(content.get("files_reviewed", []))
        expected = set(expected_files)
        uncovered = expected - reviewed
        if uncovered:
            return {"valid": False, "reason": f"Not all files reviewed. Missing: {list(uncovered)[:5]}", "checks": checks}
    checks["files_covered"] = True

    return {"valid": True, "reason": "All evidence checks passed", "checks": checks}


# CLI entry for hook usage
if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print(json.dumps({"valid": False, "reason": "Usage: evidence_path [session_id]"}))
        sys.exit(1)

    evidence_path = sys.argv[1]
    session_id = sys.argv[2] if len(sys.argv) > 2 else ""

    result = verify_review_evidence(evidence_path, main_session_id=session_id)
    print(json.dumps(result, indent=2))
    sys.exit(0 if result["valid"] else 1)
