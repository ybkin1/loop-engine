# Loop v4 Design — B2: SLO / Error Budget + Loop-DORA Metrics + Learning Loop

| | |
|---|---|
| **Task** | T-0083 — Design deliverable B2 |
| **Role** | system-architect |
| **Date** | 2026-07-31 |
| **Status** | draft (design blueprint for T-0086, T-0087, T-0088) |
| **Basis** | gap-analysis §2.1 (no SLO/error budget), §2.2 (no DORA metrics), §2.3 (no postmortem/retro), §5 priority matrix rows 4/5/6, §6.2 (governance metrics), §6.3 (learning-loop phases); roles-research §10 (SRE), §11 (PM sets the SLO); delivery-governance-research §6.3 (Amazon COE + second-failure doctrine); current Loop types: `Phase` S0–S11 with S11→S1 loop (state_machine.py:14-27, 65), `USER_GATE_PHASES = {S1, S6}` (state_machine.py:93-96), `GateStatus` (36-41), `ReportBinding` (verdicts.py:37), `.ai/gates.yaml` register, `.ai/ledger/executions.jsonl`, `Verdict` enum (verdicts.py:11) |
| **Scope** | Design only. No code changes in T-0083. Consumed by T-0086/T-0087/T-0088. |

---

## 0. Executive summary

Three subsystems convert Loop from a **write-control and approval-tracking system** into a **quality and delivery governance system** (gap verdict):

1. **SLO subsystem** — SLI→SLO→error budget; a depleted budget *automatically* freezes releases (gate-block at S6). Makes delivery governance data-driven instead of opinion-based (gap §2.1). PM sets the SLO (roles-research §11: "product management sets the SLO"); `slo.yaml` is the project artifact.
2. **Loop-DORA metrics subsystem** — quantitative delivery telemetry derived from the ledger/register: gate rejection rate, phase dwell time, rework cycles, evidence regeneration, guard block/pass/error rates, drift events, approval latency. Aggregation module `loop_core/governance_metrics.py` + dashboard + per-sprint review (gap §2.2, §6.2).
3. **Learning loop** — incident records + retrospectives with owned action items; the **second-failure doctrine** (same failure class recurs → auto task creation + gate block until an owned action item exists); S11→S1 becomes a PDCA loop with metrics as the Check step (gap §2.3, §6.3).

Shared design principles (inherited from B1): every new gate condition is fail-closed via `NOT_VERIFIED` (gap §3.2/§6.5); artifacts are `ReportBinding`-bound; enforcement is progressive (wave 1 advisory → wave 2 enforced → wave 3 default-on).

---

## 1. SLO subsystem — gap §2.1, priority-matrix T-0086

### 1.1 Purpose

Loop has no concept of "how much failure can this project tolerate" (gap §2.1 evidence: zero SLO/error-budget hits in loop_core/hooks; `USER_GATE_PHASES = {S1, S6}` makes the release gate a human checkbox, not a budget check). The SLO subsystem adds: SLI definitions, SLO targets, error-budget accounting, and **automatic release freeze when the budget is exhausted** — the mechanism that makes release throttling non-political (roles-research §10: "depleted budget → releases slowed or halted"; "the system itself gates release velocity").

Important scoping note: Loop's SLOs govern the **delivery process itself** (governance quality: gate correctness, rework, dwell time) and — for agent projects (B1) — the **agent runtime** (eval pass rates, cost/latency budgets). They are process SLOs, not production uptime SLOs; production SLOs for delivered products are out of scope until a real deployment channel exists (T-0094).

### 1.2 SLI definitions per phase / project type

SLIs are the quantitative inputs; each is **derivable from existing or B2-added ledger data** (see §2.2 for sources).

| Phase | SLI (id) | Definition | Default SLO target (proposal) |
|---|---|---|---|
| S1-requirements | `req_gate_rejection_rate` | S1 gate rejections / (approvals + rejections) | ≤ 0.35 |
| S1 | `ac_invest_rate` | acceptance criteria meeting INVEST/verifiable shape | 1.0 (checked by DoD gate, T-0089) |
| S2-architecture | `design_review_rejection_rate` | design review rejections / decisions | ≤ 0.30 |
| S4-implementation | `guard_block_rate` | guard blocks / (blocks + passes) across hooks | ≤ 0.05 false-positive proxy (see §2.2) |
| S4 | `rework_cycle_rate` | S4↔S5 bounce count / tasks completed | ≤ 0.25 (target 0 by definition of Done, T-0089) |
| S4 | `delta_quality_pass_rate` | tasks passing delta gates (no new coverage/lint/security regressions on the diff) | = 1.0 |
| S5-quality | `quality_gate_rejection_rate` | S5 rejections / decisions | ≤ 0.30 |
| S5 | `evidence_regeneration_rate` | evidence regeneration events (C8) / tasks | ≤ 0.10 |
| S5 | `defect_fail_verdict_rate` | tasks with `FAIL` verdicts (warning class) | ≤ 0.20 (feeds bug-cap backlog, gap §2.5) |
| S6-delivery | `delivery_gate_rejection_rate` | S6 rejections (incl. NOGO) / decisions | ≤ 0.20 |
| S6 | `approval_latency_p95` | p95 of gate requested_at → recorded_at | ≤ 24 h |
| S11-maintenance | `drift_event_rate` | governance drift events / window | ≤ 2 per window |
| All | `gate_decision_coverage` | gates decided with evidence dossier vs. decided | = 1.0 |

**Agent project type additions** (only when the project has agent deliverables; SLIs defined in B1): `eval_task_completion_pass1`, `eval_safety_pass3`, `trace_coverage`, `cost_per_run_p95`, `redteam_pass_rate` — these bind the B1 gate conditions to error budgets so repeated eval failures consume budget instead of merely blocking once.

SLO setting flow: **product-manager proposes** targets (the reliability tradeoff conversation — roles-research §11), **system-architect + delivery-manager validate** feasibility (can the process actually meet this?), **user approves at the S1 gate** (S1 is already a `USER_GATE_PHASE`). Changes to SLOs are governance changes → CAB path (T-0095).

### 1.3 Project artifact — `.ai/slo.yaml`

```yaml
schema_version: 1
project_id: loop-engine
owner_role: product-manager
reviewed_by: [ delivery-manager, system-architect ]
approved_by: user
approved_gate: G-T-XXXX-S1-SLO
budget_window: quarterly        # research: quarterly error budgets (SRE book ch3)
window_start: "2026-07-01"
window_end: "2026-09-30"
slos:
  - sli_id: quality_gate_rejection_rate
    target: { op: "<=", value: 0.30, per: "window" }
    severity: error-budget-slo     # budget-consuming
    budget_share: 0.5              # half the budget window is allocated here
  - sli_id: approval_latency_p95
    target: { op: "<=", value: "24h" }
    severity: error-budget-slo
    budget_share: 0.25
  - sli_id: delta_quality_pass_rate
    target: { op: ">=", value: 1.0 }
    severity: hard-gate             # not budget-consuming: every violation blocks
  - sli_id: drift_event_rate
    target: { op: "<=", value: 2 }
    severity: informational
freeze_policy:
  trigger: budget_exhausted
  freeze_scope: [ S6-delivery ]      # releases freeze; feature work continues (research §10)
  unfreeze: budget_recovers           # window rollover or approved budget increase
  escalation: delivery-manager → user
```

### 1.4 Budget accounting model (per-release consumption)

- **Window**: quarterly (configurable). **Budget**: 100 units per window.
- **Consumption**: each SLO breach event consumes `budget_share × (100 / expected_breaches_at_target)` — concretely: at target compliance (e.g., rejection rate ≤ 0.30) the SLO is expected to be violated a bounded number of times per window; a breach beyond the expectation consumes proportionally. Simplified v1 rule: **one breach = 1 unit per budget-consuming SLO**, with the freeze at 100 units; `budget_share` scales a unit's weight.
- **Per-release consumption**: every release (S6→S7 promotion) consumes a fixed **release fee** (e.g., 5 units) — "releases are the primary consumer of the budget" (SRE book ch3-4, gap §2.1). Fee is configurable in `slo.yaml` (`release_fee_units`).
- **Depletion → automatic release freeze**: when remaining units ≤ 0, the S6 gate condition `slo_budget_available` evaluates False → **gate-block** (release freeze). Feature work in S1–S5 is NOT frozen (research §10: freeze releases, not development). Unfreeze only via: window rollover (budget resets), or an explicit user-approved budget increase (recorded as a governance change, T-0095).
- **Accounting record**: `.ai/ledger/budget_events.jsonl` — append-only, chain-hashed like `executions.jsonl`: `{event, sli_id, units, remaining, at, task_id, gate_id, binding}`. The ledger makes budget state reconstructible (mirrors the runtime-state reconstruction principle, gap §3.7/§6.7).

### 1.5 Gate integration

| Point | Mechanism |
|---|---|
| S6 gate (release) | new condition `slo_budget_available` (params: `slo: .ai/slo.yaml`, `require_remaining_units > 0`); evaluates budget ledger; False → gate blocked with reason `ERROR_BUDGET_EXHAUSTED` |
| S1 gate | condition `slo_defined` (params: require `.ai/slo.yaml` present + user-approved) — "no SLO, no project baseline" |
| S5 gate | `slo_report_fresh` — metrics report (§2.4) for the current window exists and is fresh (feeds the Check step) |
| All gates | `GateStatus.BLOCKED` gains a `reason` payload (`blocked_reason: { code, sli_id, units_remaining }`) so the user sees *why* (extends T-0097 decision vocabulary) |

### 1.6 Roles, migration, effort

| Item | Value |
|---|---|
| Roles | **product-manager** (sets SLO — the missing responsibility today), **delivery-manager** (freeze escalation), **system-architect** (SLI derivation feasibility), **release-engineer** (budget ledger), **user** (S1 approval of SLOs) |
| Migration | Wave 1: `slo.yaml` + budget ledger (advisory, no blocking); Wave 2: `slo_budget_available` enforced at S6 for projects with `slo.yaml`; Wave 3: `slo_defined` mandatory at S1 for governed projects |
| Effort | M |
| Depends on | T-0088 (metrics aggregation — SLIs computed from the same module), T-0089 (DoD — SLO targets need a defined Done bar), T-0094 (runtime safety net — release freeze is a release-path control), T-0095 (SLO changes = governance changes) |

---

## 2. Loop-DORA metrics subsystem — gap §2.2, priority-matrix T-0088

### 2.1 Purpose

Nothing measures whether Loop's governance is *improving* delivery (gap §2.2: "the only counters are per-task file-write counts"). This subsystem turns the ledger/register into DORA-style governance telemetry — "measure the system, not individuals" (dora.dev; quality-mechanisms §4.4) — and is the root of Goodhart-proofing: with metrics, gaming becomes detectable rather than impossible-but-unsteerable.

### 2.2 Metric catalog (definitions + data sources)

| Metric | Definition | Data source (existing) | New data needed |
|---|---|---|---|
| `gate_rejection_rate` | rejected / (approved + rejected) per gate per phase | `.ai/gates.yaml` (status/decision) | none |
| `gate_decision_coverage` | gates decided with evidence dossier / decided | `.ai/gates.yaml` (evidence fields) | none |
| `phase_dwell_time` | p50/p95 time per phase per task | `.ai/state.yaml` phases (entered_at) + ledger `launched_at`/`completed_at` | none |
| `task_rework_cycles` | S4→S5→S4 bounce count per task | state.yaml transition history / ledger role sequence | transition journal (see below) |
| `evidence_regeneration_events` | count of evidence re-runs (C8 freshness failures) | ledger `evidence_refs`, `execution_id` reuse | none |
| `guard_block_pass_error_rates` | per-guard block/pass/error counts | T-0083 guard-health battery reports + hook decision logs | `.ai/ledger/guard_decisions.jsonl` (append-only hook decision log — new, small) |
| `drift_events` | governance drift detections (stale HANDOFF, state mismatch) | `.ai/ledger/runtime-events.jsonl` + continuity auditor (T-0078) | none |
| `approval_latency` | p50/p95 of gate `requested_at` → `recorded_at` | `.ai/gates.yaml` | none |
| `dead_guard_events` | guards reporting DORMANT/BROKEN in health battery | guard-health reports (T-0083/B3) | none |
| `task_cycle_time` | task created → completed | task_graph.yaml + ledger | none |
| (B1) `eval_pass_trend` | eval pass-rate per dimension over time | eval_report.json artifacts | none |

**Rework-cycle precision requires a transition journal**: today `state.yaml` holds the current phase, not the transition history. Add `.ai/ledger/phase_transitions.jsonl` (append-only: `{task_id, from_phase, to_phase, at, binding}`) written by the phase-change path. This single small addition makes dwell time, rework cycles, and reentry behavior all computable — highest value-per-effort change in this subsystem.

### 2.3 Aggregation module — `loop_core/governance_metrics.py` (design sketch for T-0088)

```python
"""loop_core/governance_metrics.py — v4 design sketch (T-0088).

Aggregates ledger/register artifacts into Loop-DORA governance telemetry.
Pure functions over immutable inputs; no I/O except explicit loaders.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timedelta

@dataclass
class GateMetric:
    gate_id: str
    task_id: str
    phase: str
    status: str            # pending|approved|rejected|blocked
    decision: str | None
    requested_at: datetime | None
    recorded_at: datetime | None
    evidence_paths: list[str] = field(default_factory=list)

# ── loaders ────────────────────────────────────────────────────────────
def load_gates(root: str, since: datetime | None = None) -> list[GateMetric]: ...
def load_guard_decisions(root: str) -> list[dict]: ...
def load_phase_transitions(root: str) -> list[dict]: ...
def load_ledger_executions(root: str) -> list[dict]: ...

# ── metrics (pure) ─────────────────────────────────────────────────────
def gate_rejection_rate(gates: list[GateMetric], phase: str | None = None) -> float: ...
def gate_decision_coverage(gates: list[GateMetric]) -> float: ...
def approval_latency(gates: list[GateMetric], phase: str | None = None) -> dict:
    """-> {"p50": timedelta, "p95": timedelta, "mean": timedelta, "count": int}"""
def phase_dwell_times(transitions: list[dict]) -> dict[str, list[timedelta]]:
    """phase -> list of dwell durations"""
def rework_cycles(transitions: list[dict], a: str = "S4-implementation",
                  b: str = "S5-quality") -> dict[str, int]:
    """task_id -> bounce count between phases a and b"""
def evidence_regenerations(executions: list[dict]) -> int: ...
def guard_rates(decisions: list[dict]) -> dict[str, dict]:
    """guard_id -> {"block": n, "pass": n, "error": n, "rate": float}"""
def drift_events(events: list[dict]) -> list[dict]: ...
def task_cycle_times(tasks: list[dict], executions: list[dict]) -> dict[str, timedelta]: ...
def dead_guard_events(health_reports: list[dict]) -> list[dict]: ...

# ── report ─────────────────────────────────────────────────────────────
@dataclass
class MetricsReport:
    window: tuple[datetime, datetime]
    metrics: dict
    sli_eval: dict      # each SLO in slo.yaml vs. actual (feeds §1)
    generated_at: datetime

def build_report(root: str, window: tuple[datetime, datetime],
                 slo_path: str = ".ai/slo.yaml") -> MetricsReport: ...
def render_markdown(report: MetricsReport) -> str: ...   # dashboard/report output
```

Placement and rules: module lives in `loop_core/` (host-independent, like `verdicts.py`); every metric is a pure function of ledger inputs so results are reproducible from a commit; report binds `git_commit` + window; **aggregation never writes to the ledger** (read-only) — the ledger is written only by the enforcement/hook path (append-only rule).

### 2.4 Dashboard / report output

- **Machine output**: `.ai/metrics/{window}.json` written by a CLI (`tools/loop_metrics.py --window quarterly --report`), ReportBinding-bound; consumed by gates (`slo_report_fresh`, §1.5) and by the dashboard.
- **Human output**: `render_markdown` produces `.ai/metrics/{window}.md` — the DORA-style report (deployment-frequency analog = phase-promotion rate, change-fail-rate analog = gate rejection rate, lead-time analog = task cycle time, recovery analog = rework cycles). Extend `.ai/status_dashboard.py` (currently renders state, not delivery performance — gap §2.2) with a metrics panel; no new UI framework.
- **Review cadence**: per-sprint — the report is reviewed at the **S11 retro** (the Check step of the PDCA loop, §3.4); a quarterly management snapshot derived from the same data. Per-sprint review is the minimum cadence (gap §2.2: "metrics reviewed periodically"; delivery-governance §4.4).

### 2.5 Goodhart-proofing notes

- Metrics are process telemetry, not individual performance (dora.dev) — the report shows tasks/teams only as aggregates.
- Gaming surfaces as drift: a sudden drop in `evidence_regeneration_events` alongside a rise in `guard_block_rate` is itself a drift event (T-0078-era continuity audit pattern).
- All metrics are reproducible from the ledger: an asserted metric that cannot be recomputed from `.ai/` artifacts is a `NOT_VERIFIED` report (fail-closed, IV&V via T-0090).

### 2.6 Roles, migration, effort

| Item | Value |
|---|---|
| Roles | **delivery-manager** (report owner, per-sprint review chair), **release-engineer** (aggregation tooling), **project-manager** (S11 retro consumption), **system-architect** (metric definitions) |
| Migration | Wave 1: `guard_decisions.jsonl` + `phase_transitions.jsonl` writers (invisible, append-only); Wave 2: `governance_metrics.py` + report CLI (advisory); Wave 3: `slo_report_fresh` gate + dashboard panel |
| Effort | S–M (two small ledger writers + one pure module + CLI) |
| Depends on | T-0084 (guard-health battery output feeds `guard_rates`), T-0086 (SLI evaluation consumes `build_report`), T-0087 (retro consumes reports), T-0095 (drift events feed CAB) |

---

## 3. Learning loop — gap §2.3, priority-matrix T-0087

### 3.1 Purpose

Loop's S11→S1 transition (state_machine.py:65) is a *cycle*, not a *learning loop* (gap §2.3): no incident record, no retro artifact, no action-item registry, nothing prevents the same failure class from recurring. Real practice: blameless postmortems with owned action items tracked to closure (SRE book ch15); sprint retros producing improvement plans (Scrum Guide); Amazon COE + **second-failure doctrine** — "the second failure is the process's fault" (delivery-governance §6.3). This subsystem makes the loop learn.

### 3.2 Incident record — `.ai/incidents/incident-{id}.yaml`

```yaml
schema_version: 1
incident_id: INC-2026-004
severity: P1 | P2 | P3
title: "Guard DORMANT silent PASS for 4 weeks"
trigger:
  type: guard-failure | gate-rejection | drift | incident-flag | agent-bad-output
  ref: "rule_id: GC-001 | gate: G-T-0083-… | drift: DR-007"
timeline:                       # blameless, chronological
  - { at: "2026-07-28T09:00:00+08:00", event: "detected", by: guard-health-battery }
  - { at: "2026-07-28T11:30:00+08:00", event: "contained", by: security-engineer }
  - { at: "2026-07-29T15:00:00+08:00", event: "resolved", by: developer }
detection: { method: automated | manual, tool: "loop_guard_health.py | reviewer", by_role: quality-engineer }
root_cause:
  failure_class: FC-003            # registry key (see §3.3)
  rule_id: "bash_content_guard.bad-escape"
  contributing: [ "no guard-health battery", "exit-code-only tests" ]
resolution:
  action: "repair regex + add death test"
  reverted: false
  verified_by: test-engineer
  verified_method: guard-death-test
links:
  eval_case_added: "eval-014"      # B1: incidents become eval cases (research §10.3)
  retro: RETRO-2026-Q3-02
binding: { task_id: "T-0083", phase: "S4-implementation", git_commit: "d01b53e", timestamp: "…" }
```

Severity guidance: P1 = governance silent (guard death, fail-open — the T-0082 class); P2 = gate mis-decision with recovery; P3 = near-miss / process friction. **Blame-free by construction**: `resolution` names actions, `contributing` names mechanisms, never individuals.

### 3.3 Retrospective artifact — `.ai/retros/retro-{id}.yaml` + failure-class registry

```yaml
schema_version: 1
retro_id: RETRO-2026-Q3-02
phase: S11-maintenance
sprint: "2026-Q3"
linked_incidents: [ INC-2026-004 ]
metrics_report: .ai/metrics/2026-Q3.json      # the PDCA Check input
what_worked:
  - "guard-health battery caught the dormancy within a day"
what_failed:
  - "no battery existed before T-0083"
action_items:
  - id: AI-004
    text: "Add guard-death fixture for content_guard semantic rules"
    owner_role: security-engineer
    due_date: "2026-08-15"
    failure_class: FC-003
    status: open | in_progress | closed
    verification: { method: guard-death-test, ref: "tests/test_guard_health.py::GC-002" }
    closed_at: null
```

Failure-class registry — `.ai/retros/failure-classes.yaml`:

```yaml
schema_version: 1
failure_classes:
  - id: FC-003
    name: guard-dormancy
    rule_ids: [ "bash_content_guard.*", "content_guard.semantic_rules" ]
    first_seen: INC-2026-002
    occurrences: [ INC-2026-002, INC-2026-004 ]
    doctrine_state: second-failure-triggered | action-item-open | closed
    current_action_item: AI-004
```

### 3.4 Second-failure doctrine enforcement (the loop that closes)

Rule: an incident whose `root_cause.failure_class` already appears in the registry (`occurrences` ≥ 1) is a **second failure** of that class.

1. **Auto task creation**: `loop_core/learning_loop.py` (design sketch) creates a follow-up task (T-XXXX, phase S1-requirements per reentry, `depends_on` the failing task) with the action item from the first failure's retro as its scope — no human needs to notice the recurrence.
2. **Gate block**: the current phase gate (any phase, but typically S5/S6/S11) gains condition `action_item_closed` for the recurring class — the phase cannot promote until an **owned, dated action item** exists for the class (status `open` with owner_role + due_date); if the class already has `closed` action items that were ineffective, the block is on **re-opening** with a new owner.
3. **Escalation**: third occurrence of a class with an overdue action item escalates to the user (delivery-manager + user decision — extend the escalation ladder, T-0097).
4. **Close-out**: action items close only via `verification` (a machine-checked method — test, audit, guard fixture) — mirroring the "protection-vs-execution" rule of T-0083 (AC-05) and gap §3.5. A closed-by-assertion action item is not closed.

### 3.5 S11→S1 as a PDCA loop

| PDCA step | Loop mechanism |
|---|---|
| **Plan** | S1-requirements: retro action items + incident-derived tasks enter the backlog (auto-created per §3.4); SLOs set (B2 §1) |
| **Do** | S2–S10 phases (unchanged machine) |
| **Check** | S11: metrics report review (`build_report`, §2.3) + guard-health battery + drift events; the phase evidence for S11 must include `metrics_report` + `retro` when the window has incidents |
| **Act** | S11 retro produces action items with owners/due dates; S11→S1 carries them (state_machine.py:65 unchanged — the artifacts are what change) |

Phase-machine changes: **no new phase enum values**; the loop rides S11 and the S1 reentry (minimal diff, honors "fix is mostly wiring, not invention" — gap §7.4). `retro_required`/`incident_required` are conditions on the S11→S1 transition and on any gate that rejects with a new failure class.

### 3.6 Roles, migration, effort

| Item | Value |
|---|---|
| Roles | **project-manager** (retro chair, action-item registry owner — the missing Scrum/PM ceremony, gap §1 #6), **delivery-manager** (incident triage, escalation), **security-engineer/quality-engineer** (RCA owners per class), **system-architect** (failure-class taxonomy), **independent-reviewer** (blamelessness and verification audit) |
| Migration | Wave 1: incident/retro schemas + failure-class registry (advisory, manual); Wave 2: `learning_loop.py` auto task creation + `action_item_closed` gate block; Wave 3: `retro_required` at S11 default-on |
| Effort | M |
| Depends on | T-0088 (metrics report = Check input), T-0084 (guard-health feeds incident triggers), T-0086 (SLO freeze interacts with incident gates), T-0095 (incident-driven governance changes go through CAB), B1 §8 (agent incidents) |

---

## 4. Cross-cutting summary

### 4.1 New gate condition types (added to `evaluate_condition`, state_machine.py)

| Condition | Artifact | Behavior on failure | Phase |
|---|---|---|---|
| `slo_defined` | `.ai/slo.yaml` + user approval | NOT_VERIFIED | S1 |
| `slo_budget_available` | budget ledger + slo.yaml | BLOCKED `ERROR_BUDGET_EXHAUSTED` (release freeze) | S6 |
| `slo_report_fresh` | `.ai/metrics/{window}.json` | NOT_VERIFIED | S5, S11 |
| `incident_required` | `.ai/incidents/incident-*.yaml` | NOT_VERIFIED | S11→S1, after gate rejections |
| `retro_required` | `.ai/retros/retro-*.yaml` | NOT_VERIFIED | S11→S1 |
| `action_item_closed` | failure-classes.yaml + retro action items | BLOCKED (second-failure doctrine) | any phase gate on recurrence |

### 4.2 New ledger files (all append-only, chain-hashed like executions.jsonl)

| File | Writer | Consumed by |
|---|---|---|
| `.ai/ledger/guard_decisions.jsonl` | hook chain (PreToolUse guards) | `guard_rates`, SLO `guard_block_rate` |
| `.ai/ledger/phase_transitions.jsonl` | phase-change path | `phase_dwell_times`, `rework_cycles` |
| `.ai/ledger/budget_events.jsonl` | SLO subsystem | `slo_budget_available` |

### 4.3 Role additions/extensions

| Role | Change |
|---|---|
| product-manager | **new responsibility**: sets SLOs (user-approved at S1) |
| delivery-manager | report owner, freeze escalation, incident triage |
| project-manager | retro chair, action-item registry |
| release-engineer | budget ledger, metrics tooling |
| system-architect | SLI definitions, failure-class taxonomy |
| (new, later) sre | production SLO/incident discipline when a deployment channel exists (gap §1 #10 folded into T-0086/T-0094; explicit role only if a second governed project needs it) |

### 4.4 Acceptance criteria (sketch for T-0086/T-0087/T-0088)

- AC-SLO: a project with `slo.yaml` whose budget is exhausted is **blocked at S6** with reason `ERROR_BUDGET_EXHAUSTED`; feature phases remain open; unfreeze requires window rollover or user-approved budget change.
- AC-SLO: every SLO breach is an append-only budget ledger event reconstructible from `.ai/`.
- AC-MET: `rework_cycles` for a task that bounced S4→S5→S4 equals 1; `approval_latency` is computable for every gate with a recorded decision; a metrics report missing data is `NOT_VERIFIED`, never a silent zero.
- AC-LEARN: reproducing an incident of an already-registered failure class auto-creates a follow-up task **and** blocks the phase gate until an owned+dated action item exists.
- AC-LEARN: an action item closes only via machine-verifiable evidence (test/fixture/audit), not assertion.

---

*Design deliverable B2 of T-0083. Companion docs: `docs/designs/loop-v4-ai-agent-governance.md` (B1), `docs/designs/loop-v4-consolidated-roadmap.md` (roadmap + B3–B7 status).*
