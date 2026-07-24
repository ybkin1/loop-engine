# T-0036 HANDOFF Semantic Anchoring Execution Test Results v0.1

## Focused Semantic Suite

Command:

`C:\Python312\python.exe -B C:\Users\Administrator\.codex\skills\project-governor\scripts\test_handoff_semantic_anchoring.py`

Result: exit `0`, `10/10`, no failures or errors.

Coverage includes exact anchor emission, swapped values, current-topic substitution, paraphrase, Gate constraint misclassification, misplaced fields, missing Project Anchors, authoritative-source drift, repeated closeout determinism, and pending-gate blocking.

## Existing Regression Subsets

- Candidate `transaction`: `4/4`, exit `0`.
- Candidate `close_session`: `3/3`, exit `0`.
- Candidate `audit_handoff`: `7/7`, exit `0`.
- Candidate `validate_state`: `3/3`, exit `0`.
- Candidate `action_mode`: `1/1`, exit `0`.

All test runs used `-B`; no compiled test artifacts were created.
