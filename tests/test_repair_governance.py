"""T-0111 修复器治理 — repair 事件两分支 / 归类规则 / 兜底边界（AC-01~03）。

覆盖：
- AC-01: REPAIR_MODE 运行产生 guard-events check_type="repair" 事件
  （validate_state PASS/FAIL 两分支；close_session 收尾动态修复事件）。
- AC-02: fixed=0 连续场景归类 over_strict；fixed>0 归类
  unstable_generation；报告制不自动阻断（repair_trigger_rate /
  repair_classification 纯函数 + 集成）。
- AC-03: dynamic_only 不重算 semantic_sha256（含 source_sha256 不重算的
  可观测断言）；非 repair 模式 SOURCE_DRIFT 仍 exit 2 且不写 repair 事件。
- 向后兼容：既有消费者（load_guard_events / guard_anomaly_rates）对
  repair 事件不感知不报错（check_type 枚举扩展）。

硬约束落实：repair_continuity.py 零改动（本测试只读调用其函数）；
validate_state/close_session 判定语义零改动（只验证事件旁路写入）。
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
TOOLS = REPO / ".zcode" / "tools"

for _p in (str(REPO), str(TOOLS)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from loop_core.governance_metrics import (  # noqa: E402
    NOT_AVAILABLE,
    classify_repair_event,
    repair_classification,
    repair_trigger_rate,
)
from loop_core.observability import (  # noqa: E402
    CHECK_HEALTH,
    CHECK_REPAIR,
    RESULT_FAIL,
    RESULT_PASS,
    GuardCheckEvent,
    GuardEventRecorder,
)

# 治理工具只读复用（fixture 构建用；不修改任何工具代码）
from continuity_producer import _sha  # noqa: E402
from repair_continuity import repair_continuity  # noqa: E402


# ═══════════════════════════════════════════════════════════════════════════
# Fixture：最小治理项目（ProjectContinuity 从真实仓库载荷派生，schema 合法）
# ═══════════════════════════════════════════════════════════════════════════

REQUIRED_FILES = [
    "PROJECT.md", "NON_GOALS.md", "ARCHITECTURE.md", "CONTRACTS.md",
    "CODING_STANDARDS.md", "CONVENTIONS.md", "CODEMAP.md", "PROGRESS.md",
    "QUALITY_GATES.md", "ACCEPTANCE.md", "DECISIONS.md", "KNOWN_ISSUES.md",
    "state.yaml", "task_graph.yaml", "gates.yaml", "HANDOFF.md",
]

TASK_ID = "T-0111-TEST"


def _continuity(root: Path) -> dict:
    import yaml
    return yaml.safe_load((root / ".ai" / "project_continuity.yaml").read_text(
        encoding="utf-8"))


def _manifest_entry(root: Path, rel_path: str) -> dict:
    data = (root / rel_path).read_bytes()
    return {"path": rel_path, "sha256": _sha(data), "size": len(data)}


def _make_project(root: Path) -> Path:
    """构建可通过 validate_state 的治理项目。

    ProjectContinuity：载荷（project_continuity 段 + semantic_sha256）直接
    复用真实仓库文件（schema 合法由构造保证）；source_manifest 重建为
    本 fixture 的两个源文件（.ai/state.yaml 动态 + .ai/README.md 静态），
    source_sha256 按 canonical JSON 重算。
    """
    import yaml
    ai = root / ".ai"
    (ai / "tasks").mkdir(parents=True, exist_ok=True)
    (ai / "evidence" / "observability").mkdir(parents=True, exist_ok=True)

    for name in REQUIRED_FILES:
        (ai / name).write_text("", encoding="utf-8")
    (ai / "README.md").write_text("# fixture README\n", encoding="utf-8")

    (ai / "state.yaml").write_text(yaml.safe_dump({
        "schema_version": 1,
        "current_phase": "S6-delivery",
        "current_task_id": TASK_ID,
    }), encoding="utf-8")
    (ai / "tasks" / f"{TASK_ID}.md").write_text(
        f"# {TASK_ID}\n\n## Status\n\nactive\n", encoding="utf-8")
    (ai / "task_graph.yaml").write_text(yaml.safe_dump({
        "schema_version": 1,
        "tasks": [{"id": TASK_ID, "status": "active"}],
    }), encoding="utf-8")
    (ai / "gates.yaml").write_text(yaml.safe_dump({
        "schema_version": 1, "gates": [],
    }), encoding="utf-8")

    # ProjectContinuity：载荷复用真实仓库（schema 合法），清单重建
    real = yaml.safe_load((REPO / ".ai" / "project_continuity.yaml").read_text(
        encoding="utf-8"))
    manifest = [
        _manifest_entry(root, ".ai/state.yaml"),
        _manifest_entry(root, ".ai/README.md"),
    ]
    continuity = {
        "schema": "ProjectContinuity/v1",
        "contract_id": "PCC-2026-07-16-R1",
        "requirements_revision": "v1.0.0",
        "project_id": "loop-engine-test",
        "created_at": "2026-08-03T00:00:00Z",
        "created_by": "test-fixture",
        "authority_ref": "G-TEST",
        "source_manifest": manifest,
        "source_sha256": _sha(manifest),
        "semantic_sha256": real["semantic_sha256"],
        "project_continuity": real["project_continuity"],
    }
    (ai / "project_continuity.yaml").write_text(
        yaml.safe_dump(continuity, allow_unicode=True, sort_keys=False),
        encoding="utf-8")
    return root


def _drift(root: Path, rel_path: str) -> None:
    """让某清单源文件哈希漂移（追加一行）。"""
    p = root / rel_path
    p.write_text(p.read_text(encoding="utf-8") + "# drift\n", encoding="utf-8")


def _add_missing_manifest_entry(root: Path) -> None:
    """给清单加一个不存在的源条目 → 修复无物可修（fixed=0 FAIL 分支）。"""
    import yaml
    data = _continuity(root)
    data["source_manifest"] = data["source_manifest"] + [
        {"path": ".ai/nonexistent.md", "sha256": "A" * 64, "size": 1},
    ]
    data["source_sha256"] = _sha(data["source_manifest"])
    (root / ".ai" / "project_continuity.yaml").write_text(
        yaml.safe_dump(data, allow_unicode=True, sort_keys=False),
        encoding="utf-8")


def _run_validate_state(root: Path, repair: bool) -> subprocess.CompletedProcess:
    env = dict(os.environ)
    env.pop("LOOP_REPAIR_CONTINUITY", None)
    if repair:
        env["LOOP_REPAIR_CONTINUITY"] = "1"
    return subprocess.run(
        [sys.executable, str(TOOLS / "validate_state.py"), str(root)],
        capture_output=True, text=True, env=env, timeout=120,
    )


def _read_repair_events(root: Path) -> list[GuardCheckEvent]:
    rec = GuardEventRecorder(
        root / ".ai" / "evidence" / "observability" / "guard-events.jsonl")
    return [e for e in rec.read_events() if e.check_type == CHECK_REPAIR]


# ═══════════════════════════════════════════════════════════════════════════
# AC-01: REPAIR_MODE 产生 repair 事件（PASS/FAIL 两分支）
# ═══════════════════════════════════════════════════════════════════════════

class TestRepairEvents:
    def test_repair_mode_pass_branch_writes_repair_event(self, tmp_path):
        """SOURCE_DRIFT + REPAIR_MODE → repair 成功（fixed>0）+ 重新校验
        通过 → 事件 PASS，failure_reason 带漂移类型与 fixed 计数。"""
        root = _make_project(tmp_path / "proj")
        _drift(root, ".ai/state.yaml")
        proc = _run_validate_state(root, repair=True)
        assert proc.returncode == 0, proc.stdout + proc.stderr

        events = _read_repair_events(root)
        assert len(events) == 1
        ev = events[0]
        assert ev.guard_id == "repair_continuity"
        assert ev.result == RESULT_PASS
        assert "SOURCE_DRIFT" in (ev.failure_reason or "")
        assert "fixed=1" in (ev.failure_reason or "")
        # 修复确实落盘：state.yaml 清单条目哈希已同步
        data = _continuity(root)
        entry = next(i for i in data["source_manifest"]
                     if i["path"] == ".ai/state.yaml")
        assert entry["sha256"] == _sha(
            (root / ".ai" / "state.yaml").read_bytes())

    def test_repair_mode_fail_branch_writes_repair_event(self, tmp_path):
        """清单含不存在的源文件 → 修复 fixed=0 → 事件 FAIL + exit 2。"""
        root = _make_project(tmp_path / "proj")
        _add_missing_manifest_entry(root)
        proc = _run_validate_state(root, repair=True)
        assert proc.returncode == 2

        events = _read_repair_events(root)
        assert len(events) == 1
        ev = events[0]
        assert ev.result == RESULT_FAIL
        assert "fixed=0" in (ev.failure_reason or "")

    def test_close_session_dynamic_repair_writes_event(self, tmp_path):
        """close_session 收尾动态修复写 PASS 事件（dynamic fixed=N）。"""
        root = _make_project(tmp_path / "proj")
        _drift(root, ".ai/state.yaml")
        proc = subprocess.run(
            [sys.executable, str(TOOLS / "close_session.py"), str(root)],
            capture_output=True, text=True, timeout=120,
        )
        # 事件写入点在判定之前（旁路观测）；close_session 后续判定结果不
        # 影响事件存在性 —— 只断言事件本身
        events = _read_repair_events(root)
        assert len(events) == 1, proc.stdout + proc.stderr
        ev = events[0]
        assert ev.result == RESULT_PASS
        assert "dynamic fixed=1" in (ev.failure_reason or "")

    def test_repair_events_loadable_by_existing_consumers(self, tmp_path):
        """向后兼容：load_guard_events（strict-parse）与 guard_anomaly_rates
        对 repair 事件不感知、不报错（check_type 枚举扩展）。"""
        from loop_core.governance_aggregations import guard_anomaly_rates
        from loop_core.governance_loaders import load_guard_events

        root = _make_project(tmp_path / "proj")
        _drift(root, ".ai/state.yaml")
        proc = _run_validate_state(root, repair=True)
        assert proc.returncode == 0

        events = load_guard_events(root)  # 不抛 DataSourceUnavailableError
        repairs = [e for e in events if e.check_type == CHECK_REPAIR]
        assert len(repairs) == 1
        rates = guard_anomaly_rates(events)
        assert rates["by_check_type"].get("repair", 0) == 1  # 消费者仍可计数


# ═══════════════════════════════════════════════════════════════════════════
# AC-02: 归类规则（报告制，不自动阻断）
# ═══════════════════════════════════════════════════════════════════════════

def _ev(check_type, result, failure_reason, guard_id="repair_continuity"):
    return GuardCheckEvent(
        guard_id=guard_id, check_type=check_type, result=result,
        duration_ms=0.0, failure_reason=failure_reason,
        timestamp="2026-08-03T00:00:00Z", source="tool:test",
    )


class TestRepairClassification:
    def test_fixed_gt_zero_is_unstable_generation(self):
        ev = _ev(CHECK_REPAIR, RESULT_PASS, "SOURCE_DRIFT fixed=3")
        assert classify_repair_event(ev) == "unstable_generation"

    def test_fixed_zero_fail_is_over_strict(self):
        ev = _ev(CHECK_REPAIR, RESULT_FAIL,
                 "SOURCE_DRIFT fixed=0 (auto-repair found nothing to fix)")
        assert classify_repair_event(ev) == "over_strict"

    def test_fixed_zero_pass_is_benign(self):
        # 动态收尾 fixed=0 = 正常无漂移，不是校验过严
        ev = _ev(CHECK_REPAIR, RESULT_PASS, "dynamic fixed=0")
        assert classify_repair_event(ev) == "benign"

    def test_unparseable_reason_is_benign(self):
        ev = _ev(CHECK_REPAIR, RESULT_FAIL, "dynamic repair failed: boom")
        assert classify_repair_event(ev) == "benign"

    def test_consecutive_over_strict_runs_detected(self):
        """fixed=0 连续场景（AC-02）：两连 FAIL fixed=0 记一段连续段。"""
        events = [
            _ev(CHECK_REPAIR, RESULT_FAIL, "SOURCE_DRIFT fixed=0 (nothing)"),
            _ev(CHECK_REPAIR, RESULT_FAIL, "SOURCE_DRIFT fixed=0 (nothing)"),
            _ev(CHECK_REPAIR, RESULT_PASS, "dynamic fixed=0"),  # 打断
            _ev(CHECK_REPAIR, RESULT_FAIL, "SOURCE_DRIFT fixed=0 (nothing)"),
        ]
        out = repair_classification(events)
        assert out["status"] == "computed"
        assert out["over_strict"] == 3
        assert out["benign"] == 1
        assert out["over_strict_runs"] == 1  # [0,1] 一段；[3] 单条不成段

    def test_aggregate_counts_all_three_classes(self):
        events = [
            _ev(CHECK_REPAIR, RESULT_PASS, "SOURCE_DRIFT fixed=2"),   # unstable
            _ev(CHECK_REPAIR, RESULT_FAIL, "SOURCE_DRIFT fixed=0 (x)"),  # over
            _ev(CHECK_REPAIR, RESULT_PASS, "dynamic fixed=0"),        # benign
        ]
        out = repair_classification(events)
        assert out["unstable_generation"] == 1
        assert out["over_strict"] == 1
        assert out["benign"] == 1
        assert len(out["events"]) == 3

    def test_no_repair_events_is_not_available(self):
        out = repair_classification([_ev(CHECK_HEALTH, RESULT_PASS, None,
                                         "gate_guard")])
        assert out["status"] == NOT_AVAILABLE

    def test_classification_is_report_only_no_blocking(self):
        """报告制不自动阻断：归类结果只进报告字段，函数无副作用且不
        触碰任何 gate 判定路径（纯函数断言：两次调用结果一致）。"""
        events = [
            _ev(CHECK_REPAIR, RESULT_FAIL, "SOURCE_DRIFT fixed=0 (x)"),
            _ev(CHECK_REPAIR, RESULT_PASS, "SOURCE_DRIFT fixed=1"),
        ]
        assert repair_classification(events) == repair_classification(events)


class TestRepairTriggerRate:
    def test_rate_computed(self):
        events = [
            _ev(CHECK_HEALTH, RESULT_PASS, None, "gate_guard"),
            _ev(CHECK_REPAIR, RESULT_PASS, "SOURCE_DRIFT fixed=2"),
        ]
        out = repair_trigger_rate(events)
        assert out["status"] == "computed"
        assert out["repair_events"] == 1
        assert out["total_events"] == 2
        assert out["rate"] == 0.5

    def test_zero_repairs_is_zero_rate(self):
        out = repair_trigger_rate([_ev(CHECK_HEALTH, RESULT_PASS, None,
                                       "gate_guard")])
        assert out["status"] == "computed"
        assert out["rate"] == 0.0

    def test_empty_events_not_available(self):
        assert repair_trigger_rate([])["status"] == NOT_AVAILABLE

    def test_integration_with_real_repair_run(self, tmp_path):
        """端到端：REPAIR_MODE 运行后的 guard-events 直接喂指标。"""
        root = _make_project(tmp_path / "proj")
        _drift(root, ".ai/state.yaml")
        proc = _run_validate_state(root, repair=True)
        assert proc.returncode == 0

        rec = GuardEventRecorder(
            root / ".ai" / "evidence" / "observability" / "guard-events.jsonl")
        events = rec.read_events()
        rate = repair_trigger_rate(events)
        assert rate["repair_events"] == 1
        cls = repair_classification(events)
        # 本事件 fixed=1（>0）→ unstable_generation
        assert cls["unstable_generation"] == 1
        assert cls["over_strict"] == 0


# ═══════════════════════════════════════════════════════════════════════════
# AC-03: 兜底边界 —— dynamic_only 不重算 semantic_sha256；非 repair 硬阻断
# ═══════════════════════════════════════════════════════════════════════════

class TestFallbackBoundaries:
    def test_dynamic_only_does_not_recompute_semantic_sha256(self, tmp_path):
        """repair_continuity 零改动（只读验证）：dynamic_only 只修三个动态
        条目，semantic_sha256 与 source_sha256 均不重算（哈希值不变 →
        证明 :54-56 重算块被跳过）。"""
        root = _make_project(tmp_path / "proj")
        _drift(root, ".ai/state.yaml")   # 动态条目漂移
        _drift(root, ".ai/README.md")    # 静态条目漂移

        before = _continuity(root)
        sem_before = before["semantic_sha256"]
        src_before = before["source_sha256"]

        result = repair_continuity(root, dynamic_only=True)
        assert result["fixed"] == 1  # 只修 state.yaml

        after = _continuity(root)
        assert after["semantic_sha256"] == sem_before  # 语义哈希永不自动修复
        assert after["source_sha256"] == src_before    # 清单哈希同样不重算

        state_entry = next(i for i in after["source_manifest"]
                           if i["path"] == ".ai/state.yaml")
        readme_entry = next(i for i in after["source_manifest"]
                            if i["path"] == ".ai/README.md")
        assert state_entry["sha256"] == _sha(
            (root / ".ai" / "state.yaml").read_bytes())   # 动态条目已修
        assert readme_entry["sha256"] != _sha(
            (root / ".ai" / "README.md").read_bytes())    # 静态条目未动

    def test_full_repair_does_recompute_source_sha256(self, tmp_path):
        """对照组：全量模式重算 source_sha256（manifest 变化 → 哈希变化
        可观测），证明 dynamic_only 的"不重算"是可区分行为。"""
        root = _make_project(tmp_path / "proj")
        _drift(root, ".ai/state.yaml")
        src_before = _continuity(root)["source_sha256"]
        repair_continuity(root)  # 全量模式
        src_after = _continuity(root)["source_sha256"]
        assert src_after != src_before  # manifest 已更新 → 重算后变化

    def test_non_repair_mode_source_drift_still_exit_2(self, tmp_path):
        """fail-closed 语义不变：非 REPAIR_MODE 下 SOURCE_DRIFT 仍 exit 2
        且不写任何 repair 事件（自动修复未触发）。"""
        root = _make_project(tmp_path / "proj")
        _drift(root, ".ai/state.yaml")
        proc = _run_validate_state(root, repair=False)
        assert proc.returncode == 2
        assert "Continuity source drift" in proc.stdout
        assert "SOURCE_DRIFT" in str(proc.stdout) or "source drift" in proc.stdout
        assert _read_repair_events(root) == []
        # 清单未被修复（fail-closed 不动文件）
        state_entry = next(i for i in _continuity(root)["source_manifest"]
                           if i["path"] == ".ai/state.yaml")
        assert state_entry["sha256"] != _sha(
            (root / ".ai" / "state.yaml").read_bytes())

    def test_dynamic_only_repair_never_touches_other_files(self, tmp_path):
        """dynamic_only 只写 project_continuity.yaml（原子写语义保持，
        repair_continuity.py 零改动下的只读行为验证）。"""
        root = _make_project(tmp_path / "proj")
        _drift(root, ".ai/state.yaml")
        before = {
            p.name: p.read_bytes()
            for p in (root / ".ai").iterdir() if p.is_file()
        }
        repair_continuity(root, dynamic_only=True)
        after = {
            p.name: p.read_bytes()
            for p in (root / ".ai").iterdir() if p.is_file()
        }
        for name in before:
            if name == "project_continuity.yaml":
                continue  # 修复器唯一允许写的文件
            assert after[name] == before[name], f"意外改动: {name}"
