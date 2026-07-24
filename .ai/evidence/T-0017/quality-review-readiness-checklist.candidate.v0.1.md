# Quality Review Readiness Checklist Candidate v0.1

Status: candidate evidence only
Task: T-0017

## Purpose

Define the checklist for reviewing the T-0017 package or a future real-project
design baseline.

## Lifecycle

- [ ] Artifact status is explicit.
- [ ] Candidate, approved, active, installed, and implementation-ready are not
  mixed.
- [ ] User approval gate remains separate.
- [ ] Installation/runtime/tool gate remains separate.
- [ ] Real-project application remains separately gated.

## Artifact Coverage

- [ ] package index exists
- [ ] lifecycle model exists
- [ ] stage artifact matrix exists
- [ ] real-project entry protocol exists
- [ ] product discovery protocol exists
- [ ] domain/PRD protocol exists
- [ ] architecture governance exists
- [ ] detailed design package exists
- [ ] implementation readiness gate exists
- [ ] review and quality gates exist
- [ ] boundary/risk rules exist
- [ ] traceability/evidence schema exists
- [ ] handoff/evidence protocol exists
- [ ] residual risk register exists

## Engineering Gate Coverage

- [ ] architecture nodes precede work packets
- [ ] PRD has verifiable acceptance criteria
- [ ] architecture has node traceability
- [ ] detailed design can support implementation planning
- [ ] dev plan avoids coarse work packet names
- [ ] testing strategy is linked to packets and acceptance
- [ ] security/data risks are explicit
- [ ] deployment/rollback are separately gated

## Review Coverage

- [ ] value gate reviewed
- [ ] professional gate reviewed
- [ ] contract gate reviewed last
- [ ] no self-review for Standard/Complex future work
- [ ] zero-finding review explains what was checked
- [ ] unresolved P0/P1 absent
- [ ] major P2 repaired or explicitly deferred

## T-0017 Specific Hard Fails

- [ ] Does not claim real-project entry approval.
- [ ] Does not claim build approval.
- [ ] Does not modify AGENTS.md.
- [ ] Does not enable tool/runtime behavior.
- [ ] Does not authorize high-risk actions.
- [ ] Does not treat subagents as gate approvers.
