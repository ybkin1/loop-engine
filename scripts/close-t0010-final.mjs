#!/usr/bin/env node
/**
 * close-t0010-final.mjs — T-0010 评审 PASS 后收尾
 * 评审报告存档 + 证据 + T-0010 completed（评审通过后标记）
 */
import { mkdirSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { loadState } from "../dist/src/core/state-machine.js";
import { submitEvidence } from "../dist/src/core/evidence.js";
import { AuditLedger } from "../dist/src/core/audit_ledger.js";
import { parseDocument, stringify } from "yaml";

const ROOT = process.cwd();
const AI = join(ROOT, ".ai");
const ledger = new AuditLedger(join(AI, "audit_ledger.jsonl"));

const report = `# R09 评审报告 — T-0010（P3 加固 + S8 功能测试，复审 PASS）

> 生成时间: ${new Date().toISOString()} | 评审角色: R09 独立代码评审员（只读复审）

## 任务范围
- T-0010-A: Bash 写 state.yaml 阻断（node scripts|dist 白名单收窄）
- T-0010-B: unifiedAuthCheck 补 Bash 注入检查
- T-0010-C: hook_scripts.test.ts require 路径显式化
- T-0010-D: S8 功能测试证据 + gate-S8 推进
- 评审发现 P1-1（extractYamlObjectList 嵌套解析 fail-open）+ P2-1（防锁死配套）+ P1-2（白名单收窄）

## 首轮结论（BLOCKED）
- P1-1: hook 层 gate 防护整体 fail-open（嵌套 conditions 解析截断 gate，pendingGates/blockedGates 恒空）
- P1-2: node -e 拆串绕过 EVAL_WRITE_APIS
- P2-1: 防自我锁死宣称依赖 fail-open 才成立

## 修复后复审结论（PASS）
- P1-1 FIXED：extractYamlObjectList 按缩进层级识别（topIndent + 续行深度限制）；
  实测真实 gates.yaml 11 个 gate 全解析、status 完整、pendingGates=S9/S10/S11
- P2-1 FIXED：pending 无 phase → 放行（blocked 强阻断保留）；Bash node 治理脚本豁免；
  phaseToPaths 支持 S-prefix；防锁死实测：写 tests/、node scripts/、npm test 全部放行，blocked 场景 exit 2
- P1-2 主体达成：白名单收窄为 node scripts|dist；node -e 不再无条件豁免
- SEC-009 4 用例通过；532 tests 全过；tsc 0 错误
- 整改项（P2）：node -e 拆串绕过残余风险补记 KNOWN_ISSUES.md

## verdict
PASS
`;
mkdirSync(join(AI, "reviews"), { recursive: true });
writeFileSync(join(AI, "reviews", "R09-T0010.md"), report, "utf-8");
console.log("评审报告存档: .ai/reviews/R09-T0010.md");

await submitEvidence(ROOT, {
  evidence_id: "ev-review-t0010",
  type: "review_report",
  content: "R09 复审 PASS：P1-1（gate 解析 fail-open）+ P2-1（防锁死）+ P1-2（白名单收窄）全部处理，532 tests passed（详见 .ai/reviews/R09-T0010.md）",
  role_id: "R09",
  gate_id: "gate-S9-fix-optimize",
  metadata: { verdict: "PASS", p0_count: 0, p1_count: 0 },
});
ledger.append("role_completed", "R09", { task_id: "T-0010", verdict: "PASS" });
console.log("评审证据已提交");

// T-0010 completed（评审通过后标记）
const graphFile = join(AI, "task_graph.yaml");
const graph = parseDocument(await (await import("node:fs/promises")).readFile(graphFile, "utf-8")).toJSON();
for (const t of graph.tasks ?? []) {
  if (t.id === "T-0010") {
    t.status = "completed";
    t.completed_at = new Date().toISOString().slice(0, 10);
    for (const st of t.subtasks ?? []) st.status = "completed";
  }
}
writeFileSync(graphFile, stringify(graph), "utf-8");
console.log("task_graph: T-0010 completed（评审 PASS 后标记）");

const state = await loadState(ROOT);
console.log(`阶段: ${state.current_phase} | gate: ${state.current_gate_id} | task: ${state.current_task_id}`);
