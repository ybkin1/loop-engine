# Lifecycle Transition Recommendation v0.1

Status: evidence
Task: T-0011

## Recommendation

Recommend lifecycle transition:

```text
repaired -> baseline_candidate
```

Artifact package:

```text
T-0010 repaired Loop engineering method candidate package
```

## Basis

- T-0009 P1 findings are verified as repaired.
- Major T-0009 P2 findings are accepted or explicitly deferred.
- T-0011 rerun found no P0 and no unresolved P1.
- Candidate-only, baseline approval, active reference, installed behavior, and real-project application remain separated.

## Required Later User Gate

The next user decision must be a separate baseline approval gate if the user wants to approve the method as a baseline.

## Forbidden Interpretations

- `baseline_candidate` is not `baseline_approved`.
- `baseline_candidate` is not `active_reference`.
- `baseline_candidate` is not `installed`.
- `baseline_candidate` does not modify `AGENTS.md`.
- `baseline_candidate` does not authorize real-project entry, implementation, deployment, rollback, migration, permission changes, secrets, payment actions, or production-data actions.
