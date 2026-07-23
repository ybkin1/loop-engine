# Commands For T-0032

- Read required governance records and necessary T-0030/T-0031 evidence.
- Ran `validate_state.py` before registration; exit code `2` with exactly six preserved historical mismatches.
- Ran `audit_handoff.py` before registration; exit code `2` with exactly six preserved historical mismatches.
- Created T-0032 registration records and a pending gate only.
- Ran both validators after registration; each returned exit code `2` with only the expected T-0032 pending-gate blocker plus the six preserved historical mismatches.
- Recorded the user's explicit gate approval and stopped without executing T-0032 or creating T-0033.
- Ran post-approval read-only validation and HANDOFF audit; both reported only the six preserved historical mismatches.
