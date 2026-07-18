# Test And Acceptance Plan - T-0030

- Closeout preserves every lifecycle state, especially `completed`.
- Validator detects T-0028-style mismatch with stable nonzero exit code.
- Handoff audit detects semantic mismatch and stale or unauthorized next actions.
- Gate approval and execution remain separate transitions.
- Five action modes are mutually exclusive.
- Partial writes have deterministic recovery or rollback.
- Existing valid workflows and CLI contracts continue to pass.
- No historical record is silently rewritten and all evidence is retained.
