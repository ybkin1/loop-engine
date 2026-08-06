"""T-0118 测试：subagent_evidence_verifier 七态映射消费。

验证：
1. checks_to_evidence_state 映射表（全过→Outcome-supported；file 缺失→Missing；
   内容/会话/字段失败→Present；仅覆盖失败→Exercised）
2. verify_review_evidence 结果含 evidence_state 字段且与 valid/checks 一致
3. 既有行为零变化（valid/reason/checks/findings 语义不变；CLI 退出码不变）
4. 七态仅呈现层：映射函数不引用任何 gate 判定路径（静态断言）
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

PROJECT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT))

from loop_core.schemas.evidence_state import EvidenceState  # noqa: E402
from loop_core.subagent_evidence_verifier import (  # noqa: E402
    checks_to_evidence_state,
    verify_review_evidence,
)


VALID_CONTENT = {
    "reviewer_session_id": "sess_independent_abc123",
    "developer_session_id": "sess_dev_xyz",
    "verdict": "PASS",
    "findings": [{"id": "F1", "severity": "low"}],
    "files_reviewed": ["src/a.py", "src/b.py"],
}


def _write_evidence(tmp_path: Path, content: dict | str, name: str = "review.json") -> Path:
    p = tmp_path / name
    if isinstance(content, str):
        p.write_text(content, encoding="utf-8")
    else:
        p.write_text(json.dumps(content, ensure_ascii=False), encoding="utf-8")
    return p


# ── 1. 映射表 ───────────────────────────────────────────────────────────────

def test_mapping_all_pass_outcome_supported():
    checks = {k: True for k in ("file_exists", "valid_json", "not_simulated",
                                "has_session_id", "independent_session",
                                "required_fields", "files_covered")}
    assert checks_to_evidence_state(checks) == EvidenceState.OUTCOME_SUPPORTED


def test_mapping_file_missing():
    checks = {k: False for k in ("file_exists", "valid_json", "not_simulated",
                                 "has_session_id", "independent_session",
                                 "required_fields", "files_covered")}
    assert checks_to_evidence_state(checks) == EvidenceState.MISSING


def test_mapping_invalid_json():
    checks = {"file_exists": True, "valid_json": False,
              "not_simulated": False, "has_session_id": False,
              "independent_session": False, "required_fields": False,
              "files_covered": False}
    assert checks_to_evidence_state(checks) == EvidenceState.PRESENT


@pytest.mark.parametrize("failed_check", [
    "not_simulated", "has_session_id", "independent_session", "required_fields",
])
def test_mapping_content_failure_present(failed_check: str):
    checks = {k: True for k in ("file_exists", "valid_json", "not_simulated",
                                "has_session_id", "independent_session",
                                "required_fields", "files_covered")}
    checks[failed_check] = False
    assert checks_to_evidence_state(checks) == EvidenceState.PRESENT


def test_mapping_coverage_failure_exercised():
    checks = {k: True for k in ("file_exists", "valid_json", "not_simulated",
                                "has_session_id", "independent_session",
                                "required_fields")}
    checks["files_covered"] = False
    assert checks_to_evidence_state(checks) == EvidenceState.EXERCISED


def test_mapping_coverage_unchecked_exercised():
    """expected_files 未提供（files_covered 未检查，保持 False）→ Exercised。"""
    checks = {k: True for k in ("file_exists", "valid_json", "not_simulated",
                                "has_session_id", "independent_session",
                                "required_fields")}
    checks["files_covered"] = False
    assert checks_to_evidence_state(checks) == EvidenceState.EXERCISED


def test_state_value_is_serializable():
    """evidence_state 字段为七态字符串值（JSON 可序列化）。"""
    assert checks_to_evidence_state(
        {k: True for k in ("file_exists", "valid_json", "not_simulated",
                           "has_session_id", "independent_session",
                           "required_fields", "files_covered")}).value == "Outcome-supported"


# ── 2. verify_review_evidence 集成 ─────────────────────────────────────────

def test_verify_valid_outcome_supported(tmp_path):
    p = _write_evidence(tmp_path, VALID_CONTENT)
    result = verify_review_evidence(str(p), main_session_id="sess_main_1",
                                    expected_files=["src/a.py", "src/b.py"])
    assert result["valid"] is True
    assert result["evidence_state"] == EvidenceState.OUTCOME_SUPPORTED.value
    assert result["findings"] == []


def test_verify_valid_without_expected_files_exercised(tmp_path):
    p = _write_evidence(tmp_path, VALID_CONTENT)
    result = verify_review_evidence(str(p), main_session_id="sess_main_1")
    assert result["valid"] is True
    assert result["evidence_state"] == EvidenceState.EXERCISED.value


def test_verify_missing_file_missing(tmp_path):
    result = verify_review_evidence(str(tmp_path / "nope.json"))
    assert result["valid"] is False
    assert result["evidence_state"] == EvidenceState.MISSING.value
    assert result["checks"]["file_exists"] is False


def test_verify_invalid_json_present(tmp_path):
    p = _write_evidence(tmp_path, "{:not json::")
    result = verify_review_evidence(str(p))
    assert result["valid"] is False
    assert result["evidence_state"] == EvidenceState.PRESENT.value
    assert result["checks"]["valid_json"] is False


def test_verify_simulated_present(tmp_path):
    content = dict(VALID_CONTENT, summary="Simulated output for demo")
    p = _write_evidence(tmp_path, content)
    result = verify_review_evidence(str(p))
    assert result["valid"] is False
    assert result["evidence_state"] == EvidenceState.PRESENT.value
    assert result["checks"]["not_simulated"] is False


def test_verify_self_review_present(tmp_path):
    """reviewer_session_id 与主会话相同 → 自审检测（T-0067 语义）。"""
    p = _write_evidence(tmp_path, VALID_CONTENT)
    result = verify_review_evidence(str(p), main_session_id="sess_independent_abc123")
    assert result["valid"] is False
    assert result["evidence_state"] == EvidenceState.PRESENT.value
    assert result["checks"]["independent_session"] is False


def test_verify_missing_fields_present(tmp_path):
    content = dict(VALID_CONTENT)
    del content["verdict"]
    p = _write_evidence(tmp_path, content)
    result = verify_review_evidence(str(p))
    assert result["valid"] is False
    assert result["evidence_state"] == EvidenceState.PRESENT.value
    assert result["checks"]["required_fields"] is False


def test_verify_coverage_failure_exercised(tmp_path):
    p = _write_evidence(tmp_path, VALID_CONTENT)
    result = verify_review_evidence(str(p), main_session_id="sess_main_1",
                                    expected_files=["src/a.py", "src/b.py", "src/c.py"])
    assert result["valid"] is False
    assert result["evidence_state"] == EvidenceState.EXERCISED.value
    assert result["checks"]["files_covered"] is False
    assert result["checks"]["not_simulated"] is True


# ── 3. 既有行为零变化 ──────────────────────────────────────────────────────

def test_legacy_fields_preserved(tmp_path):
    """valid/reason/checks/findings 语义与 T-0108 F7 前一致（add-only）。"""
    p = _write_evidence(tmp_path, VALID_CONTENT)
    result = verify_review_evidence(str(p), main_session_id="sess_main_1",
                                    expected_files=["src/a.py", "src/b.py"])
    assert set(result) >= {"valid", "reason", "checks", "findings", "evidence_state"}
    assert result["reason"] == "All evidence checks passed"
    assert len(result["checks"]) == 7


def test_cli_exit_code_unchanged(tmp_path):
    """CLI 退出码语义不变：valid→0，invalid→1（hooks trace-only 调用依赖）。"""
    p = _write_evidence(tmp_path, VALID_CONTENT)
    r = subprocess.run([sys.executable, str(PROJECT / "loop_core" / "subagent_evidence_verifier.py"),
                        str(p), "sess_main_1"], capture_output=True, text=True, timeout=60)
    assert r.returncode == 0
    payload = json.loads(r.stdout)
    assert payload["evidence_state"] in EvidenceState.values()

    bad = _write_evidence(tmp_path, "{bad", name="bad.json")
    r2 = subprocess.run([sys.executable, str(PROJECT / "loop_core" / "subagent_evidence_verifier.py"),
                         str(bad)], capture_output=True, text=True, timeout=60)
    assert r2.returncode == 1


# ── 4. 呈现层静态断言 ──────────────────────────────────────────────────────

def test_mapping_not_used_in_gate_decision():
    """七态映射只呈现：映射函数所在模块不被 gate 判定路径引用（AC 断言）。"""
    verifier_src = (PROJECT / "loop_core" / "subagent_evidence_verifier.py").read_text(encoding="utf-8")
    assert "should_allow_write" not in verifier_src
    assert "can_approve_gate" not in verifier_src
    evidence_state_src = (PROJECT / "loop_core" / "schemas" / "evidence_state.py").read_text(encoding="utf-8")
    assert "不提供任何 gate 判定函数" in evidence_state_src
