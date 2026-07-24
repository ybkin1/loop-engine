# Generic Handoff Spec Candidate v0.1

Status: candidate
Approved: false
Installed: false
Scope: temporary handoff format for current no-write design work

## 1. Purpose

A handoff document lets a new Codex session continue without reading the full chat history.

It must answer:

- What are we trying to achieve?
- What is the current state?
- What has been decided?
- What is allowed and forbidden?
- What should the next session read?
- What should the next session do first?
- What must not be mistaken as approved, installed, or complete?

The handoff is not an authority source. It is a routing and continuity aid.

## 2. Core Rules

- Keep handoff short enough for a new session to read first.
- Link to source documents instead of copying full documents.
- Separate facts, candidates, assumptions, and open questions.
- Never use handoff to grant permissions.
- Never let handoff override `state.yaml`, task files, gates, or authority-boundary rules.
- Always state whether the work is candidate, reviewed, user-approved, active, or installed.
- Always state the current mode: no-write, write-docs, write-code, deploy, or blocked.

## 3. Required Sections

### 3.1 Header

```yaml
handoff_id:
project:
date:
current_phase:
current_task_id:
current_mode:
artifact_status:
approved: false
installed: false
```

### 3.2 User Origin

Briefly restate the stable user position:

```text
The user has no coding background and no project management background.
The goal is to use Codex with loop engineering to move from rough requirements to real, usable, deployable, acceptable, and maintainable software.
```

Do not rewrite the whole user-origin document. Link to it when available.

### 3.3 Current Objective

State the active objective in one short paragraph.

Include:

- what the current task is;
- why it matters;
- what it must not become.

### 3.4 Current Scope

Use two lists:

```text
Allowed:
- ...

Forbidden:
- ...
```

Forbidden should explicitly include anything that could be misread:

- installing protocols;
- entering real business projects;
- writing code when current mode is no-write;
- claiming approved, active, installed, production-ready, or project-complete.

### 3.5 Must Read

List exact files the next session must read.

Each entry should include why it matters:

```text
- .ai/state.yaml: current phase, task, gate state.
- .ai/tasks/T-0001.md: active task scope and acceptance.
```

Do not list large old histories unless necessary.

### 3.6 Key Decisions

List only decisions that should affect the next step.

Each decision should include:

```yaml
decision:
status:
source:
scope:
revisit_when:
```

Do not treat candidate text as an approved decision.

### 3.7 Current Artifacts

Separate artifacts by status:

```text
Candidate:
- ...

Reviewed:
- ...

User-approved:
- ...

Active:
- ...

Evidence:
- ...
```

If there are no approved or active artifacts, say so explicitly.

### 3.8 Open Questions

List questions that block progress or require user judgment.

Each question should include:

- why it matters;
- who must answer;
- what happens if unanswered.

### 3.9 Risks And Watch Items

Include risks the next session must actively guard against:

- context drift;
- candidate/approved confusion;
- review PASS treated as user approval;
- task card treated as authority;
- document work replacing software delivery;
- stale files treated as current.

### 3.10 Next Session First Step

Give one concrete first action.

Good:

```text
Read the listed files, run validate_state.py, then generate a Coordinator task card for the next candidate package.
```

Bad:

```text
Continue improving things.
```

### 3.11 Copyable Startup Prompt

Provide a prompt the user can paste into the next session.

It must include:

- project root;
- current task;
- files to read;
- current mode;
- forbidden actions;
- expected first output.

## 4. Optional Sections

Use these only when relevant:

- Recent Changes
- Verification Performed
- Not Verified
- Pending Gates
- Evidence Location
- Suggested Reviewer Focus
- Suggested Repair Focus
- User Decision Needed

## 5. Completion Criteria

A handoff is acceptable when:

- a fresh Codex session can identify the project, phase, task, and mode;
- the next session knows what to read first;
- the next session knows what not to do;
- candidate, reviewed, approved, active, and installed states are not confused;
- the next action is concrete;
- user gate requirements are explicit;
- the handoff does not become a new authority source.

## 6. Temporary Template

```markdown
# Handoff: [Short Name]

Status: candidate
Approved: false
Installed: false

## Project

- Root:
- Name:
- Current phase:
- Current task:
- Current mode:

## User Origin

[1-3 sentences. Link source if available.]

## Current Objective

[What we are trying to do now.]

## Allowed

- ...

## Forbidden

- ...

## Must Read

- `[path]`: [why]

## Current Artifacts

Candidate:
- ...

Reviewed:
- ...

User-approved:
- ...

Active:
- ...

Evidence:
- ...

## Key Decisions

- [decision] | status: [candidate/active/etc.] | source: [path]

## Open Questions

- [question] | owner: [user/Codex] | impact: [why it matters]

## Risks

- ...

## Next Session First Step

[One concrete first action.]

## Startup Prompt

```text
[Copyable prompt]
```
```

