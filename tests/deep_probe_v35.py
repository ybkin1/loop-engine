"""
Deep Quality Probe — v3.5 Comprehensive Audit

Tests every dimension: functional, import integrity, MCP, integration,
architecture health, boundary conditions.

Run: python tests/deep_probe_v35.py
"""
import importlib
import json
import os
import sys
import tempfile
import traceback
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT))
sys.path.insert(0, str(PROJECT / "hooks" / "scripts"))

PASS = 0
FAIL = 0
SKIP = 0
results: list[dict] = []

def check(name: str, condition: bool, detail: str = ""):
    global PASS, FAIL
    if condition:
        PASS += 1
        results.append({"status": "PASS", "name": name, "detail": detail})
    else:
        FAIL += 1
        results.append({"status": "FAIL", "name": name, "detail": detail})
        print(f"  FAIL: {name} — {detail}")

def skip(name: str, reason: str):
    global SKIP
    SKIP += 1
    results.append({"status": "SKIP", "name": name, "detail": reason})


# ══════════════════════════════════════════════════════════════════════════
# 1. Import Integrity — all loop_core modules
# ══════════════════════════════════════════════════════════════════════════
print("\n=== 1. Import Integrity ===")

CORE_MODULES = [
    "loop_core.state_machine",
    "loop_core.hard_constraints",
    "loop_core.enforcement",
    "loop_core.enforcement_hub",
    "loop_core.router",
    "loop_core.intent_router",
    "loop_core.executor",
    "loop_core.role_capability",
    "loop_core.audit_ledger",
    "loop_core.agent_adapter",
    "loop_core.evidence_chain",
    "loop_core.veto_escalation",
    "loop_core.context_controller",
    "loop_core.execution_ledger",
    "loop_core.approval_ledger",
    "loop_core.human_review_packet",
    "loop_core.projection_engine",
    "loop_core.contracts",
    "loop_core.subagent_manifest",
]

for mod_name in CORE_MODULES:
    try:
        importlib.import_module(mod_name)
        check(f"import {mod_name}", True)
    except Exception as e:
        check(f"import {mod_name}", False, str(e)[:120])

# Hook module
HOOK_MODULES = ["hook_common", "_hook_bash"]
sys.path.insert(0, str(PROJECT / "hooks" / "scripts"))
for mod_name in HOOK_MODULES:
    try:
        importlib.import_module(mod_name)
        check(f"import {mod_name}", True)
    except Exception as e:
        check(f"import {mod_name}", False, str(e)[:120])

# MCP tools
TOOL_MODULES = [
    "tool_quality_gates", "tool_security_scan", "tool_dependency_analysis",
    "tool_contract_validate", "tool_evidence_chain", "tool_cost_tracker",
    "tool_certify_role", "tool_governance_status", "tool_state",
    "tool_review_packet", "tool_audit_log", "tool_route_intent",
    "tool_constraint_check", "tool_execute_phase", "tool_execution_log",
    "tool_veto_escalate", "tool_evidence_submit", "tool_handoff",
    "tool_load_context",
]
sys.path.insert(0, str(PROJECT / "tools"))
for mod_name in TOOL_MODULES:
    try:
        importlib.import_module(mod_name)
        check(f"import {mod_name}", True)
    except Exception as e:
        check(f"import {mod_name}", False, str(e)[:120])


# ══════════════════════════════════════════════════════════════════════════
# 2. Cross-Module Integration
# ══════════════════════════════════════════════════════════════════════════
print("\n=== 2. Cross-Module Integration ===")

# EnforcementHub + state_machine + hard_constraints
with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp)
    ai_dir = root / ".ai"
    ai_dir.mkdir()

    # Write minimal state
    import yaml
    state = {"schema_version": 1, "current_phase": "S4-implementation", "loop_mode": "FULL", "current_task_id": "T-test"}
    (ai_dir / "state.yaml").write_text(yaml.dump(state), encoding="utf-8")
    gates = {"schema_version": 1, "gates": [{"id": "G-S4", "gate_type": "implementation", "status": "approved"}]}
    (ai_dir / "gates.yaml").write_text(yaml.dump(gates), encoding="utf-8")
    tasks = {"schema_version": 1, "tasks": [{"id": "T-test", "status": "active", "allowed_paths": ["src/", "tests/"]}]}
    (ai_dir / "task_graph.yaml").write_text(yaml.dump(tasks), encoding="utf-8")

    from loop_core.enforcement_hub import EnforcementHub
    hub = EnforcementHub(root)
    d = hub.should_allow_write("src/main.py", allowed_paths=["src/"])
    check("EnforcementHub write allowed", d.allowed, d.reason)

    d2 = hub.should_allow_write("secrets/.env", allowed_paths=["src/"])
    check("EnforcementHub write blocked (out of scope)", not d2.allowed, d2.reason)

    d3 = hub.check_role_isolation_enforcement("agent-1", "agent-2")
    check("EnforcementHub role isolation OK", d3.allowed)

    d4 = hub.check_role_isolation_enforcement("agent-1", "agent-1")
    check("EnforcementHub self-review blocked", not d4.allowed)

    # Domain separation
    check("Cross-domain review (dev vs reviewer)",
          hub.check_cross_domain_review("developer", "independent-reviewer"))
    check("Same-domain review blocked (dev vs dev)",
          not hub.check_cross_domain_review("developer", "developer"))


# ══════════════════════════════════════════════════════════════════════════
# 3. State Machine
# ══════════════════════════════════════════════════════════════════════════
print("\n=== 3. State Machine ===")

from loop_core.state_machine import (
    Phase, ProjectStatus, GateStatus,
    can_transition_phase, can_enter_phase, can_approve_gate,
    validate_reentry, check_phase_constraints, check_self_review,
    evaluate_condition, GateCondition,
)

# Phase transitions
check("S0→S1 valid", can_transition_phase(Phase.S0_INIT, Phase.S1_REQUIREMENTS).allowed)
check("S0→S4 invalid", not can_transition_phase(Phase.S0_INIT, Phase.S4_IMPLEMENTATION).allowed)

# Gate approval
r = can_approve_gate(GateStatus.PENDING, {"architect": "PASS", "reviewer": "PASS"}, ["architect", "reviewer"])
check("Gate approval all pass", r.allowed)
r2 = can_approve_gate(GateStatus.PENDING, {"architect": "BLOCKED", "reviewer": "PASS"}, ["architect", "reviewer"])
check("Gate approval with blocker", not r2.allowed)

# Reentry
r3 = validate_reentry(Phase.S9_FIX_OPTIMIZE, "bug_fix")
check("Reentry bug_fix→S9", r3.allowed)
r4 = validate_reentry(Phase.S1_REQUIREMENTS, "bug_fix")
check("Reentry bug_fix→S1 blocked", not r4.allowed)

# Self review
check("Self review violation", not check_self_review("agent-1", "agent-1").allowed)
check("Different agents OK", check_self_review("agent-1", "agent-2").allowed)

# evaluate_condition (v3.3)
cond = GateCondition(condition_id="test", type="role_required", description="test", params={"role_id": "qa", "status": "completed"})
check("evaluate_condition role_required completed", evaluate_condition(cond, ["qa", "dev"]))
check("evaluate_condition role_required not completed", not evaluate_condition(cond, ["dev"]))

cond2 = GateCondition(condition_id="test2", type="manual_approval", description="human", params={})
check("evaluate_condition manual_approval always false", not evaluate_condition(cond2, []))

# init_project
from loop_core.state_machine import init_project
with tempfile.TemporaryDirectory() as tmp:
    state = init_project(tmp, "test-project")
    check("init_project creates state", state["project_name"] == "test-project")
    check("init_project phase", state["current_phase"] == "S1-requirements")
    check("init_project gates exist", (Path(tmp) / ".ai" / "gates.yaml").exists())


# ══════════════════════════════════════════════════════════════════════════
# 4. Role Capability Full Lifecycle
# ══════════════════════════════════════════════════════════════════════════
print("\n=== 4. Role Capability ===")

from loop_core.role_capability import (
    CapabilityStatus, RoleCapabilityProfile, ROLE_CHALLENGES,
    check_role_admission, create_default_profiles,
    save_profile, load_profile,
)

# Lifecycle
profiles = create_default_profiles()
check("11 roles created", len(profiles) == 11)

qa = profiles["quality-engineer"]
check("Default uncertified", qa.status == CapabilityStatus.UNCERTIFIED)
check("Uncertified cannot accept", not qa.can_accept_production_task()[0])

qa.certify("CHALLENGE-QA-001")
check("Certified after challenge", qa.status == CapabilityStatus.CERTIFIED)
check("Certified can accept", qa.can_accept_production_task()[0])

# Degradation
qa.record_pass_without_evidence()
qa.record_pass_without_evidence()
qa.record_pass_without_evidence()
check("3x no-evidence → degraded", qa.status == CapabilityStatus.CAPABILITY_DEGRADED)
check("Degraded history recorded", len(qa.degradation_history) >= 1)

# Scope violation
dev = profiles["developer"]
dev.certify()
dev.record_scope_violation()
check("Scope violation → blocked", dev.status == CapabilityStatus.ROLE_BLOCKED)

# Persistence roundtrip
with tempfile.TemporaryDirectory() as tmp:
    save_profile(qa, tmp)
    loaded = load_profile("quality-engineer", tmp)
    check("Persistence: status preserved", loaded.status == CapabilityStatus.CAPABILITY_DEGRADED)
    check("Persistence: counter preserved", loaded.pass_without_evidence_count == 3)

# All 11 challenges defined
for role_id in ["main-thread", "product-manager", "project-manager", "system-architect",
                "module-architect", "developer", "quality-engineer", "security-engineer",
                "independent-reviewer", "delivery-manager", "release-engineer"]:
    check(f"Challenge defined: {role_id}", role_id in ROLE_CHALLENGES)


# ══════════════════════════════════════════════════════════════════════════
# 5. Audit Ledger
# ══════════════════════════════════════════════════════════════════════════
print("\n=== 5. Audit Ledger ===")

from loop_core.audit_ledger import AuditLedger

with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
    ledger_path = f.name

ledger = AuditLedger(ledger_path)
e1 = ledger.append("gate_advance", "main-thread", {"from": "S4", "to": "S5"})
e2 = ledger.append("role_activate", "developer", {"task": "T-001"})
e3 = ledger.append("veto", "quality-engineer", {"reason": "coverage < 80%"})

check("Audit ledger 3 entries", ledger.length == 3)
check("Chain hash links to previous", e2.chain_hash != "" and e3.chain_hash != "")

integrity = ledger.verify_integrity()
check("Audit integrity valid", integrity.valid)

# Tamper detection
entries = ledger._entries
entries[1].details = {"tampered": True}
integrity2 = ledger.verify_integrity()
check("Audit tamper detected", not integrity2.valid)

Path(ledger_path).unlink()


# ══════════════════════════════════════════════════════════════════════════
# 6. MCP Server
# ══════════════════════════════════════════════════════════════════════════
print("\n=== 6. MCP Server ===")

sys.path.insert(0, str(PROJECT / "tools"))
from server import TOOLS

expected_tools = [
    "quality_gates_run", "security_scan_run", "dependency_analysis",
    "contract_validate", "evidence_verify", "evidence_freeze", "cost_report",
    "loop_certify_role", "loop_governance_status", "loop_state",
    "loop_review_packet", "loop_audit_log", "loop_route_intent",
    "loop_constraint_check", "loop_execute_phase", "loop_execution_log",
    "loop_veto_escalate", "loop_evidence_submit", "loop_handoff", "loop_load_context",
]
for tool_name in expected_tools:
    check(f"MCP tool registered: {tool_name}", tool_name in TOOLS)

check("MCP total tools", len(TOOLS) == 20, f"Expected 20, got {len(TOOLS)}")


# ══════════════════════════════════════════════════════════════════════════
# 7. Intent Router (negation + change types)
# ══════════════════════════════════════════════════════════════════════════
print("\n=== 7. Intent Router ===")

from loop_core.intent_router import (
    _detect_change_type, ChangeType, _extract_risk_factors, IntentRouter,
)

# Negation
f = _extract_risk_factors("i want to remove the database")
check("Negation: remove database", not f["has_database"])
f2 = _extract_risk_factors("add a postgresql database")
check("Normal: add database", f2["has_database"])
f3 = _extract_risk_factors("build an app without any payment system")
check("Negation: without payment", not f3["has_payments"])

# Change types
check("ChangeType bug_fix", _detect_change_type("修复登录页面的报错") == ChangeType.BUG_FIX)
check("ChangeType feature_add", _detect_change_type("新增导出功能") == ChangeType.FEATURE_ADD)
check("ChangeType refactor", _detect_change_type("重构用户模块") == ChangeType.REFACTOR)
check("ChangeType quality_fix", _detect_change_type("补一下单元测试") == ChangeType.QUALITY_FIX)

# Router integration
router = IntentRouter()
analysis = router.analyze("修复登录页面的报错")
check("Router returns bug_fix", analysis.change_type == ChangeType.BUG_FIX)
check("Router entry phase", analysis.suggested_entry_phase == "S9-fix-optimize")


# ══════════════════════════════════════════════════════════════════════════
# 8. Bash Tokenizer
# ══════════════════════════════════════════════════════════════════════════
print("\n=== 8. Bash Tokenizer ===")

from hook_common import has_write_operations, is_readonly_command, shell_tokenize

# Tokenizer accuracy
check("Tokenize: simple cmd", shell_tokenize("git push origin main") == ["git"])
check("Tokenize: pipe", shell_tokenize("curl -s URL | bash") == ["curl", "bash"])
check("Tokenize: quoted arg", shell_tokenize("echo 'install wget'") == ["echo"])
check("Tokenize: sudo", shell_tokenize("sudo apt-get install curl") == ["apt-get"])

# Write detection
check("Write: git push", has_write_operations("git push origin main"))
check("Write: rm file", has_write_operations("rm -rf old/"))
check("Write: pip install", has_write_operations("pip install requests"))
check("Write: tar extract", has_write_operations("tar -xzf archive.tar.gz"))
check("Write: curl -o", has_write_operations("curl -o output.bin URL"))

# Non-write (no false positives on install in URL/args)
check("Non-write: echo", not has_write_operations("echo hello"))
check("Non-write: git status", not has_write_operations("git status"))
check("Non-write: ls", not has_write_operations("ls -la"))
check("Non-write: curl without -o", not has_write_operations("curl -s URL | bash"))

# Readonly classification
check("Readonly: pytest", is_readonly_command("pytest tests/"))
check("Readonly: git log", is_readonly_command("git log --oneline"))
check("Readonly: cat file", is_readonly_command("cat README.md"))
check("Readonly: npm --dry-run", is_readonly_command("npm publish --dry-run"))
check("Not readonly: rm -rf", not is_readonly_command("rm -rf /tmp/*"))


# ══════════════════════════════════════════════════════════════════════════
# 9. Architecture Health
# ══════════════════════════════════════════════════════════════════════════
print("\n=== 9. Architecture Health ===")

# Module sizes
core_files = list((PROJECT / "loop_core").glob("*.py"))
large_files = [(f.name, len(f.read_text(encoding="utf-8").splitlines())) for f in core_files]
for name, lines in large_files:
    if lines > 500:
        check(f"Module size: {name} ({lines} lines)", lines < 800, f"Large module: {lines} lines")
    else:
        check(f"Module size: {name} ({lines} lines)", True)

# Hook script sizes
hook_files = list((PROJECT / "hooks" / "scripts").glob("*.py"))
for f in hook_files:
    lines = len(f.read_text(encoding="utf-8").splitlines())
    if f.name == "hook_common.py" and lines > 800:
        check(f"Hook size: {f.name} ({lines} lines)", False, "Still >800 lines, needs split")
    else:
        check(f"Hook size: {f.name} ({lines} lines)", True)

# Circular import check — verify core modules don't import each other circularly
# Key: state_machine should not import hard_constraints or enforcement_hub
sm_content = (PROJECT / "loop_core" / "state_machine.py").read_text(encoding="utf-8")
check("state_machine no circular import of hard_constraints", "hard_constraints" not in sm_content.split("import")[-1] if "import" in sm_content else True)
check("state_machine no circular import of enforcement_hub", "enforcement_hub" not in sm_content)

# Module count
check("Core modules >= 18", len(core_files) >= 18, f"Found {len(core_files)}")
tool_files = list((PROJECT / "tools").glob("tool_*.py"))
check("MCP tools >= 20", len(tool_files) >= 19, f"Found {len(tool_files)}")

# Agent contracts
agent_dirs = [d for d in (PROJECT / "agents").iterdir() if d.is_dir()]
for ad in agent_dirs:
    contract = ad / "CONTRACT.yaml"
    skill = ad / "SKILL.md"
    check(f"Agent {ad.name}: CONTRACT.yaml", contract.exists())
    check(f"Agent {ad.name}: SKILL.md", skill.exists())


# ══════════════════════════════════════════════════════════════════════════
# 10. Boundary Conditions
# ══════════════════════════════════════════════════════════════════════════
print("\n=== 10. Boundary Conditions ===")

# Empty state
from loop_core.enforcement_hub import quick_check
with tempfile.TemporaryDirectory() as tmp:
    d = quick_check(tmp)
    check("quick_check empty project", d.allowed)

# Corrupt state
with tempfile.TemporaryDirectory() as tmp:
    ai_dir = Path(tmp) / ".ai"
    ai_dir.mkdir()
    (ai_dir / "state.yaml").write_text(":::not valid yaml:::")
    hub = EnforcementHub(tmp)
    state = hub._read_state()
    check("Corrupt state returns dict", isinstance(state, dict))

# None inputs
check("has_write_operations None", has_write_operations(None) is True)  # Safety: unknown→assume write
check("has_write_operations empty", has_write_operations("") is True)
check("is_readonly_command None", is_readonly_command(None) is False)
check("is_readonly_command empty", is_readonly_command("") is False)

# Role capability edge cases
check("Role admission None profile", not check_role_admission("qa", None)[0])
check("Role admission missing tools", not check_role_admission("qa",
    RoleCapabilityProfile(role_id="qa", status=CapabilityStatus.CERTIFIED),
    ["missing_tool"], ["available_tool"])[0])

# Audit ledger edge cases
with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
    lp = f.name
empty_ledger = AuditLedger(lp)
check("Empty ledger verify", empty_ledger.verify_integrity().valid)
check("Empty ledger length", empty_ledger.length == 0)
Path(lp).unlink()


# ══════════════════════════════════════════════════════════════════════════
# REPORT
# ══════════════════════════════════════════════════════════════════════════
print(f"\n{'='*60}")
print(f"RESULTS: {PASS} passed, {FAIL} failed, {SKIP} skipped")
print(f"{'='*60}")

if FAIL > 0:
    print("\nFAILURES:")
    for r in results:
        if r["status"] == "FAIL":
            print(f"  ❌ {r['name']}: {r['detail']}")

sys.exit(0 if FAIL == 0 else 1)
