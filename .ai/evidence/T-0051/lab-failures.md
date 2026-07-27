# T-0051 residual lab failures

The non-lab suite passes. The legacy lab suite currently reports 63 failures, all in `tests/lab/test_project_governor_consistency.py`. The first failure is setup-time `PROJECT_CONTINUITY_HASH_MISMATCH` after the fixture invokes `close_session.py`; subsequent failures cascade from that fixture setup and from historical contracts that still require the previous two-step approval semantics.

These failures are not classified as passed or ignored. They remain an explicit compatibility work item for the next P0 migration slice. No full-suite green claim is made.
