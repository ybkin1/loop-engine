"""
test_idle_semantics.py — T-0101 idle 稳态语义分流验收测试。

- idle 合法态（current_task_id=null 且无其他 blocker）：
  validate_state / audit_handoff → 独立 [info] NO_ACTIVE_TASK 输出段 + exit 3，
  不输出 "[ok] state is usable"（v2.0.0 安全意图保留：新会话不得误以为可开工）。
- 真实损坏（project_continuity 哈希失配）→ [error] + exit 2（fail-closed 保持）。
- idle + 其他 blocker（待决 gate）→ 仍 exit 2（NO_ACTIVE_TASK 错误行可保留）。
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TOOLS = PROJECT_ROOT / ".zcode" / "tools"
VALIDATE_STATE = TOOLS / "validate_state.py"
AUDIT_HANDOFF = TOOLS / "audit_handoff.py"

REQUIRED_FILES = [
    "PROJECT.md", "NON_GOALS.md", "ARCHITECTURE.md", "CONTRACTS.md",
    "CODING_STANDARDS.md", "CONVENTIONS.md", "CODEMAP.md", "PROGRESS.md",
    "QUALITY_GATES.md", "ACCEPTANCE.md", "DECISIONS.md", "KNOWN_ISSUES.md",
]
REQUIRED_HEADINGS = [
    "## Product Direction And Authority", "## Current Phase", "## Current Task",
    "## Allowed Scope", "## Forbidden Scope", "## Verified", "## Unverified",
    "## Evidence", "## Integration Impact", "## Structured Lifecycle",
    "## Structured Next Action", "## Checkpoint", "## Next Session First Step",
]


def _sha(value) -> str:
    payload = value if isinstance(value, bytes) else json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest().upper()


def _continuity_payload() -> dict:
    """独立校验（continuity_producer/continuity_auditor 同 schema）接受的 payload。"""
    decisions = [
        {"decision_id": decision_id, "statement": "x", "rationale_ref": "x",
         "authority_ref": "x", "change_policy": "x"}
        for decision_id in (
            "USER_AUTHORITY", "CODEX_DELIVERY_RESPONSIBILITY",
            "EVIDENCE_ONLY_BOUNDARY", "MEANS_END_BOUNDARY",
        )
    ]
    return {
        "user_origin": {"audience": [], "capability_assumptions": [],
                        "user_authorities": []},
        "product_identity": {"project_id": "loop-engine-test",
                             "one_sentence_outcome": "x", "north_star": "x",
                             "success_signals": []},
        "protected_decisions": decisions,
        "non_goals": [],
        "design_language": {"terms": {}, "forbidden_equivalences": {}},
        "engineering_invariants": {"architecture": [], "technology": [],
                                   "interfaces": [], "coding_standards": [],
                                   "quality": [], "security": []},
        "golden_references": [],
        "authorization_boundaries": {"allowed_effects": [],
                                     "forbidden_effects": [],
                                     "current_gate_id": None},
        "lifecycle": {"phase": "S6-delivery", "task_id": None, "task_status": None,
                      "active_transaction_ids": [], "in_flight_actor_ids": []},
        "evidence_index": {"canonical": [], "additive": [],
                           "superseded_not_deleted": []},
        "revision_lineage": {"parent_revision": None, "change_set_id": "test-v1",
                             "impact_assessment_ref": None, "approval_ref": None},
    }


def _write_continuity(root: Path) -> Path:
    """构造独立校验通过的 project_continuity.yaml（source_manifest 指向真实文件）。"""
    project_md = root / ".ai" / "PROJECT.md"
    sources = [{
        "path": ".ai/PROJECT.md",
        "sha256": _sha(project_md.read_bytes()),
        "size": project_md.stat().st_size,
    }]
    payload = _continuity_payload()
    data = {
        "schema": "ProjectContinuity/v1",
        "contract_id": "PCC-2026-07-16-R1",
        "requirements_revision": "R1",
        "project_id": "loop-engine-test",
        "source_manifest": sources,
        "source_sha256": _sha(sources),
        "semantic_sha256": _sha({k: v for k, v in payload.items() if k != "lifecycle"}),
        "created_at": "2026-08-02T00:00:00+08:00",
        "created_by": "tests/test_idle_semantics.py",
        "authority_ref": "x",
        "project_continuity": payload,
    }
    path = root / ".ai" / "project_continuity.yaml"
    path.write_text(
        yaml.safe_dump(data, allow_unicode=True, sort_keys=False,
                       default_flow_style=False),
        encoding="utf-8",
    )
    return path


def _handoff_text() -> str:
    """HANDOFF.md：含 audit_handoff 必需的全部 heading + 4 个结构化 JSON 块
    （idle 分支只解析块存在性，不比对内容）。"""
    blocks = ""
    for name in ("PROJECT-CONTINUITY", "NEXT-ACTION", "LIFECYCLE", "CHECKPOINT"):
        blocks += (
            f"<!-- PROJECT-GOVERNOR-{name}-BEGIN -->\n```json\n{{}}\n```\n"
            f"<!-- PROJECT-GOVERNOR-{name}-END -->\n\n"
        )
    headings = "\n\n".join(REQUIRED_HEADINGS)
    return "# Handoff\n\n" + blocks + headings + "\n"


@pytest.fixture
def idle_root(tmp_path: Path) -> Path:
    """最小 idle 稳态 fixture：全部必需文件 + 有效 continuity + 结构化 HANDOFF。"""
    root = tmp_path / "idle"
    base = root / ".ai"
    (base / "tasks").mkdir(parents=True)
    for name in REQUIRED_FILES:
        (base / name).write_text(f"# {name}\n", encoding="utf-8")
    (base / "state.yaml").write_text(
        "schema_version: 1\nproject_name: Loop Engine Test\n"
        "current_phase: S6-delivery\ncurrent_task_id: null\ncurrent_gate_id: null\n"
        "loop_mode: FULL\n",
        encoding="utf-8",
    )
    (base / "task_graph.yaml").write_text(
        "schema_version: 1\ntasks: []\nedges: []\n", encoding="utf-8"
    )
    (base / "gates.yaml").write_text("schema_version: 1\ngates: []\n", encoding="utf-8")
    (base / "HANDOFF.md").write_text(_handoff_text(), encoding="utf-8")
    _write_continuity(root)
    return root


def _run(script: Path, root: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-B", str(script), str(root)],
        cwd=str(root), capture_output=True, text=True,
    )


class TestIdleSemantics:
    def test_validate_state_idle_exit_3(self, idle_root):
        """AC-01: idle 合法态 → [info] NO_ACTIVE_TASK 独立段 + exit 3，
        无 [ok] state is usable、无 [error] 级输出。"""
        proc = _run(VALIDATE_STATE, idle_root)
        assert proc.returncode == 3, proc.stdout + proc.stderr
        assert "[info] NO_ACTIVE_TASK: state.current_task_id is null" in proc.stdout
        assert "合法阻塞态" in proc.stdout
        assert "[ok] state is usable" not in proc.stdout
        assert "[error]" not in proc.stdout

    def test_audit_handoff_idle_exit_3(self, idle_root):
        """AC-01: audit_handoff.py 同语义 —— [info] NO_ACTIVE_TASK + exit 3。"""
        proc = _run(AUDIT_HANDOFF, idle_root)
        assert proc.returncode == 3, proc.stdout + proc.stderr
        assert "[info] NO_ACTIVE_TASK" in proc.stdout
        assert "[ok] handoff audit passed" not in proc.stdout
        assert "[error]" not in proc.stdout

    def test_validate_state_corruption_exit_2(self, idle_root):
        """AC-02: project_continuity 哈希失配（真实损坏）→ [error] + exit 2，
        fail-closed 保持，不被 idle 分流吞掉。"""
        path = idle_root / ".ai" / "project_continuity.yaml"
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        data["semantic_sha256"] = "A" * 64
        path.write_text(
            yaml.safe_dump(data, allow_unicode=True, sort_keys=False,
                           default_flow_style=False),
            encoding="utf-8",
        )
        proc = _run(VALIDATE_STATE, idle_root)
        assert proc.returncode == 2, proc.stdout + proc.stderr
        assert "[error]" in proc.stdout
        assert "ProjectContinuity" in proc.stdout

    def test_audit_handoff_corruption_exit_2(self, idle_root):
        """AC-02: audit_handoff.py 对损坏态同样 exit 2（分流不放松 fail-closed）。"""
        path = idle_root / ".ai" / "project_continuity.yaml"
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        data["semantic_sha256"] = "A" * 64
        path.write_text(
            yaml.safe_dump(data, allow_unicode=True, sort_keys=False,
                           default_flow_style=False),
            encoding="utf-8",
        )
        proc = _run(AUDIT_HANDOFF, idle_root)
        assert proc.returncode == 2, proc.stdout + proc.stderr
        assert "[error]" in proc.stdout
        assert "PROJECT_CONTINUITY_HASH_MISMATCH" in proc.stdout

    def test_validate_state_idle_with_other_blocker_exit_2(self, idle_root):
        """idle + 其他 blocker（待决 gate）→ 仍 exit 2（fail-closed），
        NO_ACTIVE_TASK 错误行可保留，绝不输出 usable。"""
        (idle_root / ".ai" / "gates.yaml").write_text(
            "schema_version: 1\ngates:\n  - id: G-BLOCK\n    task_id: T-XXXX\n"
            "    status: pending\n",
            encoding="utf-8",
        )
        proc = _run(VALIDATE_STATE, idle_root)
        assert proc.returncode == 2, proc.stdout + proc.stderr
        assert "[error] Pending gate(s) require user decision" in proc.stdout
        assert "[error] NO_ACTIVE_TASK" in proc.stdout
        assert "[ok] state is usable" not in proc.stdout
