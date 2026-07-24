# Codemap

## Important Paths

- `.ai/checkers/run_governance_checks.py`: governance check entry point.
- `.ai/checkers/validate_gate_register.py`: core gate register validator.
- `.ai/guards/policy_guard.py`: runtime policy guard decision engine.
- `.ai/schemas/`: JSON Schema definitions for checker results and gate register.
- `.ai/policies/tool-entry-restrictions.yaml`: tool entry restriction policies.
- `.ai/tests/`: governance check and guard tests with sample fixtures.

## Ownership Boundaries

- `.ai/` checkers, guards, schemas, and policies require a separate implementation gate before modification.
- Project-local `.ai/` records may document governance facts but do not install or enable Skill/runtime behavior.
