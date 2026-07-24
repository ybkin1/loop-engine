# Enforcement Gap Review v0.1

Status: evidence
Task: T-0018

## Result

FAIL_FOR_BASELINE_CONSIDERATION.

T-0017 is strong as a Markdown governance candidate, but it is not ready for
baseline consideration because the most important controls are not yet
machine-enforced.

## Finding

`FIND-T0018-P1-001`: Markdown-only governance can be skipped by future agents
or sessions unless a later enforcement architecture defines concrete guards.

## Evidence

- T-0017 package index lists a known gap: Markdown rules are not
  machine-enforced validation.
- T-0017 residual risk `RR-T0017-005` records this as a known P2 risk.
- `gate-register.md` describes the stronger mechanism needed: pending items
  must mechanically block phase progression until resolved.
- Current project validation proved pending user gates can block work through
  `validate_state.py`, but T-0017 does not define equivalent enforcement for
  PRD completeness, architecture node coverage, work-packet traceability,
  security/data checks, deployment/rollback separation, or tool-entry
  restrictions.
- T-0017 identifies future skill, MCP, wrapper, policy guard, and tool-entry
  restriction possibilities, but does not design their lifecycle, target
  paths, failure modes, allowed commands, rollback behavior, or validation
  evidence.

## Impact

Without an enforcement layer, future real-project work still depends on the
assistant remembering and obeying Markdown rules. That is acceptable for a
candidate package, but not for baseline promotion, installation, or real-project
application.

## Required Repair Direction

Open a later separate design/repair task, likely `T-0019`, for enforcement
architecture. It should define:

- machine-readable gate register shape for each lifecycle stage
- mandatory checker catalog and blocking semantics
- policy guard or wrapper behavior for real-project entry and high-risk tools
- startup validation that detects pending gates and missing required evidence
- tool-entry restrictions for deployment, rollback, DB, permissions, secrets,
  payment, production data, migrations, `AGENTS.md`, skill/MCP/runtime/tool
  enablement
- evidence schema for checker execution and unavailable-checker handling
- rollback/recovery plan for any future installed guard

## Boundary

This review does not install or enable any enforcement layer.
