# Loop Product Baseline v0.1

## Product Statement

Loop is an independent or pluggable external Agent engineering control and
delivery system for AI coding hosts. It identifies when an intent requires
large-project engineering discipline, routes the work into a complete Loop,
and blocks or truthfully reports unsupported shortcuts.

## First Release Boundary

The first release must prove a complete controlled delivery path on
`loop-engineering-lab` itself. It does not need to support every host or every
technology stack before the core lifecycle is proven.

## Required Product Capabilities

- intent classification and full-Loop routing;
- durable requirements, architecture, task, role, quality, evidence, and Gate
  state;
- role and phase loops with explicit contracts;
- workspace and command enforcement with declared capability levels;
- deterministic test, lint, type, build, architecture, and security checks;
- independent review, repair, regression, and stale-evidence detection;
- human-readable phase delivery packets;
- independent operation and host-adapter interfaces;
- cross-session recovery from durable documents and machine state;
- cost, rework, and escaped-defect measurement.

## User Responsibility

The user supplies intent, business truth, key tradeoffs, risk acceptance, and
Gate decisions. The user does not inspect source code or make technical
quality judgments.

## Product Proof

The first product proof is a self-hosted vertical slice that includes a real
code change, at least one seeded or adversarial defect, deterministic checks,
independent review, repair and regression, and a phase packet that the user
can read without understanding the implementation.

## Durable Memory Rule

No product fact is valid only because it appears in chat or HANDOFF. New
sessions must recover product identity from `.ai/PROJECT.md`, architecture from
`.ai/ARCHITECTURE.md`, contracts from `.ai/CONTRACTS.md`, acceptance from
`.ai/ACCEPTANCE.md`, quality from `.ai/QUALITY_GATES.md`, decisions from
`.ai/DECISIONS.md` and `docs/decisions/`, issues from `.ai/KNOWN_ISSUES.md`,
progress from `.ai/PROGRESS.md`, and current authority from `.ai/state.yaml`,
`.ai/gates.yaml`, and `.ai/task_graph.yaml`.
