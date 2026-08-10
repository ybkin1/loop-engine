#!/usr/bin/env python3
"""fix_p2_remaining.py — 修复审查 P2 项：F2（参数校验）+ F9（guard 注释/loadState 去重）+ F7（evidence_ref 文档对齐）"""
from pathlib import Path

TOOLS = Path(r"C:\Users\Administrator\.qoder-cn\loop-engine-lab\src\server\tools.ts")
GUARD = Path(r"C:\Users\Administrator\.qoder-cn\loop-engine-lab\..\hooks\scripts\output_quality_guard.js").resolve()

def main() -> int:
    # ── F2: loop_output_quality 参数校验 ──
    t = TOOLS.read_text(encoding="utf-8")
    old = '        case "loop_output_quality": {\n          const { OutputQualityEngine, renderReportSummary } = await import("../core/output_quality.js");'
    new = '        case "loop_output_quality": {\n          const target = args?.target as string | undefined;\n          if (typeof target !== "string" || target.trim().length === 0) {\n            return textReply("loop_output_quality: invalid target — expected a non-empty path.");\n          }\n          const { OutputQualityEngine, renderReportSummary } = await import("../core/output_quality.js");'
    assert t.count(old) == 1, f"F2 anchor1 count={t.count(old)}"
    t = t.replace(old, new)

    old2 = '          const report = engine.verifyTarget(args!.target as string, {\n            task_id: args?.task_id as string | undefined,\n            phase: args?.phase as string | undefined,\n            role: args?.role as string | undefined,'
    new2 = '          const report = engine.verifyTarget(target, {\n            task_id: args?.task_id as string | undefined,\n            phase: args?.phase as string | undefined,\n            role: args?.role as string | undefined,'
    assert t.count(old2) == 1, f"F2 anchor2 count={t.count(old2)}"
    t = t.replace(old2, new2)

    # loop_quality_gate 参数校验
    old3 = '        case "loop_quality_gate": {\n          const { OutputQualityEngine } = await import("../core/output_quality.js");'
    new3 = '        case "loop_quality_gate": {\n          const target = args?.target as string | undefined;\n          if (typeof target !== "string" || target.trim().length === 0) {\n            return textReply("loop_quality_gate: invalid target — expected a non-empty path.");\n          }\n          const { OutputQualityEngine } = await import("../core/output_quality.js");'
    assert t.count(old3) == 1, f"F2 anchor3 count={t.count(old3)}"
    t = t.replace(old3, new3)

    old4 = '          const report = engine.verifyTarget(args!.target as string, {\n            task_id: args?.task_id as string | undefined,\n          });'
    new4 = '          const report = engine.verifyTarget(target, {\n            task_id: args?.task_id as string | undefined,\n          });'
    assert t.count(old4) == 1, f"F2 anchor4 count={t.count(old4)}"
    t = t.replace(old4, new4)
    TOOLS.write_text(t, encoding="utf-8")
    print("[F2] tools.ts param validation added (both tools)")

    # ── F9: guard loadState 去重 + 注释对齐 ──
    g = GUARD.read_text(encoding="utf-8")
    # loadState 缓存：把两处 loadState 调用合并为一次
    old_g1 = '  let loopActive = false;\n  try {\n    const state = common.loadState(root);\n    const phase = ((state && state.current_phase) || \'\').toLowerCase();\n    loopActive = phase !== \'\' && phase !== \'null\' && phase !== \'s0-init\' && phase !== \'none\';\n  } catch {\n    loopActive = false;\n  }\n  if (!loopActive) process.exit(0);'
    new_g1 = '  let loopActive = false;\n  let stateCache = null;\n  try {\n    stateCache = common.loadState(root);\n    const phase = ((stateCache && stateCache.current_phase) || \'\').toLowerCase();\n    loopActive = phase !== \'\' && phase !== \'null\' && phase !== \'s0-init\' && phase !== \'none\';\n  } catch {\n    loopActive = false;\n  }\n  if (!loopActive) process.exit(0);'
    assert g.count(old_g1) == 1, f"F9 anchor1 count={g.count(old_g1)}"
    g = g.replace(old_g1, new_g1)

    old_g2 = '  // ── Task binding (advisory) ──\n  try {\n    const state = common.loadState(root);\n    if (state && !state.current_task_id && !state.active_task_id) {'
    new_g2 = '  // ── Task binding (advisory) ──\n  try {\n    const state = stateCache || common.loadState(root);\n    if (state && !state.current_task_id && !state.active_task_id) {'
    assert g.count(old_g2) == 1, f"F9 anchor2 count={g.count(old_g2)}"
    g = g.replace(old_g2, new_g2)

    # 注释对齐：.ai 豁免说明
    old_g3 = '  // 4. Governance files always allowed (decision-recording exemption)\n  if (common.isGovernanceFile(filePath, root)) process.exit(0);'
    new_g3 = '  // 4. Governance files always allowed (decision-recording exemption).\n  //    NOTE: isGovernanceFile covers the GOVERNANCE_PATHS whitelist (.ai/state.yaml etc.);\n  //    other .ai/ paths (tasks/, evidence/) still go through code-quality checks.\n  if (common.isGovernanceFile(filePath, root)) process.exit(0);'
    assert g.count(old_g3) == 1, f"F9 anchor3 count={g.count(old_g3)}"
    g = g.replace(old_g3, new_g3)
    GUARD.write_text(g, encoding="utf-8")
    print("[F9] guard loadState cached + comment aligned")

    # ── F7: standards.md evidence_ref 对齐 ──
    std = Path(r"C:\Users\Administrator\.qoder-cn\skills\loop-engineering\references\output-quality-standards.md")
    s = std.read_text(encoding="utf-8")
    old_s = '2. **证据绑定**：报告可通过 `loop_evidence_submit`（type: `quality`）写入\n   `.ai/evidence/<task_id>/`，内容哈希由引擎计算，防篡改。'
    new_s = '2. **证据绑定**：报告可通过 `loop_evidence_submit`（type: `quality`）写入\n   `.ai/evidence/<task_id>/`，内容哈希由引擎计算，防篡改。\n   `loop_quality_gate` 工具输出含 `evidence_ref`（`quality:<hash12>`），\n   用于 Gate 证据引用。'
    assert s.count(old_s) == 1, f"F7 anchor count={s.count(old_s)}"
    s = s.replace(old_s, new_s)
    std.write_text(s, encoding="utf-8")
    print("[F7] standards.md evidence_ref aligned")

    print("\n[ok] all remaining P2 fixes applied (F2/F7/F9)")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
