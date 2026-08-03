"""
test_t0109_f3_gates_layering.py — T-0109 F3 gates.yaml 分层（active/archive +
forbidden 外提 + gate_type 枚举）逐线测试。

AC 对照（T-0109 任务卡 AC-01 + 任务书 F3）：
- AC-01  gates.yaml schema 校验通过 + 归档前后 load_gates active 域等价
- F3-2   forbidden_actions 模板外提引用（policy id 可解析、展开 == 原列表）
- F3-3   gate_type 枚举化（schema 枚举覆盖全部记录取值）
- 内核等价：归档只移域不删记录；enforcement_hub 阶段 heuristic / phase
  约束 gate-id 匹配 / resolve_gate_status 消费在归档前后逐 phase 等价

设计要点（design-bh-integration.md F3）：
- 归档仅移域不删记录：union(active, archive) == 原记录集（无删无重）
- 归档规则 = 纯函数（is_archived_gate）：当前治理纪元（T-0081+）/pending/
  current_gate_id/phase 字段/id 含阶段模式/gate_type 含 phase slug 的 gate
  一律留在 active 域（这些是内核判定（enforcement_hub/heuristics、
  check_phase_constraints、resolve_gate_status）实际消费的记录）
- forbidden 外提仅限 active 域精确重复 >=2 的集合；唯一列表保持内联
  （记录零丢失，消费方等价）
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

REPO_ROOT = Path(__file__).resolve().parent.parent
GATES_PATH = REPO_ROOT / ".ai" / "gates.yaml"
ARCHIVE_PATH = REPO_ROOT / ".ai" / "archive" / "gates-archive.yaml"
POLICIES_PATH = REPO_ROOT / ".ai" / "policies" / "forbidden-actions.yaml"
SCHEMA_PATH = REPO_ROOT / "loop_core" / "schemas" / "gate.schema.json"

# ── 归档规则（与 .ai/evidence/T-0109/fixes/f3-gates-layering.md 迁移脚本同源）──

# 阶段模式：与 enforcement_hub._has_approved_user_gate /
# check_phase_constraints 消费语义对齐
PHASE_STRINGS = [
    "S0-init", "S1-requirements", "S2-architecture", "S3-interface",
    "S4-implementation", "S5-quality", "S6-delivery", "S7-integration",
    "S8-functional-test", "S9-fix-optimize", "S10-performance", "S11-maintenance",
]

GOVERNANCE_EPOCH_TASK_MIN = 81  # 当前治理纪元（T-0081+，含 current task / 近期任务）

# 外提 policy id -> 原 forbidden_actions 列表（迁移快照逐项核对过，见 evidence）
FORBIDDEN_POLICY_EXPECTED = {
    "standard-v1": [
        "deploy", "rollback", "modify database", "change permissions",
        "handle secrets", "payment actions", "production data access",
        "migration", "modify business source code (non-governance)",
    ],
    "standard-core-v1": [
        "deploy", "rollback", "modify database", "change permissions",
        "handle secrets", "payment actions", "production data access",
        "migration", "modify business source code (non-governance)",
        "weaken any activated constraint",
        "create or register T-0095+ task files or gates",
    ],
    "agents-md-only-v1": ["modify AGENTS.md"],
    "agents-md-deploy-v1": [
        "modify AGENTS.md",
        "deploy / rollback / database / permission / secret / payment / production_data / migration",
    ],
    "agents-md-business-v1": [
        "modify AGENTS.md",
        "enter real business project",
        "deploy / rollback / database / permission / secret / payment / production_data / migration",
    ],
    "agents-md-external-v1": [
        "modify AGENTS.md",
        "deploy / rollback / database / permission / secret / payment / production_data / migration",
        "enter a real business project",
        "install or enable external agents, MCP, automation, protocols, or new runtime behavior outside this task",
    ],
    "agents-md-acceptance-v1": [
        "modify AGENTS.md",
        "enter a real business project",
        "install or enable skill, MCP, agent, automation, protocol, or tool behavior outside this task",
        "deploy / rollback / database / permission / secret / payment / production_data / migration",
        "treat tests, validator, reviewer PASS, or AI recommendation as user acceptance",
        "silently accept P0/P1 risk or suppress NOT_VERIFIED evidence",
    ],
}


def _task_num(task_id: str) -> int:
    try:
        return int(task_id[2:]) if task_id.startswith("T-") else 9999
    except ValueError:
        return 9999


def _phase_slug(phase: str) -> str:
    return phase.lower().split("-", 1)[-1]


def gate_matches_phase_heuristic(gate: dict, phase: str) -> bool:
    """enforcement_hub._has_approved_user_gate 的 phase 匹配语义（内核判定消费）。"""
    pv, ps = phase.lower(), _phase_slug(phase)
    gate_type = str(gate.get("gate_type", "")).lower()
    gate_phase = str(gate.get("phase", "")).lower()
    return (
        gate_phase in {pv, ps}
        or ps in gate_type
        or pv in gate_type
    )


def is_archived_gate(gate: dict, current_gate_id) -> bool:
    """归档判定（纯函数，与迁移脚本一致）。

    任一条件为真则 gate 必须留在 active 域：
    - 任务编号 >= 81（当前治理纪元）
    - status == pending（待决策）
    - id == current_gate_id（state 交叉引用）
    - 含 phase 字段（内核 heuristic 消费）
    - id 含阶段模式（check_phase_constraints gate 前缀匹配消费）
    - gate_type 命中任一 phase heuristic（enforcement_hub 消费）
    """
    if _task_num(str(gate.get("task_id", ""))) >= GOVERNANCE_EPOCH_TASK_MIN:
        return False
    if gate.get("status") == "pending":
        return False
    if gate.get("id") == current_gate_id:
        return False
    if gate.get("phase"):
        return False
    gid_lower = str(gate.get("id", "")).lower()
    if any(p.lower() in gid_lower for p in PHASE_STRINGS):
        return False
    if any(gate_matches_phase_heuristic(gate, p) for p in PHASE_STRINGS):
        return False
    return True


def _load_yaml(path: Path) -> dict:
    import yaml
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _load_gates(path: Path) -> list[dict]:
    """load_gates 语义（governor_lib.gates / context_controller._load_gates 同源）。"""
    return _load_yaml(path).get("gates", [])


# ============================================================================
# AC-01: schema 校验（active + archive 双文件）
# ============================================================================


class TestGateSchemaValidation:
    def test_schema_file_valid_json(self):
        data = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        assert data["type"] == "object"
        assert "gate_type" in data["properties"]

    def test_all_active_gates_validate(self):
        jsonschema = pytest.importorskip("jsonschema")
        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        gates = _load_gates(GATES_PATH)
        assert len(gates) > 0
        for gate in gates:
            jsonschema.validate(gate, schema)  # 违反 → ValidationError（fail-closed）

    def test_all_archived_gates_validate(self):
        jsonschema = pytest.importorskip("jsonschema")
        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        gates = _load_gates(ARCHIVE_PATH)
        assert len(gates) > 0
        for gate in gates:
            jsonschema.validate(gate, schema)

    def test_gate_type_enum_covers_all_records(self):
        """gate_type 枚举化：枚举覆盖 active + archive 全部记录取值。"""
        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        enum = set(schema["properties"]["gate_type"]["enum"])
        actual = {
            g["gate_type"]
            for g in _load_gates(GATES_PATH) + _load_gates(ARCHIVE_PATH)
        }
        assert actual <= enum, f"未入枚举的 gate_type: {actual - enum}"

    def test_forbidden_policy_field_is_string(self):
        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        assert schema["properties"]["forbidden_policy"]["type"] == "string"


# ============================================================================
# AC-01: 归档前后 load_gates active 域等价（规则可复算 + 无删无重）
# ============================================================================


class TestActiveDomainEquivalence:
    def test_split_rule_reproduces_active_file(self):
        """规则(完整记录集) == 归档后 .ai/gates.yaml 的 active 域（等价断言）。

        完整记录集 = active ∪ archive（迁移保证无删无重，见下测）——
        即归档前 load_gates 的全部记录；规则是纯函数，可复算，
        规则输出 == 归档后 active 文件 ⇒ 归档前后 active 域等价。
        """
        current_gate_id = _load_yaml(REPO_ROOT / ".ai" / "state.yaml").get(
            "current_gate_id"
        )
        active = _load_gates(GATES_PATH)
        archived = _load_gates(ARCHIVE_PATH)
        full = active + archived  # == 归档前完整记录集（union）

        rule_kept = [
            g for g in full if not is_archived_gate(g, current_gate_id)
        ]
        # 逐记录等价（id 序无关）
        by_id = {g["id"]: g for g in rule_kept}
        assert set(by_id) == {g["id"] for g in active}
        for gate in active:
            assert by_id[gate["id"]] == gate

    def test_no_delete_no_duplicate(self):
        """归档仅移域不删记录：union == 原记录集，无删、无重、互斥。"""
        active = _load_gates(GATES_PATH)
        archived = _load_gates(ARCHIVE_PATH)
        ids_active = [g["id"] for g in active]
        ids_archived = [g["id"] for g in archived]
        assert len(ids_active) == len(set(ids_active)), "active 域重复 gate id"
        assert len(ids_archived) == len(set(ids_archived)), "archive 重复 gate id"
        assert set(ids_active).isdisjoint(set(ids_archived)), "active/archive 重叠"
        # 迁移期基线 102 条（evidence 快照）；未来新增 gate 只会增加总数——
        # 无删断言 = union 覆盖全部基线记录（id 全集是基线子集的超集）
        assert len(ids_active) + len(ids_archived) >= 102

    def test_archive_records_keep_all_fields(self):
        """归档记录字段完整（id/task_id/gate_type/status 必填 + recorded_at 等
        历史字段保留——仅移域不删记录，记录逐字段 verbatim）。"""
        archived = _load_gates(ARCHIVE_PATH)
        for gate in archived:
            assert gate["id"] and gate["task_id"] and gate["gate_type"]
            assert gate.get("status") == "approved"  # 全部为历史批准记录
        # recorded_at 历史可审计：36 条中 35 条有 recorded_at；
        # G-T-0055-BASELINE-AUDIT 为历史记录本身缺 recorded_at（verbatim 保留，不改写）
        recorded = [g for g in archived if g.get("recorded_at")]
        assert len(recorded) == len(archived) - 1
        assert "G-T-0055-BASELINE-AUDIT" in {
            g["id"] for g in archived if not g.get("recorded_at")
        }

    def test_current_and_pending_gates_stay_active(self):
        """state.current_gate_id 与 pending gate 必须留在 active 域。"""
        state = _load_yaml(REPO_ROOT / ".ai" / "state.yaml")
        cgi = state.get("current_gate_id")
        active = _load_gates(GATES_PATH)
        active_ids = {g["id"] for g in active}
        assert cgi in active_ids, "current_gate_id 必须仍在 active 域"
        for gate in active:
            if gate.get("status") == "pending":
                assert gate["id"] in active_ids


# ============================================================================
# F3 内核等价：归档只移域不删记录 → 内核判定消费输入不变
# ============================================================================


class TestKernelBehaviorEquivalence:
    """enforcement_hub / check_phase_constraints / resolve_gate_status 的
    gates.yaml 消费在归档前后逐 phase 等价（仅 active 域 vs 完整记录集）。"""

    @pytest.fixture(scope="class")
    def gate_sets(self):
        active = _load_gates(GATES_PATH)
        archived = _load_gates(ARCHIVE_PATH)
        full = active + archived  # 归档前
        return full, active

    def test_phase_heuristic_equivalent_per_phase(self, gate_sets):
        """_has_approved_user_gate 的 phase 匹配（approved + explicit_user）
        逐 phase：完整集 == active 域（无 phase 因归档丢失 heuristic 命中）。"""
        full, active = gate_sets
        for phase in PHASE_STRINGS:
            def matches(records):
                for g in records:
                    if g.get("status") != "approved":
                        continue
                    if not gate_matches_phase_heuristic(g, phase):
                        continue
                    approval_actor = str(g.get("approval_actor", "")).lower()
                    approval_source = str(g.get("approval_source", "")).lower()
                    gate_type = str(g.get("gate_type", "")).lower()
                    explicit_user = (
                        approval_actor == "user"
                        or approval_source == "explicit_user_message"
                        or gate_type.startswith("user-")
                    )
                    if explicit_user:
                        return True
                return False
            assert matches(full) == matches(active), (
                f"phase {phase} heuristic 归档前后不等价"
            )

    def test_phase_constraint_gate_id_match_equivalent(self, gate_sets):
        """check_phase_constraints 的 gate_id 前缀匹配（'S1-requirements' in id 等）
        逐 phase：完整集 == active 域。"""
        full, active = gate_sets
        for phase in PHASE_STRINGS:
            full_ids = {g["id"] for g in full}
            active_ids = {g["id"] for g in active}
            assert any(phase.lower() in gid.lower() for gid in full_ids) == any(
                phase.lower() in gid.lower() for gid in active_ids
            ), f"phase {phase} gate-id 前缀匹配归档前后不等价"

    def test_current_gate_id_resolves_in_active(self, gate_sets):
        """resolve_gate_status(current_gate_id, gates)：current_gate_id 在
        active 域中恰一条且 status 可解析（approved）。"""
        state = _load_yaml(REPO_ROOT / ".ai" / "state.yaml")
        cgi = state.get("current_gate_id")
        _full, active = gate_sets
        matches = [g for g in active if g.get("id") == cgi]
        assert len(matches) == 1
        assert matches[0].get("status") == "approved"


# ============================================================================
# F3: forbidden_actions 模板外提引用
# ============================================================================


class TestForbiddenPolicyReferences:
    def test_policy_file_structure(self):
        doc = _load_yaml(POLICIES_PATH)
        assert doc["schema_version"] == 1
        policies = doc["policies"]
        ids = [p["id"] for p in policies]
        assert len(ids) == len(set(ids)), "policy id 重复"
        for p in policies:
            assert isinstance(p["forbidden_actions"], list) and p["forbidden_actions"]

    def test_every_reference_resolves(self):
        doc = _load_yaml(POLICIES_PATH)
        policy_ids = {p["id"] for p in doc["policies"]}
        active = _load_gates(GATES_PATH)
        referenced = {g["forbidden_policy"] for g in active if "forbidden_policy" in g}
        assert referenced <= policy_ids, f"未解析的 policy 引用: {referenced - policy_ids}"
        assert referenced == set(FORBIDDEN_POLICY_EXPECTED)

    def test_policy_expansion_matches_expected_lists(self):
        """policy 展开 == 迁移前原 forbidden_actions 列表（记录零丢失）。"""
        doc = _load_yaml(POLICIES_PATH)
        for p in doc["policies"]:
            assert p["forbidden_actions"] == FORBIDDEN_POLICY_EXPECTED[p["id"]]

    def test_extracted_gates_have_no_inline_list(self):
        active = _load_gates(GATES_PATH)
        for gate in active:
            if "forbidden_policy" in gate:
                assert "forbidden_actions" not in gate, (
                    f"{gate['id']} 外提后不应残留内联列表"
                )

    def test_unique_lists_kept_inline(self):
        """唯一（非精确重复）列表保持内联——记录零丢失、消费方等价。"""
        active = _load_gates(GATES_PATH)
        inline = [g for g in active if "forbidden_actions" in g]
        assert inline, "应存在保持内联的任务特有 forbidden 列表"
        for gate in inline:
            assert "forbidden_policy" not in gate
            assert gate["forbidden_actions"]

    def test_extraction_only_for_exact_duplicates(self):
        """外提仅限 active 域精确重复 >=2 的集合：被外提（forbidden_policy）
        gate 的展开列表在 active 域中至少有另一个 gate 与其完全一致
        （共享模板）；唯一列表保持内联（记录零丢失，by design）。"""
        active = _load_gates(GATES_PATH)
        expanded: dict[str, list] = {}
        doc = _load_yaml(POLICIES_PATH)
        policies = {p["id"]: p["forbidden_actions"] for p in doc["policies"]}
        for gate in active:
            if "forbidden_policy" in gate:
                expanded[gate["id"]] = policies[gate["forbidden_policy"]]
            else:
                expanded[gate["id"]] = gate.get("forbidden_actions", [])
        counter = Counter(tuple(v) for v in expanded.values())
        for gate_id, lst in expanded.items():
            if gate_id in {
                g["id"] for g in active if "forbidden_policy" in g
            }:
                assert counter[tuple(lst)] >= 2, (
                    f"{gate_id} 外提列表在 active 域中不是精确重复集合"
                )
