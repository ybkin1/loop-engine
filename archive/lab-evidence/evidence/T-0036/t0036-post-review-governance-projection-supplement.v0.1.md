# T-0036 Post-review Governance-projection Supplement v0.1

## Purpose

This additive evidence records the current disk facts for four T-0036 governance
projection files after the independent review closeout. It repairs evidence
freshness only. It does not replace or amend any historical review evidence.

Recorded at: `2026-07-19T19:25:20.5181558+08:00`.

## Historical Anchor

- Review completed at: `2026-07-18T23:55:52.5241301+08:00`.
- Review verdict: `REPAIR_REQUIRED`.
- Historical manifest retained unchanged:
  `.ai/evidence/T-0036/t0036-review-changed-path-manifest.v0.1.md`.
- Historical manifest SHA-256 at supplement preflight:
  `ce8bf10c02d75bcaf914130a7d7ccda23bd6f65bf76f93d422983fae0c29f3de`.

## Current Projection Facts

| Path | Current size | Current SHA-256 | Current mtime_ns | Current local mtime |
|---|---:|---|---:|---|
| `.ai/HANDOFF.md` | 8759 | `d6bc652d9d4860ebe668b86ab2a98dfa7e652db4d7dbf449c65ca023a52567a0` | 1784459302480147500 | `2026-07-19T19:08:22.4801475+08:00` |
| `.ai/state.yaml` | 9832 | `ed2c635b61c84c4c833211857849f7fc967e5b40000f2bf5267d49fcd7f7b2fb` | 1784459377464557800 | `2026-07-19T19:09:37.4645578+08:00` |
| `.ai/task_graph.yaml` | 11099 | `0a19d0db81d113399f702e649ae9a3f60636f11c6a1efaf593097941eb1a9c8a` | 1784459377466557300 | `2026-07-19T19:09:37.4665573+08:00` |
| `.ai/tasks/T-0036.md` | 5082 | `c6caa6469170bf8e860017da97fdaba11d40daf1cf605c635ecc4382b5b4355d` | 1784459377465557300 | `2026-07-19T19:09:37.4655573+08:00` |

All four mtimes are later than the review completion timestamp.

## Difference From Historical Review Manifest

| Path | Historical size | Historical SHA-256 | Current difference |
|---|---:|---|---|
| `.ai/HANDOFF.md` | not embedded | not embedded | The historical manifest explicitly omitted the rendered HANDOFF fingerprint; this supplement supplies its current fingerprint and proves a later mtime. |
| `.ai/state.yaml` | 9868 | `A202D3974DC337C2813B6A446E4F247DAE67022819CE2336F3963451BBA8A03A` | Size is 36 bytes smaller and SHA-256 differs. |
| `.ai/task_graph.yaml` | 11124 | `FCC3A0D02856A29B0650A8233DD1C1878711F77056C3DE60E811D432D4BC07DB` | Size is 25 bytes smaller and SHA-256 differs. |
| `.ai/tasks/T-0036.md` | 4794 | `F7CBED96BFA48DB5D305CDA56A7FD97A7FDE88ABBE95FA8A8A6B160938B635A1` | Size is 288 bytes larger and SHA-256 differs. |

The historical manifest remains a true record of its earlier checkpoint. It is
not a current-disk manifest for these four governance projections.

## Recorded Change Reason And Allowed Scope

The post-review projection updates tightened the governance semantics around
the completed T-0036 review: the verdict remains `REPAIR_REQUIRED`, findings
remain unrepaired, and completion is not installation, activation, project
PASS, user acceptance, or repair authorization. Those updates were confined to
the four projection paths listed above.

This supplement is authorized only to record those facts under
`.ai/evidence/T-0036/`. No candidate file, global Project Governor file,
`AGENTS.md`, historical T-0036 review evidence, task/Gate inventory, runtime,
controller, subagent, automation, skill, MCP, plugin, hook, or protocol is
modified or enabled.

## Timestamp Freshness Fact

`state.last_handoff_at` is
`2026-07-18T23:55:52.5241301+08:00`. It predates the current mtimes of all four
projection files and therefore does not represent the later projection writes.
This supplement does not alter, fabricate, or backfill that historical value.

## Review Evidence Integrity Preflight

The four required historical review evidence files were read and fingerprinted
before this supplement was written:

| Path | Size | SHA-256 |
|---|---:|---|
| `.ai/evidence/T-0036/t0036-review-changed-path-manifest.v0.1.md` | 2749 | `ce8bf10c02d75bcaf914130a7d7ccda23bd6f65bf76f93d422983fae0c29f3de` |
| `.ai/evidence/T-0036/t0036-independent-review-report.v0.1.md` | 3743 | `6d12aaee64015b60051c912fa9cd53f1611e2432ef93073bd72e654e5fb1f36c` |
| `.ai/evidence/T-0036/t0036-review-findings.v0.1.md` | 6950 | `fdff5bd279f341a743e1cccf279a8d6755dc9a228372169ee451bf6492573dde` |
| `.ai/evidence/T-0036/t0036-review-validation.v0.1.md` | 1168 | `b65d22a3c88538d8bb31348b113b28071b5585fd1da06d844735078beb5791d6` |

## Boundary

This supplement is not a content verdict, user acceptance, project PASS,
repair completion, installation, activation, or downstream authorization.
T-0036 remains `REPAIR_REQUIRED`; T0036-F001 through T0036-F009 remain
unrepaired, and no repair task or Gate is created.
