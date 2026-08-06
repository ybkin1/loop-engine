from __future__ import annotations

import json
import socket
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
    # KNOWN_ISSUES env-dependent 修复（T-0126）：端口注入 —— bind 一个本地
    # 端口但不 listen（连接必被 ConnectionRefused），并把 service_url 注入
    # checker。无论本机 localhost:3000/8000 是否被无关进程占用，service.startup
    # 都确定 FAIL（fail-closed 语义不变），测试不再依赖端口空闲环境。
    blocker = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    blocker.bind(("127.0.0.1", 0))
    port = blocker.getsockname()[1]  # bind 不 listen：对端连接必被拒绝
    try:
        result = run_full_runtime_gate(
            str(tmp_path), skip_browser=True,
            service_url=f"http://127.0.0.1:{port}",
        )
    finally:
        blocker.close()
    assert result["execution_mode"] == "SIMULATED_MAIN_SESSION"
    assert result["agent_takeover"] is False
    assert result["overall"] == "BLOCKED"
    assert all(c["status"] != "PASS" or c["id"] == "artifact.manifest" for c in result["checks"])
