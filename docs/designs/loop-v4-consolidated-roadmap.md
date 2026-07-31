# Loop v4 Consolidated Roadmap — B1/B2 subsystems + priority-matrix items (T-0084 → T-0103)

| | |
|---|---|
| **Task** | T-0083 — Design deliverable B3 (roadmap) |
| **Role** | system-architect |
| **Date** | 2026-07-31 |
| **Status** | draft |
| **Basis** | gap-analysis §5 priority matrix (T-0084–T-0097) + B1 design (docs/designs/loop-v4-ai-agent-governance.md) + B2 design (docs/designs/loop-v4-slo-metrics-learning.md) + T-0083 implemented meta-governance layer (B3–B7: guard health, fail-closed defaults, self-audit loop, toolchain integrity gate, e2e vertical slice) |

---

## 1. How to read this roadmap

- **Phase** = the Loop phase in which the work should be scheduled (from gap §5 or B1/B2 design).
- **Effort** = S/M/L implementation effort for a single task (blueprints in docs/designs/ provide the schemas).
- **Dependencies** = tasks that must land before or alongside.
- **Gap closed** = gap-analysis section(s) the task resolves (B1/B2 item refs where applicable).
- **T-0083 status** = how much T-0083 (the meta-governance layer, B3–B7) already covers. B3–B7 are the six T-0083 implementation blocks:
  - **B3** guard-health subsystem (`loop_core/guard_health.py` + battery + death tests, AC-03/AC-05),
  - **B4** fail-closed defaulting (4 fail-open → fail-closed paths incl. HardConstraints exception path + tool-chain gate, AC-06/AC-07),
  - **B5** self-audit loop (`tools/loop_self_audit.py` dogfooding baseline, AC-04),
  - **B6** toolchain integrity gate (mypy/ruff missing = BLOCKED, AC-07),
  - **B7** end-to-end vertical slice (S1→S6 scripted, AC-08),
  - plus **B8** (not renumbered): regression suite protection-style tests (AC-09) and full-suite green (AC-10).
  Where a T-0084+ item is substantially or partially delivered by B3–B7, the roadmap says so and lists the *remaining* work.

---

## 2. Consolidated roadmap table

### 2.1 Priority-matrix items (gap §5, T-0084 → T-0097)

| Task ID | Title | Owner role | Phase | Effort | Dependencies | Gap closed | T-0083 status |
|---|---|---|---|---|---|---|---|
| T-0084 | Guard-health subsystem + fail-open elimination | security-engineer + quality-engineer | S4 | M | — (B3/B4 already shipped) | §3.1, §3.2, §3.4, §3.5 | **MOSTLY DONE by B3/B4/B6** — remaining: (1) fail-open inventory completion (git-exemption paths, orchestration early-pass, `fail_on_state_error: open` removal), (2) startup SessionStart battery hook, (3) guard-decision ledger writer (`guard_decisions.jsonl`, B2 §2.3) |
| T-0085 | Enforcement completeness: HardConstraints kernel in write path | system-architect + developer | S4 | M | T-0084 | §2.13 | **PARTIAL by B4** — HardConstraints exception path now fail-closed; remaining: supply phase/task context (C5/C6/C8/C9/C10/C11 currently dead letters), `root`/`task_id` keys in hook context |
| T-0086 | SLO subsystem (slo.yaml, budget ledger, release freeze) | system-architect + delivery-manager | S2 | M | T-0088, T-0097 | §2.1 | NOT covered — B2 §1 is the blueprint |
| T-0087 | Learning loop (incident/retro/failure-class, second-failure doctrine) | project-manager + delivery-manager | S2 | M | T-0088, T-0084 | §2.3 | NOT covered (B5 self-audit is a *tool*, not a learning loop) — B2 §3 is the blueprint |
| T-0088 | Loop-DORA metrics subsystem (`governance_metrics.py`, report, cadence) | delivery-manager + release-engineer | S2 | S–M | T-0084 (guard rates) | §2.2 | **PARTIAL by B3** — guard block/pass/error data now exists; remaining: `guard_decisions.jsonl`, `phase_transitions.jsonl`, aggregation module, dashboard panel — B2 §2 is the blueprint |
| T-0089 | DoD contract: per-phase Definition of Done + gate conditions in register | product-manager + quality-engineer | S1 | S | T-0097 (decision vocabulary) | §2.8 | NOT covered — first instantiation of `GateCondition` in the register for non-agent gates |
| T-0090 | Evidence verification (IV&V layer, Verifier, NOGO-passes fix) | independent-reviewer + security-engineer | S5 | M | T-0085 (context supply) | §2.12, §3.2 (NOGO), §6.5 | NOT covered (B4 fixed the NOGO *bug*; the Verifier layer itself remains) |
| T-0091 | Delta-based quality gates (diff_fingerprint load-bearing, per-edit baseline) | quality-engineer + developer | S4 | M | T-0085 | §2.6, §2.5 (partial) | NOT covered |
| T-0092 | Agent QA foundation: eval harness + golden suites + observability/trace contract | system-architect + quality-engineer | S2/S4 | L | T-0085 | §4.1, §4.2, §6.6 | NOT covered — B1 §1, §2 are the blueprints |
| T-0093 | Ownership model (OWNERS-equivalent, RACI single-A, per-directory approval) | module-architect + system-architect | S2 | S | T-0089 | §2.7 | NOT covered |
| T-0094 | Runtime safety net (INCIDENT/ROLLBACK states, pre-authorized rollback) | release-engineer + system-architect | S4 | M | T-0086 (freeze), T-0087 (incidents) | §2.9 | NOT covered |
| T-0095 | Governance-of-governance: CAB + dirty-tree guard + derived runtime state | governance-controller + independent-reviewer | S1 | S–M | — | §2.10, §3.6, §3.7 | **PARTIAL by B5** (self-audit loop scripted); remaining: governance-diff review class, decision-recording exemption narrowing, dirty-tree gate rule, runtime-state reconstruction |
| T-0096 | Single-source consolidation (deprecated duplicates → one implementation per check) | developer + quality-engineer | S4 | M | — | §3.3 | **PARTIAL by T-0082** (5 duplicates marked deprecated); remaining: re-point enforcement at canonical loop_core APIs, delete or thin the deprecated scripts, integration test asserting evidence provenance |
| T-0097 | Gate decision vocabulary + escalation ladder (CONDITIONAL-GO/HOLD/KILL/RECYCLE, blocked_reason payload) | delivery-manager + project-manager | S1/S6 | S | — | §2.14 | NOT covered — required by T-0086 (freeze reasons) and T-0090 (NOGO semantics); B2 §1.5 extends `GateStatus.BLOCKED` with `reason` |

### 2.2 B1 subsystems (new tasks proposed by this design, T-0098 → T-0103)

| Task ID | Title | Owner role | Phase | Effort | Dependencies | Gap closed | B1 design section |
|---|---|---|---|---|---|---|---|
| T-0098 | Agent guardrails: guardrails.yaml + input/output/tool-result rails + prompt-injection defense (OWASP LLM01) + structured-output enforcement | security-engineer + quality-engineer | S4 | M | T-0092 (harness), T-0084 (battery fixtures) | §4.3 | B1 §3 |
| T-0099 | Agent tool-contract testing: tools.yaml, mock-tool sandbox, argument/sequence evals, failure injection | module-architect + test-engineer | S4 | M | T-0092, T-0091 | §4.4 | B1 §4 |
| T-0100 | Agent determinism block: determinism.yaml budgets, loop detection, resumable harnesses | system-architect + developer | S4 | S–M | T-0092 (trace contract) | §4.5 | B1 §5 |
| T-0101 | Agent security hardening: credential vault separation, least-privilege tool allowlist (MCP capability model), red-team suite, approval-fatigue classes | security-engineer + release-engineer | S4 | L | T-0098, T-0093, T-0094 | §4.6, §3.8 | B1 §6 |
| T-0102 | Agent CI/CD: eval-in-CI (--repeat variance), cost/latency gates, staging sandboxes, canary model+prompt deployments | release-engineer + quality-engineer | S5 | M | T-0100, T-0089, T-0086 | §4.7 | B1 §7 |
| T-0103 | Agent production governance: agent-registry.yaml, runtime policy engine, incident consumption, continuous evals (replay/shadow/drift) | release-engineer + security-engineer | S6/S11 | L | T-0102, T-0087, T-0088, T-0090, T-0095 | §4.8 | B1 §8 |

### 2.3 Backlog items (lower priority, keep on backlog — gap §5 flagged list)

| Proposed ID | Title | Owner role | Gap |
|---|---|---|---|
| T-0104 | Bug caps / defect tracking (Microsoft #engineers×5, severity triage, debt register) | project-manager + quality-engineer | §2.5 (partially fed by T-0091 delta gates) |
| T-0105 | Tech-writer role + runbooks/docs-as-code enforcement | (new) tech-writer | §1 #12 |
| T-0106 | SRE role formalization (folded into T-0086/T-0094 until a deployment channel exists) | system-architect | §1 #10 |
| T-0107 | Threat-modeling artifact gate (STRIDE) + DAST + SCA-in-chain + secret scanning beyond .py | security-engineer | §1 #11 |
| T-0108 | Test strategy enforcement (pyramid 70/20/10, sizes/hermeticity, flakiness quarantine, RTM) | quality-engineer + test-engineer | §1 #4/#5 |

---

## 3. Sequencing: four waves

| Wave | Tasks | Theme | Exit condition |
|---|---|---|---|
| **W1 — Enforcement completeness** | T-0084, T-0085, T-0096, T-0097 | the kernel must actually run; decisions must be expressible | C5/C6/C8–C11 execute in the hook; CONDITIONAL-GO/HOLD/KILL vocabulary live; NOGO blocks |
| **W2 — Measurement** | T-0086, T-0087, T-0088, T-0089, T-0090 | SLOs, metrics, learning loop, DoD, IV&V | quarterly metrics report exists; a depleted budget freezes S6; second-failure blocks a gate; Verifier signs evidence |
| **W3 — Agent QA stack** | T-0092, T-0098, T-0099, T-0100, T-0091 | evals, traces, guardrails, tool contracts, determinism, delta gates | an AGENT-mode project promotes S5→S6 only with eval+trace+guardrail+tool-contract evidence |
| **W4 — Agent production** | T-0101, T-0102, T-0103, T-0093, T-0094, T-0095 | security, CI/CD, registry, ownership, runtime safety net, CAB | production-promoted agents resolve in the registry; canary evidence at S6; rollback authority exists; governance changes are CAB-reviewed |

Dependency spine: **T-0084/85 → T-0092 → T-0098/99/100 → T-0101/02 → T-0103** for the agent stack; **T-0088 → T-0086/87** for measurement; T-0090 and T-0097 are cross-cutting enablers for W2+; T-0094 depends on T-0086/87.

---

## 4. Cross-cutting notes

1. **B1 + B2 share the condition mechanism**: `eval_required`, `trace_required`, `guardrail_required`, `redteam_required`, `tool_contract_required`, `budget_ok`, `registry_required` (B1) and `slo_defined`, `slo_budget_available`, `slo_report_fresh`, `incident_required`, `retro_required`, `action_item_closed` (B2) are all branches added to `evaluate_condition` in `loop_core/state_machine.py`. One implementation task (inside T-0089) should land the condition-*plumbing* (register parsing, NOT_VERIFIED surfacing) so all later conditions are data-only additions.
2. **Artifacts are ReportBinding-bound** (task_id/phase/gate_id/execution_id/git_commit/diff_fingerprint/timestamp) — every new report schema in B1/B2 inherits this from verdicts.py:37, which keeps T-0090 (IV&V) uniformly applicable.
3. **Ledger additions are the common substrate**: `guard_decisions.jsonl`, `phase_transitions.jsonl`, `budget_events.jsonl` (B2 §4.2) plus per-execution span files (B1 §2.2) — all append-only and chain-hashed like `executions.jsonl`. Implementers must extend the chain-hash utility once and reuse it.
4. **Gap §7.4 holds**: Loop's CONTRACT.yaml prose is ahead of enforcement; most v4 work is wiring conditions and evidence, not inventing governance theory.
5. **Sequencing rule of thumb**: measurement (W2) before agent production (W4) — you cannot govern what you cannot measure; agent QA (W3) rides on W1's enforcement completeness.

---

*Roadmap deliverable of T-0083. Blueprints: `docs/designs/loop-v4-ai-agent-governance.md` (B1), `docs/designs/loop-v4-slo-metrics-learning.md` (B2).*
