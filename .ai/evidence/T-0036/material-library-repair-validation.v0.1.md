# T-0036 F-001..F-006 Repair Validation v0.1

Gate: `G-T-0036-REPAIR-F001-F006-V0-1`
Verdict: `repair_completed_awaiting_fresh_independent_rereview`

## Acceptance matrix

| check | result |
| --- | --- |
| catalog material count | `46` |
| authority enum violations | `0` |
| source register canonical records | `46/46` |
| Markdown projection IDs | `46/46` |
| catalog/register/Markdown status conflicts | `0` |
| freshness required-key closure | `46/46` |
| HTTP/local access split | `44/2` |
| coverage IDs | `46/46`, missing `0`, extra `0` |
| phase-profile resolution | `1/1`, closure `100%` |
| project/phase material subset | `8 < 17`, strict subset `true` |
| project/phase template subset | `7 < 9`, strict subset `true` |
| simulation markers | `simulation_only=true`, `planned_not_executed=true` |
| YAML structural parse | PASS, 12 repaired/governance files |
| focused deterministic tests | PASS, 28 passed |
| full pytest suite | 40 passed, 6 existing unrelated failures |
| validate_state.py | PASS |
| git diff --check | PASS |

## Final freeze checks

- Old independent-review freeze after repair: `58` records; `9` changed paths, all explicitly allowlisted repair objects; protected unchanged paths `49/49`.
- New post-repair freeze: `65` records, `65/65` matching, mismatches `0`.
- Old independent-review evidence and old freeze manifest remained byte-for-byte unchanged.

## Freshness evidence

Canonical register: `materials/source-register.yaml`

- run ID: `T0036-REPAIR-F006-20260724T1325`
- run window: `2026-07-24T13:31:48+08:00` to `2026-07-24T13:32:43+08:00`
- 46 records each contain `retrieved_at`, `http_status`, `final_url`, `page_title`, `failure_reason`, `verification_status`, and `source_observation`.
- 37 records are `content_read`, 2 are `url_verified_only`, and 7 are `access_blocked`.
- 9 records retain non-none failure reasons; no failure was upgraded to `content_read`.
- Local LOOP records use `http_status=null` and `final_url=not_applicable`.

## Full-suite limitation

The repository-wide suite failed only in six existing `candidates/T-0030-project-governor-repair` consistency tests because the fixture is missing the authoritative `AGENTS.md:24` anchor. The focused `tests/codex_loop` suite passed 28/28. No forbidden path was changed to address the unrelated failure.

## Boundary

This validation is evidence for the repair Gate, not independent rereview or baseline acceptance. The old 58-input freeze and old independent-review evidence remain immutable. Repair execution stops after the new freeze manifest is generated.
