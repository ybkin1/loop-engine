# T-0036 HANDOFF Strict Semantic Classification Execution Test Results v0.1

Gate: `G-HANDOFF-STRICT-SEMANTIC-CLASSIFICATION-REPAIR-V0-1`

## RED

The pre-repair semantic suite passed its original `10/10` older four-anchor tests, but the newly added five-part tests failed because the pre-repair generator emitted no `Semantic Classification` section and the auditor did not validate those fields.

## GREEN

Focused semantic regression:

```text
C:\Python312\python.exe -B C:\Users\Administrator\.codex\skills\project-governor\scripts\test_handoff_semantic_anchoring.py
Ran 18 tests in 15.408s
OK
exit=0
```

Coverage includes canonical five-field presence/order, merged fields, swapped fields, missing fields, paraphrase drift, stale completed-task title contamination, explicit current-direction persistence, repeated regeneration, legacy anchor compatibility, source drift, misplaced anchors, and pending-gate blocking.

Project governance tests:

```text
C:\Python312\python.exe -B .ai\tests\test_governance_checks.py
Ran 8 tests in 0.096s
OK
exit=0
```

Target scripts compiled successfully with `py_compile` exit `0`.
