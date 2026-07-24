# Traceability And Evidence Chain Candidate v0.1

## Purpose

Define the traceability chain from business goal to requirement, scenario,
code, test, finding, and acceptance.

## Required Chain

```text
business_goal -> requirement -> scenario -> code_surface -> test_evidence -> finding -> acceptance_decision
```

## Entity IDs

- `BG-###`: business goal or business outcome.
- `REQ-###`: requirement or acceptance condition.
- `SC-###`: user, system, security, operational, or lifecycle scenario.
- `CS-###`: code surface, API, module, data object, config, or UI surface.
- `TE-###`: test evidence, manual evidence, command output, or screenshot.
- `FIND-###`: defect, quality gap, evidence gap, or residual risk.
- `ACC-###`: acceptance or user decision item.

## Minimum Matrix

```yaml
traceability_matrix:
  - business_goal_id: BG-001
    requirement_id: REQ-001
    scenario_id: SC-001
    scenario_type: happy_path | error_path | edge_case | security | operational | lifecycle
    priority: P0 | P1 | P2 | P3
    code_surfaces:
      - CS-001
    test_evidence:
      - TE-001
    findings:
      - FIND-001
    acceptance_ref: ACC-001
    status: covered | failed | not_covered | deferred | not_applicable
```

## Closure Rules

- Every P0/P1 requirement must have at least one scenario.
- Every P0/P1 scenario must have code surface mapping or an explicit missing
  implementation finding.
- Every P0/P1 scenario must have test evidence or an explicit approved deferral.
- Every finding must cite impacted scenario(s) and evidence.
- Every acceptance decision must cite the final quality verdict and residual
  risk list.

## Orphan Rules

- Requirement without scenario: plan audit fails.
- Scenario without test evidence: quality verdict cannot be `PASS_FOR_ACCEPTANCE`.
- Code surface without requirement/scenario in Standard/Complex work: review
  must flag possible scope drift.
- Test without scenario: report must mark it as supplemental, not coverage.
- Finding without scenario or evidence: finding is incomplete and cannot close.

## Evidence Chain Storage

For future real-project use, evidence should live under the task or project
artifact directory permitted by the relevant gate. In this lab task, the chain
is only a candidate design and no real-project artifact is created.
