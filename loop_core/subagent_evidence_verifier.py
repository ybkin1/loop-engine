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
import os
import re
import sys
from pathlib import Path
from typing import Any, Optional

# T-0118: 独立脚本运行加固——项目根 sys.path 注入（本机 python312._pth
# 隔离模式下 cwd/PYTHONPATH 不可靠；hook 环境与本机直跑均可用）。
# 注意：必须位于 loop_core 导入之前（模块加载期即需解析包）。
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from loop_core.schemas.evidence_state import EvidenceState
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


# ── T-0121: ZCode 会话存在性核验（呈现层，advisory）────────────────────────
# 落地 T-0120 方案 A：sess_<uuid> 会话目录在 ZCode exec 目录中真实存在性核验。
# 设计约束：
#   - 仅呈现（结果 session_source 字段标注），不参与 verdict 判定、不改 checks
#   - fail-safe：exec 目录不可探测（换机/未安装/权限）时返回 unverified 且不抛错
#   - 不读取会话日志内容（存在性 ≠ 真实性；T-0112 边界保持）
ZCODE_SESSION_EXEC_DIR = str(Path.home() / ".zcode" / "cli" / "exec")


def _zcode_session_exec_dir() -> str:
    """ZCode 会话 exec 目录（运行时读取环境变量，支持注入/换机，fail-safe）。"""
    return os.environ.get("ZCODE_SESSION_EXEC_DIR", ZCODE_SESSION_EXEC_DIR)


def session_dir_exists(session_id: str) -> bool:
    """核验 sess_<uuid> 会话目录存在（呈现层；任何异常 → False，不抛错）。"""
    if not session_id or not session_id.startswith("sess_"):
        return False
    try:
        return (Path(_zcode_session_exec_dir()) / session_id).is_dir()
    except OSError:
        return False


def session_source_label(session_id: str) -> str:
    """会话来源标注：verified-zcode / unverified-zcode / external。

    - sess_<uuid> 格式且目录存在      → verified-zcode（本地可核验）
    - sess_<uuid> 格式但目录缺失      → unverified-zcode（存在性未证实）
    - 其他格式（外部会话 ID）         → external（非 ZCode 会话，按既有语义）
    """
    if not session_id:
        return "unavailable"
    if not session_id.startswith("sess_"):
        return "external"
    return "verified-zcode" if session_dir_exists(session_id) else "unverified-zcode"


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


# ── T-0118: checks → EvidenceState 七态映射（仅供呈现/度量）───────────────
# 设计约束（evidence_state.py）：七态不进 gate 判定路径；本映射只把
# verify_review_evidence 的 7 个布尔 checks 呈现为成熟度档位。
#
# 映射规则（阶梯：失败一律落在"已登记"档，全过才升档）：
#   file_exists=False                          → MISSING（应存在但缺失）
#   valid_json=False                           → PRESENT（存在但不可解析）
#   内容/会话/必填检查任一失败                  → PRESENT（存在但未达可信/溯源标准）
#   全部通过但 files_covered 未检查或失败      → EXERCISED（已执行，覆盖未完全验证）
#   全部通过                                   → OUTCOME_SUPPORTED（结果支撑结论）
# 注：WIRED/N-A/UNOBSERVED 不由此路径产生（接线/适用性/观测性由消费方
# 上下文判定，本模块无此类信息）。
def checks_to_evidence_state(checks: dict) -> EvidenceState:
    """把 7 布尔 checks 映射为 EvidenceState（T-0118，advisory-only）。"""
    if not checks.get("file_exists"):
        return EvidenceState.MISSING
    if not checks.get("valid_json"):
        return EvidenceState.PRESENT
    content_checks = ("not_simulated", "has_session_id",
                      "independent_session", "required_fields")
    if any(not checks.get(c) for c in content_checks):
        return EvidenceState.PRESENT
    if not checks.get("files_covered"):
        return EvidenceState.EXERCISED
    return EvidenceState.OUTCOME_SUPPORTED


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
                "findings": [_evidence_finding("file_exists", evidence_path)],
                "evidence_state": checks_to_evidence_state(checks).value,
                "session_source": "unavailable"}
    checks["file_exists"] = True

    try:
        content = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, Exception) as e:
        failed.append("valid_json")
        return {"valid": False, "reason": f"Invalid JSON: {e}", "checks": checks,
                "findings": [_evidence_finding("valid_json", evidence_path)],
                "evidence_state": checks_to_evidence_state(checks).value,
                "session_source": "unavailable"}
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
            "evidence_state": checks_to_evidence_state(checks).value,
            "session_source": session_source_label(content.get("reviewer_session_id", "")),
        }

    return {"valid": True, "reason": "All evidence checks passed",
            "checks": checks, "findings": [],
            "evidence_state": checks_to_evidence_state(checks).value,
            "session_source": session_source_label(content.get("reviewer_session_id", ""))}


# CLI entry for hook usage
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(json.dumps({"valid": False, "reason": "Usage: evidence_path [session_id]"}))
        sys.exit(1)
    
    evidence_path = sys.argv[1]
    session_id = sys.argv[2] if len(sys.argv) > 2 else ""
    
    result = verify_review_evidence(evidence_path, main_session_id=session_id)
    print(json.dumps(result, indent=2))
    sys.exit(0 if result["valid"] else 1)
