from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.deployment_quality_checker import check_build_consistency, check_rollback_readiness
from scripts.runtime_delivery_gate import run_full_runtime_gate


def test_build_consistency_fails_missing_static_dir(tmp_path: Path) -> None:
    (tmp_path / ".next").mkdir()
    (tmp_path / ".next" / "BUILD_ID").write_text("build-1")
    result = check_build_consistency(str(tmp_path))
    assert result["consistent"] is False
    assert any(c["check"] == "static_dir" for c in result["checks"])


def test_build_consistency_checks_deploy_build_id(tmp_path: Path) -> None:
    for root, value in ((tmp_path / "source", "same"), (tmp_path / "deploy", "different")):
        (root / ".next").mkdir(parents=True)
        (root / ".next" / "BUILD_ID").write_text(value)
        (root / ".next" / "static").mkdir()
    result = check_build_consistency(str(tmp_path / "source"), str(tmp_path / "deploy"))
    assert result["consistent"] is False
    assert any(c["check"] == "deploy_build_id" for c in result["checks"])


def test_rollback_requires_build_id_file(tmp_path: Path) -> None:
    (tmp_path / ".next.old").mkdir()
    result = check_rollback_readiness(str(tmp_path))
    assert result["rollback_ready"] is False


def test_runtime_report_is_simulated_and_fail_closed(tmp_path: Path) -> None:
    result = run_full_runtime_gate(str(tmp_path), skip_browser=True)
    assert result["execution_mode"] == "SIMULATED_MAIN_SESSION"
    assert result["agent_takeover"] is False
    assert result["overall"] == "BLOCKED"
    assert all(c["status"] != "PASS" or c["id"] == "artifact.manifest" for c in result["checks"])
