# T-0036 Post-review Governance-projection Post-write Manifest v0.1

Generated from disk at: `2026-07-19T19:27:18.0347608+08:00`.

## Covered Governance Projections

| Path | Size | SHA-256 | mtime_ns | Local mtime |
|---|---:|---|---:|---|
| `.ai/HANDOFF.md` | 8759 | `d6bc652d9d4860ebe668b86ab2a98dfa7e652db4d7dbf449c65ca023a52567a0` | 1784459302480147500 | `2026-07-19T19:08:22.4801475+08:00` |
| `.ai/state.yaml` | 9832 | `ed2c635b61c84c4c833211857849f7fc967e5b40000f2bf5267d49fcd7f7b2fb` | 1784459377464557800 | `2026-07-19T19:09:37.4645578+08:00` |
| `.ai/task_graph.yaml` | 11099 | `0a19d0db81d113399f702e649ae9a3f60636f11c6a1efaf593097941eb1a9c8a` | 1784459377466557300 | `2026-07-19T19:09:37.4665573+08:00` |
| `.ai/tasks/T-0036.md` | 5082 | `c6caa6469170bf8e860017da97fdaba11d40daf1cf605c635ecc4382b5b4355d` | 1784459377465557300 | `2026-07-19T19:09:37.4655573+08:00` |

## New Supplement Payloads

| Path | Size | SHA-256 | mtime_ns | Local mtime |
|---|---:|---|---:|---|
| `.ai/evidence/T-0036/t0036-post-review-governance-projection-supplement.v0.1.md` | 4520 | `467bddddb393a21188dd312803b2ce2e0b72b132e48f13becb2c0b31675e64d5` | 1784460369618355900 | `2026-07-19T19:26:09.6183559+08:00` |
| `.ai/evidence/T-0036/t0036-post-review-governance-projection-closeout-validation.v0.1.md` | 1543 | `3673a0a8040b27beaa81878f2d765feec0190905f9cf85fcbaad321469767d93` | 1784460421878997100 | `2026-07-19T19:27:01.8789971+08:00` |

This manifest does not embed its own hash because doing so would create a
recursive dependency. Its post-write fingerprint is reported by the closeout
session after the file is finalized.

## Historical Review Evidence Integrity Postcheck

| Path | Size | SHA-256 | mtime_ns | Local mtime |
|---|---:|---|---:|---|
| `.ai/evidence/T-0036/t0036-review-changed-path-manifest.v0.1.md` | 2749 | `ce8bf10c02d75bcaf914130a7d7ccda23bd6f65bf76f93d422983fae0c29f3de` | 1784390861722174100 | `2026-07-19T00:07:41.7221741+08:00` |
| `.ai/evidence/T-0036/t0036-independent-review-report.v0.1.md` | 3743 | `6d12aaee64015b60051c912fa9cd53f1611e2432ef93073bd72e654e5fb1f36c` | 1784390258078896800 | `2026-07-18T23:57:38.0788968+08:00` |
| `.ai/evidence/T-0036/t0036-review-findings.v0.1.md` | 6950 | `fdff5bd279f341a743e1cccf279a8d6755dc9a228372169ee451bf6492573dde` | 1784390258078896800 | `2026-07-18T23:57:38.0788968+08:00` |
| `.ai/evidence/T-0036/t0036-review-validation.v0.1.md` | 1168 | `b65d22a3c88538d8bb31348b113b28071b5585fd1da06d844735078beb5791d6` | 1784390258079899100 | `2026-07-18T23:57:38.0798991+08:00` |

These fingerprints match the supplement preflight. No required historical
review evidence was modified, overwritten, or rewritten.

## Actual Changed Paths For This Supplement Closeout

- `.ai/evidence/T-0036/t0036-post-review-governance-projection-supplement.v0.1.md`
- `.ai/evidence/T-0036/t0036-post-review-governance-projection-closeout-validation.v0.1.md`
- `.ai/evidence/T-0036/t0036-post-review-governance-projection-post-write-manifest.v0.1.md`

No governance projection, candidate file, global Project Governor file,
`AGENTS.md`, historical evidence, task inventory, or Gate inventory was written.

## Boundary

This manifest repairs governance-projection evidence freshness only. It does
not change the T-0036 `REPAIR_REQUIRED` verdict, repair T0036-F001 through
T0036-F009, authorize repair, create a repair task or Gate, or establish user
acceptance, project PASS, installation, activation, or runtime enablement.
