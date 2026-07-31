# Loop v4 Design — B1: AI-Agent Project Governance (Agent Eval / Trace / Guardrail / Tool Contract / Determinism / Security / CI-CD / Production Governance)

| | |
|---|---|
| **Task** | T-0083 — Design deliverable B1 |
| **Role** | system-architect |
| **Date** | 2026-07-31 |
| **Status** | draft (design blueprint for T-0092, T-0098–T-0103) |
| **Basis** | gap-analysis §2.11, §4.1–4.8, §6.6; ai-agent-engineering-research.md §3–§10 (areas 1–8); current Loop types: `GateCondition`/`evaluate_condition` (loop_core/state_machine.py:596-654, instantiated only by `init_project`), `ReportBinding` (loop_core/verdicts.py:37-105), ledger `.ai/ledger/executions.jsonl` (chain-hashed dispatch records), gate register `.ai/gates.yaml`, `version-manifest.yaml` |
| **Scope** | Design only. No code changes in T-0083. Consumed by T-0084+ implementation tasks. |

---

## 0. Executive summary and design principles

Loop today can govern *where agent code may write and who approves* (gap §4 bottom line). It cannot gate on *what the agent does*, *how it behaved*, *what it was told not to do*, *how it used tools*, or *how bounded it is*. This design adds the missing second quality stack for **projects whose deliverables are AI agents** — eight subsystems matching research areas 1–8 (gap §4.1–4.8). Each subsystem lands as: (a) one or more new **artifacts** (versioned YAML/JSON with schema), (b) one or more new **gate condition types** executed by `evaluate_condition`, (c) **role extensions** or new roles, (d) a migration path.

### Design principles

1. **The agent run becomes a first-class governed object.** Today the ledger records launch/completion of dispatches. In v4, a run carries step-level spans, budgets, guardrail decisions, and eval results — all chain-hashed into the existing append-only ledger.
2. **Reuse the dormant condition mechanism.** `GateCondition` + `evaluate_condition` (state_machine.py:596-654) exist and support 4 types but are instantiated nowhere in the register (gap §2.8, §2.11). v4 extends the type vocabulary and makes the register the single place gates are defined. `GateStatus` grows the decision vocabulary only where required (see B2/roadmap T-0097 for CONDITIONAL-GO; this doc assumes pending/approved/rejected/blocked plus a new `blocked` reason payload).
3. **Statistical gates replace deterministic assertions for agent behavior.** Pass rates over repeated trials (pass@k / pass^k), not single-run pass/fail (research §3.4).
4. **Fail-closed, not advisory.** Every new condition returns a non-conclusive verdict (`NOT_VERIFIED`) when its artifact is absent — mirroring the T-0083 fail-closed defaulting work (B4) and the unused `UNAVAILABLE`/`NOT_VERIFIED` semantics (gap §3.2, §6.5).
5. **Progressive enforcement.** v4.1: agent-mode projects (`loop_mode: AGENT`, new mode value) opt in; v4.2: default-on for all projects that declare agent artifacts; v4.3: mandatory for governed agent projects. Each subsystem states which wave it lands in.
6. **Everything is evidence.** Eval reports, trace summaries, guardrail eval results, red-team reports, registry entries are `ReportBinding`-bound artifacts (task_id/phase/gate_id/execution_id/git_commit/diff_fingerprint/timestamp) so the existing IV&V layer (T-0090) can verify them.

### New artifact inventory (all under `.ai/`)

| Artifact | File | Owned by | New gate conditions |
|---|---|---|---|
| Eval suite (config) | `.ai/evals/agent-evals.yaml` | quality-engineer | `eval_required` |
| Eval report | `.ai/evidence/{task}/eval_report.json` | quality-engineer | `eval_required` |
| Trace export (spans) | `.ai/ledger/executions.jsonl` + `.ai/ledger/traces/{execution_id}.jsonl` | harness / developer | `trace_required` |
| Guardrail config | `.ai/guardrails/guardrails.yaml` | security-engineer | `guardrail_required` |
| Guardrail eval results | `.ai/evidence/{task}/guardrail-eval.json` | security-engineer | `guardrail_required` |
| Tool contracts | `.ai/tools/tools.yaml` | module-architect | `tool_contract_required` |
| Tool contract test results | `.ai/evidence/{task}/tool-contract-report.json` | test-engineer | `tool_contract_required` |
| Determinism/budget config | `.ai/harness/determinism.yaml` | system-architect | `budget_ok` |
| Red-team suite + report | `.ai/redteam/*.yaml`, `.ai/evidence/{task}/redteam_report.json` | security-engineer | `redteam_required` |
| Agent registry | `.ai/agent-registry.yaml` | release-engineer | `registry_required` |
| Runtime policy | `.ai/agent-policy.yaml` | security-engineer | — (consumed by policy engine) |
| Incident records | `.ai/incidents/incident-*.yaml` | project-manager | see B2 (learning loop) |

---

## 1. Agent eval gate type (`eval_required`) — research §3, gap §4.1

### 1.1 Purpose

Close gap §4.1: a governed agent project must be gateable on "does the agent achieve its task", "did it use tools correctly", "was its trajectory sane", "is it safe" — measured statistically over a curated golden set (research §3.1–3.4). This is the agent analog of the C10 contract gate, but statistical and load-bearing.

### 1.2 Gate condition instantiation (the mechanism the gap analysis says is unused)

Extend `GateCondition.type` vocabulary in `loop_core/state_machine.py` (currently `role_required | evidence_required | phase_required | manual_approval`) with: `eval_required`, `trace_required`, `guardrail_required`, `tool_contract_required`, `budget_ok`, `redteam_required`, `registry_required` (B1); `slo_budget_available`, `retro_required`, `incident_required`, `action_item_closed` (B2 — see docs/designs/loop-v4-slo-metrics-learning.md). `evaluate_condition` gains one branch per type; each branch is **fail-closed**: artifact missing → returns False and emits a `NOT_VERIFIED` note (per principle 4), which the phase-gate caller must surface as "cannot verify" rather than pass (adopts the unused Verdict nuance from gap §3.2/§6.5).

Register usage — a gate in `.ai/gates.yaml` for an agent-project S5 gate:

```yaml
- id: G-T-0092-S5-AGENT-EVAL
  task_id: T-0092
  gate_type: phase-eval
  phase: S5-quality
  status: pending
  conditions:
    - condition_id: agent-eval-golden-v3
      type: eval_required
      description: "Agent eval suite must pass on the task's diff (golden set v3)"
      params:
        suite: .ai/evals/agent-evals.yaml
        min_dataset_version: "2026-07"
        min_trials_per_task: 3
        dimensions:
          task_completion: { statistic: "pass@1", threshold: 0.80 }
          tool_correctness: { statistic: "pass^3", threshold: 0.85 }
          trajectory:        { statistic: "pass@1", threshold: 0.70 }
          safety:            { statistic: "pass^3", threshold: 1.00 }
        judge_calibration_required: true
        min_judge_agreement: 0.90
    - condition_id: trace-contract
      type: trace_required
      description: "All dispatches of this task exported per-step spans"
      params: { span_kinds: ["gen_ai.invoke_agent", "gen_ai.tool"], require_cost: true }
```

`evaluate_condition("eval_required", ...)` behavior: locate `eval_report.json` in the task evidence dir (ReportBinding-validated); check `dataset.version >= min_dataset_version`; check `trials.per_task >= min_trials_per_task`; for each dimension, compute pass rate under the declared statistic and compare against threshold (all dimensions must pass); check `judge_calibration.agreement >= min_judge_agreement`; return True only if every sub-check passes. Any missing field → False + `NOT_VERIFIED`.

### 1.3 Eval suite artifact — `.ai/evals/agent-evals.yaml`

```yaml
schema_version: 1
suite_id: loop-agent-golden
version: "2026-07"
owner_role: quality-engineer
dataset:
  task_count: 32
  source: [ "real-failures-2026H1", "swe-bench-verified-subset", "domain-contributions" ]
  balance: { positive: 18, negative: 14 }   # one-sided evals are a known pitfall (research §3.4)
  isolation: per-trial-clean-env           # no shared git history between trials (research §3.4/§7.6)
graders:
  - dimension: task_completion
    type: code            # end-state verification / fail-to-pass tests
    ref: .ai/evals/graders/task_completion.py
  - dimension: tool_correctness
    type: code            # tool-call verification: tool used, args, order (research §3.1)
    ref: .ai/evals/graders/tool_correctness.py
  - dimension: trajectory
    type: model           # LLM judge with rubric; isolated per dimension (research §3.4)
    ref: .ai/evals/graders/trajectory_rubric.yaml
    escape_hatch: true    # judge may return Unknown instead of hallucinating a grade
  - dimension: safety
    type: model-or-classifier
    ref: .ai/evals/graders/safety.yaml
harness:
  sandbox: isolated-container
  mock_tools: true
  disallowed_tools: [ "Bash" ]
  no_cache: true          # --no-cache: stale provider responses must not hide regressions
  repeat_default: 3
tiers:                    # research §9.1 capability tiers
  tier0_plain_llm: false
  tier1_agent_sdk: true
```

Eval suites are **code-reviewed artifacts** (research §9.4: contributed via PR, owned like unit tests). A suite with `task_count < 20` triggers a `FAIL` (warning-level) note recommending expansion (research §3.4: "20–50 simple tasks drawn from real failures is a great start").

### 1.4 Eval report artifact — `.ai/evidence/{task}/eval_report.json`

```json
{
  "type": "eval_report",
  "schema_version": 1,
  "task_id": "T-0092",
  "phase": "S5-quality",
  "gate_id": "G-T-0092-S5-AGENT-EVAL",
  "execution_id": "exec-DP-0001",
  "git_commit": "d01b53e",
  "diff_fingerprint": "a3f9…",
  "timestamp": "2026-08-01T10:00:00+08:00",
  "dataset": { "suite_id": "loop-agent-golden", "version": "2026-07", "task_count": 32 },
  "harness": { "name": "loop-eval-harness", "version": "0.4.0", "sandbox": "isolated-container" },
  "trials": { "repeat": 3, "per_task": 3, "total_runs": 96, "failed_runs": 9 },
  "pass_rates": {
    "task_completion":  { "pass@1": 0.83, "pass@3": 0.92, "pass^3": 0.71, "threshold": 0.80, "met": true },
    "tool_correctness": { "pass@1": 0.90, "pass@3": 0.97, "pass^3": 0.84, "threshold": 0.85, "met": true },
    "trajectory":       { "pass@1": 0.72, "pass@3": 0.81, "pass^3": 0.58, "threshold": 0.70, "met": true },
    "safety":           { "pass@1": 1.00, "pass@3": 1.00, "pass^3": 1.00, "threshold": 1.00, "met": true }
  },
  "judge_calibration": {
    "method": "human-spot-check",
    "sample_size": 12,
    "agreement": 0.92,
    "judge_version": "judge-llm-v2",
    "escape_hatch_used": 3,
    "calibrated_at": "2026-07-28",
    "calibrated_by_role": "independent-reviewer"
  },
  "failed_cases": [
    { "task_id": "eval-014", "dimension": "trajectory", "note": "tool sequence off by one (update before lookup)" }
  ],
  "verdict": "PASS"
}
```

All fields are mandatory when `verdict` is claimed; a report missing any mandatory field is treated as `NOT_VERIFIED` by the gate (fail-closed; principle 4).

### 1.5 pass@k / pass^k semantics (research §3.4)

- **pass@k** = P(≥1 success in k trials) — use for dimensions where one success matters (tool outcomes, task completion in capability evals). Estimate: run k trials per task, count tasks with ≥1 success, divide by task count. At k=1, pass@1 is simply the empirical pass rate.
- **pass^k** = P(all k trials succeed) — use for dimensions where consistency is essential (safety, customer-facing behavior). At k=1 identical to pass@1; at k=10 the two diverge sharply (pass@k → ~100%, pass^k → ~0%), so the choice of statistic is a governance decision recorded in the gate params, not an implementation detail.
- Gate params must name the statistic explicitly per dimension (see §1.2). The default recommendation: `pass@1` for capability dimensions (trajectory, task completion), `pass^3` for consistency dimensions (safety, tool correctness), thresholds chosen so **capability evals keep headroom** (research §3.4: saturation at 100% means no improvement signal) and **regression evals sit near 100%**.
- Variance handling: repeat runs are `--repeat 3`-style (research §7.1); single-run pass/fail is never a valid eval gate for a non-deterministic dimension.

### 1.6 Roles, migration, effort

| Item | Value |
|---|---|
| New roles | none (evaluator discipline is a **quality-engineer extension**: eval suite owner; **test-engineer extension**: harness operator; **independent-reviewer extension**: judge-calibration oversight, spot-checks) |
| Migration | Wave 1: `eval_required` type + schema validation (non-blocking); Wave 2: enforced for `loop_mode: AGENT` projects; Wave 3: regression-eval conditions required at S5/S6 for agent deliverables |
| Effort | M (mostly wiring: condition branch + report validator + harness adapter) |
| Depends on | T-0092 (agent QA foundation — eval harness + observability), T-0089 (DoD contract so eval gates attach to a defined Done bar), T-0090 (IV&V re-verifies eval reports), T-0097 (decision vocabulary: eval `FAIL` should recycle, not just reject) |

---

## 2. Trace contract — research §4, gap §4.2, §6.6

### 2.1 Purpose

Gap §4.2 is PARTIAL today: `.ai/ledger/executions.jsonl` is a chain-hashed **dispatch** audit trail (launch/completion/exit code) with **no step-level visibility** — no LLM calls, tool calls, tokens, cost, latency, decisions. Research §4.1: traces are simultaneously the debugger, the audit trail, the eval substrate, and the cost/latency monitor; "full production tracing was added to diagnose why agents failed." The contract: **no trace export = no phase promotion** (research §4 cross-cutting point 2, gap §6.6).

### 2.2 Schema: executions.jsonl extension + per-execution span file

Design decision: keep `executions.jsonl` records append-only and compact; add a **`trace_summary` block** to each record plus a **`trace_ref`** to a per-execution span file that lives beside the ledger and is itself chain-hashed into the same hash chain (the ledger's `chain_hash` covers the record; the span file's content hash is included in `trace_summary` so tampering is detectable without re-reading the whole ledger).

```json
{
  "execution_id": "exec-DP-0001",
  "task_id": "T-0092",
  "role_id": "developer",
  "session_id": "zcode-sess-0000",
  "status": "COMPLETED",
  "trace_summary": {
    "otel_compatible": true,
    "span_count": 87,
    "span_kinds": { "gen_ai.invoke_agent": 5, "gen_ai.invoke_llm": 40, "gen_ai.tool": 35, "guardrail": 7 },
    "usage": { "input_tokens": 61200, "output_tokens": 18200, "cache_read_tokens": 9400 },
    "cost_usd": 0.142,
    "latency_total_s": 312.4,
    "first_span_at": "2026-08-01T09:58:02+08:00",
    "last_span_at": "2026-08-01T10:03:14+08:00",
    "span_file": ".ai/ledger/traces/exec-DP-0001.jsonl",
    "span_file_sha256": "9f2c…"
  }
}
```

Per-step span record (`.ai/ledger/traces/{execution_id}.jsonl`, one JSON per line, OTel GenAI semconv attribute names):

```json
{
  "span_id": "sp-0001",
  "trace_id": "tr-0001",
  "parent_span_id": null,
  "kind": "gen_ai.invoke_agent",
  "name": "developer.main_loop",
  "started_at": "2026-08-01T09:58:02+08:00",
  "ended_at": "2026-08-01T09:58:11+08:00",
  "attributes": {
    "gen_ai.agent.id": "developer",
    "gen_ai.agent.version": "1.2.0",
    "gen_ai.operation.name": "plan",
    "gen_ai.request.model": "deepseek-v4",
    "gen_ai.request.temperature": 0,
    "gen_ai.request.seed": 42,
    "gen_ai.request.max_tokens": 4096,
    "gen_ai.system_instructions.sha256": "d41d…",
    "gen_ai.usage.input_tokens": 1520,
    "gen_ai.usage.output_tokens": 310,
    "gen_ai.usage.cache_read_tokens": 0,
    "gen_ai.response.finish_reasons": ["stop"],
    "gen_ai.cost.usd": 0.0012
  },
  "events": [
    {
      "name": "tool_call",
      "at": "2026-08-01T09:58:05+08:00",
      "attributes": {
        "gen_ai.tool.name": "Write",
        "gen_ai.tool.args.sha256": "5c1e…",
        "gen_ai.tool.result_truncated": false,
        "gen_ai.tool.result.sha256": "77aa…",
        "tool.duration_ms": 230,
        "tool.error": null
      }
    },
    { "name": "guardrail_decision", "at": "2026-08-01T09:58:05+08:00",
      "attributes": { "guardrail.id": "rg-loop-agent-001", "decision": "allow", "rail": "input-pii-mask" } }
  ]
}
```

Required span kinds for a compliant trace export: `gen_ai.invoke_agent` (agent/handoff spans), LLM spans with usage+cost, `gen_ai.tool` spans with args hash and result hash (truncation flag per research §6.1 Claude Code 25k-token cap practice), and guardrail decision events (research §4.3 NeMo rail tracing). OTel semconv compatibility is declared (`otel_compatible: true`) but the neutral attribute names above are the canonical internal representation, so the export works without an OTel backend.

### 2.3 Gate integration — `trace_required` condition

- Enforced at **every phase promotion for agent-mode projects** (S4→S5, S5→S6, S7–S11), per gap §6.6 "no trace export = no phase promotion".
- Evaluation: for the task, every ledger execution record with `status: COMPLETED` must carry a `trace_summary` whose `span_file` exists, hash-verifies, and covers all four span kinds; `require_cost: true` requires `cost_usd` present. Absence → False + `NOT_VERIFIED` surfaced to the user as "cannot verify" (fail-closed, principle 4).
- Session-level audit: the session log is the append-only audit record (research §4.4); trace files are **append-only and never rewritten**; superseding a trace file requires a new span file with a new hash (existing evidence rule: supersede, never delete).

### 2.4 Roles, migration, effort

| Item | Value |
|---|---|
| Roles | **quality-engineer extension**: trace-contract validator (checks completeness/hash); **release-engineer extension**: export configuration for production agent runs; **developer extension**: agent harness must emit spans (harness adapter, not the model) |
| Migration | Wave 1: span emission in the loop harness + `trace_summary` schema (opt-in, advisory); Wave 2: `trace_required` enforced for AGENT-mode; Wave 3: enforcement default-on, traces required for any production-governed agent (registry-promoted, §8) |
| Effort | M (ledger extension + one span-file writer + validator; no external OTel dependency) |
| Depends on | T-0092 (harness), T-0090 (IV&V re-verifies trace hashes), T-0084 (guard-health battery gains a trace-integrity fixture) |

---

## 3. Guardrail artifacts — research §5, gap §4.3

### 3.1 Purpose

Gap §4.3 is PARTIAL: today's guards (`content_guard`, `bash_content_guard`, `gate_guard`) are coarse regex gates on **file writes and bash commands** — they protect the repo, not the agent. v4 adds **input/output/tool-result/policy rails** as versioned, tested configuration artifacts (research §5.1: guardrails are "configuration artifacts that can be versioned, tested, and audited"), with OWASP LLM01 (prompt injection) as the defining threat (research §5.2) and structured-output enforcement (research §7.2).

### 3.2 Artifact — `.ai/guardrails/guardrails.yaml`

```yaml
schema_version: 1
guardrail_id: rg-loop-agent-001
version: "1.3.0"
applies_to: [ "all-agent-runs" ]
input_rails:
  - id: inj-deflect
    type: prompt-injection-defense        # OWASP LLM01
    mode: reject | fix | escalate
    action: escalate-to-human
    detectors: [ "suspicious-instruction-classifier", "indirect-injection-patterns" ]
  - id: input-pii-mask
    type: pii-detection
    entities: [ PERSON, EMAIL_ADDRESS, CREDENTIAL ]
    action: mask
output_rails:
  - id: structured-output-enforce
    type: json-schema
    schema_ref: .ai/evals/schemas/agent-output.schema.json
    action: retry-max-2-then-reject       # research §7.2: schema-driven retries, but graders must accept valid variants
  - id: unsafe-content-block
    type: moderation
    categories: [ violence, sexual, self-harm, hate ]
    action: reject
tool_result_rails:
  - id: tool-result-inspect
    type: tool-output-classifier          # research §5.2: tool output is an attack surface BEFORE it enters context
    action: block-before-context
policy_rails:
  - id: sop-enforce
    type: flow-policy                     # NeMo Colang-style SOP encoding (research §5.4)
    flow_ref: .ai/guardrails/flows.sop.colang
eval_results:
  - eval: vulnerability-scan              # research §5.1 NeMo evaluate / Guardrails Index
    tool: nemoguardrails-evaluate
    version: "0.9.0"
    passed: true
    report_ref: .ai/evidence/T-0098/guardrail-vuln-scan.json
```

### 3.3 Prompt-injection defense architecture (OWASP LLM01)

Layered, per research §5.2 — no single layer is sufficient ("even a successful prompt injection is fully isolated" is the goal):

| Layer | Loop mechanism (v4) | Status |
|---|---|---|
| Environment containment | existing write-scope (RuntimeController) extended by sandbox: filesystem isolated to task `allowed_paths`, network via egress proxy with domain policy | extends B3 (MCP capability) + T-0101 |
| Egress control | `agent-policy.yaml` `egress.domains` allowlist enforced by proxy; allowlist is a **capability grant**, not a destination filter (Anthropic egress-allowlist bypass lesson) | new (T-0098/T-0101) |
| Tool-result inspection | `tool_result_rails.tool-result-inspect`: classifier scans tool return values before model context | new |
| Model-layer classifier | optional small classifier model for pre-execution permission gating (Claude Code auto-mode pattern, ~83% catch) | optional |
| Human escalation | `escalate-to-human` action routes to the user gate, never to a silent allow | new |

### 3.4 Structured-output enforcement

For agent deliverables that emit machine-readable artifacts: the harness requests structured outputs (JSON schema); `output_rails.structured-output-enforce` validates conformance, retries ≤2, then rejects; the failure is a trace event. Enforcement boundary: this rail is a **harness-level contract** for agent projects, and the output schema itself is a versioned artifact (`.ai/evals/schemas/`), reviewed like code.

### 3.5 Gate integration — `guardrail_required` + `redteam_required`

- `guardrail_required` (S5/S6 for AGENT-mode): `guardrails.yaml` exists, its `eval_results` contain a passed vulnerability scan, and every rail referenced by policy is present and its decision events appear in traces (§2.3).
- `redteam_required` (S5, security sign-off): `.ai/evidence/{task}/redteam_report.json` — corpus (`.ai/redteam/`): jailbreak strategies, indirect prompt injection, secret exfiltration, sandbox-escape, network egress (research §8.4); report carries `Verdict` (PASS/BLOCKED), the corpus version, and a `binding`. Red-team results are regression-sensitive: model upgrades break agent safety, so the suite re-runs on model/prompt changes (§7.4 canary gate).
- Guardrail health: the guard-health battery (T-0083/B3, `loop_core/guard_health.py`) is extended with fixtures that prove each rail **blocks** a fixture violation (negative controls) — the guard-death lesson of §3.1 applies to rails too.

### 3.6 Roles, migration, effort

| Item | Value |
|---|---|
| Roles | **security-engineer extension**: guardrail owner, red-team operator; **quality-engineer extension**: rail eval results (vulnerability scans) reviewed; **independent-reviewer**: guardrail config review before production promotion |
| Migration | Wave 1: `guardrails.yaml` + eval-results schema (advisory); Wave 2: `guardrail_required` for AGENT-mode at S6; Wave 3: red-team required for any externally-facing agent |
| Effort | M (config schema + harness rail hook + eval runner; the classifier itself is pluggable/optional) |
| Depends on | T-0084 (guard-health battery extension), T-0092 (harness), T-0101 (agent security hardening — egress/sandbox), T-0090 (IV&V) |

---

## 4. Tool contract testing — research §6, gap §4.4

### 4.1 Purpose

Gap §4.4 is PARTIAL: schema-level contract checking exists (C10 `contract_verifier`, module-architect `validate_contract.py`) but is SOFT and self-disabling when contracts are absent, and nothing agent-specific exists (no argument evals, sequence assertions, mock-tool sandboxes, failure injection). Research §6: tools are "contracts between deterministic systems and non-deterministic agents"; the schema is the unit-testable surface.

### 4.2 Artifact — `.ai/tools/tools.yaml`

```yaml
schema_version: 1
tools:
  - name: update_seat
    namespace: booking
    description: "Update an existing reservation seat (single consolidated op — research §6.1)"
    parameters_schema: { "$ref": "schemas/update_seat.schema.json" }
    strict: true                     # strict schemas, unambiguous parameter names
    destructive: false
    side_effects: [ external-api, db-write ]
    max_response_tokens: 25000
    response_format: { kind: enum, values: [ CONFIRMED, FAILED ] }
    tests:
      schema: true                   # JSON Schema validation of the tool's own schema
      mock_sandbox: true             # deterministic fixture-based stub (research §6.3)
      failure_injection: [ timeout, malformed-response, permission-denied, rate-limit, partial-result ]
      argument_evals:
        - fixture: "reservation ABC123 → new seat 14C"
          assert: { tool: update_seat, args: { confirmation_number: "ABC123", new_seat: "14C" } }
      sequence_evals:
        - [ lookup_reservation, update_seat, faq_lookup ]   # promptfoo trajectory:tool-sequence
      output_utilization: true       # agent must use the tool result correctly (research §6.2)
```

### 4.3 Mock-tool sandbox and failure injection

- **Mock-tool sandbox**: staging runs bind every tool to fixture-based stubs (deterministic outputs, seeded data, fake credentials — research §6.3: dummy API keys, ephemeral containers, no network). The eval harness (T-0092) runs in this sandbox by default; `mock_tools: false` only with explicit justification.
- **Failure-injection suite**: each tool is exercised under injected failures (timeout/error/malformed response/rate-limit); the agent's handling is scored: retry policy sensible, no error compounding (research §6.4; MAST "task verification" failures). Assertion pattern: `trace-error-spans max_count: 0` (promptfoo) — internal tool errors inside the agent run are recorded as trace events and counted.
- **Sequence/argument evals**: `trajectory:tool-args-match`-style assertions on traces (§2.3) — the same span data powers both compliance and tool evals, which is the point of the trace contract.

### 4.4 Gate integration — `tool_contract_required`

Evaluation: `tools.yaml` exists; every tool declared has schema tests passing; the tool-contract report (`.ai/evidence/{task}/tool-contract-report.json`) records: schema validation results, argument-eval pass rates (statistical, pass@k per §1.5), sequence-eval results, failure-injection outcomes, and a `ReportBinding`. C10 semantics change for AGENT-mode: contract tests become **blocking** (fail-closed; the "skipped when no contracts exist" self-disabling behavior of hard_constraints.py:1012-1014 is replaced by `NOT_VERIFIED` when an agent project has no tool contracts).

### 4.5 Roles, migration, effort

| Item | Value |
|---|---|
| Roles | **module-architect**: tool-contract owner (schema + eval fixtures); **test-engineer**: mock-sandbox operator, failure-injection suite; **quality-engineer**: statistical thresholds review |
| Migration | Wave 1: `tools.yaml` schema + validator (advisory); Wave 2: blocking for AGENT-mode; Wave 3: default-on for any project whose codebase declares tools |
| Effort | M (schema validator + sandbox runner + report aggregator; fixtures per project) |
| Depends on | T-0092 (harness/sandbox), T-0091 (delta gates — tool evals should be diff-scoped), T-0085 (C10 enforcement completeness in the hook path) |

---

## 5. Determinism block — research §7, gap §4.5

### 5.1 Purpose

Gap §4.5 is MISSING: `DispatchLease` is a dedup lock, not determinism engineering. v4 adds budgets (steps/tokens/cost), loop detection, and resumable harnesses as **gateable, bounded behavior** for agent runs.

### 5.2 Artifact — `.ai/harness/determinism.yaml`

```yaml
schema_version: 1
seed_policy:
  default_seed: 42
  temperature: 0
  enforced: true                 # traces record gen_ai.request.seed/temperature; mismatch = FAIL note
budgets:
  max_steps: 60                 # research §7.3: budgets cap the blast radius
  max_tokens: 200000            # context budget (Anthropic 200k truncation practice, §7.6)
  max_cost_usd: 2.5             # promptfoo-style cost threshold
  max_tool_calls: 150
  max_subagent_spawns: 8        # research §7.4: "50 subagents for simple queries" anti-pattern
  max_concurrency: 3            # bounded concurrency (research §7.6: 3–5 subagents)
loop_detection:
  enabled: true
  same_tool_call_repeat_threshold: 5      # identical tool+args repeated → loop flag (research §7.4)
  same_step_repeat_threshold: 8           # trajectory sub-sequence repetition
  action: stop-and-escalate
resumability:
  checkpoint_interval_steps: 10
  state_artifact: progress-log      # claude-progress-style log + descriptive git history (research §7.5)
  resume_protocol: session-start-ritual   # read progress log, smoke-test, pick one feature, clean exit
  recoverability: git-revert        # environment reproducibility via init.sh + git
```

### 5.3 Gate integration — `budget_ok`

- Evaluation: per execution, trace summary usage/cost within budgets (`max_tokens`, `max_cost_usd`); loop detection flags absent from traces (`loop_detected: false`); resumability artifact exists for any run exceeding a duration threshold (long-running agents must be resumable, research §7.5). Exceeding a budget → `BLOCKED` for the run and a `FAIL` for the gate with the offending budget named; the task contract's `max_files`-style per-write caps already exist and are unchanged.
- Budgets are **per-run and per-task**; eval-side budgets (Foundry 1–50 turns, promptfoo 30 s / $0.25 latency-cost gates) are recorded in the eval suite (§1.3) and enforced in CI (§7).

### 5.4 Roles, migration, effort

| Item | Value |
|---|---|
| Roles | **system-architect**: determinism policy owner; **developer**: harness checkpoints; **release-engineer**: production budgets (cost ceilings per deployment) |
| Migration | Wave 1: budgets recorded in traces (advisory); Wave 2: `budget_ok` enforced for AGENT-mode; Wave 3: cost ceilings as SLO inputs (B2) |
| Effort | S–M (trace-based enforcement; no new runtime) |
| Depends on | T-0092 (trace contract), T-0086 (SLO subsystem: cost budgets feed error budgets) |

---

## 6. Agent security — research §8, gap §4.6, §3.8

### 6.1 Purpose

Gap §4.6 is PARTIAL: write-scope authorization, actor/session isolation, human-only gate approval, and bash bypass guards are real. Missing: credential vault separation, sandboxing, least-privilege tool permissions (the MCP all-or-nothing gap §3.8), red-teaming, provenance, and approval-fatigue management (users approve ~93% of prompts; Claude Code cut prompts 84% via hard boundaries — research §5.3).

### 6.2 Credential vault separation

Design (research §8.2): credentials live in a vault **outside** any execution sandbox (`.ai/credentials/` — out of agent `allowed_paths`, excluded from task contracts, never mounted in mock sandboxes). The agent calls credential-requiring tools via a **proxy** that fetches the scoped, revocable session credential and performs the external call; "the harness is never made aware of any credentials." Security tests assert the execution environment contains no credentials (synthetic-secret-read fixtures in the red-team suite). T-0082/T-0083 explicitly scoped secrets OUT; this design provides the architectural slot — actual secret handling remains gated (high-risk flag `secret: true`).

### 6.3 Least-privilege tool permissions — MCP capability model (extends B3, closes gap §3.8)

The gap §3.8 all-or-nothing problem (MCP side-effect tools blocked in FULL mode because `is_in_task_scope(None, …)` is always False) gets an explicit per-tool permission model in the **task contract**:

```yaml
# task contract extension
tool_permissions:
  - tool: mcp__node_repl__js
    allow: true
    allowed_args: { eval_only: true, max_output_chars: 10000, max_duration_s: 60 }
    requires_approval: batch            # approval class (see §6.5)
  - tool: Bash
    allow: false
  - tool: WebFetch
    allow: true
    allowed_domains: [ "docs.python.org", "pypi.org" ]
  - tool: mcp__filesystem__write
    allow: false
```

Enforcement: a new scope check `is_tool_in_task_allowlist(tool_name, args, task_contract)` replaces the blanket fail-closed; unlisted tools stay fail-closed; arg constraints are evaluated against the call's extracted arguments; allowlist decisions are trace events (`guardrail_decision`, §2.2). This is the MCP capability model flagged in gap §3.8/§5 and part of B3's mandate ("extends B3 MCP capability").

### 6.4 Red-team suite

`.ai/redteam/` corpus + `.ai/evidence/{task}/redteam_report.json` (see §3.5): jailbreak strategies, indirect injection (web/terminal/file output), secret exfiltration, sandbox escape, egress-allowlist bypass, automation poisoning, verifier sabotage (research §8.4). Report: `verdict` (Verdict enum), corpus version, per-strategy results, `binding`. Red-team results are **regression-sensitive** — re-run on any model/prompt/tool change (§7.4).

### 6.5 Approval-fatigue management

Research §5.3: permission prompts are weak gates (93% approval within weeks). Design replaces blanket prompting with a **three-class approval model**, recorded in `.ai/agent-policy.yaml`:

| Approval class | Definition | Mechanism |
|---|---|---|
| `always-prompt` (irreversible) | deployment, rollback, DB change, secret access, payment, production data, out-of-task writes | single user prompt per action; never batched (existing user-gate semantics preserved) |
| `batch` (reversible, bounded) | same-class low-risk actions within one session under a hard boundary (e.g., writes within `allowed_paths` while gate pending-but-authorized, tool calls on allowlist) | one approval covers a bounded batch (session-scoped, capped count/duration); batch decisions are ledger events |
| `none` (policy-allowed) | read-only tools, allowlisted domains, structured-output retries | no prompt; guardrail decisions logged |

Hard boundaries replace prompts wherever a policy can decide: out-of-scope = auto-block (never ask), not auto-ask. Expected effect per the industry evidence: ~84% prompt reduction on class-2/3 actions while class-1 prompts stay 100% human. Approval decisions remain user-only; this design only changes **what prompts are raised**.

### 6.6 Roles, migration, effort

| Item | Value |
|---|---|
| Roles | **security-engineer**: credential-vault policy, allowlist review, red-team owner; **release-engineer**: proxy/egress config; **independent-reviewer**: security sign-off on permission models |
| Migration | Wave 1: `tool_permissions` schema + `is_tool_in_task_allowlist` (unblocks MCP tools); Wave 2: approval classes; Wave 3: red-team + credential assertions mandatory for AGENT-mode |
| Effort | L (proxy/vault are infrastructure; allowlist + approval classes are wiring) |
| Depends on | T-0084 (guard-health fixtures for allowlist enforcement), T-0093 (ownership model: who approves an allowlist), T-0094 (runtime safety net: incident/rollback for security events), B3 (§3.8 MCP capability is the same mechanism) |

---

## 7. Agent CI/CD — research §9, gap §4.7

### 7.1 Purpose

Gap §4.7 is PARTIAL: the phase-gate chain is a genuine CI-shaped skeleton (edit/task/phase verdicts, fingerprint binding) but has no eval-in-CI, no variance handling, no cost/latency gates, no staging sandboxes, no canary deployments. v4 defines the agent CI/CD layer on top of the phase machine.

### 7.2 Eval-in-CI with variance handling

Per research §9.1, three test layers for agent code in CI:

1. **Deterministic unit layer** — tool implementations, schema validators, prompt assembly, guardrail configs: normal pytest/Jest; no LLM.
2. **Mock-LLM layer** — agent control flow against scripted fake LLMs: verifies trajectory, budgets, error paths deterministically; runs fast in every commit.
3. **Golden eval layer** — full-model eval runs with `--repeat N`, pass-rate thresholds (never single-run pass/fail), `--no-cache` (research §3.4: stale provider responses hide regressions). This layer is the `eval_required` gate of §1 and runs at S5 + pre-merge.

Variance handling: a dimension whose pass@1 sits inside [threshold − 0.1, threshold + 0.1] is reported as `FLAKY` (not pass/fail), with `--repeat` increased; a `FLAKY` eval blocks promotion until trials are expanded or the suite is repaired (the "if a prompt fails 50% of the time, the prompt is ambiguous" rule — research §3.4).

### 7.3 Cost/latency gates

`budget_ok` (§5.3) plus dedicated CI thresholds in the eval suite: `cost.max_per_task_usd`, `latency.max_per_task_s` (promptfoo-style: $0.25 / 30 s examples); token-pattern analysis (huge prompt + small completion = agent reading files — a trajectory smell) as a `FAIL`-level note.

### 7.4 Staging sandboxes and canary model+prompt deployments

- **Staging sandbox** (research §9.2): disposable environment with fake tools, dummy credentials, read-only repo mounts, `disallowed_tools`; manifest-defined workspaces (OpenAI SandboxAgent pattern). Staging is where guardrail configs and eval harnesses are validated before production.
- **Canary/rainbow deployments** (research §9.3): new model+prompt versions deploy concurrently with old ones; traffic shifts gradually; **in-flight agents are never hard-cut-over** (stateful agents break). Canary gate: A/B evals of new vs. old version on the production dataset with statistical comparison (LangSmith/Braintrust pattern); red-team suite re-runs on the candidate version ("model upgrades break agent safety"); human review checkpoint before traffic shift > 50%. Deployment records land in the agent registry (§8.1) with canary stage + traffic %.

### 7.5 Roles, migration, effort

| Item | Value |
|---|---|
| Roles | **release-engineer**: pipeline + canary operator; **quality-engineer**: eval layers, `--repeat` policy; **test-engineer**: mock-LLM fixtures; **delivery-manager**: human review checkpoints (shiproom gates) |
| Migration | Wave 1: deterministic + mock-LLM layers in the existing quality-gate chain; Wave 2: golden evals + cost/latency gates for AGENT-mode; Wave 3: staging sandboxes + canary deployment evidence required at S6 for production agents |
| Effort | M–L (mostly harness/pipeline; canary needs registry §8.1 first) |
| Depends on | T-0092 (eval foundation), T-0089 (DoD), T-0086 (cost gates → SLO/error budgets), T-0103 (production governance: canary records) |

---

## 8. Production governance — research §10, gap §4.8

### 8.1 Purpose

Gap §4.8 is PARTIAL: `version-manifest.yaml` + `transaction_registry.yaml` + the chain-hashed ledger give the *shape*, but registry entries cover only project artifacts — no prompt/model/tool/harness/guardrail versions, no runtime policy, no incident records, no continuous evals. v4 adds the agent registry and the production-facing governance loop.

### 8.2 Agent registry — `.ai/agent-registry.yaml`

```yaml
schema_version: 1
agents:
  - agent_id: loop-dev
    version: "1.2.0"
    prompt: { ref: ".ai/prompts/developer/v1.2.0.md", sha256: "9f2c…" }
    model: { provider: deepseek, name: deepseek-v4, pinned: true }
    tools:
      - { name: Write, version: "3.11.2" }
      - { name: mcp__node_repl__js, version: "1.0.0", allowlisted: true }
    harness: { name: loop-harness, version: "0.4.0" }
    guardrails: { ref: ".ai/guardrails/guardrails.yaml", version: "1.3.0" }
    eval_suite: { ref: ".ai/evals/agent-evals.yaml", version: "2026-07" }
    deployed_at: "2026-08-01T10:00:00+08:00"
    canary: { stage: production, traffic_percent: 100, prev_version: "1.1.0" }
    promoted_by: release-engineer
    promotion_evidence: [ "G-T-0102-S6-RELEASE", ".ai/evidence/T-0102/redteam_report.json" ]
```

Registry discipline (research §10.1): every production agent run resolves to the minimal audit tuple — (prompt version, model version, tool versions, harness version, guardrail config version, eval suite version). Trace spans carry `gen_ai.agent.version` + `gen_ai.request.model` so runs are attributable to registry entries; a trace whose version tuple does not resolve in the registry fails `registry_required`.

### 8.3 Runtime policy engine

`loop_core/policy_engine.py` (v4, sketched for T-0103): evaluates runtime policy (`.ai/agent-policy.yaml`) — sandbox boundaries (filesystem/network), egress domains, approval classes (§6.5), RBAC for agent operations — against each session/run; decisions are audit-logged (guardrail-decision trace events + session log); policy changes themselves are governance changes (CAB path, T-0095). Audit: append-only session logs are the canonical record (research §10.2); trace exports are the portable form.

### 8.4 Incident records and continuous evals

- **Incident records**: bad outputs are incidents (research §10.3). The incident type is designed in B2 (`.ai/incidents/incident-*.yaml`, docs/designs/loop-v4-slo-metrics-learning.md §3) — B1 consumes it: agent incidents escalate via traces, get root-caused (model/tool/prompt/injection), **replayed**, and converted into eval-suite test cases (the online → offline loop, research §3.5/§10.3).
- **Continuous evals** (research §10.4): `continuous_evals` in `.ai/agent-policy.yaml`:
  - `replay`: production traces replayed against the current agent version (Phoenix/Braintrust pattern) — shadow-eval semantics without production risk;
  - `shadow`: new prompt/model version evaluated on live traffic with reference-free judges (safety/format/quality);
  - `drift`: pass-rate/quality monitoring over time (Datadog/LangSmith anomaly detection); drift alert → incident record → eval-suite case.
  Cadence and alert thresholds are policy config; drift alerts feed B2's metrics subsystem and the S11 Check step (PDCA, B2 §3.4).

### 8.5 Roles, migration, effort

| Item | Value |
|---|---|
| Roles | **release-engineer**: registry owner; **security-engineer**: runtime policy; **project-manager/delivery-manager**: incident triage (B2); **independent-reviewer**: promotion evidence verification |
| Migration | Wave 1: registry schema + resolution check; Wave 2: runtime policy engine + audit; Wave 3: continuous evals (replay/shadow/drift) for production agents |
| Effort | L (registry M; policy engine M; continuous evals M — total L) |
| Depends on | T-0102 (CI/CD — canary records), T-0087/T-0088 (B2: incident + metrics), T-0090 (IV&V of promotion evidence), T-0095 (policy-change CAB) |

---

## 9. Cross-cutting summary

### 9.1 New gate condition types (all added to `evaluate_condition` in loop_core/state_machine.py)

| Condition type | Artifact consumed | Fail-closed behavior | Primary phase |
|---|---|---|---|
| `eval_required` | eval_report.json | missing/underaperated → NOT_VERIFIED → block | S5, S6 |
| `trace_required` | trace_summary + span files | missing spans → NOT_VERIFIED → block | S4→S5→S6→S7-11 |
| `guardrail_required` | guardrails.yaml + eval_results | missing scan → NOT_VERIFIED | S5, S6 |
| `redteam_required` | redteam_report.json | missing → NOT_VERIFIED | S5 |
| `tool_contract_required` | tools.yaml + tool-contract-report.json | missing contracts → NOT_VERIFIED | S5 |
| `budget_ok` | determinism.yaml + trace usage | over budget → BLOCKED | S4-S11 |
| `registry_required` | agent-registry.yaml | unresolvable tuple → NOT_VERIFIED | S6, S11 |

### 9.2 Role extensions

| Role | Extension |
|---|---|
| quality-engineer | eval suite owner, trace-contract validator, eval threshold review |
| test-engineer | eval harness operator, mock-tool sandbox, failure injection |
| security-engineer | guardrail owner, red-team operator, allowlist/vault policy |
| release-engineer | trace export config, agent CI/CD, canary operator, registry owner |
| module-architect | tool-contract owner |
| product-manager | eval task contributions, SLO setting (B2) |
| independent-reviewer | judge calibration oversight, guardrail/registry review, promotion evidence IV&V |

### 9.3 Implementation sequencing (waves, with task ownership)

| Wave | Content | Tasks |
|---|---|---|
| 1 | Eval foundation: suite/report schema, harness, trace contract | T-0092 (eval + observability), T-0100 (determinism) |
| 2 | Guardrails + tool contracts + red-team as blocking conditions for AGENT-mode | T-0098, T-0099, T-0101 |
| 3 | CI/CD gates, staging, canary | T-0102 |
| 4 | Production governance: registry, policy engine, continuous evals | T-0103 |
| Cross-cutting | SLO/metrics/learning (B2), DoD, decision vocabulary, IV&V | T-0086, T-0087, T-0088, T-0089, T-0090, T-0097 |

### 9.4 Acceptance criteria (sketch for the implementing tasks)

- AC: an AGENT-mode project with a passing golden eval (≥20 tasks, all four dimensions, calibrated judges) can promote S5→S6; without it the gate reports NOT_VERIFIED and blocks.
- AC: a run without step-level spans cannot promote any phase (trace contract).
- AC: a prompt-injection fixture that would succeed without rails is blocked by the guardrail config (negative control, guard-health battery).
- AC: an MCP tool on the task allowlist with conforming args executes in FULL mode; a non-allowlisted tool is fail-closed (closes §3.8).
- AC: an agent run exceeding `max_cost_usd` produces a BLOCKED verdict naming the budget.
- AC: every production-promoted agent resolves in the registry (prompt/model/tool/harness/guardrail tuple).

---

*Design deliverable B1 of T-0083. Companion docs: `docs/designs/loop-v4-slo-metrics-learning.md` (B2), `docs/designs/loop-v4-consolidated-roadmap.md` (B3–B7 status + full roadmap).*
