from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
HOOK = ROOT / "hooks" / "scripts" / "loop_enforcement.py"

STATE = """schema_version: 1
project_name: test
current_phase: S4-implementation
loop_mode: FULL
current_task_id: T-0078
"""
TASK = """# T-0078
allowed_paths:
- src/
"""


def _project(tmp_path: Path, projection: str | None = None) -> Path:
    (tmp_path / ".ai" / "tasks").mkdir(parents=True)
    (tmp_path / ".ai" / "state.yaml").write_text(STATE, encoding="utf-8")
    (tmp_path / ".ai" / "tasks" / "T-0078.md").write_text(TASK, encoding="utf-8")
    # T-0082: the enforcement hook requires the quality gate config to exist
    # for S4+ phases; without it all writes are BLOCKED with
    # "质量门禁配置不存在". Content mirrors the repo's real config; the hook
    # only checks existence (hooks/scripts/loop_enforcement.py,
    # check_phase_gate_enforcement).
    qg_dir = tmp_path / ".zcode" / "skills" / "loop-governance"
    qg_dir.mkdir(parents=True, exist_ok=True)
    (qg_dir / "config.yaml").write_text(
        "gate_guard:\n"
        "  enabled: true\n"
        "  decision_recording_exempt:\n"
        "    - .ai/gates.yaml\n"
        "    - .ai/state.yaml\n"
        "    - .ai/task_graph.yaml\n"
        "path_guard:\n"
        "  enabled: true\n"
        "  decision: ask\n"
        "session_brief:\n"
        "  enabled: true\n",
        encoding="utf-8",
    )
    if projection is not None:
        (tmp_path / ".ai" / "runtime").mkdir()
        (tmp_path / ".ai" / "runtime" / "runtime-state.json").write_text(projection, encoding="utf-8")
    return tmp_path


def _run(
    root: Path,
    tool_name: str,
    tool_input: dict,
    *,
    pytest_marker: str | None = None,
) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ, ZCODE_PROJECT_DIR=str(root))
    if pytest_marker is None:
        env.pop("PYTEST_CURRENT_TEST", None)
    else:
        env["PYTEST_CURRENT_TEST"] = pytest_marker
    return subprocess.run(
        [sys.executable, str(HOOK)],
        input=json.dumps({"tool_name": tool_name, "tool_input": tool_input}),
        text=True,
        capture_output=True,
        env=env,
        check=False,
    )


def test_missing_runtime_projection_blocks_main_read(tmp_path: Path) -> None:
    result = _run(_project(tmp_path), "Read", {"file_path": str(tmp_path / "src" / "main.py"), "caller_class": "main-thread"})
    assert result.returncode == 2
    assert "SETUP_INCOMPLETE" in result.stderr
    assert "DISPATCH_REQUIRED" in result.stderr


def test_missing_runtime_projection_blocks_main_edit_and_write(tmp_path: Path) -> None:
    root = _project(tmp_path)
    for tool_name, tool_input in (
        ("Edit", {"file_path": str(root / "src" / "main.py"), "old_string": "a", "new_string": "b", "caller_class": "main-thread"}),
        ("Write", {"file_path": str(root / "src" / "main.py"), "content": "b", "caller_class": "main-thread"}),
    ):
        result = _run(root, tool_name, tool_input)
        assert result.returncode == 2
        assert "DISPATCH_REQUIRED" in result.stderr


def test_missing_runtime_projection_blocks_main_bash_and_apply_patch(tmp_path: Path) -> None:
    root = _project(tmp_path)
    for tool_name, tool_input in (
        ("Bash", {"command": "python -c pass", "caller_class": "main-thread"}),
        ("ApplyPatch", {"patch": "*** Begin Patch\n*** End Patch", "caller_class": "main-thread"}),
    ):
        result = _run(root, tool_name, tool_input)
        assert result.returncode == 2
        assert "DISPATCH_REQUIRED" in result.stderr


def test_agent_orchestration_allowed_without_takeover_evidence(tmp_path: Path) -> None:
    result = _run(_project(tmp_path), "Agent", {"description": "dispatch developer"})
    assert result.returncode == 0
    assert "DISPATCH_REQUIRED" in result.stderr
    assert "takeover" in result.stderr


def test_corrupt_runtime_projection_blocks_business_read(tmp_path: Path) -> None:
    root = _project(tmp_path, "{not-json")
    result = _run(root, "Read", {"file_path": str(root / "src" / "main.py"), "caller_class": "main-thread"})
    assert result.returncode == 2
    assert "SETUP_INCOMPLETE" in result.stderr
    assert "DISPATCH_REQUIRED" in result.stderr


def test_governance_metadata_read_remains_allowed_without_projection(tmp_path: Path) -> None:
    root = _project(tmp_path)
    result = _run(root, "Read", {"file_path": str(root / ".ai" / "state.yaml")})
    assert result.returncode == 0


def test_missing_identity_blocks_business_read_write_and_bash(tmp_path: Path) -> None:
    root = _project(tmp_path)
    for tool_name, tool_input in (
        ("Read", {"file_path": str(root / "src" / "main.py")}),
        ("Write", {"file_path": str(root / "src" / "main.py"), "content": "x"}),
        ("Bash", {"command": "python -c pass"}),
    ):
        result = _run(root, tool_name, tool_input)
        assert result.returncode == 2
        assert "DISPATCH_REQUIRED" in result.stderr


def test_self_reported_agent_cannot_bypass_missing_projection(tmp_path: Path) -> None:
    root = _project(tmp_path)
    result = _run(root, "Write", {
        "file_path": str(root / "src" / "main.py"),
        "content": "x",
        "caller_class": "agent",
        "actor_id": "developer:T-0078",
    })
    assert result.returncode == 2
    assert "DISPATCH_REQUIRED" in result.stderr


def test_valid_projection_still_requires_caller_identity(tmp_path: Path) -> None:
    root = _project(tmp_path, json.dumps({"runtime_state": "DEVELOPER_EXECUTION"}))
    result = _run(root, "Read", {"file_path": str(root / "src" / "main.py")})
    assert result.returncode == 2
    assert "IDENTITY_REQUIRED" in result.stderr


def test_legacy_fixture_marker_allows_scoped_write_without_projection(tmp_path: Path) -> None:
    root = _project(tmp_path)
    result = _run(
        root,
        "Write",
        {"file_path": str(root / "src" / "main.py"), "content": "x"},
        pytest_marker="tests/test_enforcement.py::LoopEnforcementFullModeBlocks::test_full_mode_allows_write_within_task_scope",
    )
    assert result.returncode == 0
    assert "LEGACY_SYNTHETIC_FIXTURE" in result.stderr


def test_unmarked_host_still_blocks_without_projection(tmp_path: Path) -> None:
    root = _project(tmp_path)
    result = _run(root, "Write", {"file_path": str(root / "src" / "main.py"), "content": "x"})
    assert result.returncode == 2
    assert "DISPATCH_REQUIRED" in result.stderr


def _runtime_contract_schema() -> dict:
    schema_path = ROOT / ".ai" / "schemas" / "dispatch-runtime-contract.schema.json"
    return json.loads(schema_path.read_text(encoding="utf-8"))


def _valid_runtime_contract(**overrides: object) -> dict:
    contract = {
        "schema_version": "dispatch-runtime-contract.v1",
        "execution_id": "exec-0078",
        "task_id": "T-0078",
        "gate_id": "G-T-0078-RUNTIME-DELIVERY",
        "state": "ROLE_EXECUTION",
        "takeover": True,
        "dispatch_receipt": {
            "host_invoker": "zcode-host",
            "child_session": "session-0078",
            "actor": "developer",
            "input_hash": "sha256:abc123",
            "status": "PASS",
        },
    }
    contract.update(overrides)
    return contract


def test_dispatch_runtime_contract_accepts_passed_role_execution() -> None:
    import jsonschema

    jsonschema.validate(_valid_runtime_contract(), _runtime_contract_schema())


def test_dispatch_runtime_contract_distinguishes_all_runtime_states() -> None:
    schema = _runtime_contract_schema()
    import jsonschema

    for state in (
        "DISPATCH_REQUIRED",
        "MAIN_THREAD_RUNNING",
        "ROLE_EXECUTION",
        "AGGREGATION_REQUIRED",
        "SETUP_INCOMPLETE",
        "BLOCKED",
    ):
        contract = _valid_runtime_contract(state=state, takeover=False)
        jsonschema.validate(contract, schema)


def test_dispatch_runtime_contract_rejects_missing_identity_or_receipt_fields() -> None:
    import jsonschema

    for field in ("execution_id", "task_id", "gate_id"):
        contract = _valid_runtime_contract()
        del contract[field]
        with __import__("pytest").raises(jsonschema.ValidationError):
            jsonschema.validate(contract, _runtime_contract_schema())

    for field in ("host_invoker", "child_session", "actor", "input_hash", "status"):
        contract = _valid_runtime_contract()
        del contract["dispatch_receipt"][field]
        with __import__("pytest").raises(jsonschema.ValidationError):
            jsonschema.validate(contract, _runtime_contract_schema())


def test_dispatch_runtime_contract_never_allows_takeover_without_pass_receipt() -> None:
    import jsonschema

    for status in ("BLOCKED", "ERROR", "NOT_RUN"):
        contract = _valid_runtime_contract(
            dispatch_receipt={
                "host_invoker": "zcode-host",
                "child_session": "session-0078",
                "actor": "developer",
                "input_hash": "sha256:abc123",
                "status": status,
            }
        )
        with __import__("pytest").raises(jsonschema.ValidationError):
            jsonschema.validate(contract, _runtime_contract_schema())

    contract = _valid_runtime_contract(takeover=False)
    contract["dispatch_receipt"]["status"] = "ERROR"
    jsonschema.validate(contract, _runtime_contract_schema())


