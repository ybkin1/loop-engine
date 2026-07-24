# T-0036 HANDOFF Strict Semantic Classification Registration Commands v0.1

1. Read the current project state, task, Gate register, HANDOFF, and protected source records.
2. Confirm `T-0036` is completed and no Gate is pending before registration.
3. Recompute protected source and global target SHA-256 fingerprints.
4. Register `G-HANDOFF-STRICT-SEMANTIC-CLASSIFICATION-REPAIR-V0-1` as `pending`.
5. Point `.ai/state.yaml.current_gate_id` to the new pending Gate.
6. Add registration evidence under `.ai/evidence/T-0036/`.
7. Do not modify global target scripts during registration.
8. Stop before approval or execution.
