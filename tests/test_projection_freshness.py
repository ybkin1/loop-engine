"""
test_projection_freshness.py — 投影新鲜度测试（T-0108 F8 / F2-1，AC-05）。

覆盖：
- 投影视图 = state.yaml 派生（同一输入逐字段一致；task_status 来自
  task_graph.yaml 权威源）；
- mtime 新鲜度：视图 mtime 早于 state.yaml → stale（伪造旧 mtime 用例）；
- 视图缺失 → 不报 stale（无视图可比）；
- validate_state 集成：伪造旧 mtime 视图 → 输出 `[warn] stale view`，
  仅告警——error 集合与 exit code 与无视图时完全一致（AC-04 回归）。

约束（design F8 必须保持）：测试只读（临时目录内自建 state/视图，不触碰
真实仓库 .ai/）。
"""
from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from loop_core.projection_engine import (
    STATE_VIEW_SCHEMA,
    generate_state_view,
    is_state_view_stale,
    write_state_view,
)

VALIDATE_STATE = (
    Path(__file__).resolve().parent.parent / ".zcode" / "tools" / "validate_state.py"
)


def _make_project(root: Path, state_text: str, graph_text: str) -> Path:
    ai = root / ".ai"
    (ai / "views").mkdir(parents=True)
    (ai / "state.yaml").write_text(state_text, encoding="utf-8")
    (ai / "task_graph.yaml").write_text(graph_text, encoding="utf-8")
    return ai


# ============================================================================
# 视图 = state.yaml 派生（AC-05 一致性）
# ============================================================================


class TestStateViewConsistency:
    def test_view_matches_state_fields(self, tmp_path):
        ai = _make_project(
            tmp_path,
            "schema_version: 1\nproject_name: Loop Engine\n"
            "current_phase: S6-delivery\ncurrent_task_id: T-0108\n"
            "current_gate_id: G-T-0108-REQUIREMENTS\nloop_mode: FULL\n"
            "last_handoff_at: '2026-08-03T18:00:00+08:00'\n",
            "tasks:\n  - id: T-0108\n    status: in_progress\n",
        )
        view = generate_state_view(tmp_path)
        assert view["schema"] == STATE_VIEW_SCHEMA
        assert view["phase"] == "S6-delivery"
        assert view["current_task_id"] == "T-0108"
        assert view["current_gate_id"] == "G-T-0108-REQUIREMENTS"
        assert view["loop_mode"] == "FULL"
        assert view["task_status"] == "in_progress"
        assert view["derived_summary"]["phase"] == "S6-delivery"

    def test_deterministic_same_input(self, tmp_path):
        """同一输入 → 逐字段一致（一致性测试）。"""
        ai = _make_project(
            tmp_path,
            "current_phase: S4-implementation\ncurrent_task_id: T-0001\n",
            "tasks:\n  - id: T-0001\n    status: active\n",
        )
        v1 = generate_state_view(tmp_path)
        v2 = generate_state_view(tmp_path)
        assert v1 == v2

    def test_task_status_derived_from_task_graph(self, tmp_path):
        """task_status 派生自 task_graph.yaml（权威源），不手改。"""
        _make_project(
            tmp_path,
            "current_phase: S4-implementation\ncurrent_task_id: T-0009\n",
            "tasks:\n  - id: T-0009\n    status: completed\n",
        )
        assert generate_state_view(tmp_path)["task_status"] == "completed"

    def test_missing_state_raises(self, tmp_path):
        try:
            generate_state_view(tmp_path)
            assert False, "expected FileNotFoundError"
        except FileNotFoundError:
            pass


# ============================================================================
# mtime 新鲜度（AC-05 / AC-04）
# ============================================================================


class TestViewFreshness:
    def test_no_view_not_stale(self, tmp_path):
        _make_project(
            tmp_path, "current_phase: S0-init\n",
            "tasks: []\n",
        )
        stale, age = is_state_view_stale(tmp_path)
        assert stale is False and age is None

    def test_fresh_view_not_stale(self, tmp_path):
        _make_project(
            tmp_path, "current_phase: S0-init\n",
            "tasks: []\n",
        )
        write_state_view(tmp_path)
        stale, age = is_state_view_stale(tmp_path)
        assert stale is False

    def test_forged_old_mtime_is_stale(self, tmp_path):
        """伪造旧 mtime 视图 → stale（AC-05 新鲜度）。"""
        _make_project(
            tmp_path, "current_phase: S0-init\n",
            "tasks: []\n",
        )
        view_path = write_state_view(tmp_path)
        old = time.time() - 7200
        os.utime(view_path, (old, old))
        stale, age = is_state_view_stale(tmp_path)
        assert stale is True
        assert age is not None and age > 7000

    def test_validate_state_warns_stale_only(self, tmp_path):
        """AC-04：validate_state 对伪造旧 mtime 视图报 [warn] stale view，
        仅告警——error 集合与 exit code 与无视图时完全一致。"""
        ai = _make_project(
            tmp_path,
            "schema_version: 1\ncurrent_phase: S0-init\n",
            "tasks: []\n",
        )
        view_path = ai / "views" / "state-view.yaml"
        view_path.write_text("schema: state-view/v1\n", encoding="utf-8")
        old = time.time() - 3600
        os.utime(view_path, (old, old))

        r_with = subprocess.run(
            [sys.executable, str(VALIDATE_STATE), str(tmp_path)],
            capture_output=True, text=True,
        )
        out_with = r_with.stdout + r_with.stderr
        assert "[warn] stale view" in out_with, out_with

        view_path.unlink()
        r_without = subprocess.run(
            [sys.executable, str(VALIDATE_STATE), str(tmp_path)],
            capture_output=True, text=True,
        )
        out_without = r_without.stdout + r_without.stderr
        assert "stale view" not in out_without
        # 既有判定零变化：error 集合与 exit code 完全一致
        errors_with = sorted(
            l for l in out_with.splitlines() if l.startswith("[error]")
        )
        errors_without = sorted(
            l for l in out_without.splitlines() if l.startswith("[error]")
        )
        assert errors_with == errors_without
        assert r_with.returncode == r_without.returncode
