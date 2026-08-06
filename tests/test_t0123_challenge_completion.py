"""T-0123 测试：ROLE_CHALLENGES 补全 + certification_runner 共享常量。

验证：
1. ROLE_CHALLENGES 覆盖 12/12（含 test-engineer CHALLENGE-TE-001）
2. test-engineer 可认证（certify 流程走通）
3. certification_runner 使用共享 schema 常量（无第二处字面量）
4. security_report/v1 字面量全仓唯一（loop_core 定义处）
5. 既有 11 项 challenge 内容零变化
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT))

from loop_core.role_capability import (  # noqa: E402
    ROLE_CHALLENGES,
    ROLE_IDS,
    CapabilityStatus,
    RoleCapabilityProfile,
    check_role_admission,
    create_default_profiles,
)


# ── 1. ROLE_CHALLENGES 12/12 ───────────────────────────────────────────────

def test_all_roles_have_challenges():
    """每个 ROLE_IDS 角色都有 challenge（12/12 覆盖）。"""
    missing = [r for r in ROLE_IDS if r not in ROLE_CHALLENGES]
    assert missing == [], f"缺 challenge 的角色: {missing}"
    assert len(ROLE_CHALLENGES) == 12


def test_test_engineer_challenge_defined():
    """test-engineer challenge 定义完整（CHALLENGE-TE-001）。"""
    ch = ROLE_CHALLENGES["test-engineer"]
    assert ch.challenge_id == "CHALLENGE-TE-001"
    assert ch.role_id == "test-engineer"
    assert ch.description
    assert ch.required_tools == ["pytest"]
    assert len(ch.seeded_defects) >= 1
    assert len(ch.pass_conditions) >= 1


def test_test_engineer_certifiable():
    """test-engineer 可通过 challenge 认证（准入流程走通）。"""
    profiles = create_default_profiles()
    te = profiles["test-engineer"]
    assert te.status == CapabilityStatus.UNCERTIFIED
    te.certify("CHALLENGE-TE-001")
    assert te.status == CapabilityStatus.CERTIFIED
    assert te.can_accept_production_task()[0]


def test_challenge_ids_unique():
    """challenge_id 全唯一（无重复）。"""
    ids = [ch.challenge_id for ch in ROLE_CHALLENGES.values()]
    assert len(ids) == len(set(ids))


def test_existing_challenges_unchanged():
    """既有 11 项 challenge 的 challenge_id 保持（零修改）。"""
    expected = {
        "quality-engineer": "CHALLENGE-QA-001",
        "security-engineer": "CHALLENGE-SEC-001",
        "developer": "CHALLENGE-DEV-001",
        "independent-reviewer": "CHALLENGE-REV-001",
        "main-thread": "CHALLENGE-MAIN-001",
        "product-manager": "CHALLENGE-PM-001",
        "project-manager": "CHALLENGE-PJ-001",
        "system-architect": "CHALLENGE-SA-001",
        "module-architect": "CHALLENGE-MA-001",
        "delivery-manager": "CHALLENGE-DM-001",
        "release-engineer": "CHALLENGE-RE-001",
    }
    for role, cid in expected.items():
        assert ROLE_CHALLENGES[role].challenge_id == cid


# ── 2. certification_runner 共享常量 ───────────────────────────────────────

def test_certification_runner_uses_shared_schema():
    """certification_runner 引用共享常量，无第二处 schema 字面量。"""
    src = (PROJECT / "scripts" / "certification_runner.py").read_text(encoding="utf-8")
    assert "SECURITY_REPORT_V1_SCHEMA" in src
    assert '"security_report/v1"' not in src, "certification_runner 不得含字面量"
    assert "'security_report/v1'" not in src


def test_schema_literal_single_source():
    """security_report/v1 字面量仅 loop_core 定义处（单数据源）。"""
    scanner_src = (PROJECT / "loop_core" / "security_scanner.py").read_text(encoding="utf-8")
    assert scanner_src.count('"security_report/v1"') >= 1
    # 其余引用方不得含字面量（run_security_scan/certification_runner）
    for rel in ["agents/security-engineer/scripts/run_security_scan.py",
                "scripts/certification_runner.py"]:
        src = (PROJECT / rel).read_text(encoding="utf-8")
        assert '"security_report/v1"' not in src, f"{rel} 不得含字面量"


def test_certification_runner_imports_ok():
    """certification_runner 可导入（sys.path 注入 + 共享常量引用有效）。"""
    r = subprocess.run(
        [sys.executable, "-c",
         "import sys; sys.path.insert(0, r'" + str(PROJECT) + "'); "
         "import scripts.certification_runner as cr; "
         "print('OK', cr.SECURITY_REPORT_V1_SCHEMA)"],
        capture_output=True, text=True, timeout=60)
    assert r.returncode == 0, r.stderr[-500:]
    assert "security_report/v1" in r.stdout
