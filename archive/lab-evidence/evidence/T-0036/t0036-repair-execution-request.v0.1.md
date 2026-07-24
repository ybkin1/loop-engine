# T-0036 Repair Execution Request v0.1

Gate: `G-T-0036-REPAIR-INDEPENDENT-REVIEW-FINDINGS-V0-1`

Recorded at: `2026-07-20T13:45:45.0935674+08:00`

Exact user message:

`执行已批准的 G-T-0036-REPAIR-INDEPENDENT-REVIEW-FINDINGS-V0-1`

Decision: execute the already approved bounded repair.

This evidence authorizes only the approved isolated-candidate repair execution. It does not authorize installation, activation, host identity integration, live structured-state provisioning, controller/agent/runtime enablement, fresh independent rereview, T-0037, or real-project entry.

F001/F002 execution target remains `SECURELY_ISOLATED_AUTHORITY_LIFECYCLE_UNAVAILABLE`: fail-closed isolation is required, and production authority lifecycle availability must remain false. Installation eligibility remains `BLOCKED`.

The execution must stop before fresh independent rereview and must preserve `.ai/PROJECT.md`, `.ai/CONTRACTS.md`, both T-0034 contracts, `NOT_INSTALLED`, and `NOT_ACTIVATED` byte-for-byte.
