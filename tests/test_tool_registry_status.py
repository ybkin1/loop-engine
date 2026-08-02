"""T-0100 (F-01): tool_registry_status --json 模式回归测试。

修复前：--json 模式打印合法 JSON 后因局部变量 death 未绑定（仅文本分支赋值）
触发 UnboundLocalError → 退出码 1（健康状态被误判为失败）。
修复后：--json 模式正常退出 0，输出合法 JSON；文本模式语义不变。
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TOOL = PROJECT_ROOT / "tools" / "tool_registry_status.py"


def _run(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(TOOL), *args],
        capture_output=True, text=True, cwd=str(PROJECT_ROOT), timeout=120,
    )


class TestRegistryJsonMode:
    def test_json_mode_exits_zero_with_valid_json(self):
        r = _run("--json")
        assert r.returncode == 0, f"exit={r.returncode} stderr={r.stderr!r}"
        data = json.loads(r.stdout)  # 合法 JSON（修复前在此处崩溃）
        assert "snapshot_id" in data
        assert "canonical_json" in data
        assert "bindings" in data
        assert data["integrity"]["overall"] == "PASS"

    def test_json_mode_guard_fail_closed_still_returns_2(self, monkeypatch):
        """AC-07：death fail-closed 语义不变 —— guard 不健康时 --json 仍退出 2。"""
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "tool_registry_status_t0100", TOOL)
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)
        monkeypatch.setattr(sys, "argv", ["tool_registry_status.py", "--json"])

        class FakeHealth:
            def integrity_check(self):
                return {
                    "missing": [], "drift": [],
                    "death": {"alive": 3, "dormant": 1, "broken": 1,
                              "overall": "FAIL"},
                    "overall": "FAIL",
                    "checked_at": "2026-08-02T00:00:00+00:00",
                }

        class FakeRegistry:
            def snapshot(self):
                class Snap:
                    snapshot_id = "0" * 64
                    canonical_json = "[]"
                    entries = {}

                return Snap()

        module.GuardHealth = lambda root, registry=None: FakeHealth()
        module.build_default_registry = lambda root: FakeRegistry()
        assert module.main() == 2  # death fail-closed，退出码 2 不变

    def test_text_mode_exits_zero(self):
        r = _run()
        assert r.returncode == 0, r.stderr
        assert "Capability registry snapshot" in r.stdout
        assert "Overall: PASS" in r.stdout
