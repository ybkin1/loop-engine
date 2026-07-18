# Neutral Audit Charter And Assurance Schemas v0.2

Charter ID: `NAC-2026-07-16-R1`. Satisfies `OUT-05` and contributes to `WS-05` and `WS-06`.

## 1. Mission And Neutrality Boundary

Audits assess claims against canonical requirements and evidence. Neutrality means no preference for author, schedule, prior PASS, sunk cost, or desired narrative. It does not mean neutrality toward user authority, approved baselines, real product delivery, evidence integrity, or safety/liveness obligations.

Auditors may report findings and verdict evidence. They may not edit subject artifacts, approve gates, accept risk, create requirements, commit effects, close tasks, or infer user acceptance.

## 2. Independence Rules

- `NAC-I01`: A producer cannot be the sole auditor of its own artifact.
- `NAC-I02`: Audit context includes canonical requirements, immutable subject hashes, scope, and allowed verdict schema; it excludes hidden author persuasion.
- `NAC-I03`: Audit execution begins only after writers stop and subject hashes are fixed.
- `NAC-I04`: Every finding cites requirement IDs and disk evidence.
- `NAC-I05`: Missing evidence is not a negative claim; use `UNVERIFIED` or `BASELINE_MISSING`.
- `NAC-I06`: Review PASS is evidence only and cannot transition gate, acceptance, installation, activation, or closeout state.
- `NAC-I07`: Conflicts of interest, shared generation/context, or prior authorship are declared.

## 3. Audit Inputs

```yaml
audit_subject:
  audit_id: string
  subject_manifest: [{path: string, sha256: string, size: integer}]
  requirements_revision: string
  coverage_matrix_ref: string
  protected_baselines: [BaselineRef]
  allowed_review_scope: [string]
  forbidden_actions: [string]
  assurance_profile: AssuranceProfile
  role_overlays: [RoleOverlayRef]
  prior_findings: [FindingRef]
  declared_independence: IndependenceDeclaration
```

## 4. Professional Role Overlays

| Overlay ID | Questions | Hard-fail examples |
|---|---|---|
| `ROLE-PRODUCT` | Does the design reduce user burden and serve observable software delivery? | Governance substitutes for product outcome; user role silently expanded. |
| `ROLE-ARCH` | Are boundaries, dependencies, state ownership, recovery, and compatibility coherent? | Circular authority; ambiguous canonical owner; unrecoverable state. |
| `ROLE-TECH` | Are technology assumptions explicit, bounded, and replaceable? | Invented technology baseline; hidden runtime dependency. |
| `ROLE-API` | Are schemas versioned, validated, compatible, and hard to misuse? | Unknown-field acceptance; inconsistent errors; implicit breaking change. |
| `ROLE-CODE` | Are coding/style/golden references explicit rather than invented? | Missing baseline treated as PASS; style drift ignored. |
| `ROLE-QA` | Do acceptance and tests trace to every requirement and failure path? | Scenario names without deterministic oracle; missing negative tests. |
| `ROLE-SEC` | Are authority, input, path, evidence, secret, and injection boundaries fail-closed? | Gate bypass; path escape; untrusted text treated as instruction. |
| `ROLE-PERF` | Are context, time, agent, storage, and repair budgets bounded? | Unbounded retry/audit loop; no closeout reserve. |
| `ROLE-DELIVERY` | Are build/install/activate/deploy/rollback boundaries separated? | Design approval triggers runtime effect. |
| `ROLE-PROJECT` | Are progress, dependencies, roadmap, and blockers truthful? | Downstream task auto-created; status upgraded without authority. |
| `ROLE-HANDOFF` | Can a fresh successor recover protected semantics within budget? | Missing active transaction; stale next action; unsigned checkpoint. |
| `ROLE-CONTINUITY` | Are step/anchor/goal drift and re-anchor rules complete? | Local coherence hides goal drift; baseline revision conflict ignored. |

Profiles select overlays by risk; `ROLE-PRODUCT`, `ROLE-ARCH`, `ROLE-QA`, `ROLE-SEC`, and `ROLE-CONTINUITY` are mandatory for controller/continuity review.

## 5. `AssuranceProfile/v1.0`

```yaml
AssuranceProfile:
  profile_id: string
  level: A0|A1|A2|A3
  risk_dimensions:
    authority: low|medium|high|critical
    scope: low|medium|high|critical
    security: low|medium|high|critical
    continuity: low|medium|high|critical
    reversibility: low|medium|high|critical
    user_impact: low|medium|high|critical
  mandatory_roles: [string]
  mandatory_checks: [string]
  adversarial_vectors: [string]
  independence_level: self_check|separate_role|fresh_context|external
  evidence_depth: summary|artifact|cross_file|end_to_end
  pass_rule: string
  escalation_rule: string
```

| Level | Minimum assurance |
|---|---|
| `A0` | Deterministic syntax/schema checks only; never sufficient for task PASS. |
| `A1` | Producer self-check plus deterministic requirement coverage. |
| `A2` | Separate-role review with risk overlays and adversarial vectors. |
| `A3` | Fresh-context independent audit, protected hashes, full coverage, recovery and goal re-anchor. |

## 6. `Finding/v1.0`

```yaml
finding:
  finding_id: string
  severity: P0|P1|P2|P3
  confidence: confirmed|probable|uncertain
  category: string
  requirement_ids: [string]
  role_overlay: string
  statement: string
  evidence_refs: [{path: string, locator: string, sha256: string|null}]
  reproduction: [string]
  impact: string
  blocked_effects: [string]
  recommended_disposition: repair|user_decision|accept_risk|reject|observe
  status: open|accepted_for_repair|resolved_pending_review|verified|rejected|superseded
```

Severity:

- `P0`: authority/safety/data-integrity breach or irreversible uncontrolled effect; verdict `BLOCKED`.
- `P1`: foundational contract/coverage/correctness gap blocking downstream consideration; `REPAIR_REQUIRED`.
- `P2`: material quality/test/clarity gap that must be repaired or explicitly accepted before implementation consideration.
- `P3`: improvement with no current blocking effect.

## 7. `Verdict/v1.0`

```yaml
verdict:
  verdict_id: string
  subject_hash: string
  requirements_revision: string
  assurance_profile_id: string
  coverage_complete: boolean
  value: PASS|REPAIR_REQUIRED|BLOCKED|USER_DECISION_REQUIRED|SCOPE_VIOLATION
  blocking_findings: [string]
  unresolved_findings: [string]
  unverified_requirements: [string]
  residual_risk: [Risk]
  evidence_refs: [EvidenceRef]
  reviewer_independence: IndependenceDeclaration
  authority_effect: evidence_only
```

Verdict rules:

- Any P0 -> `BLOCKED`.
- Any unresolved P1 or incomplete required coverage -> `REPAIR_REQUIRED`.
- Conflicting user/business truth or authority -> `USER_DECISION_REQUIRED`.
- Any review action outside scope -> `SCOPE_VIOLATION`.
- `PASS` requires complete profile coverage, no blocking findings, all mandatory evidence, current hashes, and declared independence.

## 8. Audit Procedure

1. Verify fixed subject hashes and review authority.
2. Load canonical requirements and coverage matrix.
3. Select AssuranceProfile and required overlays deterministically.
4. Execute deterministic checks before interpretive review.
5. Review each mapped requirement and adversarial vector.
6. Record findings without editing artifacts.
7. Compute verdict from rules, not narrative preference.
8. Report residual risk, unverified items, and exact next safe action.

## 9. Audit Checks

- `MC-AUDIT-001`: independence declaration completeness.
- `MC-AUDIT-002`: every finding has requirement and evidence refs.
- `MC-AUDIT-003`: severity-to-verdict rule.
- `MC-AUDIT-004`: mandatory role/check coverage from AssuranceProfile.
- `MC-AUDIT-005`: subject hash freshness.
- `ADV-AUDIT-001`: reviewer attempts to approve gate; expected rejection.
- `ADV-AUDIT-002`: prior PASS cited instead of current evidence; expected `REPAIR_REQUIRED`.
- `ADV-AUDIT-003`: missing baseline treated as no defect; expected `BASELINE_MISSING` finding.

## 10. Boundary

This charter does not perform the fresh independent L0 review. That review requires a later separate pending review Gate after repair execution stops.
