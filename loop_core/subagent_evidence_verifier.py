"""
subagent_evidence_verifier.py — Verify that review evidence came from an
independent sub-agent session, not from main-session role-playing.

T-0067: Gate_guard uses this to enforce quality-gate evidence authenticity.

T-0108 F7: the verification result is also emitted as schema-validated
fix-contract findings (``loop_core.schemas.finding_contract``, aligned
with BH harness-findings.input.json).  Old result fields
(valid/reason/checks) are preserved verbatim; ``findings`` is additive.
"""

import hashlib
import json
import logging
import re
from pathlib import Path
from typing import Any, Optional

from loop_core.schemas.finding_contract import mark_schema_status

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


# T-0108 F7: contract-shaped finding for a failed verification check.
_EVIDENCE_CHECK_META = {
    "file_exists": {"title": "证据文件缺失", "message": "审查证据文件不存在"},
    "valid_json": {"title": "证据 JSON 非法", "message": "审查证据不是合法 JSON"},
    "not_simulated": {"title": "证据疑似模拟", "message": "证据内容命中模拟/伪造标记"},
    "has_session_id": {"title": "缺少 reviewer_session_id", "message": "证据缺少有效的 reviewer_session_id"},
    "independent_session": {"title": "自审（非独立会话）", "message": "审查会话与主会话相同（self-review）"},
    "required_fields": {"title": "证据必填字段缺失", "message": "证据缺少必填字段"},
    "files_covered": {"title": "审查文件覆盖不足", "message": "未覆盖全部应审查文件"},
}


def _evidence_finding(check_id: str, evidence_path: str) -> dict:
    """Build a schema-validated fix-contract finding for a failed check."""
    meta = _EVIDENCE_CHECK_META.get(check_id, {"title": check_id, "message": check_id})
    finding = {
        "finding_id": f"EVID-{check_id.upper()}",
        "source": "subagent_evidence_verifier",
        "severity": "high",
        "title": f"[{check_id}] {meta['title']}",
        "message": f"{meta['message']}（evidence: {evidence_path}）",
        "file": evidence_path,
        "line": 0,
        "expected_output": "提供独立子代理会话的真实审查证据（reviewer_session_id 有效、非模拟、字段完整、覆盖全部目标文件）",
        "fix_boundary": {
            "allowed_paths": [".ai/evidence/"],
            "forbidden": ["hooks/", "loop_core/gate_guard.py",
                          "loop_core/enforcement.py"],
        },
        "verification_command": (
            "python -m loop_core.subagent_evidence_verifier <evidence_path> "
            "<main_session_id>"
        ),
        "acceptance_checks": [
            "valid=true 且全部 checks 通过",
            "证据来自独立会话（reviewer_session_id != developer_session_id）",
        ],
    }
    return mark_schema_status(finding)


def verify_review_evidence(
    evidence_path: str,
    main_session_id: str = "",
    expected_files: Optional[list[str]] = None,
) -> dict:
    """Complete evidence verification for a quality-gate review.

    Args:
        evidence_path: Path to the review evidence JSON file
        main_session_id: Current main session ID (to detect self-review)
        expected_files: List of files that should have been reviewed

    Returns:
        {"valid": bool, "reason": str, "checks": {...}, "findings": [...]}
        ``findings`` (T-0108 F7) lists schema-validated fix-contract dicts
        for every failed check; empty when valid.
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
    failed: list[str] = []

    if not path.exists():
        failed.append("file_exists")
        return {"valid": False, "reason": f"Evidence file not found: {evidence_path}",
                "checks": checks,
                "findings": [_evidence_finding("file_exists", evidence_path)]}
    checks["file_exists"] = True

    try:
        content = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, Exception) as e:
        failed.append("valid_json")
        return {"valid": False, "reason": f"Invalid JSON: {e}", "checks": checks,
                "findings": [_evidence_finding("valid_json", evidence_path)]}
    checks["valid_json"] = True

    # 1. Anti-simulation
    if is_simulated(content):
        failed.append("not_simulated")
    else:
        checks["not_simulated"] = True

    # 2. Session ID
    if not has_valid_session_id(content):
        failed.append("has_session_id")
    else:
        checks["has_session_id"] = True

    # 3. Independence
    if not is_independent_session(content, main_session_id):
        failed.append("independent_session")
    else:
        checks["independent_session"] = True

    # 4. Required fields
    ok, missing = has_required_fields(content)
    if not ok:
        failed.append("required_fields")
    else:
        checks["required_fields"] = True

    # 5. File coverage (if expected files provided)
    if expected_files:
        reviewed = set(content.get("files_reviewed", []))
        expected = set(expected_files)
        uncovered = expected - reviewed
        if uncovered:
            failed.append("files_covered")
        else:
            checks["files_covered"] = True

    if failed:
        # Preserve legacy reason semantics: report the first failed check.
        first = failed[0]
        if first == "not_simulated":
            reason = "Evidence appears to be simulated/fabricated"
        elif first == "has_session_id":
            reason = "Missing or invalid reviewer_session_id"
        elif first == "independent_session":
            reason = "Reviewer session is not independent (self-review detected)"
        elif first == "required_fields":
            reason = f"Missing required fields: {missing}"
        else:
            reason = f"Not all files reviewed. Missing: {list(uncovered)[:5]}"
        return {
            "valid": False,
            "reason": reason,
            "checks": checks,
            "findings": [_evidence_finding(f, evidence_path) for f in failed],
        }

    return {"valid": True, "reason": "All evidence checks passed",
            "checks": checks, "findings": []}


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
