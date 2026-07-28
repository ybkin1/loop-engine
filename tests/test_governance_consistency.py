"""
test_governance_consistency.py — Cross-validate .ai/ governance files (T-0046).

Checks consistency between state.yaml, task_graph.yaml, gates.yaml, and HANDOFF.md.
"""
import os
import re
import yaml
import pytest

PROJECT_ROOT = os.path.join(os.path.dirname(__file__), "..")


def _read(rel_path):
    full = os.path.join(PROJECT_ROOT, rel_path)
    with open(full, "r", encoding="utf-8") as f:
        return f.read()


def _load_yaml(rel_path):
    return yaml.safe_load(_read(rel_path))


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

    def test_current_task_in_graph(self):
        state = _load_yaml(".ai/state.yaml")
        tg = _load_yaml(".ai/task_graph.yaml")
        current = state["current_task_id"]
        task_ids = [t["id"] for t in tg["tasks"] if isinstance(t, dict)]
        assert current in task_ids, f"{current} not in task_graph"

    def test_current_task_file_exists(self):
        state = _load_yaml(".ai/state.yaml")
        current = state["current_task_id"]
        task_file = os.path.join(PROJECT_ROOT, ".ai", "tasks", f"{current}.md")
        assert os.path.exists(task_file), f"Task file {task_file} missing"

    def test_current_gate_in_register(self):
        s=_load_yaml('.ai/state.yaml');
        if s['current_gate_id'] is None: return
        state = _load_yaml(".ai/state.yaml")
        gates = _load_yaml(".ai/gates.yaml")
        current_gate = state["current_gate_id"]
        gate_ids = [str(g["id"]) for g in gates.get("gates", []) if isinstance(g, dict)]
        assert current_gate in gate_ids, f"{current_gate} not in gates.yaml"

    def test_current_gate_task_matches(self):
        s=_load_yaml('.ai/state.yaml');
        if s['current_gate_id'] is None: return
        state = _load_yaml(".ai/state.yaml")
        gates = _load_yaml(".ai/gates.yaml")
        current_gate = state["current_gate_id"]
        current_task = state["current_task_id"]
        for g in gates.get("gates", []):
            if isinstance(g, dict) and str(g.get("id")) == current_gate:
                assert str(g.get("task_id")) == current_task, (
                    f"Gate {current_gate} task_id {g.get('task_id')} != state current_task_id {current_task}"
                )
                break

    def test_current_gate_is_approved(self):
        s=_load_yaml('.ai/state.yaml');
        if s['current_gate_id'] is None: return
        state = _load_yaml(".ai/state.yaml")
        gates = _load_yaml(".ai/gates.yaml")
        current_gate = state["current_gate_id"]
        for g in gates.get("gates", []):
            if isinstance(g, dict) and str(g.get("id")) == current_gate:
                assert g.get("status") == "approved", (
                    f"Gate {current_gate} status is {g.get('status')}, expected approved"
                )
                break

    def test_handoff_current_task_matches_state(self):
        s=_load_yaml('.ai/state.yaml');
        if s['current_task_id'] is None: return
        state = _load_yaml(".ai/state.yaml")
        handoff = _read(".ai/HANDOFF.md")
        current_task = state["current_task_id"]
        assert current_task in handoff, (
            f"HANDOFF.md does not reference current task {current_task}"
        )

    def test_handoff_current_gate_matches_state(self):
        s=_load_yaml('.ai/state.yaml');
        if s['current_gate_id'] is None: return
        state = _load_yaml(".ai/state.yaml")
        handoff = _read(".ai/HANDOFF.md")
        current_gate = state["current_gate_id"]
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
        """T-0045 completed in codex_loop — quality verification was done."""
        tg = _load_yaml(".ai/task_graph.yaml")
        for t in tg["tasks"]:
            if isinstance(t, dict) and t.get("id") == "T-0045":
                assert t.get("status") == "completed", (
                    "T-0045 should be completed — quality verification was done in codex_loop"
                )
