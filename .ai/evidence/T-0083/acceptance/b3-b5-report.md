# B3 + B5 Acceptance Report — MCP capability model + legacy gate approval_actor migration

- **Task**: T-0083
- **Gate**: G-T-0083-REQUIREMENTS
- **Role**: security-engineer
- **Actor**: zcode-actor-1ebd8d10ce8a
- **Date**: 2026-07-31
- **Scope**: B3 (gap-analysis §3.8 MCP capability model) + B5 (legacy gate `approval_actor` data migration)

## 1. B5 — Legacy gates missing approval_actor (data migration, low risk)

### What was implemented
`.ai/gates.yaml` had 76 gates; 24 approved gates (the 2026-07-06/07 legacy era, T-0002…T-0072
cohort) predated the `approval_actor` / `approval_source` fields. For each of those 24 gates the
following two fields were added immediately after `decision: approved`:

```yaml
approval_actor: user
approval_source: legacy_pre_field
```

- `approval_actor: user` — these gates were all user-approved (approval_text/evidence confirm it);
  the field was simply absent because it predated the schema field.
- `approval_source: legacy_pre_field` — honest provenance: the decision predates the
  `approval_source` taxonomy (`explicit_user_message` etc.), so the source is marked as a
  pre-field legacy approval rather than pretending it was an explicit modern recorded message.

### Before/after
- **Before**: 52/76 approved gates carried `approval_actor`; 24 approved gates carried neither
  `approval_actor` nor `approval_source` (gates G-T-0002-APPROVE-V0.2.1 through G-T-0072-DEPLOY-QUALITY).
- **After**: 76/76 approved gates carry `approval_actor`; the 24 migrated gates carry
  `approval_source: legacy_pre_field` (4 newer gates — G-T-0066/G-T-0067/G-T-0069/G-T-0070 — already
  had `approval_actor: user` but no `approval_source`; they were NOT touched, see limitations).

### Migration mechanics
Text-level insertion (byte-preserving for everything else): a script tracked each `- id: <GID>`
block and inserted the two lines after the exact `  decision: approved` line. YAML validity was
verified with `yaml.safe_load` after the edit (76 gates, all 24 annotated, `bad: []`).
No decisions, statuses, or recorded_at timestamps were changed.

### Verification
`validate_state.py` initially reported `PROJECT_CONTINUITY_SOURCE_DRIFT: .ai/gates.yaml` (expected —
the gate register is a continuity source and legitimately changed). Running the sanctioned repair
(`validate_state.py --repair` → `repair_continuity`) refreshed the continuity hashes; the final
validate_state run reports `[ok] state is usable` (see §4).

## 2. B3 — MCP tool capability model (gap-analysis §3.8)

### Background
T-0082 closed the Node-REPL bypass by fail-closing **all** `mcp__*` tools in FULL/STANDARD mode
(no capability model existed to unblock them). Gap-analysis §3.8: "MCP / side-effect tools are
unusable in FULL mode (capability gap)" — legitimate MCP use became impossible. B3 implements the
recommended fix direction: "an explicit MCP tool allow-list in the task contract".

### 3a — Task contract allow-list parsing (`hooks/scripts/loop_enforcement.py`)
`load_task_contract()` (the task-contract parser used by the hook) now parses the optional
`mcp_allowed_tools` field, in three forms:

1. inline flow list — `mcp_allowed_tools: [mcp__node_repl__js, mcp__other__x]`
2. block list — `mcp_allowed_tools:` followed by `- mcp__node_repl__js`
3. 基本信息 markdown-table row — `| mcp_allowed_tools | mcp__node_repl__js |`
   (the canonical front-matter form used by T-0082.md / T-0083.md)

Default: field absent → empty list → no MCP tools allowed (the fail-closed default stays).
A dedicated helper `_task_mcp_allowed_tools(root, task_id)` returns the list (empty when the task
file is missing).

### 3b — Enforcement wiring
The `mcp__` branch in `main()` is now:

```python
if tool_name.startswith("mcp__"):
    if not task_id:
        ...return EXIT_BLOCK   # unchanged: DISPATCH_REQUIRED
    mcp_allowed = _task_mcp_allowed_tools(root, task_id)
    if tool_name not in mcp_allowed:
        logger.warning("BLOCKED: mcp__ tool %s not in task %s allowed list", tool_name, task_id)
        return EXIT_BLOCK
    # fall through to identity/DISPATCH gates
```

Deviation from the mission sketch, noted honestly: the sketch's format string used `T-%s` with
`task_id`, but `state.current_task_id` already carries the `T-` prefix ("T-0001"), which would
render "T-T-0001". The implemented message uses plain `%s`.

### 3c — Task files wired
- `.ai/tasks/T-0083.md`: `| mcp_allowed_tools | mcp__node_repl__js |` added to the 基本信息 table
  (Node REPL authorized for governance diagnostics).
- `.ai/tasks/T-0082.md`: same row added for consistency (historical).

### 3d — Tests (`tests/test_mcp_capability.py`, 13 tests)
Mission cases 1–4 all covered, plus parser-form coverage:

| Case | Test | Result |
|---|---|---|
| 1. mcp__ without task → BLOCK | `test_mcp_tool_without_task_blocks` | PASS (exit 2, DISPATCH_REQUIRED message) |
| 2. mcp__ with task, not in allow-list → BLOCK | `test_mcp_tool_with_task_not_in_allowlist_blocks`, `test_mcp_tool_with_task_but_other_tool_allowed_blocks` | PASS (exit 2, allow-list message) |
| 3. mcp__ with task AND in allow-list → passes mcp gate | `test_mcp_tool_in_allowlist_passes_mcp_gate` (+ table-row and block-form variants) | PASS (no mcp-specific block message) |
| 4. task file without field → all mcp__ blocked | `test_task_without_mcp_allowed_tools_blocks_all_mcp` | PASS (3 tools, all exit 2) |
| parser unit tests | `McpAllowedToolsParser` (6 tests: inline / table / block / absent / missing file / helper) | PASS |

### Real test results (run 2026-07-31)

```
$ python -m pytest tests/test_enforcement.py tests/test_mcp_capability.py -q --tb=short
40 passed in 10.43s   (27 existing enforcement + 13 new capability tests)

$ python -m pytest tests/test_mcp_capability.py -q --tb=short
13 passed in 2.65s
```

No regressions in the existing enforcement suite.

## 3. Honest limitations

1. **End-to-end MCP unblock is not complete.** The allow-list gate passes, but an `mcp__` call
   still falls through to the identity/scope gates; an MCP call has no statically extractable
   target path, so it terminates at the final task-scope gate (`is_in_task_scope(None, contract)`
   is False) unless identity+runtime projection are present and a first-class MCP scope path
   exists. The mission's test spec anticipated this ("may still be blocked by other gates") — the
   fully scoped end-to-end MCP path (gap-analysis §3.8 "tool names + allowed args, enforced by a
   new scope check") remains a follow-up. What B3 delivers now is the **capability model itself**:
   explicit per-task grants, fail-closed default, parser, wiring, and tests.
2. **B5 scope**: only the 24 gates missing `approval_actor` were migrated. 4 gates
   (G-T-0066-FINAL-CLEANUP, G-T-0067-EVIDENCE-VERIFIER, G-T-0069-DEPLOYMENT-VERIFICATION,
   G-T-0070-AGENT-INSTALL-FIX) carry `approval_actor: user` but no `approval_source`; they were
   left untouched per the task scope (the migration targets gates missing `approval_actor`).
   A future data-completeness pass could add `approval_source: legacy_pre_field` to them too.
3. **Message wording**: the allow-list block message uses `task %s` (not `T-%s`) to avoid the
   "T-T-0001" duplication (see §3b).
4. The evidence manifest was rebuilt and the HANDOFF structured blocks regenerated from
   structured state after the gates.yaml migration (see §4) — these are consequences of the
   legitimate governance-source change, handled through the sanctioned tools
   (`repair_continuity`, `continuity_producer.build_handoff_model`).

## 4. Final state validation

```
$ python .zcode/tools/validate_state.py <root> --repair   # refreshes continuity hashes
$ python .zcode/tools/validate_state.py <root>
[loop-governance] project_root: C:\Users\Administrator\ZCodeProject\loop-engine
[loop-governance] phase: S6-delivery
[loop-governance] current_task_id: T-0083
[ok] state is usable
```
