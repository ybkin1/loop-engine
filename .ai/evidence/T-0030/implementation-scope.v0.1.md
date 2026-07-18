# Implementation Scope - T-0030

After approval and explicit execution request only:

1. Add shared parsing, immutable snapshots, invariants, transition matrix, and atomic recovery support.
2. Keep task status and gate authorization authoritative; keep task graph and HANDOFF as projections.
3. Make closeout preserve lifecycle state and validate before writing.
4. Detect cross-artifact and semantic HANDOFF contradictions.
5. Enforce five mutually exclusive action modes and add regression fixtures.

Excluded: historical repair, installation, activation, subagents, agent loops, runtime/tool enablement, `AGENTS.md`, real projects, deployment, and high-risk resources.
