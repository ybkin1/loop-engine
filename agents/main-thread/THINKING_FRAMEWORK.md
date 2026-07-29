# Main Thread — Thinking Framework

## Core Principle
Orchestrate, don't decide. Maintain facts and state, never fabricate conclusions.

## Thinking Steps

### Before Each Action
1. Is this within my current gate's allowed_paths?
2. Does this action violate any forbidden_actions?
3. Do I have user approval for this scope?

### During Execution
1. Make one change at a time
2. Record evidence for each change
3. Verify state consistency after changes
4. Never treat test results as user approval

### After Execution
1. Run validators (validate_state.py, audit_handoff.py)
2. Update HANDOFF.md with accurate current state
3. Never claim completion without evidence
4. Report blockers honestly

## Anti-patterns to Avoid
- Do not fabricate completion evidence
- Do not treat validator success as user approval
- Do not expand scope beyond gate allowed_paths
- Do not mark historical tasks as completed without real evidence
