# Commands For T-0017

## Startup And Gate Registration

- Read latest user request and attached startup note.
- Read `AGENTS.md`.
- Read `.ai/state.yaml`, `.ai/HANDOFF.md`, `.ai/tasks/T-0016.md`,
  `.ai/gates.yaml`, `.ai/task_graph.yaml`, and `.ai/PROGRESS.md`.
- Ran `validate_state.py` before T-0017 registration:

```text
[project-governor] phase: S0-method-repair
[project-governor] current_task_id: T-0016
[ok] state is usable
```

- Confirmed no `status: pending` gate existed before T-0017 registration.
- Spawned read-only explorer subagents for sidecar evidence review:
  `019f411a-d0aa-7ca1-ad83-81f5fb314f30`,
  `019f411a-d1f5-7c92-875b-7f4c99df82e3`,
  `019f411a-d260-77f0-a7d7-82af3592ca46`.
- Ran `new_task.py --allow-parallel` to create T-0017 task and evidence
  skeleton.
- Recorded pending gate
  `G-T-0017-REAL-PROJECT-DELIVERY-ARCHITECTURE-GOVERNANCE-DESIGN`.

## Approval

- User explicitly approved:

```text
批准 G-T-0017-REAL-PROJECT-DELIVERY-ARCHITECTURE-GOVERNANCE-DESIGN
```

- Recorded approval as user approval, not AI approval.
- Updated `.ai/gates.yaml`, `.ai/state.yaml`, `.ai/task_graph.yaml`, and
  `.ai/tasks/T-0017.md`.

## Candidate Package Generation

- Read prior evidence from T-0001, T-0002, T-0006, T-0008, T-0010, T-0011,
  and T-0016.
- Consulted relevant external contracts for architecture, PRD, design,
  development planning, traceability, review, testing, security, data,
  deployment, work packets, document depth, and closeout.
- Created T-0017 candidate artifacts under `.ai/evidence/T-0017/`.
- Spawned bounded read-only subagents for contract review, historical method
  synthesis, and governance audit.
- Recorded subagent review summary as evidence only.

## Validation And Closeout

- Ran `validate_state.py` after candidate package generation:

```text
[project-governor] phase: S0-method-repair
[project-governor] current_task_id: T-0017
[ok] state is usable
```

- Confirmed no `status: pending` entries in `.ai/gates.yaml`.
- Ran `close_session.py` for T-0017 closeout.
- Corrected generated handoff to T-0017-specific closeout facts.
- Ran final `validate_state.py`:

```text
[project-governor] phase: S0-method-repair
[project-governor] current_task_id: T-0017
[ok] state is usable
```

- Ran `audit_handoff.py`:

```text
[ok] handoff audit passed
[evidence] C:\Users\Administrator\.codex\loop-engine-lab\.ai\evidence\T-0017
```

- Confirmed no `status: pending` entries remain in `.ai/gates.yaml`.
- Confirmed `.ai/task_graph.yaml` records T-0017 as `completed`.
- Confirmed T-0017 evidence directory contains 29 files.
- Ran dangerous-phrase scan for build / real-project authorization wording; the
  matches are boundary statements such as "not build approval" and "not a
  real-project entry approval".
