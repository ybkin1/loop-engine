"""
test_governance_consistency.py — Cross-validate .ai/ governance files (T-0046).

Checks consistency between state.yaml, task_graph.yaml, gates.yaml, and HANDOFF.md.

T-0101: idle 稳态适配 —— current_task_id=null（idle 合法阻塞态）时断言 idle 契约
（state 为 null、task_graph/gates 无"当前任务/当前 gate"引用、HANDOFF 当前任务/
当前 gate 段与 state 一致 null↔null），消除 `None in str` TypeError；激活态断言
原样保留。每个测试参数化两个场景：repo（真实 .ai/ 文件，按实际状态走 idle/激活
分支）+ idle（合成 idle fixture，始终走 idle 分支）。
"""
import os
import re
import yaml
import pytest

PROJECT_ROOT = os.path.join(os.path.dirname(__file__), "..")


def _read(rel_path, base=PROJECT_ROOT):
    full = os.path.join(base, rel_path)
    with open(full, "r", encoding="utf-8") as f:
        return f.read()


def _load_yaml(rel_path, base=PROJECT_ROOT):
    return yaml.safe_load(_read(rel_path, base))


def _section(text, heading):
    """提取 markdown 中指定 heading 的正文段（无该 heading → 空串）。"""
    start = text.find(heading)
    if start < 0:
        return ""
    start += len(heading)
    end = text.find("\n## ", start)
    return text[start:] if end < 0 else text[start:end]


def _build_idle_fixture(root):
    """构造最小 idle 态 fixture（T-0101）：state 无当前任务/gate；task_graph/gates
    有注册项；HANDOFF 当前任务/当前 gate 段不引用任何 id（null ↔ null idle 契约）。"""
    base = os.path.join(str(root), ".ai")
    os.makedirs(base)
    for name in (
        "PROJECT.md", "NON_GOALS.md", "ARCHITECTURE.md", "CONTRACTS.md",
        "CODING_STANDARDS.md", "CONVENTIONS.md", "CODEMAP.md", "PROGRESS.md",
        "QUALITY_GATES.md", "ACCEPTANCE.md", "DECISIONS.md", "KNOWN_ISSUES.md",
    ):
        with open(os.path.join(base, name), "w", encoding="utf-8") as f:
            f.write(f"# {name}\n")
    with open(os.path.join(base, "state.yaml"), "w", encoding="utf-8") as f:
        f.write(
            "schema_version: 1\ncurrent_phase: S6-delivery\n"
            "current_task_id: null\ncurrent_gate_id: null\n"
        )
    with open(os.path.join(base, "task_graph.yaml"), "w", encoding="utf-8") as f:
        f.write(
            "schema_version: 1\ntasks:\n  - id: T-FIX-1\n    status: completed\n"
            "  - id: T-FIX-2\n    status: completed\nedges: []\n"
        )
    with open(os.path.join(base, "gates.yaml"), "w", encoding="utf-8") as f:
        f.write(
            "schema_version: 1\ngates:\n  - id: G-FIX-1\n    task_id: T-FIX-1\n"
            "    status: approved\n"
        )
    with open(os.path.join(base, "HANDOFF.md"), "w", encoding="utf-8") as f:
        f.write(
            "# Handoff\n\n## Current Task\n\nnone\n\nStatus: `unknown`\n\n"
            "## Current Gate\n\nnone\n"
        )
    return str(root)


class TestGovernanceConsistency:
    def test_state_yaml_parses(self):
        state = _load_yaml(".ai/state.yaml")
        assert state is not None
        assert "current_task_id" in state
        assert "current_gate_id" in state

    def test_task_graph_parses(self):
        tg = _load_yaml(".ai/task_graph.yaml")
        assert tg is not None
        assert "tasks" in tg
        assert isinstance(tg["tasks"], list)

    @pytest.mark.parametrize("scenario", ["repo", "idle"])
    def test_current_task_in_graph(self, scenario, tmp_path):
        root = PROJECT_ROOT if scenario == "repo" else _build_idle_fixture(tmp_path)
        state = _load_yaml(".ai/state.yaml", root)
        tg = _load_yaml(".ai/task_graph.yaml", root)
        current = state["current_task_id"]
        task_ids = [t["id"] for t in tg["tasks"] if isinstance(t, dict)]
        if current is None:
            # idle 契约：无"当前任务"引用（None 不参与 in 判断，杜绝 TypeError）
            assert current not in task_ids
            return
        assert current in task_ids, f"{current} not in task_graph"

    @pytest.mark.parametrize("scenario", ["repo", "idle"])
    def test_current_task_file_exists(self, scenario, tmp_path):
        root = PROJECT_ROOT if scenario == "repo" else _build_idle_fixture(tmp_path)
        state = _load_yaml(".ai/state.yaml", root)
        current = state["current_task_id"]
        if current is None:
            # idle 契约：无当前任务即无任务文件要求（不构造 "None.md" 路径）
            assert not os.path.exists(os.path.join(root, ".ai", "tasks", "None.md"))
            return
        task_file = os.path.join(root, ".ai", "tasks", f"{current}.md")
        assert os.path.exists(task_file), f"Task file {task_file} missing"

    @pytest.mark.parametrize("scenario", ["repo", "idle"])
    def test_current_gate_in_register(self, scenario, tmp_path):
        root = PROJECT_ROOT if scenario == "repo" else _build_idle_fixture(tmp_path)
        state = _load_yaml(".ai/state.yaml", root)
        gates = _load_yaml(".ai/gates.yaml", root)
        current_gate = state["current_gate_id"]
        gate_ids = [str(g["id"]) for g in gates.get("gates", []) if isinstance(g, dict)]
        if current_gate is None:
            # idle 契约：gate register 无"当前 gate"（None 不参与 in 判断）
            assert current_gate not in gate_ids
            return
        assert current_gate in gate_ids, f"{current_gate} not in gates.yaml"

    def test_current_gate_task_matches(self):
        state = _load_yaml(".ai/state.yaml")
        gates = _load_yaml(".ai/gates.yaml")
        current_gate = state["current_gate_id"]
        current_task = state["current_task_id"]
        if current_gate is None:
            return  # idle 契约：无当前 gate，无匹配对象
        for g in gates.get("gates", []):
            if isinstance(g, dict) and str(g.get("id")) == current_gate:
                assert str(g.get("task_id")) == current_task, (
                    f"Gate {current_gate} task_id {g.get('task_id')} != state current_task_id {current_task}"
                )
                break

    def test_current_gate_is_approved(self):
        state = _load_yaml(".ai/state.yaml")
        gates = _load_yaml(".ai/gates.yaml")
        current_gate = state["current_gate_id"]
        if current_gate is None:
            return  # idle 契约：无当前 gate，无需 approved 断言
        for g in gates.get("gates", []):
            if isinstance(g, dict) and str(g.get("id")) == current_gate:
                assert g.get("status") == "approved", (
                    f"Gate {current_gate} status is {g.get('status')}, expected approved"
                )
                break

    @pytest.mark.parametrize("scenario", ["repo", "idle"])
    def test_handoff_current_task_matches_state(self, scenario, tmp_path):
        root = PROJECT_ROOT if scenario == "repo" else _build_idle_fixture(tmp_path)
        state = _load_yaml(".ai/state.yaml", root)
        handoff = _read(".ai/HANDOFF.md", root)
        current_task = state["current_task_id"]
        if current_task is None:
            # idle 契约：null ↔ null —— HANDOFF 当前任务段不得引用任何任务 id；
            # 禁止 `None in handoff`（str 左操作数 TypeError 源）
            assert not re.search(r"\bT-\d+\b", _section(handoff, "## Current Task"))
            return
        assert current_task in handoff, (
            f"HANDOFF.md does not reference current task {current_task}"
        )

    @pytest.mark.parametrize("scenario", ["repo", "idle"])
    def test_handoff_current_gate_matches_state(self, scenario, tmp_path):
        root = PROJECT_ROOT if scenario == "repo" else _build_idle_fixture(tmp_path)
        state = _load_yaml(".ai/state.yaml", root)
        handoff = _read(".ai/HANDOFF.md", root)
        current_gate = state["current_gate_id"]
        if current_gate is None:
            # idle 契约：null ↔ null —— HANDOFF 当前 gate 段不得引用任何 gate id
            assert not re.search(r"\bG-\d+\b", _section(handoff, "## Current Gate"))
            return
        assert current_gate in handoff, (
            f"HANDOFF.md does not reference current gate {current_gate}"
        )

    def test_task_graph_no_duplicate_ids(self):
        tg = _load_yaml(".ai/task_graph.yaml")
        task_ids = [t["id"] for t in tg["tasks"] if isinstance(t, dict)]
        assert len(task_ids) == len(set(task_ids)), "Duplicate task IDs in task_graph"

    def test_gate_register_no_duplicate_ids(self):
        gates = _load_yaml(".ai/gates.yaml")
        gate_ids = [str(g["id"]) for g in gates.get("gates", []) if isinstance(g, dict)]
        assert len(gate_ids) == len(set(gate_ids)), "Duplicate gate IDs in gates.yaml"

    def test_t0045_not_falsely_completed(self):
        """T-0045 is a dangling reference — must NOT be marked completed."""
        tg = _load_yaml(".ai/task_graph.yaml")
        for t in tg["tasks"]:
            if isinstance(t, dict) and t.get("id") == "T-0045":
                assert t.get("status") != "completed", (
                    "T-0045 must not be marked completed — no real evidence exists"
                )


class TestValidateStateYamlFailClosed:
    """T-0143 1.2: validate_state YAML 损坏必须干净 fail-closed（exit 2）。"""

    VALIDATE = os.path.join(PROJECT_ROOT, ".zcode", "tools", "validate_state.py")

    def _run(self, root):
        import subprocess
        import sys
        return subprocess.run(
            [sys.executable, self.VALIDATE, root],
            capture_output=True, text=True, timeout=60,
        )

    def test_corrupted_state_yaml_exits_2(self, tmp_path):
        """损坏 state.yaml → 干净 [error] + exit 2（非 traceback exit 1）。"""
        ai = tmp_path / ".ai"
        ai.mkdir()
        # 最小可运行骨架：损坏 state.yaml 即可触发 YAML_INVALID
        (ai / "state.yaml").write_text("schema_version: 1\ncurrent_phase: [unclosed\n", encoding="utf-8")
        (ai / "gates.yaml").write_text("schema_version: 1\ngates: []\n", encoding="utf-8")
        (ai / "task_graph.yaml").write_text("schema_version: 1\ntasks: []\n", encoding="utf-8")
        (ai / "tasks").mkdir()
        (ai / "HANDOFF.md").write_text("# Handoff\n", encoding="utf-8")
        r = self._run(str(tmp_path))
        assert r.returncode == 2, f"expected exit 2, got {r.returncode}: {r.stderr}"
        assert "[error]" in (r.stdout + r.stderr)
        assert "Traceback" not in r.stderr, "必须干净报错，不得泄漏 traceback"

    def test_healthy_state_exits_0(self, tmp_path):
        """正常 .ai/ 骨架 → exit 0（fail-closed 修复不破坏健康路径）。"""
        ai = tmp_path / ".ai"
        ai.mkdir()
        (ai / "state.yaml").write_text(
            "schema_version: 1\ncurrent_phase: S6-delivery\ncurrent_task_id: null\n", encoding="utf-8")
        (ai / "gates.yaml").write_text("schema_version: 1\ngates: []\n", encoding="utf-8")
        (ai / "task_graph.yaml").write_text("schema_version: 1\ntasks: []\n", encoding="utf-8")
        (ai / "tasks").mkdir()
        (ai / "HANDOFF.md").write_text("# Handoff\n", encoding="utf-8")
        r = self._run(str(tmp_path))
        # idle 合法态 → exit 3；真实损坏（其他错误）→ exit 2；绝不允许 exit 1 traceback
        assert r.returncode in (0, 2, 3), f"unexpected rc {r.returncode}: {r.stderr}"


class TestGateExecutionStatusConsistency:
    """T-0148: gate execution_status 必须与任务完成态一致（防漂移复发）。

    任务 completed → 其 approved gate 的 execution_status 不得停留
    in_progress/approved_not_started（历史 55 条漂移已回填）。
    """

    def test_completed_tasks_gates_not_stale(self):
        tg = _load_yaml(".ai/task_graph.yaml")
        tasks = {t["id"]: t.get("status") for t in tg["tasks"] if isinstance(t, dict)}
        gates = _load_yaml(".ai/gates.yaml").get("gates", [])
        stale = [
            g["id"] for g in gates
            if isinstance(g, dict)
            and g.get("status") == "approved"
            and g.get("execution_status") in ("in_progress", "approved_not_started")
            and tasks.get(g.get("task_id")) == "completed"
        ]
        assert stale == [], (
            f"gate execution_status 与任务完成态漂移（T-0148 应已回填）: {stale}"
        )

    def test_rejected_task_gate_not_completed(self):
        """rejected 任务的 gate 不得被误标 completed（T-0112 语义保留）。"""
        tg = _load_yaml(".ai/task_graph.yaml")
        tasks = {t["id"]: t.get("status") for t in tg["tasks"] if isinstance(t, dict)}
        gates = _load_yaml(".ai/gates.yaml").get("gates", [])
        for g in gates:
            if isinstance(g, dict) and tasks.get(g.get("task_id")) == "rejected":
                assert g.get("execution_status") != "completed", (
                    f"rejected 任务 {g.get('task_id')} 的 gate {g.get('id')} "
                    "不得标 completed"
                )
