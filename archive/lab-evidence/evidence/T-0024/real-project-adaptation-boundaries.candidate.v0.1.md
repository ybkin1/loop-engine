# Real Project Adaptation Boundaries Candidate v0.1

## Purpose

Define how the T-0024 quality governance loop adapts to real project context
without entering or modifying a real project before a separate explicit gate.

## Adaptation Inputs

- Product/domain type and business criticality.
- User segments and primary workflows.
- Architecture type and integration surfaces.
- Data classification and privacy obligations.
- Security surface: auth, permissions, external input, file upload, secrets,
  payment, production data, or third-party APIs.
- Delivery target: prototype, internal tool, beta, production release, or
  regulated delivery.
- Team capacity and environment availability.

## Risk Tiers

- Tier 0: documentation-only or trivial change; lightweight self-check may be
  enough if project rules allow it.
- Tier 1: low-risk feature with no sensitive data and limited integration;
  require scenario plan and focused tests.
- Tier 2: user-facing or integration-heavy feature; require full plan audit,
  scenario traceability, independent review, and report evidence.
- Tier 3: security, PII, payment, database, migration, permission, production
  data, deployment, or rollback risk; require separate explicit high-risk
  gates and security/data/deployment evidence.

## Artifact Profile Matrix

| Tier | Applies When | Required Evidence | Optional Evidence | Independent Review | Subagent Review | Minimum Tests | Minimum Traceability | Exit Criteria | Promotion Triggers |
|---|---|---|---|---|---|---|---|---|---|
| Tier 0 | Documentation-only, typo, comment, formatting, or trivial non-runtime change with no user-facing behavior and no high-risk surface | task note, changed-path list, self-check result, boundary statement | screenshot or rendered preview if useful | Not required unless project rules require it | Not required | Read-only/render check or no-test rationale | Link change to task and affected artifact | Change is reviewed by main thread, no high-risk surface exists, and no behavior claim is made | Any runtime behavior, user-facing behavior, integration, data handling, security, permission, deployment, or unclear impact |
| Tier 1 | Low-risk feature or local behavior change with no sensitive data, no privileged action, and limited integration | scenario plan, focused test evidence, changed-path list, risk note, rollback or recovery note if applicable | lightweight peer/AI review, screenshots, manual test notes | Recommended for user-facing or acceptance-sensitive changes | Not required by default | Focused automated or manual tests for touched scenarios | Requirement -> scenario -> touched surface -> evidence | Required focused scenarios pass, no open P0/P1, residual risk is documented | Cross-module impact, external dependency, auth/data/security concern, repeated failure, unclear acceptance, or release readiness claim |
| Tier 2 | User-facing, integration-heavy, workflow, API/backend, data/reporting, or acceptance-critical work without Tier 3 high-risk action | full test plan, plan audit, scenario traceability, independent review, test report, review report, audit report, final quality verdict | subagent read-only review, performance/accessibility/security-focused checks as relevant | Required | Optional but recommended for broad surfaces | Scenario-based automated and/or manual tests covering P0/P1 and representative P2 | Business goal -> requirement -> scenario -> code surface -> test evidence -> finding -> acceptance decision | P0/P1 scenarios covered, reports complete, no open blocking P0/P1, residual risk has user decision boundary | Any high-risk action, production data, deployment/release/rollback, database/permission/secret/payment/migration, or unresolved P0/P1 |
| Tier 3 | Security, PII, payment, database, migration, permission, production data, deployment, release, rollback, secrets, regulated delivery, or irreversible risk | separate explicit high-risk gate, security/data/deployment evidence, full traceability, independent review, final quality verdict, rollback/recovery plan where relevant | subagent reviews by domain, threat model, load/performance evidence, migration dry-run evidence | Required | Recommended when the scope is broad or specialized | Full scenario, regression, and risk-specific tests appropriate to the action | Complete chain plus gate IDs and user decisions for high-risk boundaries | User approves required high-risk gates, evidence closes P0/P1 risks, rollback/recovery is documented, and no forbidden action remains unapproved | Any missing high-risk approval, unresolved blocker, unsafe data condition, weak rollback, or unclear user/business decision |

Tier rules:

- Tier 0 and Tier 1 are lightweight paths only; they do not bypass explicit
  gates for high-risk actions.
- Security, permission, database, payment, production-data, migration,
  deployment, rollback, secret, regulated, or irreversible-risk content must
  promote to Tier 3 or require a separate explicit gate before action.
- If a task starts at Tier 0 or Tier 1 and discovers P0/P1 impact, external
  integration, sensitive data, or unclear acceptance criteria, it must promote
  before claiming delivery readiness.
- Tier selection is evidence for planning. It is not user approval for
  implementation, release, deployment, rollback, database, permission, secret,
  payment, production-data, or migration action.

## Project Type Adaptation

- SaaS/business system: prioritize role permissions, workflow correctness,
  data integrity, audit trail, and regression selection.
- Consumer frontend: prioritize primary journeys, accessibility, responsive
  behavior, browser/device matrix, analytics sanity, and visual regressions.
- API/backend: prioritize contracts, input validation, auth, persistence,
  idempotency, concurrency, error semantics, and observability.
- Data/reporting: prioritize source lineage, transformation correctness,
  privacy, sampling, reconciliation, and explainability.
- Mobile/desktop: prioritize lifecycle, offline, permissions, updates, platform
  differences, crash resilience, and device compatibility.
- Infrastructure/deployment: prioritize pipeline evidence, artifact
  immutability, environment parity, smoke tests, rollback planning, and later
  deployment gate separation.

## Forbidden Without Later Gate

This design does not authorize:

- entering, creating, or modifying a real business project
- writing business code
- implementing checkers, workflows, subagent protocols, runtime behavior, or
  tool behavior
- modifying `AGENTS.md`
- enabling skills, MCP, agents, automations, hooks, plugins, protocols, or
  tool-entry behavior
- build, release, deployment, rollback
- database, permission, secret, payment, production-data, or migration action

## Later Gate Sequence

Recommended future gates, if the user wants to continue:

1. Review-only gate for the T-0024 design package.
2. Repair gate if the review finds blocking gaps.
3. Baseline-consideration gate if the review passes.
4. Implementation-planning gate for lab-local tooling or templates only.
5. Separate implementation gate for any lab-local artifacts.
6. Separate installation/runtime/tool enablement gate if any behavior is to be
   enabled.
7. Separate real-project-entry gate before applying the loop to a real project.
8. Separate delivery/release/deployment/high-risk gates as applicable.
