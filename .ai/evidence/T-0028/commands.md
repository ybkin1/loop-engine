# Commands - T-0028

## Startup

```powershell
Get-Content -LiteralPath 'C:\Users\Administrator\.codex\skills\project-governor\SKILL.md' -Raw -Encoding UTF8
Get-Content -LiteralPath 'C:\Users\Administrator\.codex\loop-engine-lab\AGENTS.md' -Raw -Encoding UTF8
Get-Content -LiteralPath 'C:\Users\Administrator\.codex\loop-engine-lab\.ai\state.yaml' -Raw -Encoding UTF8
Get-Content -LiteralPath 'C:\Users\Administrator\.codex\loop-engine-lab\.ai\HANDOFF.md' -Raw -Encoding UTF8
Get-Content -LiteralPath 'C:\Users\Administrator\.codex\loop-engine-lab\.ai\tasks\T-0027.md' -Raw -Encoding UTF8
Get-Content -LiteralPath 'C:\Users\Administrator\.codex\loop-engine-lab\.ai\gates.yaml' -Raw -Encoding UTF8
Get-Content -LiteralPath 'C:\Users\Administrator\.codex\loop-engine-lab\.ai\task_graph.yaml' -Raw -Encoding UTF8
& 'C:\Python312\python.exe' 'C:\Users\Administrator\.codex\skills\project-governor\scripts\validate_state.py' 'C:\Users\Administrator\.codex\loop-engine-lab'
```

Startup validation passed before T-0028 gate registration.

## Gate Registration

```powershell
New-Item -ItemType Directory -Path 'C:\Users\Administrator\.codex\loop-engine-lab\.ai\evidence\T-0028' -Force
```

Created T-0028 task, startup validation evidence, gate request evidence, user
decision packet, and governance state updates for a pending gate only.

## Post-Registration Validation

```powershell
& 'C:\Python312\python.exe' 'C:\Users\Administrator\.codex\skills\project-governor\scripts\validate_state.py' 'C:\Users\Administrator\.codex\loop-engine-lab'
```

Observed result:

```text
[project-governor] phase: S0-method-repair
[project-governor] current_task_id: T-0028
[error] Pending gate(s) require user decision before continuing: G-T-0028-REAL-PROJECT-TEST-REVIEW-QUALITY-ASSURANCE-GOVERNANCE-BASELINE-CONSIDERATION
```

Observed exit code: 1.

## Approval Recording

```text
User explicitly approved:
批准 G-T-0028-REAL-PROJECT-TEST-REVIEW-QUALITY-ASSURANCE-GOVERNANCE-BASELINE-CONSIDERATION
```

The same user message required handoff/startup prompt to include a
`Next Action Contract` for `T-0027 hygiene cleanup + baseline consideration`.

Created approval evidence:

```text
.ai/evidence/T-0028/real-project-test-review-quality-assurance-governance-baseline-consideration.approval.record.v0.1.md
```

Post-approval validation:

```powershell
& 'C:\Python312\python.exe' 'C:\Users\Administrator\.codex\skills\project-governor\scripts\validate_state.py' 'C:\Users\Administrator\.codex\loop-engine-lab'
```

Observed result:

```text
[project-governor] phase: S0-method-repair
[project-governor] current_task_id: T-0028
[ok] state is usable
```

## T-0027 Hygiene Cleanup

Checked duplicate T-0027 evidence entries in `.ai/tasks/T-0027.md` and
`.ai/HANDOFF.md`, removed the duplicate `handoff-audit.v0.1.md` entry in each
file, verified no obvious duplicate remained, and verified listed T-0027
evidence files exist.

Created cleanup evidence:

```text
.ai/evidence/T-0028/t-0027-handoff-evidence-hygiene-cleanup.v0.1.md
```

## Baseline Consideration

Read the required T-0024, T-0025, T-0026, and T-0027 evidence listed in
`.ai/evidence/T-0028/baseline-consideration-scope.v0.1.md`.

Created baseline consideration evidence:

```text
.ai/evidence/T-0028/baseline-consideration-scope.v0.1.md
.ai/evidence/T-0028/baseline-consideration-review.v0.1.md
.ai/evidence/T-0028/baseline-consideration-decision.v0.1.md
.ai/evidence/T-0028/next-gate-recommendation.v0.1.md
```

Decision:

```text
BASELINE_REFERENCE_CANDIDATE_ACCEPTED_FOR_LATER_IMPLEMENTATION_PLANNING
```

## Final Validation And Handoff Audit

```powershell
& 'C:\Python312\python.exe' 'C:\Users\Administrator\.codex\skills\project-governor\scripts\validate_state.py' 'C:\Users\Administrator\.codex\loop-engine-lab'
& 'C:\Python312\python.exe' 'C:\Users\Administrator\.codex\skills\project-governor\scripts\audit_handoff.py' 'C:\Users\Administrator\.codex\loop-engine-lab'
```

Observed results:

```text
[project-governor] phase: S0-method-repair
[project-governor] current_task_id: T-0028
[ok] state is usable

[ok] handoff audit passed
[evidence] C:\Users\Administrator\.codex\loop-engine-lab\.ai\evidence\T-0028
```

Created final evidence:

```text
.ai/evidence/T-0028/final-validation.v0.1.md
.ai/evidence/T-0028/handoff-audit.v0.1.md
```

## Boundary

No baseline approval, implementation planning, implementation, installation,
runtime/tool enablement, `AGENTS.md` change, real-project entry, business code,
build, deployment, release, rollback, database, permission, secret, payment,
production-data, or migration action is authorized by this approval.
