"""
test_t0109_f2_write_convergence.py — T-0109 F2-2 状态写入收敛逐线测试。

AC 对照（T-0109 任务卡 AC-02）：
- 写入收敛后仅 governor_lib 写 state 相关路径（静态检查）
- 双写告警清零（收敛写 → 无 `[warn] stale view`；未收敛写 → 告警仍在）
- projection 刷新（状态转换后派生视图 .ai/views/state-view.yaml 自动更新）

设计要点（design-bh-integration.md F2 阶段 2 + 任务书 F2-2）：
- 写路径统一经 governor_lib 事务写（transactional_write_texts 既有机制）
  + projection 刷新（复用 T-0108 projection_engine.write_state_view）
- state_machine.atomic_write_state 保持为唯一权威 state.yaml 写入入口，
  仅加「转换后触发 projection 刷新」调用（不改决策语义）
- 静态检查为只读 grep/解析断言；遗留写路径（executor/runtime_controller/
  zcode_adapter/loop_auto_activate）不在 T-0109 allowed_paths，未改动，
  以「文档化遗留例外」显式列入白名单——新增未登记写路径即测试失败
"""
from __future__ import annotations

import ast
import os
import re
import subprocess
import sys
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

REPO_ROOT = Path(__file__).resolve().parent.parent

# ── 状态五写路径（静态检查覆盖清单）──────────────────────────────
STATE_RELATED = ("state.yaml", "task_graph.yaml", "HANDOFF.md", "PROGRESS.md", "tasks/")
WRITE_OP = re.compile(r"write_text|write_bytes|os\.replace|\.write\(")

# 收敛写入口全名单（每项附理由；新增 state 写路径未登记 → 测试失败）
SANCTIONED_WRITERS = {
    ".zcode/tools/governor_lib.py",   # 收敛写库本身（transactional_write_texts / write_state_files）
    ".zcode/tools/close_session.py",  # 经 governor_lib 事务写（既有收敛，T-0058 起）
    "scripts/install.py",             # 经 governor_lib 事务写
    "scripts/upgrade.py",             # 经 governor_lib 事务写
    "loop_core/state_machine.py",     # 唯一权威 state.yaml 写入口（F2-2 保持 + projection 刷新）
    "loop_core/projection_engine.py",  # 派生视图写（write_state_view，T-0108 F2-1 起）
}

# 遗留写路径（T-0109 未改动；治理收敛范围外；硬约束：hooks/ 零改动）
LEGACY_WRITERS = {
    "loop_core/executor.py": "PhaseExecutor 遗留持久化（T-0110 拆分目标）",
    "loop_core/runtime_controller.py": "S0-init onboard 引导 ensure-file（遗留初始化路径）",
    "loop_engine/adapters/zcode_adapter.py": "host adapter save_state API（适配层遗留）",
    "hooks/scripts/loop_auto_activate.py": "SessionStart 自动激活写 loop_mode（hooks 零改动）",
}

# 防篡改 manifest 修复（仅重写 project_continuity.yaml，非状态五写）
MANIFEST_REPAIR_WRITERS = {
    ".zcode/tools/repair_continuity.py",
}

# 代码引用 state 路径 + 写操作，但写目标非状态五写（快照/报告/事件日志/自测 fixture）
NON_STATE_WRITERS = {
    "loop_core/dashboard_views.py",   # 快照 .md/.html/.json
    "loop_core/dashboard_status.py",  # T-0124 拆分：Dashboard/ProjectStatus 迁入（state.yaml 仅读 + 快照写）
    "loop_core/evals.py",             # eval 报告输出
    "loop_core/slo_gate.py",          # slo exemptions 文件
    "loop_core/guard_health.py",      # 自测 fixture（临时目录）
    "hooks/scripts/hook_common.py",   # 仅 stdout/stderr 写
    "hooks/scripts/loop_enforcement.py",  # guard-events 计数文件（事件日志）
    "hooks/scripts/role_isolation.py",    # 仅 stdout 写
    "hooks/scripts/session_brief.py",     # 仅 stdout 写
    "tools/loop_onboard.py",          # AGENTS.md/skills 模板拷贝（state 仅读）
    ".zcode/tools/validate_state.py", # T-0111 repair 事件写 guard-events.jsonl（事件日志，非状态五写）
    ".zcode/tools/event_log.py",      # T-0155 事件溯源影子层：追加写 state-events.jsonl（事件日志，非状态五写）
}


def _code_string_literals(text: str) -> set[str]:
    """AST 提取代码级字符串字面量（剥离 docstring；注释不产生字面量）。"""
    tree = ast.parse(text)
    literals: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            literals.add(node.value)

    def drop_docstring(body) -> None:
        if (
            body
            and isinstance(body[0], ast.Expr)
            and isinstance(body[0].value, ast.Constant)
            and isinstance(body[0].value.value, str)
        ):
            literals.discard(body[0].value.value)

    drop_docstring(tree.body)
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            drop_docstring(node.body)
    return literals


def _state_write_candidates() -> dict[str, set[str]]:
    """仓库级扫描：代码级引用 state 路径 + 写操作的文件（排除 tests/archive/
    .ai/evidence 等非治理代码目录）。返回 {rel_path: {命中的 state 路径}}。"""
    results: dict[str, set[str]] = {}
    skip_dirs = {"tests", "archive", "evidence", "__pycache__", "lab", "dist",
                 "build", ".git", "node_modules", "vertical_slice", "seeded_defects", "references"}
    scan_roots = [".zcode/tools", "loop_core", "hooks/scripts", "tools", "scripts",
                  "src", "loop_engine"]
    for root in scan_roots:
        base = REPO_ROOT / root
        if not base.exists():
            continue
        for f in sorted(base.rglob("*.py")):
            if any(part in skip_dirs for part in f.parts):
                continue
            text = f.read_text(encoding="utf-8")
            try:
                literals = _code_string_literals(text)
            except SyntaxError:
                continue
            if not WRITE_OP.search(text):
                continue
            hits = {s for s in STATE_RELATED if any(s in lit for lit in literals)}
            if hits:
                results[f.relative_to(REPO_ROOT).as_posix()] = hits
    return results


# ============================================================================
# AC-02: 静态检查「仅 governor_lib 写 state 相关路径」
# ============================================================================


class TestStaticWriteConvergence:
    def test_all_state_write_candidates_registered(self):
        """仓库内所有「state 路径引用 + 写操作」文件必须登记在
        收敛/遗留/manifest/非状态写 四类白名单之一；未登记 → FAIL。"""
        candidates = _state_write_candidates()
        registered = (
            set(SANCTIONED_WRITERS)
            | set(LEGACY_WRITERS)
            | set(MANIFEST_REPAIR_WRITERS)
            | set(NON_STATE_WRITERS)
        )
        unknown = set(candidates) - registered
        assert not unknown, (
            f"未登记的 state 写路径文件（AC-02 违反——状态写入须仅经 "
            f"governor_lib/登记入口）: {sorted(unknown)}"
        )
        assert candidates, "扫描应至少命中收敛写入口（自检）"

    def test_categories_are_disjoint(self):
        legacy = set(LEGACY_WRITERS)
        assert SANCTIONED_WRITERS.isdisjoint(legacy)
        assert SANCTIONED_WRITERS.isdisjoint(MANIFEST_REPAIR_WRITERS)
        assert SANCTIONED_WRITERS.isdisjoint(NON_STATE_WRITERS)
        assert legacy.isdisjoint(MANIFEST_REPAIR_WRITERS)
        assert legacy.isdisjoint(NON_STATE_WRITERS)
        assert MANIFEST_REPAIR_WRITERS.isdisjoint(NON_STATE_WRITERS)

    def test_tools_and_scripts_writers_use_governor_lib_transaction(self):
        """.zcode/tools 与 scripts 的收敛写入口必须引用 governor_lib 事务写
        （transactional_write_texts / write_state_files）。"""
        for rel in SANCTIONED_WRITERS:
            if not (rel.startswith(".zcode/tools/") or rel.startswith("scripts/")):
                continue
            text = (REPO_ROOT / rel).read_text(encoding="utf-8")
            assert re.search(
                r"transactional_write_texts|write_state_files", text
            ), f"{rel} 未经 governor_lib 事务写"

    def test_state_machine_is_single_authoritative_entry(self):
        """loop_core 中引用 state.yaml + 写操作的文件集合被钉死为登记名单
        （state_machine = 唯一权威全量写入口；executor/runtime_controller =
        遗留；projection_engine = 视图写；guard_health = 自测 fixture）。
        新增未登记写路径 → FAIL。"""
        core_writers = {
            rel for rel, hits in _state_write_candidates().items()
            if rel.startswith("loop_core/") and "state.yaml" in hits
        }
        expected = {
            "loop_core/state_machine.py",      # 唯一权威入口（F2-2 + projection 刷新）
            "loop_core/executor.py",           # 遗留：PhaseExecutor 持久化
            "loop_core/runtime_controller.py",  # 遗留：S0-init onboard 引导
            "loop_core/projection_engine.py",  # 派生视图写（读 state.yaml 派生）
            "loop_core/guard_health.py",       # 自测 fixture（临时目录）
            # T-0109 F5 dashboard 合并：Dashboard._load_state 随 status_dashboard
            # 收敛至 dashboard_views（只读呈现 + 快照 .md/.html/.json 写，非状态
            # 五写；NON_STATE_WRITERS 已登记。state_machine 仍为唯一权威写入口）。
            # T-0124 拆分：Dashboard/ProjectStatus 移入 dashboard_status 外部模块
            #（写路径随迁，dashboard_views 为同名 re-export 壳）。
            "loop_core/dashboard_status.py",
        }
        assert core_writers == expected, (
            f"loop_core state.yaml 写路径集合漂移: "
            f"新增={sorted(core_writers - expected)} 缺失={sorted(expected - core_writers)}"
        )


# ============================================================================
# F2-2: projection 刷新（状态转换后派生视图自动更新）
# ============================================================================


def _make_project(root: Path) -> None:
    ai = root / ".ai"
    (ai / "tasks").mkdir(parents=True)
    (ai / "state.yaml").write_text(
        "schema_version: 1\ncurrent_phase: S0-init\ncurrent_task_id: null\n"
        "current_gate_id: null\nloop_mode: FULL\n",
        encoding="utf-8",
    )
    (ai / "task_graph.yaml").write_text("schema_version: 1\ntasks: []\n", encoding="utf-8")


class TestProjectionRefreshOnStateWrite:
    def test_atomic_write_state_refreshes_view(self, tmp_path):
        from loop_core.state_machine import atomic_write_state

        _make_project(tmp_path)
        assert not (tmp_path / ".ai" / "views" / "state-view.yaml").exists()
        atomic_write_state(tmp_path, {
            "schema_version": 1,
            "current_phase": "S4-implementation",
            "current_task_id": "T-0001",
            "current_gate_id": "G-T-0001",
            "loop_mode": "FULL",
        })
        view_path = tmp_path / ".ai" / "views" / "state-view.yaml"
        assert view_path.exists(), "状态转换后派生视图未刷新"
        import yaml
        view = yaml.safe_load(view_path.read_text(encoding="utf-8"))
        assert view["phase"] == "S4-implementation"
        assert view["source"] == "state.yaml"

    def test_atomic_write_state_view_not_stale(self, tmp_path):
        from loop_core.projection_engine import is_state_view_stale
        from loop_core.state_machine import atomic_write_state

        _make_project(tmp_path)
        atomic_write_state(tmp_path, {"current_phase": "S1-requirements"})
        stale, _age = is_state_view_stale(tmp_path)
        assert stale is False, "收敛写后视图不应 stale（双写告警清零前置条件）"

    def test_refresh_failure_non_fatal_with_warning(self, tmp_path, monkeypatch):
        """刷新失败不回滚权威写；显式告警（绝不静默吞错）。"""
        from loop_core.state_machine import atomic_write_state

        _make_project(tmp_path)
        import loop_core.projection_engine as pe
        monkeypatch.setattr(
            pe, "write_state_view",
            lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom")),
        )
        with pytest.warns(UserWarning, match="STATE_VIEW_REFRESH_FAILED"):
            atomic_write_state(tmp_path, {"current_phase": "S2-architecture"})
        state_path = tmp_path / ".ai" / "state.yaml"
        assert "S2-architecture" in state_path.read_text(encoding="utf-8")

    def test_write_state_files_refreshes_view_and_rejects_non_state(self, tmp_path):
        sys.path.insert(0, str(REPO_ROOT / ".zcode" / "tools"))
        from governor_lib import GovernanceError, write_state_files

        _make_project(tmp_path)
        state_path = tmp_path / ".ai" / "state.yaml"
        result = write_state_files(tmp_path, {
            state_path: "current_phase: S3-interface\nloop_mode: FULL\n",
        })
        assert result is not None
        view_path = tmp_path / ".ai" / "views" / "state-view.yaml"
        assert view_path.exists()
        import yaml
        assert yaml.safe_load(view_path.read_text(encoding="utf-8"))["phase"] == "S3-interface"

        # 非 state 相关路径 → SCOPE_VIOLATION（fail-closed 不静默）
        with pytest.raises(GovernanceError) as exc:
            write_state_files(tmp_path, {tmp_path / ".ai" / "gates.yaml": "x\n"})
        assert exc.value.code == "SCOPE_VIOLATION"
        # .ai 外路径 → SCOPE_VIOLATION
        with pytest.raises(GovernanceError) as exc:
            write_state_files(tmp_path, {tmp_path / "notes.txt": "x\n"})
        assert exc.value.code == "SCOPE_VIOLATION"

    def test_write_state_files_accepts_task_card_and_handoff(self, tmp_path):
        sys.path.insert(0, str(REPO_ROOT / ".zcode" / "tools"))
        from governor_lib import write_state_files

        _make_project(tmp_path)
        task_card = tmp_path / ".ai" / "tasks" / "T-0001.md"
        handoff = tmp_path / ".ai" / "HANDOFF.md"
        write_state_files(tmp_path, {
            task_card: "# T-0001\n\n## Status\n\npending\n",
            handoff: "# Handoff\n",
        }, refresh_projection=False)
        assert task_card.read_text(encoding="utf-8").startswith("# T-0001")
        assert handoff.read_text(encoding="utf-8").startswith("# Handoff")

    def test_write_state_files_idempotent_kwargs_passthrough(self, tmp_path):
        sys.path.insert(0, str(REPO_ROOT / ".zcode" / "tools"))
        from governor_lib import write_state_files

        _make_project(tmp_path)
        state_path = tmp_path / ".ai" / "state.yaml"
        content = "current_phase: S5-quality\nloop_mode: FULL\n"
        r1 = write_state_files(tmp_path, {state_path: content}, idempotent=True,
                               refresh_projection=False)
        assert r1.written == [str(state_path)]
        r2 = write_state_files(tmp_path, {state_path: content}, idempotent=True,
                               refresh_projection=False)
        assert r2.skipped == [str(state_path)]  # 幂等表去重


# ============================================================================
# F2-2: 双写告警清零（收敛写 → 无 stale view 告警；未收敛写 → 告警仍在）
# ============================================================================


class TestDualWriteWarningZeroed:
    def test_raw_write_without_refresh_warns(self, tmp_path):
        """未收敛写（直接写 state.yaml 不刷新视图）→ 双写检测告警仍在。"""
        sys.path.insert(0, str(REPO_ROOT / ".zcode" / "tools"))
        from validate_state import check_state_view_freshness
        from loop_core.projection_engine import write_state_view

        _make_project(tmp_path)
        view_path = write_state_view(tmp_path)  # 先有视图
        state_path = tmp_path / ".ai" / "state.yaml"
        # 直接裸写（不刷新视图）——模拟未收敛写路径；并把视图 mtime 置为
        # 早于 state.yaml（确定性双写条件，规避 Windows mtime 粒度）
        state_path.write_text("current_phase: S6-delivery\nloop_mode: FULL\n", encoding="utf-8")
        old = state_path.stat().st_mtime - 60
        os.utime(view_path, (old, old))
        warns = check_state_view_freshness(tmp_path, tmp_path / ".ai")
        assert any("[warn] stale view" in w for w in warns), warns

    def test_converged_write_no_warning(self, tmp_path):
        """收敛写（经 state_machine 权威入口）→ 视图随写刷新 → 告警清零。"""
        sys.path.insert(0, str(REPO_ROOT / ".zcode" / "tools"))
        from validate_state import check_state_view_freshness
        from loop_core.state_machine import atomic_write_state

        _make_project(tmp_path)
        atomic_write_state(tmp_path, {"current_phase": "S6-delivery", "loop_mode": "FULL"})
        time.sleep(1.05)
        warns = check_state_view_freshness(tmp_path, tmp_path / ".ai")
        assert not any("[warn] stale view" in w for w in warns), warns

    def test_validate_state_no_stale_after_converged_write(self, tmp_path):
        """集成：收敛写后 validate_state 输出不含 `[warn] stale view`。"""
        from loop_core.state_machine import atomic_write_state

        _make_project(tmp_path)
        atomic_write_state(tmp_path, {
            "schema_version": 1,
            "project_name": "tmp",
            "current_phase": "S0-init",
            "current_task_id": None,
            "current_gate_id": None,
            "loop_mode": "FULL",
        })
        r = subprocess.run(
            [sys.executable, str(REPO_ROOT / ".zcode" / "tools" / "validate_state.py"),
             str(tmp_path)],
            capture_output=True, text=True,
        )
        out = r.stdout + r.stderr
        assert "stale view" not in out, out
