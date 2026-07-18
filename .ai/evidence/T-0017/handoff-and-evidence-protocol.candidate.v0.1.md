# Handoff And Evidence Protocol Candidate v0.1

Status: candidate evidence only
Task: T-0017

## Purpose

Keep real-project work resumable without letting handoff become an authority
source or importing stale history into a new task.

## Handoff Required Fields

- current phase
- current task
- current gate
- lifecycle state
- allowed scope
- forbidden scope
- recent changes
- verified items
- unverified items
- evidence location
- integration impact
- quarantined examples or old product cases
- pending gates and blockers
- next session first step
- copyable startup prompt

## Evidence Required Fields

Each evidence record should include:

- task ID
- timestamp
- source request or gate
- commands run
- files read or changed
- validation result
- review result if any
- boundary confirmation
- residual risks

## Contamination Controls

- Handoff cannot grant permission.
- Handoff cannot override state, gate records, or task files.
- Old product examples must be labeled as examples or quarantined context.
- Historical approvals must not be copied forward unless the current gate
  references them explicitly.
- Stable decisions belong in stable memory or evidence, not only in handoff.

## Closeout Checklist

- [ ] `validate_state.py` passes.
- [ ] No unintended pending gate remains.
- [ ] Current task status matches `state.yaml`.
- [ ] PROGRESS and HANDOFF describe the current task, not a stale task.
- [ ] Evidence paths are listed.
- [ ] Next step is a gate, review, repair, or pause.
- [ ] Forbidden scope is explicit.
