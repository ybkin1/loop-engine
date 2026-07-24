# Amendment Pre-Approval Validation - T-0032

- `validate_state.py`: exit code `2`; only the target amendment pending-gate blocker plus the six preserved historical status mismatches.
- `audit_handoff.py`: exit code `2`; only the same pending-gate blocker plus the six preserved historical status mismatches.
- The original gate remained approved, the amendment gate was the sole pending gate, T-0032 remained active and unexecuted, and T-0033 through T-0039 did not exist.
