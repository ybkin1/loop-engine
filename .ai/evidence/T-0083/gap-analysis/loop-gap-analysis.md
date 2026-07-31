# Loop Gap Analysis Report — Loop Governance vs. Real-World Engineering Practice

| | |
|---|---|
| **Task** | T-0083 — Research phase: gap analysis |
| **Role** | system-architect |
| **Date** | 2026-07-31 |
| **Basis** | 4 research reports (roles-research.md, quality-mechanisms-research.md, delivery-governance-research.md, ai-agent-engineering-research.md) vs. Loop's actual design and implementation (state_machine.py, hard_constraints.py, runtime_controller.py, verdicts.py, security_scanner.py, static_analyzer.py, role_dispatch.py, hooks/scripts/*, agents/*/CONTRACT.yaml, .ai/gates.yaml, .ai/QUALITY_GATES.md, T-0082 evidence chain) |
| **Method** | Direct code/file audit (this session) + T-0082 phase 0-6 evidence (baseline-report.md, convergence-report.md, quality-chain-report.md, role-dispatch-report.md, independent-reviewer-report.md, side-effect-authorization-report.md, layered-quality-gates-report.md, acceptance-report.md, commands.md) |

**Verdict up front:** Loop has built a real, working enforcement kernel (runtime takeover, write authorization, role isolation, fingerprint-bound reports, human-only gate approval) — the T-0082 acceptance evidence (12/12 AC, independent re-verification) is genuine. But against the four research baselines, Loop's governance is a **write-control and approval-tracking system**, not yet a **quality and delivery governance system**. The most important real-world mechanisms — SLOs/error budgets, DORA metrics, postmortems/retros, delta-based quality gates, test strategy enforcement, evidence independence, and the entire AI-agent QA stack — are absent from the design, and a significant fraction of the enforcement that *does* exist has been proven (by T-0082's own audit) to have been silently dead or fail-open until days ago.

---

## 1. Role Mapping Matrix (real-world role → Loop role → gaps)

Loop ships 12 agent roles: `main-thread`, `product-manager`, `project-manager`, `system-architect`, `module-architect`, `developer`, `quality-engineer`, `security-engineer`, `independent-reviewer`, `delivery-manager`, `release-engineer`, `test-engineer` (agents/README.md). The 12 real-world roles researched map as follows.

| # | Real role (research) | Loop role | Exists? | What real quality mechanism is missing / unenforced |
|---|---|---|---|---|
| 1 | Software Engineer / Developer | `developer` | YES | Exists with write-scope capability (RuntimeController, task allowed_paths). **Missing:** small-CL discipline (~200 LOC, Google eng-practices) — no size gate; tests-in-the-same-CL (Google) — not enforced; self-review (Google) — no artifact; "Beyoncé Rule" (test what you don't want to break) — no gate; build-cop consequence for breaking changes (SWE book ch23) — none; bug cap (`#engineers × 5`, Microsoft) — no defect tracking at all. C11 file-limit is a **soft** warning and counts `allowed_paths` entries, not actual change size (hard_constraints.py:1027-1101; per-write counter `file_write_count.json` is optional via `max_files`). |
| 2 | Tech Lead / Senior Engineer | `module-architect` + `independent-reviewer` + `main-thread` (split, no single owner) | PARTIAL | No OWNERS-equivalent: no per-directory approval lists (SWE book ch16; GitHub CODEOWNERS; Kubernetes Prow). Design-doc review is a prompt-level contract claim; nothing requires a design doc or ADR before implementation (gates.yaml register has **zero `conditions`** — no automated design-review gate; state_machine.GateCondition exists but is never instantiated by the register). No technical-debt management (Google LSC, Microsoft zero-debt sprint). No readability/code-review-standard artifact enforced. Escalation for review deadlock exists in `veto_escalation.py` but as library code, not an enforced path. |
| 3 | Architect (System/Application) | `system-architect` + `module-architect` | YES | ADR/decision log exists as `.ai/DECISIONS.md` but **nothing gates on ADR presence** (adr.github.io practice). No ATAM-style architecture evaluation (SEI), no API-review-board equivalent (dotnet APIReviewProcess), no NFR documents, no NFR→SLO handoff (SRE book ch4) — there are no SLOs at all (see §2.1). Module-architect has `scripts/validate_contract.py` and `loop_core/contract_verifier.py` (C10) — but C10 is SOFT and skipped whenever no contract files exist (hard_constraints.py:1012-1014), i.e., **the contract test gate disappears exactly when contracts are absent**. |
| 4 | QA Engineer / SDET | `quality-engineer` | YES | Contract (CONTRACT.yaml) claims: test strategy, ≥80% coverage threshold, veto on low coverage, "no coverage data = false PASS". **What is actually enforced** (loop_enforcement.check_quality_gate_evidence): existence of `quality_report.json` with a non-empty `overall` field + a narrow anti-fabrication check (exit_code vs claimed status, only for checks that carry `execution_evidence`) + log-only ledger cross-reference ("当前只做日志记录（非阻断）", loop_enforcement.py:421-432). **Missing:** test pyramid enforcement (Fowler; Google 70/20/10), test sizes/hermeticity (Google), flakiness management (~0.15% target, quarantine), mutation testing, coverage-on-**new-code** delta gates (SonarQube), test execution time budget (DORA: <10 min), test strategy/test plan artifacts as gate evidence. |
| 5 | Test Engineer | `test-engineer` | YES | Contract claims ISTQB-style planning, defect reproduction, coverage reports. **Missing:** requirements traceability matrix (RTM) — no requirement→test traceability exists anywhere; exit-criteria sign-off — nothing; UAT — nothing; risk-based testing — nothing; test evidence is only "JSON report exists with overall=PASS". |
| 6 | Project Manager / Scrum Master | `project-manager` | YES | Contract exists. **Missing:** sprint ceremonies are not modeled (no sprint/review/retro events in the phase machine); risk register / RAID log (PMBOK) — not enforced, no artifact gate; status reporting (Microsoft end-of-sprint mail) — HANDOFF.md serves this but is drift-prone (baseline audit found 4 HANDOFF contract mismatches); Definition of Ready — absent. |
| 7 | Product Manager | `product-manager` | YES | Contract claims verifiable acceptance criteria and value traceability. **Missing:** no gate validates acceptance criteria exist or are INVEST-compliant (INVEST, BDD Given/When/Then); no acceptance-criteria→test traceability (ATDD); no PRFAQ/outcome metrics (Working Backwards, OKRs); no error-budget input (Google PM sets the SLO — there is no SLO mechanism, §2.1). |
| 8 | Release Engineer / DevOps | `release-engineer` | YES | Contract claims CI/CD, rings, canary, rollback drills. **Actual state:** deployment/rollback/database changes are explicitly **OUT OF SCOPE** of T-0082 (task file); there is **no pipeline** — the "pipeline" is the PreToolUse hook chain; no release trains, no ring/bake-time, no canary analysis, no artifact promotion (build-once-promote), no SBOM/signing (SLSA). `check_delivery_gate_evidence` (loop_enforcement.py:495-558) accepts `release_decision.json` with **any truthy `decision` value — including `NOGO`** — or a `CERTIFIED` marker in certifications/state.yaml. |
| 9 | Delivery Manager | `delivery-manager` | YES | Exists; CONTRACT.yaml is genuinely shiproom-flavored (GO/NO-GO, rollback, monitoring readiness, vetoes). **Enforcement gap:** the S6 gate only checks that *a decision was recorded*, not what it was (see #8 bug); no stakeholder sign-off matrix; no readiness checklist artifact; no GO/CONDITIONAL-GO/HOLD/KILL vocabulary in the state machine (GateStatus is only pending/approved/rejected/blocked — state_machine.py:36-41); no record that the decision was based on evidence (no evidence dossier requirement). |
| 10 | Site Reliability Engineer (SRE) | — | **MISSING** | No role, no SLI/SLO/error budget (SRE book ch3-4), no burn-rate alerting, no incident management (IC/ops/comms), no blameless postmortem, no on-call, no capacity planning, no production-readiness review, no game days/DiRT, no toil management. This is the largest role-shaped hole. |
| 11 | Security Engineer | `security-engineer` | YES | Fail-closed policy is real (critical→BLOCKED, security_scanner.py:60-66; verified by T-0082 AC-04). **Missing:** threat modeling (OWASP STRIDE) — claimed in contract, no artifact gate; SAST is regex-on-.py only and **excludes test files entirely** (security_scanner.py:154-161 — an attacker can bury secrets in test code); no DAST; no red team/war games (Microsoft security-in-devops); no vulnerability-remediation SLA; no SCA gate in the enforcement chain (pip-audit parsing fixed in run_quality_gates.py by T-0082 GAP-4a, but the security evidence gate reads only the pre-generated audit JSON); no secret scanning of config/other languages. |
| 12 | Tech Writer / Documentation | — | **MISSING** | No role. Docs-as-code (SWE book ch10), Diátaxis, runbooks, release notes are nowhere enforced; docs are not part of any Definition of Done; delivery-manager contract mentions monitoring config but no runbook artifact; runbooks are never validated in drills (game days don't exist). |

**Cross-cutting role finding:** every role's veto/escalation powers exist only as **prose in CONTRACT.yaml**. The only verdicts the enforcement kernel actually consumes are: `quality_report.json.overall`, `security_audit.json.verdict`, `release_decision.json.decision`, phase evidence JSONs (`overall=PASS`), and role/session isolation IDs. All other veto claims ("覆盖率低于阈值 → 否决交付", "回滚未演练 → 否决发布", "验收标准不可验证 → 否决需求") are unenforceable because no code reads them.

---

## 2. Design-level Gaps (what Loop's DESIGN lacks vs. real practices)

### 2.1 No SLO / error-budget mechanism (SRE concept absent)
- **Real practice:** SLI→SLO→error budget; a depleted budget *automatically* slows or halts releases; releases are the primary consumer of the budget (SRE book ch3-4; roles-research §10).
- **Why it matters:** Loop has no concept of "how much failure can this project tolerate." Gate approval is binary and opinion-based; there is no data-driven release throttle, which is the mechanism that makes delivery governance non-political.
- **Evidence:** grep of loop_core/ and hooks/ for SLO/error-budget concepts → zero hits. No SLI definition anywhere; ProjectStatus/Phase enums contain no reliability dimension; `USER_GATE_PHASES = {S1, S6}` (state_machine.py:93-96) makes the release gate a human checkbox, not a budget check.

### 2.2 No quantitative delivery metrics (DORA), no metrics subsystem
- **Real practice:** deployment frequency, change lead time, change fail rate, failed-deployment recovery time; "measure the system, not individuals"; metrics reviewed periodically (dora.dev; quality-mechanisms §4.4).
- **Why it matters:** without metrics there is no way to know whether Loop's governance is *improving* delivery; "no metrics" is also the root of Goodhart-proofing's absence — nothing can be gamed because nothing is measured, but also nothing can be steered.
- **Evidence:** no metrics collection in any hook or core module; `.ai/status_dashboard.py` renders state, not delivery performance; the only counters are per-task file-write counts (`file_write_count.json`). The gate register records approvals but nothing aggregates gate rejection rates, phase dwell times, or rework cycles.

### 2.3 No postmortem / retrospective feedback loop in the phase machine
- **Real practice:** blameless postmortems with owned action items tracked to closure (SRE book ch15); sprint retrospectives that produce improvement plans (Scrum Guide); Amazon COE + "second failure" doctrine (delivery-governance §6.3).
- **Why it matters:** every real governance framework closes the loop — a gate that fails should feed a tracked remediation. Loop's S11→S1 loop (state_machine.py:65) is a *cycle*, not a *learning loop*: there is no incident record type, no postmortem artifact, no action-item registry, and nothing that prevents the same failure class from recurring (the "second failure is the process's fault" doctrine is unmodeled).
- **Evidence:** Phase enums S0-S11 contain no retro/postmortem phase; T-0082's own phase-5 honest-gaps list documents known recurring defect classes (dead guards, fail-open paths) with no tracking mechanism to retire them.

### 2.4 Gates are advisory in key paths — no branch-protection equivalent
- **Real practice:** required status checks, branch policies, merge queues, OWNERS approval are *structural* — they hold even when humans are busy or an AI agent is committing (quality-mechanisms §2.1, §4.1; Microsoft branch policies).
- **Why it matters:** advisory gates decay; T-0082 proved Loop's gates decayed into dead code for months (§3).
- **Evidence (specific advisory/bypass paths):**
  - `gate_guard.py:102-105`: a **pending gate belonging to another task → `allow_legacy` → writes allowed**. Pending gates only block for the current task.
  - `gate_guard.py:180-181` / `content_guard.py:141-142` / `bash_content_guard.py:162-163`: every guard can be disabled via `enabled: false` in `.zcode/skills/loop-governance/config.yaml`; `fail_on_state_error: open` flips gate_guard to fail-open (gate_guard.py:195-204).
  - `loop_enforcement.py:876-880, 987-993`: broad git exemptions — `git add/commit/diff/status/log/branch/show/tag/config` are exempt even with **no task**; with a task, all local git ops (`checkout`, `reset`, `merge`, `rebase`, `rm`, `mv`, `stash`) pass, plus any compound command containing `" git "` and `cd`.
  - `loop_enforcement.py:870-872, 963-964, 1131-1132`: `Agent`/`Skill`/`Task` tools with no extractable target get the orchestration **early-pass** (the same tools an agent could use to delegate a write).
  - `loop_enforcement.py:881-886`: the `LEGACY_SYNTHETIC_FIXTURE` marker is derived from the `PYTEST_CURRENT_TEST` environment variable — a test-context-based trust signal in the production enforcement path.

### 2.5 No bug caps / defect / tech-debt tracking
- **Real practice:** Microsoft bug cap (`#engineers × 5`) stops feature work; "zero debt" sprints; debt is a conscious loan with interest (roles-research §1, §2).
- **Why it matters:** Loop cannot decide "quality is acceptable" because it never counts defects or debt. `Verdict.FAIL` exists for warnings but nothing aggregates warning counts into a quality trend or a stop-work trigger.
- **Evidence:** no defect list, severity triage, or debt register anywhere in loop_core/hooks; C10 (contract tests) and C11 (file limit) are explicitly SOFT/WARNING by default (hard_constraints.py:975-978, 1084-1085); the S6 phase evidence requires only "all of [test, lint, build] PASS" (C5, hard_constraints.py:562-607) — no defect-count criterion, no coverage criterion, no tech-debt criterion.

### 2.6 Gates apply to absolutes, not deltas (no per-edit regression baseline)
- **Real practice:** quality gates evaluate **new code** — "coverage on new code ≥80%", "no new bugs/vulnerabilities" — so legacy debt doesn't permanently block and new code can't make things worse (SonarQube "Sonar way"; quality-mechanisms §2.1).
- **Why it matters:** Loop's S5 gate reads a whole-project `quality_report.json`. A project that fails coverage globally is blocked forever; a project that passes globally masks a new change that is worse than the code it replaced. There is no before/after comparison of a task's diff.
- **Evidence:** `ReportBinding.diff_fingerprint` field exists (verdicts.py:49) but is never used by any check; the diff-scope check (T-0082 GAP-5a) counts *which files* changed, not *whether quality changed*; `check_quality_gate_evidence` compares nothing to a baseline.

### 2.7 No OWNERS-equivalent; role-based approval is coarse
- **Real practice:** OWNERS files give per-directory approval at commit time; OWNERS + LGTM + readability is the Google gate stack (SWE book ch09/ch16).
- **Why it matters:** in Loop, *any* `quality-engineer` verdict or *any* user approval applies to the whole project scope of a task; there is no notion of who owns a directory, so nothing prevents a reviewer from "owning" code they never touched and no per-area accountability exists. The RACI single-A principle (delivery-governance §5.1) — one accountable person per deliverable — is unmodeled.
- **Evidence:** task contracts carry only `developer_agent_id`/`reviewer_agent_id` (loop_enforcement.py:165-168); no ownership data structure exists; `can_approve_gate` checks only that required roles submitted non-BLOCKED verdicts (state_machine.py:123-144).

### 2.8 Definition of Done is not formalized per phase
- **Real practice:** DoD is a formal, binding quality contract; a backlog item failing DoD cannot be released or even presented (Scrum Guide); organizational DoDs are checklist-driven (code reviewed, tests pass, coverage met, no open P1/P2, docs updated, rollback verified).
- **Why it matters:** "Done" is Loop's most important judgment, and it is currently defined by (a) 4 lines in `.ai/QUALITY_GATES.md` (3 bullet gates + "Only the user may approve stage transitions"), and (b) whatever a phase evidence JSON claims. Nothing encodes per-phase DoD checklists, so phases are exited based on minimum evidence presence, not on a defined quality bar.
- **Evidence:** `.ai/QUALITY_GATES.md` is 12 lines total; gates.yaml register entries have **zero `conditions`** (grep count = 0), although `GateCondition` + `evaluate_condition` exist and are used only by the unused `init_project` path (state_machine.py:595-654, 676-733).

### 2.9 No build-cop / rollback authority / incident response in the runtime
- **Real practice:** pre-authorized rollback (ITIL standard-change model, Google automated rollback on canary failure); incident commander; rollback-before-root-cause ("roll back first, fix second" — Knight Capital §6.5 cautionary tale).
- **Why it matters:** Loop's runtime state machine (RuntimeState: PROPOSAL→APPROVAL→DEVELOPER_EXECUTION→REVIEW→REPAIR→ACCEPTANCE→CLOSED) has no INCIDENT state, no ROLLBACK state, no pre-authorized rollback path, and no authority that can undo a merge. T-0082 explicitly scoped deployment/rollback OUT. The system that *governs* software delivery cannot itself perform or authorize a rollback.
- **Evidence:** runtime_controller.py:21-34 (RuntimeState enum — no incident/rollback states); `dispatch_lease.py` grants execution leases but nothing revokes or rolls back; acceptance report AC-12 confirms S6 "只提交人工 GO/NO-GO" — there is no post-GO safety net.

### 2.10 No change advisory board (CAB) for governance changes themselves
- **Real practice:** ITIL change enablement: changes to production/process go through risk assessment + authorization; governance of governance (CMMI ML3 "defined" requires org-wide standards; ISO 12207 audits).
- **Why it matters:** Loop's governance files (`state.yaml`, `gates.yaml`, `task_graph.yaml`, HANDOFF) are writable only by `controller` (GOVERNANCE_CONTROLLER_ONLY, runtime_controller.py:253-254; loop_enforcement.py:898-904) — but the *controller is the AI main thread*, i.e., the governed entity's orchestrator approves its own rule changes. There is no independent review of governance mutations, no rollback of a bad governance change, and no versioned audit of who changed the rules (T-0082 itself demonstrates the pattern: the governance takeover rewrote state/gates/HANDOFF under its own gate).
- **Evidence:** `.ai/gates.yaml` is the decision record, but edits to it are exempt from every guard (decision-recording exemption, gate_guard.py:183-189); `auto_sync_to_plugin_cache` propagates local hook changes to the plugin cache without any review step (loop_enforcement.py:799).

### 2.11 Missing AI-agent-specific design (evals, guardrail runtime, tool contracts, red-teaming, prompt versioning, traces)
- See §4 for the full 8-area mapping. Design-level summary: the entire second quality stack that ai-agent-engineering-research.md documents — statistical evals, observability traces, guardrail configs as artifacts, tool contracts, determinism engineering, agent security, agent CI/CD, production registries — has no corresponding design element in Loop. The role contracts model *human* roles, and the enforcement kernel models *file writes*; nothing models *agent runs*, *tool calls*, or *model/prompt versions*.
- **Evidence:** no eval, trace, or prompt-versioning type in any schema (`version-manifest.yaml`, `transaction_registry.yaml`, `dispatch-runtime-contract.schema.json` are the registry artifacts; none reference model/prompt/tool versions).

### 2.12 No evidence independence (IV&V) — "PASS" is self-asserted
- **Real practice:** evidence beats assertion: machine-produced tool output with hashes/provenance (SLSA), independent verification (IEEE 1012 IV&V), sampling and surprise checks (delivery-governance §4.4); "the weakest link in every governance system is *asserted* evidence".
- **Why it matters:** every Loop gate ultimately trusts a JSON file whose `overall: "PASS"` was written by the same agent that did the work. The only independence mechanism is the independent-reviewer role, and its verdict is consumed by humans, not by the enforcement kernel (the kernel reads evidence files, not reviewer verdicts, at S7-S11; C6 runs only in S4 and only when `current_phase` is supplied — which the enforcement hook never does, §2.13).
- **Evidence:** S7-S11 phase gates accept any candidate JSON with `overall=PASS` from the task's own evidence dir (loop_enforcement.py:604-689); S8 additionally accepts a self-declared `baseline.json` with `has_regressions: false` (phase-5 honest gap #2); the security fallback is a substring search for "BLOCKED" in a markdown report (loop_enforcement.py:731-733, documented false-positive risk); `quality_report.json` integrity depends on the report's own `content_hash` (self-hash, not signed).

### 2.13 The hard-constraint "control kernel" is largely dormant in the write path
- **Evidence:** loop_enforcement.py:1059-1071 constructs the HardConstraints context with `current_phase=None`, `target_phase=None`, `phase_gates={}`, `quality_results={}`, `review_status={}`, `evidence_list=[]`, and **no `root`/`task_id` keys**. Trace through hard_constraints.check_all: C1/C2 return empty (`relevant_phases` never matches None), C5 returns early (`target_phase=None` → warning + skip, hard_constraints.py:552-558), C6 returns early (`current_phase=None`), C8 iterates an empty list, C9/C10/C11 return early (root is None). **Of the 11 "non-bypassable" constraints, only C3 (task package), C4 (path scope), and C7 (blockers) actually execute in the primary enforcement path.** C5 (verification), C6 (independent review), C8 (evidence freshness), C9 (imports), C10 (contracts), C11 (file limit) are dead letters in the hook; C5/C6 run only if some *other* caller supplies phase context.
- **Why it matters:** the module's own docstring calls C1-C11 "the non-bypassable control kernel ... every host adapter must implement to claim Loop compliance." The actual write path enforces a third of it.

### 2.14 No gate decision vocabulary or escalation ladder
- **Real practice:** GO / CONDITIONAL-GO / HOLD / KILL / RECYCLE with named gatekeepers and documented escalation (Stage-Gate: Go/Kill/Hold/Recycle; PMBOK phase-exit: proceed/iterate/kill; delivery-governance §2.1, §5.3).
- **Why it matters:** Loop's only decision is binary approve/reject by a single user. There is no conditional-approval-with-owners-and-deadlines, no "recycle with re-review date", no kill/project-termination decision, no escalation beyond the user. T-0082's own acceptance ended in "CONDITIONAL GO" — a decision the governance system itself cannot represent.
- **Evidence:** `GateStatus` = pending/approved/rejected/blocked only (state_machine.py:36-41); gates.yaml records `decision: approved` only; `veto_escalation.py` exists as a library but no hook or controller invokes an escalation ladder.

---

## 3. Actual-practice Gaps (what Loop's IMPLEMENTATION fails at — from T-0082 evidence)

### 3.1 Guard death produced silent PASS for months (P0)
- **Gap:** entire guards were dead while reporting success — the canonical "governance theater" failure.
- **Evidence:** (a) `bash_content_guard.py` — 20 lines containing literal 0x08 backspace bytes instead of `\b`, every `\s/\S/\d` stripped of its backslash, an unbalanced `(` causing `re.error` **at import time** (crash on every invocation), plus `main()` calling `project_root()` without `hook_input` (TypeError on every invocation). It was 100% dead; T-0082 phase-4 repaired it. (b) `content_guard.py` — same `project_root()` TypeError crashed the whole hook at startup, so lint/secret/architecture checks **never ran**; the semantic-rule engine (`load_semantic_rules`/`check_semantic_rules`/`check_suspense_boundary`) referenced an undefined variable `target` — NameError swallowed by `except Exception` — so the `.ai/checks/*.rules.yaml` engine never executed (phase-5 GAP-1). (c) `_run_ruff_check` used `--output-format text` which ruff ≥0.15 removed → rc=2 with empty stdout was treated as "pass" → **lint always green** (phase-5 GAP-1).
- **Consequence:** the edit-level quality chain (lint, secrets, semantics) silently did nothing for the period these bugs lived in the committed tree; "tests passed" throughout because the tests asserted exit codes of the *crash* (see 3.5).
- **Fix direction:** guard self-test/guard-health subsystem (see §6.2): every guard must prove on every run (or on a cadence) that it can block a fixture violation; exit-code-only testing is banned.

### 3.2 Fail-open defaults are pervasive by design
- **Gap:** many enforcement paths explicitly choose to pass when a tool/state is unavailable.
- **Evidence:**
  - `check_diff_scope` (loop_enforcement.py:236-257): non-git repo / git missing / git error / `git diff` failure → **fail-open** ("非 git 仓库…跳过", "git 不可用…跳过", "git diff 失败…跳过") — and it also does not track untracked files (phase-5 honest gap #1).
  - HardConstraints block in loop_enforcement.py:1094-1101: any exception in the constraint kernel → **fallback to legacy logic (pass)**; comment states this is intentional.
  - `_run_ruff_check` (content_guard.py:79-86): `FileNotFoundError`/timeout → `return True, []`; rc≠0 with **empty stdout** (e.g., `python -m ruff` module missing — error goes to stderr) → PASS.
  - `gate_guard.py:195-204`: `fail_on_state_error: open` in config → fail-open; `should_fail_closed` is config-driven (hook_common.py:355-366).
  - `content_guard.py:299-300`: semantic-rule exceptions are non-blocking by design ("非阻塞").
  - Ledger failures are non-blocking throughout (`role_dispatch.py:168-169`: "ledger failure is non-blocking; receipts still authoritative"; loop_enforcement.py:431-432).
  - `trace_review_evidence_isolation` (loop_enforcement.py:440-492): **self-review is only logged, never blocks** ("never returns a blocking verdict") — a direct self-review (reviewer_session_id == developer_session_id) does not stop the gate; only gate_guard's optional `require_subagent_review` path blocks, and only when the gate author opted in via `content_quality` config.
  - S7-S11 evidence checks: "任一候选通过即整体通过（fail-open 于多候选场景）" (loop_enforcement.py:638) — one passing candidate among several satisfies the phase gate.
- **Consequence:** the same project state can be governed differently depending on git availability, ruff presence, config values, and whether an exception path was hit; an attacker or a broken environment widens the opening.
- **Fix direction:** inventory every fail-open path; default to fail-closed for *governance-critical* checks (scope, security, evidence), and make any deliberate fail-open produce a `NOT_VERIFIED` verdict that the phase gate must treat as non-conclusive (Verdict semantics already exist: `UNAVAILABLE`/`NOT_VERIFIED` are non-blocking *and non-conclusive* — but nothing consumes that nuance today).

### 3.3 Dead code and duplicate implementations coexist (single source of truth violated)
- **Gap:** multiple implementations of the same function exist; the operative one is often the deprecated one.
- **Evidence:** (a) T-0082 phase-2 marked 5 duplicates deprecated: `scripts/security_scan.py`, `agents/security-engineer/scripts/run_security_scan.py`, `agents/quality-engineer/scripts/run_quality_gates.py`, `tools/tool_security_scan.py`, `tools/tool_quality_gates.py` — yet `run_quality_gates.py` (header: "DEPRECATED: Prefer loop_core.static_analyzer…") is **still the script the quality-engineer role calls and the one that produces the `quality_report.json` the enforcement hook requires** — the deprecated script, not the "preferred" loop_core API, is the operative quality chain. (b) Compatibility aliases were bolted on because the schema expected classes (`Executor`, `SecurityScanner`, `StaticAnalyzer`) that the modules never exported (baseline-report: 3 import FAILs; convergence-report "Added `Executor = PhaseExecutor` alias…"). (c) `subagent_evidence_verifier.py` was dead code until T-0082 phase-3 wired it as a **trace-only** path; `loop_enforcement.py.bak` (17KB) sits in the hooks directory. (d) Role-dispatch infra report: "receipts/ledger/identity scaffolding existed but no dispatch path was wired, receipts were never persisted" — the scaffolding predated any consumer.
- **Consequence:** two sources of truth for the same check produce divergent behavior; enforcement can read the legacy artifact while the "canonical" API reports something else; a deprecation notice is not a migration.
- **Fix direction:** enforcement chain must be re-pointed at exactly one implementation per check (loop_core API with Verdict bindings), and the deprecated scripts deleted or reduced to thin CLI shims with the same code path; add an integration test asserting the hook's evidence files are produced by the canonical implementation.

### 3.4 No self-audit: the governance system never checks its own guards
- **Gap:** nothing verifies that guards are alive, effective, and non-regressing — the T-0082 baseline audit (a *manual, task-driven* audit) was the first time the dead guards were discovered.
- **Evidence:** no guard-health check exists in the hook chain; `auto_sync_to_plugin_cache` copies hook scripts to the plugin cache but does not verify they run; hooks.json matcher changes are **not hot-reloaded** — they take effect only on the next ZCode session restart, so a session can run with a matcher that excludes `mcp__node_repl__js` (phase-4 remaining gap #1); T-0082's own evidence for AC-03/AC-09 was produced by manual subprocess runs, not by a built-in self-test.
- **Consequence:** guard death is invisible until a manual audit; between a guard's failure and the next audit, the project operates unguarded while appearing governed.
- **Fix direction:** §6.2 guard-health subsystem; also a startup self-check hook (SessionStart) that runs a fixture-based guard battery and records results to the ledger.

### 3.5 Tests verify execution, not protection
- **Gap:** the test suite asserted that scripts *ran and exited*, not that they *blocked the right things* — so a crashing guard "passed" its tests.
- **Evidence:** T-0082 phase-4 report: the pre-existing `TestBashContentGuard` subprocess tests "only 'passed' via the crash exit code 1" — the expected exit code coincided with the crash; 18 existing tests asserted the old (bypass) classification and were flipped by T-0082; the acceptance AC-03 treats exit-code observation as protection evidence.
- **Consequence:** tests give false confidence; a guard can be deleted or crash and the suite stays green (exactly what happened).
- **Fix direction:** for every guard, add negative-control tests that prove the guard *denies a real bypass attempt* (a fixture that would succeed without the guard) and positive controls; assert on the deny payload (`permissionDecision`), not just exit code; mutation-test the guards themselves.

### 3.6 No meta-governance: the takeover itself ran with uncommitted, unreviewed state
- **Gap:** the governance upgrade was validated against a working tree that was not committed; a clean checkout could not reproduce any of it.
- **Evidence:** independent-reviewer-report (phase-3): "`loop_core/verdicts.py` is untracked; … The developer's tests pass only against the working tree — a clean HEAD checkout would fail to import `loop_core.verdicts`." Acceptance report: "the entire T-0082 slice is NOT committed to HEAD… 39 modified/untracked files"; overall verdict **CONDITIONAL GO** with the condition being "commit the slice so the evidence chain is reproducible." (Note: state.yaml now records T-0082 COMPLETED at v3.12.22 — the condition was later met.)
- **Consequence:** during the takeover, HEAD and the governed reality diverged; if the machine had crashed, the "governance" would have been unrecoverable — the exact failure mode (governance state not reproducible from version control) that CMMI ML2+ and SLSA provenance exist to prevent.
- **Fix direction:** governance changes must be committed before their gates can be approved (a "governance-dirty-tree" check in the enforcement chain), and gate approval must bind to a git commit.

### 3.7 Runtime-state deadlock and manual recovery channel
- **Gap:** a stale/missing runtime-state file can deadlock the entire governed project; recovery is a manual, minimally-scoped backdoor.
- **Evidence:** phase-5 honest gap #5: missing `.ai/runtime/runtime-state.json` caused `loop_enforcement` to block **all business writes** at the runtime-projection check ("SETUP_INCOMPLETE") — the runtime takeover froze the project; T-0082 commands.md records `DEADLOCK_FIX: 删除runtime-state.json解除死锁` (manual deletion by the controller). The `GOVERNANCE_RECOVERY` channel (loop_enforcement.py:950-958) allows governance-path writes only, which is reasonable, but it is controller-triggered, i.e., the governed party decides when recovery is needed.
- **Consequence:** a single JSON file is a single point of failure for the whole governance system; recovery depends on the controller's honesty.
- **Fix direction:** derive runtime state from the YAML sources of truth (or a chain-hashed ledger) instead of a standalone snapshot; make recovery audited and user-gated.

### 3.8 MCP / side-effect tools are unusable in FULL mode (capability gap)
- **Gap:** the T-0082 fix that closed the Node-REPL bypass made MCP side-effect tools **impossible** in governed projects.
- **Evidence:** phase-4 remaining gap #4: "MCP tools have no statically extractable target, so in FULL/STANDARD mode they are fail-closed blocked even with identity + active task… `is_in_task_scope(None, …)` is always False" — documented as intentional fail-closed with no capability model to unblock it.
- **Consequence:** legitimate developer work via MCP tools (Node REPL, MCP servers) is blocked; the only workaround is LIGHTWEIGHT mode (which disables all enforcement). This is an all-or-nothing gap, not a scoped-permission gap.
- **Fix direction:** an explicit MCP tool allow-list in the task contract (tool names + allowed args), enforced by a new scope check, matching the AI-agent practice of explicit tool permissions (§4.6).

---

## 4. AI-Agent-Project Readiness Gaps (loop-engine governing AI agent projects)

Mapping of the 8 practice areas from ai-agent-engineering-research.md to Loop's current capability. **READY** = enforceable today; **PARTIAL** = some element exists but not the practice; **MISSING** = no element.

| # | AI-agent practice (research) | Loop capability | Status | Evidence / what is missing |
|---|---|---|---|---|
| 4.1 | **Agent evals** (golden sets, task-success/tool-use/trajectory metrics, pass@k/pass^k, judge calibration, 20-50 seed tasks) | None | **MISSING** | No eval artifact type, no dataset/grader concept, no statistical pass-rate gate. Closest analog: contract tests (C10, SOFT + skipped when no contracts) and pytest gates (whole-suite green, deterministic only). A governed agent project cannot be gated on "does the agent achieve its task" — only on "did files lint". |
| 4.2 | **Observability/tracing** (OTel GenAI semconv: per-step LLM/tool spans, tokens, cost, latency; session logs as audit trail; trace replay) | Execution ledger + receipts + audit ledger | **PARTIAL** | `.ai/ledger/executions.jsonl` (chain-hashed, cross-validatable), `.ai/runtime/dispatch/*.receipt.json` (append-only per dispatch), `audit_ledger.py`, journal `runtime-events.jsonl` — a solid *dispatch* audit trail. **Missing:** any trace of LLM calls/tool calls/decisions inside a run (the ledger records launch/completion, not steps); no token/cost/latency capture; no OTel compatibility; no session replay; no `gen_ai.*` attributes. |
| 4.3 | **Guardrails** (input/output rails, prompt-injection defense, structured-output enforcement, guardrail config as tested artifact, classifier-in-loop) | content_guard / bash_content_guard / gate_guard | **PARTIAL** | Guards are coarse regex gates on *file writes and bash commands* — they protect the repo, not the agent. **Missing:** input/output content validation, injection defense (OWASP LLM01 is the #1 LLM risk — untackled), structured-output enforcement, guardrail eval results (NeMo-style vulnerability scans), tool-result inspection before context entry. Guard config IS a versioned artifact (config.yaml) — that part exists. |
| 4.4 | **Tool contracts** (schema validation, arg/selection/sequence evals, mock-tool suites, failure injection: timeouts/errors/retries, sandboxed staging) | contract_verifier + C10 + module-architect validate_contract.py | **PARTIAL** | Schema-level contract checking exists (`.ai/evidence/{task}/contract*.yaml` → tests_required → C10). **Missing:** everything agent-specific — no tool-call argument evals, no tool-sequence assertions, no mock-tool sandbox, no tool-failure-injection tests, no trajectory checks. C10 is SOFT and skipped when contracts are absent (self-disabling gate). |
| 4.5 | **Determinism engineering** (seeds/temperature policy, structured outputs, max steps/tokens/cost budgets, loop detection, resumable harnesses, concurrency bounds) | DispatchLease only | **MISSING** | `DispatchLease` prevents duplicate dispatch (a dedup lock), not agent determinism. No budget types (steps/tokens/cost), no loop/cycle detection, no checkpoint/resume for long-running agents, no seed/temperature policy. A governed agent project cannot be gated on bounded behavior. |
| 4.6 | **Agent security** (least-privilege permission model, credential vault outside sandbox, human approval for irreversible actions, red-teaming, provenance of prompts/models/tools, approval-fatigue management) | Write-scope authorization + role isolation + user gates | **PARTIAL** | Real strengths: capability-scoped writes (RuntimeController), actor/session isolation (AC-06), human-only gate approval (AC-12), bash bypass guards. **Missing:** credential vault separation (no secrets handling at all — T-0082 explicitly OUT OF SCOPE); no sandboxing (filesystem/network); no red-team suite (prompt-injection, jailbreak, exfiltration — promptfoo-style); no prompt/model/tool version provenance; **approval fatigue is unmanaged** — the design prompts the user for every gate and writes are all-or-nothing (research: users approve ~93% of permission prompts within weeks; Claude Code cut prompts 84% via hard boundaries). |
| 4.7 | **CI/CD for agents** (deterministic unit layer + mock-LLM tests, golden evals with `--repeat` variance handling, cost/latency gates, staging sandboxes, canary/rainbow model+prompt deployments, human review checkpoints) | Hook-based phase gates + verdicts | **PARTIAL** | The phase-gate chain (edit/task/phase layers, Verdict semantics, fingerprint binding) is a genuine CI-shaped skeleton. **Missing:** any eval-in-CI concept, variance handling (single-run pass/fail only), cost/latency gates, staging sandboxes with fake tools/credentials, canary/rainbow deployment of agent versions, and the eval suites themselves (§4.1). |
| 4.8 | **Production governance** (agent registries with prompt/model/tool/harness/guardrail versions, runtime policy, append-only session logs, incident management for bad outputs, continuous evals: replay/shadow/drift) | version-manifest.yaml + transaction_registry.yaml + ledger | **PARTIAL** | Registry artifacts exist (`version-manifest.yaml`, `transaction_registry.yaml`) and the ledger is append-only + chain-hashed — the *shape* of production governance. **Missing:** registry entries don't cover prompt/model/tool/guardrail versions (only project artifacts); no runtime policy engine; no incident record type for bad outputs (see §2.3 — no postmortem at all); no continuous eval/drift detection; no replay/shadow evals. |

**Bottom line:** Loop can govern *where agent code may write and who approves* (READY-ish for 4.6's write half) but cannot gate on *what the agent does* (4.1), *how it behaved* (4.2), *what it was told not to do* (4.3/4.6 red-team), *how it used tools* (4.4), or *how bounded it is* (4.5). For governing AI-agent projects, the missing eval+observability+guardrail stack is not an enhancement — it is the core QA mechanism (research: "20-50 simple tasks drawn from real failures is a great start"; "full production tracing was added to diagnose why agents failed").

---

## 5. Priority Matrix — top 15 gaps by (impact × urgency)

Scoring: **Impact** = how much governed-project quality/trust is damaged (1-5). **Urgency** = how soon it will bite (1-5, 5 = already biting). Priority = Impact × Urgency. Fix owner = Loop role that should own the fix; Phase = suggested future task phase for scheduling.

| # | Gap (reference) | Impact | Urgency | P | Fix owner | Suggested task phase |
|---|---|---|---|---|---|---|
| 1 | **Guard death silent PASS / no guard self-audit** (§3.1, §3.4) | 5 | 5 | 25 | security-engineer + quality-engineer | T-0084 (guard-health subsystem, S4) |
| 2 | **Fail-open defaults in governance-critical paths** (§3.2: diff-scope, ruff-missing, gate_guard config, evidence any-candidate) | 5 | 5 | 25 | security-engineer | T-0084 |
| 3 | **HardConstraints kernel dormant in write path** (§2.13: only C3/C4/C7 run; C5/C6/C8 dead) | 5 | 4 | 20 | system-architect + developer | T-0085 (enforcement completeness, S4) |
| 4 | **No SLO / error budget** (§2.1) | 4 | 4 | 16 | system-architect + delivery-manager | T-0086 (SLO subsystem, S2-architecture) |
| 5 | **No postmortem/retro feedback loop** (§2.3) | 4 | 4 | 16 | project-manager + delivery-manager | T-0087 (learning loop, S2) |
| 6 | **No DORA-style delivery metrics** (§2.2) | 4 | 3 | 12 | delivery-manager + release-engineer | T-0088 (metrics subsystem, S2) |
| 7 | **Definition of Done / gate conditions unformalized (0 conditions in register)** (§2.8) | 4 | 4 | 16 | product-manager + quality-engineer | T-0089 (DoD contract, S1) |
| 8 | **Evidence independence: self-asserted PASS + NOGO-passes bug** (§2.12, §3.x: check_delivery_gate_evidence accepts NOGO) | 4 | 5 | 20 | independent-reviewer + security-engineer | T-0090 (evidence verification, S5) |
| 9 | **Delta-based quality gates (no per-edit regression baseline; diff_fingerprint unused)** (§2.6) | 4 | 3 | 12 | quality-engineer + developer | T-0091 (delta gates, S4) |
| 10 | **AI-agent eval + observability stack absent** (§4.1, §4.2) | 5 | 3 | 15 | system-architect + quality-engineer | T-0092 (agent QA foundation, S2/S4) |
| 11 | **No OWNERS-equivalent / no per-area accountability (RACI single-A)** (§2.7) | 3 | 3 | 9 | module-architect + system-architect | T-0093 (ownership model, S2) |
| 12 | **No incident/rollback authority in runtime (no INCIDENT/ROLLBACK states)** (§2.9) | 4 | 3 | 12 | release-engineer + system-architect | T-0094 (runtime safety net, S4) |
| 13 | **No CAB/meta-governance for governance changes** (§2.10) | 3 | 4 | 12 | governance-controller + independent-reviewer | T-0095 (governance-of-governance, S1) |
| 14 | **Deprecated-duplicate implementation drift (operative path is deprecated script)** (§3.3) | 3 | 4 | 12 | developer + quality-engineer | T-0096 (single-source consolidation, S4) |
| 15 | **Gate decision vocabulary + escalation ladder missing (CONDITIONAL-GO/HOLD/KILL/RECYCLE)** (§2.14) | 3 | 3 | 9 | delivery-manager + project-manager | T-0097 (decision model, S1/S6) |

Also flagged (lower priority, keep on backlog): MCP capability model (§3.8), bug caps/defect tracking (§2.5), tech-writer role/runbooks (§1 #12), SRE role (§1 #10 — may be folded into the SLO subsystem T-0086 + runtime safety net T-0094), approval-fatigue management (§4.6).

---

## 6. Design Implications for Loop v4 (architectural changes to Loop itself)

The deep gaps share three roots: **(a) nothing verifies the verifiers**, **(b) nothing measures the delivery system**, **(c) the phase machine models a linear V-model with no learning loop and no reliability dimension**. Seven concrete architectural recommendations:

### 6.1 "Guard Health" subsystem (closes §3.1, §3.4, §3.5)
A first-class subsystem — not a test suite — that owns guard verification:
- **Fixture battery:** a fixed set of positive/negative control operations (write out-of-scope, redirect write, pending-gate write, secret-in-content, self-review evidence, drifted gate) run against the live hook chain on SessionStart and before every phase gate.
- **Guard coverage contract:** every guard must declare which fixture it kills; a guard with zero kills is flagged `DORMANT` in the gate verdict; T-0082-style dead-guard bugs become gate failures, not audit findings.
- **Protection-vs-execution test rule:** guard tests must assert on deny payloads and on the *effect* (file not created, command denied), not exit codes; mutation-test the guard patterns themselves (a mutated regex must fail the battery).
- Result recorded to the execution ledger so guard health is auditable and trendable (feeds 6.2).

### 6.2 "Governance Metrics" subsystem (closes §2.2, §2.1, partially §2.14)
A metrics core that turns the ledger/register into DORA-style governance telemetry:
- **Loop-DORA:** gate rejection rate, phase dwell time, task rework cycles (S4→S5 bounce count), evidence regeneration events (C8), guard block/pass/error rates, drift events, approval latency.
- **Gate error budget:** each phase gate gets a tolerance budget (e.g., allowed evidence-invalidity events, allowed guard-errors per task); exhausting it automatically freezes the phase — the SRE error-budget pattern applied to the governance process itself.
- Every report binding already carries `task_id/phase/gate_id/execution_id/git_commit/timestamp` (verdicts.py) — the telemetry schema is already there; only the aggregation layer is missing.

### 6.3 Learning-loop phase additions: Postmortem/Retro as first-class phases (closes §2.3)
- Add phase-level artifacts: an `incident` record type (severity, timeline, trigger, detection, resolution) and a `retrospective` artifact (what worked/failed, action items with owner + due date), both required before S11→S1 iteration and after any gate rejection or guard failure.
- Enforce the **"second failure" doctrine**: if the same failure class (same rule_id/constraint/guard) recurs across tasks, the follow-up task is automatically created and the phase gate blocks until an action item exists with an owner.
- This converts S11→S1 from a cycle into a PDCA loop (Plan-Do-Check-Act with the "Check" being metrics from 6.2).

### 6.4 Delta-based quality gates (closes §2.6, strengthens §2.5)
- Make `ReportBinding.diff_fingerprint` load-bearing: every S5/S7-S11 evidence check compares the task's diff against the pre-task baseline — "new code may not regress" (SonarQube pattern): no new coverage loss on changed files, no new lint/security findings attributable to the diff, zero new bugs.
- Add a **per-edit regression baseline** at the content_guard layer: snapshot quality attributes (lint errors, secret hits) of the pre-edit file and require the merged file to be no worse.
- Keep whole-project gates advisory (metrics), make delta gates blocking.

### 6.5 Evidence verification layer: IV&V for self-asserted PASS (closes §2.12, §3.2, NOGO bug)
- A `Verifier` component that independently re-runs a sample of claimed evidence (random sampling + full re-run for critical paths) and signs the result; gate approval requires verifier-signed evidence, not the producer's own JSON.
- Fix the delivery-gate semantics: `decision` must be validated against an enum (`GO`/`NOGO`/`CONDITIONAL_GO`), `NOGO` must *block* with a recycle path, and `CONDITIONAL_GO` must carry named owners + deadlines (extends §2.14's decision vocabulary).
- Adopt the verdict nuance that already exists but is unused: `UNAVAILABLE`/`NOT_VERIFIED` are non-conclusive — a gate with any non-conclusive evidence must not pass silently; it must surface as "cannot verify" to the user.

### 6.6 "Agent Eval" gate type + agent observability requirement (closes §4.1, §4.2, §4.5)
- New gate condition type `eval_required` in the register (the `conditions` mechanism already exists in state_machine.GateCondition but is never used — §2.8): gate params carry eval suite path, pass-rate threshold, and `pass@k`/`pass^k` semantics.
- New phase evidence type: eval report (dataset version, trial count, pass rates per dimension: task completion, tool correctness, trajectory, safety; judge-calibration record).
- Mandatory trace contract for governed agent projects: sessions must emit per-step logs (LLM call, tool call, tokens, cost, latency) to the existing ledger format (extend `executions.jsonl` records) — "no trace export = no phase promotion" (research §4.2).
- Determinism block: max-steps/max-cost budgets, loop detection, and resumability checks as gate conditions (§4.5).

### 6.7 Governance-of-governance: CAB + dirty-tree guard (closes §2.10, §3.6, §3.7)
- Governance changes (state.yaml, gates.yaml, task_graph.yaml, HANDOFF, hooks, config.yaml) become a change class with review: a "governance diff" evidence artifact reviewed by independent-reviewer before the controller may apply it; the decision-recording exemption in gate_guard is narrowed to the act of recording, not to arbitrary register edits.
- **Dirty-tree rule:** a phase gate cannot be approved while governance files are uncommitted (the T-0082 CONDITIONAL-GO failure mode becomes an enforced invariant); gate records bind to the git commit hash they were decided on.
- Replace the standalone `runtime-state.json` snapshot with a derived state (reconstructible from state.yaml + ledger) so a missing snapshot degrades to reconstruction, not deadlock (closes §3.7).

---

## 7. Honest caveats

1. This analysis was conducted on the live working tree at commit state v3.12.22-era (T-0082 slice committed per state.yaml notes); behavior was verified by reading code + T-0082's independently re-verified evidence, not by re-executing every check in this session.
2. Some "gaps" are deliberate scope decisions (T-0082 explicitly excluded deployment/rollback/secrets/production data). They are listed as design gaps because the *architecture* has no slot for them, not because T-0082 forgot them.
3. The T-0082 acceptance was CONDITIONAL GO on committing the working tree; per .ai/state.yaml the condition was met (v3.12.22). Any further uncommitted governance drift should be re-checked before acting on this report's recommendations.
4. Role contracts (CONTRACT.yaml) are significantly *better* than the enforcement they describe — Loop's design documents are ahead of its implementation, which is the opposite of the usual case, and means the fix is mostly wiring, not invention.

---

## Appendix: evidence index (file → finding)

| Evidence location | Finding(s) it supports |
|---|---|
| `.ai/evidence/T-0082/baseline/baseline-report.md` | 3.3 (import aliases), 3.4 (manual audit), 3.6 (uncommitted), 2.10 (HANDOFF drift) |
| `.ai/evidence/T-0082/phase-3/independent-reviewer-report.md` | 3.5 (crash-exit tests), 3.6 (untracked verdicts.py), 3.4 |
| `.ai/evidence/T-0082/phase-4/side-effect-authorization-report.md` | 3.1 (bash guard death), 3.8 (MCP fail-closed), 3.2 (heuristic gaps), hooks.json restart |
| `.ai/evidence/T-0082/phase-5/layered-quality-gates-report.md` | 3.1 (content_guard crash, ruff format), 3.2 (fail-open paths), 3.7 (runtime deadlock), 2.12 (substring BLOCKED) |
| `.ai/evidence/T-0082/phase-6/acceptance-report.md` | 3.6 (CONDITIONAL GO, 39 files), 2.14 (no CONDITIONAL-GO in system) |
| `loop_core/hard_constraints.py` | 2.13 (dormant kernel), 2.5 (SOFT C10/C11), 2.6 |
| `loop_core/state_machine.py` | 2.3 (no retro), 2.8 (GateCondition unused), 2.14 (GateStatus), 2.1 (no SLO), 2.9 |
| `loop_core/runtime_controller.py` | 2.9 (no incident state), 2.10 (GOVERNANCE_CONTROLLER_ONLY) |
| `loop_core/verdicts.py` | 2.6 (diff_fingerprint unused), 3.2 (UNAVAILABLE/NOT_VERIFIED non-conclusive but unused), docstring-vs-is_blocking FAIL inconsistency |
| `loop_core/security_scanner.py` | 1 #11 (test files excluded), 2.12 |
| `loop_core/role_dispatch.py` | 3.3 (scaffolding dead), 3.2 (ledger non-blocking) |
| `hooks/scripts/loop_enforcement.py` | 2.4 (git exemptions, orchestration pass, LEGACY_FIXTURE), 2.13 (context empty), 2.12 (any-candidate evidence, NOGO pass, substring check), 3.2 (fail-open), 3.7 (recovery) |
| `hooks/scripts/gate_guard.py` | 2.4 (allow_legacy, enabled flag), 2.10 (decision exemption) |
| `hooks/scripts/content_guard.py` | 1 #11 (only .py), 3.2 (ruff-missing PASS), 2.6 |
| `hooks/scripts/bash_content_guard.py` | 2.4 (exempt substring), 3.1 |
| `agents/*/CONTRACT.yaml` | 1 (prose-only vetoes), 1 #4/#7/#8 |
| `.ai/gates.yaml` | 2.8 (zero conditions), 2.14 (approval-only vocabulary) |
| `.ai/QUALITY_GATES.md` | 2.8 |
| `.ai/evidence/T-0083/research/*.md` | the four baselines (roles, quality mechanisms, delivery governance, AI-agent engineering) |
