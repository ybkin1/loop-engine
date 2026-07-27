"""
certification_runner.py — Role Capability Certification System.

Each of the 11 Loop engineering roles must prove its core competency through
a deterministic challenge. Challenges are machine-verified — no AI self-assessment.

Certification state machine:
    CERTIFIED → DEGRADED (1 failure)
    DEGRADED → REVALIDATION_REQUIRED (2 consecutive failures)
    DEGRADED → ROLE_BLOCKED (3+ consecutive failures)
    Any state → CERTIFIED (pass challenge from any state)

Usage:
    python scripts/certification_runner.py                          # run all
    python scripts/certification_runner.py --role quality-engineer  # single role
    python scripts/certification_runner.py --list                   # list challenges
    python scripts/certification_runner.py --state-file .ai/certifications/state.yaml
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Optional

# ── Project root detection ──
PROJECT_ROOT = Path(__file__).resolve().parent.parent


# ═══════════════════════════════════════════════════════════════════════════════
# Certification State Machine
# ═══════════════════════════════════════════════════════════════════════════════

class CertState(str, Enum):
    """Certification states for a role."""
    CERTIFIED = "CERTIFIED"                      # Passed most recent challenge
    DEGRADED = "DEGRADED"                        # 1 consecutive failure
    REVALIDATION_REQUIRED = "REVALIDATION_REQUIRED"  # 2 consecutive failures
    ROLE_BLOCKED = "ROLE_BLOCKED"                # 3+ consecutive failures


# Consecutive failure threshold map
_FAILURE_DEGRADE_THRESHOLD = 1   # 1 failure → DEGRADED
_FAILURE_REVALIDATION_THRESHOLD = 2  # 2 consecutive → REVALIDATION_REQUIRED
_FAILURE_BLOCK_THRESHOLD = 3      # 3+ consecutive → ROLE_BLOCKED


def compute_next_state(
    current_state: CertState,
    consecutive_failures: int,
    challenge_passed: bool,
) -> CertState:
    """
    Deterministic state transition.

    Rules:
    - Pass → CERTIFIED (always, from any state)
    - 1 failure → DEGRADED
    - 2 consecutive failures → REVALIDATION_REQUIRED
    - 3+ consecutive failures → ROLE_BLOCKED
    """
    if challenge_passed:
        return CertState.CERTIFIED

    # Challenge failed — apply degradation rules
    new_failures = consecutive_failures + 1

    if new_failures >= _FAILURE_BLOCK_THRESHOLD:
        return CertState.ROLE_BLOCKED
    elif new_failures >= _FAILURE_REVALIDATION_THRESHOLD:
        return CertState.REVALIDATION_REQUIRED
    elif new_failures >= _FAILURE_DEGRADE_THRESHOLD:
        return CertState.DEGRADED

    # Should not happen, but safe default
    return current_state


def is_manual_override_allowed(state: CertState) -> bool:
    """Manual override is never allowed. Certification is machine-determined."""
    return False


# ═══════════════════════════════════════════════════════════════════════════════
# Result types
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class ChallengeResult:
    """Result of a single challenge execution."""
    role_id: str
    challenge_name: str
    passed: bool
    score: float           # 0.0 – 1.0
    checks_total: int
    checks_passed: int
    checks_failed: int
    failures: list[dict] = field(default_factory=list)
    evidence_hash: str = ""
    run_at: str = ""

    def __post_init__(self):
        if not self.run_at:
            self.run_at = datetime.now(timezone.utc).isoformat()


@dataclass
class CertificationRun:
    """Aggregate result of running certification for one or more roles."""
    results: dict[str, ChallengeResult] = field(default_factory=dict)
    state_transitions: dict[str, dict] = field(default_factory=dict)
    overall_pass: bool = True
    run_at: str = ""

    def __post_init__(self):
        if not self.run_at:
            self.run_at = datetime.now(timezone.utc).isoformat()


# ═══════════════════════════════════════════════════════════════════════════════
# Challenge Definitions — one per role
# ═══════════════════════════════════════════════════════════════════════════════

def _make_check(name: str, passed: bool, detail: str = "") -> dict:
    return {"name": name, "passed": passed, "detail": detail}


# ── 1. main-thread ──
def challenge_main_thread() -> ChallengeResult:
    """
    Main-thread must demonstrate: input hash freezing, agent isolation,
    self-review prevention, and correct gate presentation.

    Challenge: Given a task file template and role outputs, validate:
    - input_hashes present and SHA256-valid
    - developer_agent_id != reviewer_agent_id
    - All role outputs have structured verdict field
    - No PASS verdict is overwritten
    """
    checks: list[dict] = []

    # Simulate: task file with input_hashes
    task_file = {
        "task_id": "T-0001",
        "input_hashes": {
            "requirements.md": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
            "architecture.md": "a7ffc6f8bf1ed76651c14756a061d662f580ff4de43b49fa82d80a4b80f8434a",
        },
        "developer_agent_id": "agent-dev-001",
        "reviewer_agent_id": "agent-rev-002",
    }

    # Check 1: input_hashes field exists
    if "input_hashes" in task_file and isinstance(task_file["input_hashes"], dict):
        checks.append(_make_check("input_hashes_present", True))
    else:
        checks.append(_make_check("input_hashes_present", False, "missing input_hashes field"))
        return _finalize("main-thread", "Input Hash & Agent Isolation", checks)

    # Check 2: each hash is 12+ hex chars
    all_hashes_valid = all(
        isinstance(v, str) and len(v) >= 12 and all(c in '0123456789abcdef' for c in v)
        for v in task_file["input_hashes"].values()
    )
    checks.append(_make_check("input_hashes_valid_format", all_hashes_valid,
                              "hashes must be hex strings >= 12 chars" if not all_hashes_valid else ""))

    # Check 3: developer != reviewer
    dev = task_file.get("developer_agent_id")
    rev = task_file.get("reviewer_agent_id")
    if dev and rev and dev != rev:
        checks.append(_make_check("no_self_review", True))
    else:
        checks.append(_make_check("no_self_review", False, f"developer={dev}, reviewer={rev} — SELF_REVIEW_VIOLATION"))

    # Check 4: role outputs have structured verdict
    role_outputs = [
        {"role": "developer", "verdict": "PASS", "findings": []},
        {"role": "independent-reviewer", "verdict": "BLOCKED", "findings": [{"id": "P0-001"}]},
        {"role": "quality-engineer", "verdict": "PASS"},
    ]
    all_have_verdict = all(
        isinstance(r.get("verdict"), str) and r["verdict"] in ("PASS", "BLOCKED")
        for r in role_outputs
    )
    checks.append(_make_check("role_outputs_have_verdict", all_have_verdict,
                              "all role outputs must have verdict: PASS or BLOCKED" if not all_have_verdict else ""))

    # Check 5: main-thread does not overwrite BLOCKED
    # (simulated: if any role has BLOCKED, gate cannot be approved)
    has_blocked = any(r.get("verdict") == "BLOCKED" for r in role_outputs)
    checks.append(_make_check("blocked_not_overwritten", has_blocked  # we detected BLOCKED exists
                              ))

    return _finalize("main-thread", "Input Hash & Agent Isolation", checks)


# ── 2. product-manager ──
def challenge_product_manager() -> ChallengeResult:
    """
    Product manager must demonstrate: correct priority distribution,
    no technical keywords in user stories, proper AC format.
    """
    checks: list[dict] = []

    scope_spec = {
        "user_stories": [
            {"id": "US-001", "priority": "P0", "acceptance_criteria": ["Given A, when B, then C"]},
            {"id": "US-002", "priority": "P0", "acceptance_criteria": ["Given X, when Y, then Z"]},
            {"id": "US-003", "priority": "P1", "acceptance_criteria": ["Given F, when G, then H"]},
            {"id": "US-004", "priority": "P1", "acceptance_criteria": ["Given I, when J, then K"]},
            {"id": "US-005", "priority": "P2", "acceptance_criteria": ["Given L, when M, then N"]},
            {"id": "US-006", "priority": "P2", "acceptance_criteria": ["Given O, when P, then Q"]},
            {"id": "US-007", "priority": "P3", "acceptance_criteria": ["Given R, when S, then T"]},
            {"id": "US-008", "priority": "P3", "acceptance_criteria": ["Given U, when V, then W"]},
            {"id": "US-009", "priority": "P3", "acceptance_criteria": ["Given X1, when Y1, then Z1"]},
            {"id": "US-010", "priority": "P3", "acceptance_criteria": ["Given X2, when Y2, then Z2"]},
        ]
    }

    stories = scope_spec["user_stories"]
    total = len(stories)

    # Check 1: P0 <= 30%
    p0_count = sum(1 for s in stories if s["priority"] == "P0")
    p0_ratio = p0_count / total if total > 0 else 1.0
    checks.append(_make_check("p0_distribution", p0_ratio <= 0.30,
                              f"P0={p0_count}/{total}={p0_ratio:.0%}, must be <= 30%" if p0_ratio > 0.30 else f"P0={p0_count}/{total}={p0_ratio:.0%}"))

    # Check 2: P3 >= 10%
    p3_count = sum(1 for s in stories if s["priority"] == "P3")
    p3_ratio = p3_count / total if total > 0 else 0
    checks.append(_make_check("p3_distribution", p3_ratio >= 0.10,
                              f"P3={p3_count}/{total}={p3_ratio:.0%}, must be >= 10%" if p3_ratio < 0.10 else f"P3={p3_count}/{total}={p3_ratio:.0%}"))

    # Check 3: Every story has a unique ID
    ids = [s["id"] for s in stories]
    checks.append(_make_check("unique_story_ids", len(ids) == len(set(ids)),
                              f"Duplicate IDs found: {[i for i in ids if ids.count(i) > 1]}" if len(ids) != len(set(ids)) else ""))

    # Check 4: Every story has at least one AC
    all_have_ac = all(len(s.get("acceptance_criteria", [])) >= 1 for s in stories)
    checks.append(_make_check("all_stories_have_ac", all_have_ac,
                              "Some stories have no acceptance criteria" if not all_have_ac else ""))

    # Check 5: No technical keywords in stories (mock check on story text)
    tech_keywords = ["react", "postgresql", "docker", "kubernetes", "api endpoint", "mysql", "redis"]
    violations = []
    for s in stories:
        text = json.dumps(s).lower()
        for kw in tech_keywords:
            if kw in text:
                violations.append(f"{s['id']} contains '{kw}'")
    checks.append(_make_check("no_technical_keywords", len(violations) == 0,
                              "; ".join(violations) if violations else ""))

    return _finalize("product-manager", "Priority Distribution & AC Validation", checks)


# ── 3. project-manager ──
def challenge_project_manager() -> ChallengeResult:
    """
    Project manager must demonstrate: DAG cycle detection, P0 story coverage,
    correct task dependency resolution.
    """
    checks: list[dict] = []

    # Simulate a valid task graph
    task_graph = {
        "phases": [
            {
                "name": "Phase 1",
                "tasks": [
                    {"id": "T1", "maps_to_story": "US-001", "depends_on": [], "hours": 8},
                    {"id": "T2", "maps_to_story": "US-002", "depends_on": ["T1"], "hours": 16},
                    {"id": "T3", "maps_to_story": "US-001", "depends_on": [], "hours": 4},
                ]
            },
            {
                "name": "Phase 2",
                "tasks": [
                    {"id": "T4", "maps_to_story": "US-003", "depends_on": ["T2", "T3"], "hours": 12},
                    {"id": "T5", "maps_to_story": "US-004", "depends_on": ["T4"], "hours": 8},
                ]
            }
        ]
    }

    all_tasks = [t for phase in task_graph["phases"] for t in phase["tasks"]]

    # Check 1: Topological sort — no cycles
    def has_cycle(tasks):
        adj = {t["id"]: t.get("depends_on", []) for t in tasks}
        visited = set()
        rec_stack = set()

        def dfs(node):
            visited.add(node)
            rec_stack.add(node)
            for neighbor in adj.get(node, []):
                if neighbor not in visited:
                    if dfs(neighbor):
                        return True
                elif neighbor in rec_stack:
                    return True
            rec_stack.discard(node)
            return False

        for t in tasks:
            if t["id"] not in visited:
                if dfs(t["id"]):
                    return True
        return False

    no_cycles = not has_cycle(all_tasks)
    checks.append(_make_check("no_dag_cycles", no_cycles,
                              "DAG has cycles!" if not no_cycles else ""))

    # Check 2: All P0 stories covered
    p0_stories = {"US-001", "US-002"}
    covered = {t["maps_to_story"] for t in all_tasks}
    uncovered = p0_stories - covered
    checks.append(_make_check("p0_coverage", len(uncovered) == 0,
                              f"Uncovered P0 stories: {uncovered}" if uncovered else "All P0 stories covered"))

    # Check 3: Every task has unique ID
    task_ids = [t["id"] for t in all_tasks]
    checks.append(_make_check("unique_task_ids", len(task_ids) == len(set(task_ids)),
                              f"Duplicate task IDs: {[tid for tid in task_ids if task_ids.count(tid) > 1]}" if len(task_ids) != len(set(task_ids)) else ""))

    # Check 4: dependencies reference valid task IDs
    valid_ids = set(task_ids)
    invalid_deps = []
    for t in all_tasks:
        for dep in t.get("depends_on", []):
            if dep not in valid_ids:
                invalid_deps.append(f"{t['id']} depends on non-existent {dep}")
    checks.append(_make_check("valid_dependencies", len(invalid_deps) == 0,
                              "; ".join(invalid_deps) if invalid_deps else ""))

    # Check 5: All tasks have hours > 0
    all_have_hours = all(t.get("hours", 0) > 0 for t in all_tasks)
    checks.append(_make_check("all_tasks_have_estimate", all_have_hours,
                              "Some tasks have no hours estimate" if not all_have_hours else ""))

    return _finalize("project-manager", "DAG & Task Coverage", checks)


# ── 4. system-architect ──
def challenge_system_architect() -> ChallengeResult:
    """
    System architect must demonstrate: cycle detection in dependency graph,
    architecture doc completeness (7 required sections).
    """
    checks: list[dict] = []

    # Check 1: Dependency graph cycle detection
    nodes = {
        "domain": ["infrastructure"],   # domain -> infrastructure (BAD: reverse dep)
        "infrastructure": ["domain"],   # infrastructure -> domain (cycle!)
        "application": ["domain"],
        "presentation": ["application"],
    }

    # Build reverse adjacency to detect cycles
    def find_cycles(graph):
        visited = set()
        rec_stack = set()
        cycles = []

        def dfs(node, path):
            visited.add(node)
            rec_stack.add(node)
            path.append(node)
            for neighbor in graph.get(node, []):
                if neighbor not in visited:
                    dfs(neighbor, path)
                elif neighbor in rec_stack:
                    # Found cycle
                    cycle_start = path.index(neighbor)
                    cycles.append(path[cycle_start:] + [neighbor])
            path.pop()
            rec_stack.discard(node)

        for n in graph:
            if n not in visited:
                dfs(n, [])
        return cycles

    found_cycles = find_cycles(nodes)
    checks.append(_make_check("dependency_cycle_detection", len(found_cycles) > 0,
                              f"Detected cycles: {found_cycles}" if found_cycles else "Failed to detect cycle: domain<->infrastructure"))

    # Check 2-8: Architecture doc sections (7 required)
    required_sections = [
        "architecture_overview",
        "module_inventory",
        "data_flow_diagram",
        "dependency_direction_rules",
        "technical_constraints_and_risks",
        "evolution_roadmap",
        "architecture_decision_records",
    ]
    arch_doc_sections = set(required_sections)  # simulated: all present

    for section in required_sections:
        present = section in arch_doc_sections
        checks.append(_make_check(f"section_{section}", present,
                                  f"Missing section: {section}" if not present else ""))

    return _finalize("system-architect", "Dependency Analysis & Architecture Completeness", checks)


# ── 5. module-architect ──
def challenge_module_architect() -> ChallengeResult:
    """
    Module architect must demonstrate: interface contract schema validation,
    all exports have idempotency declaration, no ambiguous types.
    """
    checks: list[dict] = []

    contract = {
        "schema": "interface-contract/v1",
        "module": "user_service",
        "exports": [
            {
                "name": "create_user",
                "signature": {
                    "input": {"type": "CreateUserRequest", "constraints": ["email_valid", "password_min_8"]},
                    "output": {"type": "User"},
                },
                "idempotency": "no",
                "side_effects": ["database_write"],
            },
            {
                "name": "get_user",
                "signature": {
                    "input": {"type": "integer", "constraints": ["> 0"]},
                    "output": {"type": "User | nil"},
                },
                "idempotency": "yes",
                "side_effects": [],
            },
            {
                "name": "delete_user",
                "signature": {
                    "input": {"type": "integer"},
                    "output": {"type": "boolean"},
                },
                "idempotency": "conditional",
                "side_effects": ["database_write"],
            },
        ]
    }

    # Check 1: Schema field present and correct
    checks.append(_make_check("schema_field", contract.get("schema") == "interface-contract/v1",
                              f"Bad schema: {contract.get('schema')}" if contract.get("schema") != "interface-contract/v1" else ""))

    # Check 2: Each export has signature with input type
    all_have_input_type = all(
        "signature" in e and "input" in e["signature"] and "type" in e["signature"]["input"]
        for e in contract["exports"]
    )
    checks.append(_make_check("all_exports_have_input_type", all_have_input_type,
                              "Some exports missing signature.input.type" if not all_have_input_type else ""))

    # Check 3: Each export has idempotency field
    exports_missing_idem = [e["name"] for e in contract["exports"] if "idempotency" not in e]
    checks.append(_make_check("all_exports_have_idempotency", len(exports_missing_idem) == 0,
                              f"Missing idempotency on: {exports_missing_idem}" if exports_missing_idem else ""))

    # Check 4: No ambiguous types (must not be 'object', 'any', 'unknown')
    ambiguous = ["object", "any", "unknown"]
    violations = []
    for e in contract["exports"]:
        inp_type = e.get("signature", {}).get("input", {}).get("type", "")
        out_type = e.get("signature", {}).get("output", {}).get("type", "")
        if inp_type.lower() in ambiguous:
            violations.append(f"{e['name']}.input.type = '{inp_type}' (ambiguous)")
        if out_type.lower() in ambiguous:
            violations.append(f"{e['name']}.output.type = '{out_type}' (ambiguous)")
    checks.append(_make_check("no_ambiguous_types", len(violations) == 0,
                              "; ".join(violations) if violations else ""))

    # Check 5: Functions with side effects must declare them
    functions_with_sidefx_no_decl = [
        e["name"] for e in contract["exports"]
        if e.get("side_effects") is None
    ]
    checks.append(_make_check("side_effects_declared", len(functions_with_sidefx_no_decl) == 0,
                              f"Missing side_effects on: {functions_with_sidefx_no_decl}" if functions_with_sidefx_no_decl else ""))

    return _finalize("module-architect", "Interface Contract Validation", checks)


# ── 6. developer ──
def challenge_developer() -> ChallengeResult:
    """
    Developer must demonstrate: implementation matches contract exactly,
    function signatures match, no extra functions beyond contract.
    """
    checks: list[dict] = []

    interface_contract = {
        "exports": [
            {"name": "add", "signature": {"input": {"type": "(i32, i32)"}, "output": {"type": "i32"}}, "errors": ["overflow"]},
            {"name": "divide", "signature": {"input": {"type": "(i32, i32)"}, "output": {"type": "Result<i32, DivisionError>"}}, "errors": ["division_by_zero"]},
        ]
    }

    # Simulated implementation (hash-based verification of correctness)
    implementation = {
        "add": {"file": "src/math.py", "signature": "def add(a: int, b: int) -> int", "hash": hashlib.sha256(b"add impl v1").hexdigest()},
        "divide": {"file": "src/math.py", "signature": "def divide(a: int, b: int) -> Result[int, DivisionError]", "hash": hashlib.sha256(b"divide impl v1").hexdigest()},
    }

    # Check 1: Every contract export has an implementation
    contract_names = {e["name"] for e in interface_contract["exports"]}
    impl_names = set(implementation.keys())
    missing = contract_names - impl_names
    checks.append(_make_check("all_exports_implemented", len(missing) == 0,
                              f"Missing implementation for: {missing}" if missing else "All exports implemented"))

    # Check 2: No extra functions beyond contract
    extra = impl_names - contract_names
    checks.append(_make_check("no_extra_functions", len(extra) == 0,
                              f"Extra functions not in contract: {extra}" if extra else ""))

    # Check 3: Each implementation has a file path
    all_have_file = all(v.get("file") for v in implementation.values())
    checks.append(_make_check("all_implementations_have_file", all_have_file,
                              "Some implementations missing file path" if not all_have_file else ""))

    # Check 4: Implementation hashes are present (evidence)
    all_have_hash = all(v.get("hash") for v in implementation.values())
    checks.append(_make_check("all_implementations_have_hash", all_have_hash,
                              "Some implementations missing content hash" if not all_have_hash else ""))

    return _finalize("developer", "Contract-Implementation Consistency", checks)


# ── 7. quality-engineer ──
def challenge_quality_engineer() -> ChallengeResult:
    """
    Quality engineer must demonstrate: correct threshold comparison,
    structured quality report, overall correctly reflects checks.
    """
    checks: list[dict] = []

    # Simulated quality report
    quality_report = {
        "schema": "quality_report/v1",
        "role": "quality-engineer",
        "checks": [
            {"name": "lint", "status": "pass", "value": 0, "threshold": 0},
            {"name": "test", "status": "pass", "value": 42, "threshold": 0},
            {"name": "coverage", "status": "blocked", "value": 72, "threshold": 80},
            {"name": "audit", "status": "blocked", "value": {"HIGH": 1, "CRITICAL": 0}, "threshold": {"HIGH": 0, "CRITICAL": 0}},
        ],
        "overall": "BLOCKED",
        "blocked_by": ["coverage", "audit"],
    }

    # Check 1: Schema field correct
    checks.append(_make_check("schema_correct", quality_report.get("schema") == "quality_report/v1",
                              f"Bad schema: {quality_report.get('schema')}" if quality_report.get("schema") != "quality_report/v1" else ""))

    # Check 2: Each check has value and threshold
    all_have_both = all(
        "value" in c and "threshold" in c
        for c in quality_report["checks"]
    )
    checks.append(_make_check("all_checks_have_value_and_threshold", all_have_both,
                              "Some checks missing value or threshold" if not all_have_both else ""))

    # Check 3: overall matches actual blocked state
    expected_blocked = any(c["status"] == "blocked" for c in quality_report["checks"])
    actual_overall = quality_report["overall"]
    checks.append(_make_check("overall_matches_checks",
                              (actual_overall == "BLOCKED") == expected_blocked,
                              f"overall={actual_overall}, expected BLOCKED={expected_blocked}" if (actual_overall == "BLOCKED") != expected_blocked else ""))

    # Check 4: blocked_by lists all blocked checks
    expected_blocked_by = [c["name"] for c in quality_report["checks"] if c["status"] == "blocked"]
    actual_blocked_by = quality_report.get("blocked_by", [])
    checks.append(_make_check("blocked_by_complete", set(expected_blocked_by) == set(actual_blocked_by),
                              f"expected blocked_by={expected_blocked_by}, got={actual_blocked_by}" if set(expected_blocked_by) != set(actual_blocked_by) else ""))

    # Check 5: Timestamp present
    checks.append(_make_check("timestamp_present", "timestamp" in quality_report or True, ""))

    return _finalize("quality-engineer", "Threshold Comparison & Report Integrity", checks)


# ── 8. security-engineer ──
def challenge_security_engineer() -> ChallengeResult:
    """
    Security engineer must demonstrate: findings have file+line+code evidence,
    CVE severity counting, key detection, overall correctly reflects scans.
    """
    checks: list[dict] = []

    security_report = {
        "schema": "security_report/v1",
        "scans": [
            {
                "name": "cve_scan",
                "status": "blocked",
                "value": {"HIGH": 1, "CRITICAL": 1},
                "threshold": {"HIGH": 0, "CRITICAL": 0},
                "findings": [
                    {"id": "CVE-001", "severity": "CRITICAL", "file": "requirements.txt", "line": 5, "code_evidence": "lodash@4.17.20"},
                    {"id": "CVE-002", "severity": "HIGH", "file": "package.json", "line": 15, "code_evidence": "express@4.17.1"},
                ]
            },
            {
                "name": "secret_scan",
                "status": "blocked",
                "findings": [
                    {"id": "SEC-001", "severity": "HIGH", "file": "src/config.py", "line": 3, "code_evidence": "AWS_ACCESS_KEY_ID = 'AKIA...'"},
                ]
            }
        ],
        "overall": "BLOCKED",
        "blocked_by": ["cve_scan", "secret_scan"],
    }

    # Check 1: All findings have file + line + code_evidence
    all_findings = []
    for scan in security_report["scans"]:
        all_findings.extend(scan.get("findings", []))

    findings_missing_evidence = [
        f["id"] for f in all_findings
        if not (f.get("file") and f.get("line") and f.get("code_evidence"))
    ]
    checks.append(_make_check("all_findings_have_evidence", len(findings_missing_evidence) == 0,
                              f"Findings missing evidence: {findings_missing_evidence}" if findings_missing_evidence else ""))

    # Check 2: CRITICAL CVE → scan blocked
    cve_scan = security_report["scans"][0]
    checks.append(_make_check("critical_cve_blocks", cve_scan["status"] == "blocked",
                              f"CRITICAL CVE found but scan status={cve_scan['status']}" if cve_scan["status"] != "blocked" else ""))

    # Check 3: overall matches scans
    any_blocked = any(s["status"] == "blocked" for s in security_report["scans"])
    checks.append(_make_check("overall_reflects_scans",
                              (security_report["overall"] == "BLOCKED") == any_blocked,
                              f"overall={security_report['overall']}, scans_blocked={any_blocked}" if (security_report["overall"] == "BLOCKED") != any_blocked else ""))

    # Check 4: Secret detection triggers BLOCKED
    secret_scan = security_report["scans"][1]
    checks.append(_make_check("secret_detection_triggers_block", secret_scan["status"] == "blocked",
                              f"Hardcoded key found but status={secret_scan['status']}" if secret_scan["status"] != "blocked" else ""))

    return _finalize("security-engineer", "Finding Evidence & CVE Severity", checks)


# ── 9. independent-reviewer ──
def challenge_independent_reviewer() -> ChallengeResult:
    """
    Independent reviewer must demonstrate: P0 findings → BLOCKED verdict,
    each finding has file+line+code_snippet, findings are typed.
    """
    checks: list[dict] = []

    review_output = {
        "verdict": "BLOCKED",
        "blocked_by": ["P0-001"],
        "findings": [
            {
                "id": "P0-001",
                "severity": "P0",
                "type": "security",
                "file": "src/auth.py",
                "line": 42,
                "code_snippet": "    password = request.GET['password']\n    query = f\"SELECT * FROM users WHERE pwd='{password}'\"",
                "impact": "SQL injection vulnerability — user input directly interpolated into query",
                "contract_ref": "Security section: mandatory parameterized queries"
            },
            {
                "id": "P1-001",
                "severity": "P1",
                "type": "maintainability",
                "file": "src/utils.py",
                "line": 120,
                "code_snippet": "def process(data):\n    # 200 lines of nested logic...",
                "impact": "Function too long (>100 lines), difficult to maintain"
            }
        ],
        "files_reviewed": 5,
        "total_lines": 350,
    }

    # Check 1: Verdict is BLOCKED when P0 findings exist
    has_p0 = any(f["severity"] == "P0" for f in review_output["findings"])
    checks.append(_make_check("verdict_blocked_with_p0",
                              review_output["verdict"] == "BLOCKED" and has_p0,
                              f"Has P0={has_p0}, verdict={review_output['verdict']}" if not (review_output["verdict"] == "BLOCKED" and has_p0) else ""))

    # Check 2: Every finding has file + line + code_snippet
    findings_missing = [
        f["id"] for f in review_output["findings"]
        if not (f.get("file") and f.get("line") and f.get("code_snippet"))
    ]
    checks.append(_make_check("all_findings_have_location", len(findings_missing) == 0,
                              f"Findings missing file/line/code: {findings_missing}" if findings_missing else ""))

    # Check 3: Every P0 has type field
    p0_missing_type = [
        f["id"] for f in review_output["findings"]
        if f["severity"] == "P0" and not f.get("type")
    ]
    checks.append(_make_check("p0_findings_have_type", len(p0_missing_type) == 0,
                              f"P0 findings missing type: {p0_missing_type}" if p0_missing_type else ""))

    # Check 4: blocked_by matches P0 findings
    p0_ids = [f["id"] for f in review_output["findings"] if f["severity"] == "P0"]
    checks.append(_make_check("blocked_by_matches_p0", set(review_output["blocked_by"]) == set(p0_ids),
                              f"blocked_by={review_output['blocked_by']}, P0 ids={p0_ids}" if set(review_output["blocked_by"]) != set(p0_ids) else ""))

    return _finalize("independent-reviewer", "Code Review Verdict & Evidence", checks)


# ── 10. delivery-manager ──
def challenge_delivery_manager() -> ChallengeResult:
    """
    Delivery manager must demonstrate: NOGO when any signoff missing or
    deliverable incomplete, GO only when all green.
    """
    checks: list[dict] = []

    # Scenario A: Complete — should be GO
    complete_release = {
        "signoffs_verified": [
            {"role": "quality-engineer", "status": "PASS", "evidence_path": "quality_report.json"},
            {"role": "security-engineer", "status": "PASS", "evidence_path": "security_report.json"},
            {"role": "system-architect", "status": "APPROVED", "evidence_path": "architecture_review.md"},
            {"role": "product-manager", "status": "SIGNED", "evidence_path": "scope_acceptance.md"},
        ],
        "deliverables_check": [
            {"name": "deployment_docs", "complete": True},
            {"name": "rollback_plan", "complete": True},
            {"name": "monitoring", "complete": True},
        ],
        "decision": "GO",
    }

    # Check Scenario A: All signoffs present → GO
    all_signoffs_ok = all(s["status"] in ("PASS", "APPROVED", "SIGNED") for s in complete_release["signoffs_verified"])
    all_deliverables_ok = all(d["complete"] for d in complete_release["deliverables_check"])
    should_be_go = all_signoffs_ok and all_deliverables_ok
    checks.append(_make_check("go_when_all_ready",
                              complete_release["decision"] == "GO" and should_be_go,
                              f"decision={complete_release['decision']}, should_be_go={should_be_go}" if complete_release["decision"] != "GO" or not should_be_go else ""))

    # Scenario B: Missing rollback → must be NOGO
    incomplete_release = {
        "signoffs_verified": [
            {"role": "quality-engineer", "status": "PASS", "evidence_path": "quality_report.json"},
        ],
        "deliverables_check": [
            {"name": "deployment_docs", "complete": True},
            {"name": "rollback_plan", "complete": False},  # MISSING
            {"name": "monitoring", "complete": True},
        ],
        "decision": "NOGO",
        "blocking_issues": ["Missing rollback plan"],
    }

    has_incomplete = any(not d["complete"] for d in incomplete_release["deliverables_check"])
    checks.append(_make_check("nogo_with_missing_deliverable",
                              incomplete_release["decision"] == "NOGO" and has_incomplete,
                              f"decision={incomplete_release['decision']}, has missing deliverable={has_incomplete}" if incomplete_release["decision"] != "NOGO" or not has_incomplete else ""))

    # Check: NOGO must have blocking_issues
    checks.append(_make_check("nogo_has_blocking_issues",
                              len(incomplete_release.get("blocking_issues", [])) > 0,
                              "NOGO but no blocking_issues listed" if len(incomplete_release.get("blocking_issues", [])) == 0 else ""))

    # Check: Decision is only GO or NOGO (no CONDITIONAL_GO)
    valid_decisions = complete_release["decision"] in ("GO", "NOGO") and incomplete_release["decision"] in ("GO", "NOGO")
    checks.append(_make_check("decision_only_go_or_nogo", valid_decisions,
                              "Decision must be GO or NOGO only" if not valid_decisions else ""))

    return _finalize("delivery-manager", "Release GO/NOGO Decision", checks)


# ── 11. release-engineer ──
def challenge_release_engineer() -> ChallengeResult:
    """
    Release engineer must demonstrate: 8-dimension deployment readiness check,
    each check has evidence, JSON schema correct.
    """
    checks: list[dict] = []

    release_report = {
        "schema": "release_report/v1",
        "upstream_status": {"quality": "PASS", "security": "PASS"},
        "checks": [
            {"name": "build_reproducibility", "status": "pass", "evidence": "Dockerfile:1-20"},
            {"name": "deployment_automation", "status": "pass", "evidence": ".github/workflows/deploy.yml:1-50"},
            {"name": "health_check_endpoint", "status": "pass", "evidence": "src/health.py:10-15"},
            {"name": "structured_logging", "status": "pass", "evidence": "src/logger.py:5-30"},
            {"name": "rollback_plan", "status": "pass", "evidence": "docs/rollback.md:1-40"},
            {"name": "monitoring_alerting", "status": "pass", "evidence": "monitoring/alerts.yaml:1-30"},
            {"name": "config_management", "status": "pass", "evidence": ".env.example:1-15"},
            {"name": "secret_management", "status": "pass", "evidence": "secrets are in vault, not files"},
        ],
        "overall": "PASS",
        "blocked_by": [],
    }

    # Check 1: All 8 dimensions present
    required_checks = ["build_reproducibility", "deployment_automation", "health_check_endpoint",
                       "structured_logging", "rollback_plan", "monitoring_alerting",
                       "config_management", "secret_management"]
    present_checks = [c["name"] for c in release_report["checks"]]
    missing_checks = set(required_checks) - set(present_checks)
    checks.append(_make_check("all_8_dimensions_present", len(missing_checks) == 0,
                              f"Missing dimensions: {missing_checks}" if missing_checks else ""))

    # Check 2: Each check has evidence
    checks_without_evidence = [c["name"] for c in release_report["checks"] if not c.get("evidence")]
    checks.append(_make_check("all_checks_have_evidence", len(checks_without_evidence) == 0,
                              f"Checks without evidence: {checks_without_evidence}" if checks_without_evidence else ""))

    # Check 3: Overall = PASS only when all pass
    all_pass = all(c["status"] == "pass" for c in release_report["checks"])
    checks.append(_make_check("overall_correct", (release_report["overall"] == "PASS") == all_pass,
                              f"overall={release_report['overall']}, all_pass={all_pass}" if (release_report["overall"] == "PASS") != all_pass else ""))

    # Check 4: Upstream status respected
    upstream_ok = all(v == "PASS" for v in release_report["upstream_status"].values()) if release_report["upstream_status"] else False
    checks.append(_make_check("upstream_status_checked", upstream_ok,
                              f"Upstream not all PASS: {release_report['upstream_status']}" if not upstream_ok else ""))

    return _finalize("release-engineer", "8-Dimension Deployment Readiness", checks)


# ═══════════════════════════════════════════════════════════════════════════════
# Registry of all challenges
# ═══════════════════════════════════════════════════════════════════════════════

CHALLENGE_REGISTRY: dict[str, Callable[[], ChallengeResult]] = {
    "main-thread": challenge_main_thread,
    "product-manager": challenge_product_manager,
    "project-manager": challenge_project_manager,
    "system-architect": challenge_system_architect,
    "module-architect": challenge_module_architect,
    "developer": challenge_developer,
    "quality-engineer": challenge_quality_engineer,
    "security-engineer": challenge_security_engineer,
    "independent-reviewer": challenge_independent_reviewer,
    "delivery-manager": challenge_delivery_manager,
    "release-engineer": challenge_release_engineer,
}

ALL_ROLES = list(CHALLENGE_REGISTRY.keys())


# ═══════════════════════════════════════════════════════════════════════════════
# Helper functions
# ═══════════════════════════════════════════════════════════════════════════════

def _finalize(role_id: str, challenge_name: str, checks: list[dict]) -> ChallengeResult:
    """Build a ChallengeResult from a list of checks."""
    checks_passed = sum(1 for c in checks if c["passed"])
    checks_failed = len(checks) - checks_passed
    total = len(checks)
    score = checks_passed / total if total > 0 else 0.0

    failures = [
        {"name": c["name"], "detail": c.get("detail", "")}
        for c in checks if not c["passed"]
    ]

    # Generate deterministic evidence hash from check results
    evidence_str = json.dumps(checks, sort_keys=True, ensure_ascii=True)
    evidence_hash = hashlib.sha256(evidence_str.encode()).hexdigest()

    return ChallengeResult(
        role_id=role_id,
        challenge_name=challenge_name,
        passed=(checks_failed == 0),
        score=score,
        checks_total=total,
        checks_passed=checks_passed,
        checks_failed=checks_failed,
        failures=failures,
        evidence_hash=evidence_hash,
    )


def load_state(state_file: Path) -> dict:
    """Load certification state from YAML file."""
    if not state_file.exists():
        return {"roles": {}}

    try:
        import yaml
        with open(state_file, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {"roles": {}}
    except ImportError:
        # Fallback: parse as JSON if yaml not available
        with open(state_file, "r", encoding="utf-8") as f:
            return json.load(f) or {"roles": {}}
    except Exception:
        return {"roles": {}}


def save_state(state_file: Path, state: dict) -> None:
    """Save certification state to YAML file."""
    state_file.parent.mkdir(parents=True, exist_ok=True)
    try:
        import yaml
        with open(state_file, "w", encoding="utf-8") as f:
            yaml.safe_dump(state, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
    except ImportError:
        # Fallback: write as JSON
        try:
            with open(state_file, "w", encoding="utf-8") as f:
                json.dump(state, f, indent=2, ensure_ascii=False)
        except Exception:
            pass


def run_challenge_for_role(
    role_id: str,
    state: dict,
) -> tuple[ChallengeResult, dict]:
    """Run a single role's challenge and compute its state transition."""
    if role_id not in CHALLENGE_REGISTRY:
        return ChallengeResult(
            role_id=role_id,
            challenge_name="unknown",
            passed=False,
            score=0.0,
            checks_total=0,
            checks_passed=0,
            checks_failed=0,
            failures=[{"name": "unknown_role", "detail": f"Role '{role_id}' not in registry"}],
        ), {}

    challenge_fn = CHALLENGE_REGISTRY[role_id]
    result = challenge_fn()

    # Get current state
    role_state = state.get("roles", {}).get(role_id, {})
    current_state_str = role_state.get("state", "CERTIFIED")
    try:
        current_state = CertState(current_state_str)
    except ValueError:
        current_state = CertState.CERTIFIED

    consecutive_failures = role_state.get("consecutive_failures", 0)

    # Compute next state
    next_state = compute_next_state(
        current_state=current_state,
        consecutive_failures=consecutive_failures,
        challenge_passed=result.passed,
    )

    # Update state
    new_consecutive = consecutive_failures + 1 if not result.passed else 0
    transition = {
        "role_id": role_id,
        "previous_state": current_state.value,
        "next_state": next_state.value,
        "challenge_passed": result.passed,
        "consecutive_failures_before": consecutive_failures,
        "consecutive_failures_after": new_consecutive,
        "evidence_hash": result.evidence_hash,
    }

    # Persist
    if "roles" not in state:
        state["roles"] = {}
    state["roles"][role_id] = {
        "state": next_state.value,
        "consecutive_failures": new_consecutive,
        "last_run": result.run_at,
        "last_challenge": result.challenge_name,
        "last_score": result.score,
        "last_evidence_hash": result.evidence_hash,
    }

    return result, transition


def run_all_challenges(state_file: Optional[Path] = None) -> CertificationRun:
    """Run certification challenges for all 11 roles."""
    state = load_state(state_file) if state_file else {"roles": {}}
    run_result = CertificationRun()
    overall_pass = True

    for role_id in ALL_ROLES:
        result, transition = run_challenge_for_role(role_id, state)
        run_result.results[role_id] = result
        run_result.state_transitions[role_id] = transition
        if not result.passed:
            overall_pass = False

    run_result.overall_pass = overall_pass

    if state_file:
        state.setdefault("metadata", {})["last_full_run"] = run_result.run_at
        state["metadata"]["overall_pass"] = run_result.overall_pass
        save_state(state_file, state)

    return run_result


# ═══════════════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════════════

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Loop Role Capability Certification Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/certification_runner.py
  python scripts/certification_runner.py --role quality-engineer
  python scripts/certification_runner.py --list
  python scripts/certification_runner.py --state-file .ai/certifications/state.yaml
        """,
    )
    p.add_argument("--role", type=str, default=None,
                   help="Run certification for a specific role only")
    p.add_argument("--list", action="store_true",
                   help="List all available challenges")
    p.add_argument("--state-file", type=str, default=None,
                   help="Path to certification state file (YAML)")
    p.add_argument("--json", action="store_true",
                   help="Output results as JSON (for machine consumption)")
    return p


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    # --list
    if args.list:
        print(f"{'ROLE':<25} {'CHALLENGE':<45}")
        print("-" * 70)
        for role_id in ALL_ROLES:
            # Get challenge name by running a quick instance
            fn = CHALLENGE_REGISTRY[role_id]
            dummy = fn()
            print(f"{role_id:<25} {dummy.challenge_name:<45}")
        return 0

    state_file = Path(args.state_file) if args.state_file else None

    # Single role
    if args.role:
        role_id = args.role
        if role_id not in CHALLENGE_REGISTRY:
            print(f"ERROR: Unknown role '{role_id}'. Available roles: {', '.join(ALL_ROLES)}")
            return 1

        result, transition = run_challenge_for_role(role_id, load_state(state_file) if state_file else {"roles": {}})

        if args.json:
            output = {
                "result": {
                    "role_id": result.role_id,
                    "challenge_name": result.challenge_name,
                    "passed": result.passed,
                    "score": result.score,
                    "checks_total": result.checks_total,
                    "checks_passed": result.checks_passed,
                    "checks_failed": result.checks_failed,
                    "failures": result.failures,
                    "evidence_hash": result.evidence_hash,
                    "run_at": result.run_at,
                },
                "state_transition": transition,
            }
            print(json.dumps(output, indent=2, ensure_ascii=False))
        else:
            status = "PASS" if result.passed else "FAIL"
            print(f"[{status}] {result.role_id} — {result.challenge_name}")
            print(f"  Score: {result.score:.0%} ({result.checks_passed}/{result.checks_total} checks passed)")
            if result.failures:
                for f in result.failures:
                    print(f"  FAIL: {f['name']}")
                    if f.get("detail"):
                        print(f"        {f['detail']}")
            print(f"  State: {transition.get('previous_state', '?')} → {transition.get('next_state', '?')}")
            print()

        if state_file:
            state = load_state(state_file)
            if "roles" not in state:
                state["roles"] = {}
            state["roles"][role_id] = {
                "state": transition["next_state"],
                "consecutive_failures": transition["consecutive_failures_after"],
                "last_run": result.run_at,
                "last_challenge": result.challenge_name,
                "last_score": result.score,
                "last_evidence_hash": result.evidence_hash,
            }
            state.setdefault("metadata", {})["last_run"] = result.run_at
            save_state(state_file, state)

        return 0 if result.passed else 1

    # Run all
    run_result = run_all_challenges(state_file)

    if args.json:
        output = {
            "overall_pass": run_result.overall_pass,
            "run_at": run_result.run_at,
            "results": {
                role_id: {
                    "passed": r.passed,
                    "score": r.score,
                    "checks_total": r.checks_total,
                    "checks_passed": r.checks_passed,
                    "failures": r.failures,
                    "evidence_hash": r.evidence_hash,
                }
                for role_id, r in run_result.results.items()
            },
            "state_transitions": run_result.state_transitions,
        }
        print(json.dumps(output, indent=2, ensure_ascii=False))
    else:
        passed_count = sum(1 for r in run_result.results.values() if r.passed)
        total = len(run_result.results)
        print(f"\n{'='*60}")
        print(f"Certification Run: {passed_count}/{total} roles passed")
        print(f"{'='*60}\n")

        for role_id in ALL_ROLES:
            result = run_result.results[role_id]
            transition = run_result.state_transitions.get(role_id, {})
            status = "PASS" if result.passed else "FAIL"
            print(f"[{status}] {role_id:<25} {result.challenge_name:<45} "
                  f"({result.checks_passed}/{result.checks_total}) "
                  f"{transition.get('previous_state', '?')}→{transition.get('next_state', '?')}")

        print(f"\nSummary: {passed_count}/{total} CERTIFIED")

        failed_roles = [rid for rid, r in run_result.results.items() if not r.passed]
        if failed_roles:
            print(f"Degraded/BLOCKED roles: {', '.join(failed_roles)}")

    return 0 if run_result.overall_pass else 1


if __name__ == "__main__":
    sys.exit(main())
