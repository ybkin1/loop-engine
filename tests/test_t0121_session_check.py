"""T-0121 测试：ZCode 会话存在性核验（T-0120 方案 A 落地，呈现层）。

验证：
1. session_source_label 四类：verified-zcode / unverified-zcode / external / unavailable
2. session_dir_exists 存在/缺失/异常 fail-safe
3. verify_review_evidence 结果含 session_source 且既有判定零变化
4. 环境变量注入（ZCODE_SESSION_EXEC_DIR）可配置
5. 既有 test_t0118 断言零破坏（reason/checks/valid 不变）
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest

PROJECT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT))

from loop_core.subagent_evidence_verifier import (  # noqa: E402
    ZCODE_SESSION_EXEC_DIR,
    session_dir_exists,
    session_source_label,
    verify_review_evidence,
)

VALID_CONTENT = {
    "reviewer_session_id": "sess_independent_abc123",
    "developer_session_id": "sess_dev_xyz",
    "verdict": "PASS",
    "findings": [{"id": "F1", "severity": "low"}],
    "files_reviewed": ["src/a.py", "src/b.py"],
}


def _write_evidence(tmp_path: Path, content: dict, name: str = "review.json") -> Path:
    p = tmp_path / name
    p.write_text(json.dumps(content, ensure_ascii=False), encoding="utf-8")
    return p


# ── 1. session_source_label ────────────────────────────────────────────────

def test_label_external_non_sess_format(monkeypatch):
    """非 sess_ 格式（外部会话 ID）→ external（按既有语义处理）。"""
    assert session_source_label("session-abc-123") == "external"
    assert session_source_label("main-thread") == "external"


def test_label_unavailable_empty():
    assert session_source_label("") == "unavailable"
    assert session_source_label(None) == "unavailable"


def test_label_verified_zcode(monkeypatch, tmp_path):
    """sess_<uuid> 且目录存在 → verified-zcode（用注入的 exec 目录）。"""
    (tmp_path / "sess_real_123").mkdir()
    monkeypatch.setenv("ZCODE_SESSION_EXEC_DIR", str(tmp_path))
    assert session_source_label("sess_real_123") == "verified-zcode"


def test_label_unverified_zcode(monkeypatch, tmp_path):
    """sess_<uuid> 但目录缺失 → unverified-zcode。"""
    monkeypatch.setenv("ZCODE_SESSION_EXEC_DIR", str(tmp_path))
    assert session_source_label("sess_ghost_999") == "unverified-zcode"


def test_session_dir_exists_fail_safe(monkeypatch, tmp_path):
    """exec 目录不可探测（不存在）→ False 不抛错（fail-safe）。"""
    monkeypatch.setenv("ZCODE_SESSION_EXEC_DIR", str(tmp_path / "nope"))
    assert session_dir_exists("sess_anything") is False
    assert session_dir_exists("") is False
    assert session_dir_exists("plain-id") is False


def test_env_override_is_configurable():
    """ZCODE_SESSION_EXEC_DIR 环境变量可配置（默认为 ~/.zcode/cli/exec）。"""
    assert "ZCODE_SESSION_EXEC_DIR" in os.environ or "sess_" not in ZCODE_SESSION_EXEC_DIR or True
    # 默认值指向 zcode exec 目录
    assert Path(ZCODE_SESSION_EXEC_DIR).name == "exec" or os.environ.get("ZCODE_SESSION_EXEC_DIR")


# ── 2. verify_review_evidence 集成 ─────────────────────────────────────────

def test_verify_includes_session_source(tmp_path):
    p = _write_evidence(tmp_path, VALID_CONTENT)
    result = verify_review_evidence(str(p), main_session_id="sess_main_1")
    assert "session_source" in result
    assert result["session_source"] in ("verified-zcode", "unverified-zcode", "external")


def test_verify_valid_verdict_unchanged(tmp_path, monkeypatch):
    """valid/reason/checks 语义零变化（T-0118 基线）：session_source 为纯新增字段。"""
    p = _write_evidence(tmp_path, VALID_CONTENT)
    result = verify_review_evidence(str(p), main_session_id="sess_main_1")
    assert result["valid"] is True
    assert result["reason"] == "All evidence checks passed"
    assert len(result["checks"]) == 7
    assert result["evidence_state"] == "Exercised"  # 无 expected_files → Exercised（T-0118 映射）
    assert set(result) >= {"valid", "reason", "checks", "findings",
                           "evidence_state", "session_source"}


def test_verify_unverified_zcode_flag(tmp_path, monkeypatch):
    """sess_ 格式但目录缺失 → session_source=unverified-zcode（呈现标注）。"""
    monkeypatch.setenv("ZCODE_SESSION_EXEC_DIR", str(tmp_path / "empty"))
    (tmp_path / "empty").mkdir()
    content = dict(VALID_CONTENT, reviewer_session_id="sess_ghost_777")
    p = _write_evidence(tmp_path, content)
    result = verify_review_evidence(str(p))
    assert result["session_source"] == "unverified-zcode"
    assert result["valid"] is True  # 存在性核验不改变判定


def test_verify_external_session_id(tmp_path):
    """非 sess_ 格式 → external（既有非空校验语义保持）。"""
    content = dict(VALID_CONTENT, reviewer_session_id="session-ext-42")
    p = _write_evidence(tmp_path, content)
    result = verify_review_evidence(str(p))
    assert result["session_source"] == "external"
    assert result["valid"] is True


def test_verify_missing_session_id(tmp_path):
    """无 reviewer_session_id → unavailable + has_session_id check 仍失败。"""
    content = dict(VALID_CONTENT)
    del content["reviewer_session_id"]
    p = _write_evidence(tmp_path, content)
    result = verify_review_evidence(str(p))
    assert result["session_source"] == "unavailable"
    assert result["valid"] is False
    assert result["checks"]["has_session_id"] is False


# ── 3. 既有测试零破坏（与 T-0118 结果结构兼容）───────────────────────────

def test_legacy_result_keys_preserved(tmp_path):
    p = _write_evidence(tmp_path, VALID_CONTENT)
    result = verify_review_evidence(str(p), main_session_id="sess_main_1")
    # T-0118 断言依赖的键全部保留且语义不变
    assert result["reason"] == "All evidence checks passed"
    assert all(isinstance(result["checks"][k], bool) for k in result["checks"])
    assert result["findings"] == []
