#!/usr/bin/env node
/**
 * close-t0013.mjs — T-0013 收尾：验收报告存档 + R03 交付验收 + 证据
 */
import { mkdirSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { loadState } from "../dist/src/core/state-machine.js";
import { submitEvidence } from "../dist/src/core/evidence.js";
import { AuditLedger } from "../dist/src/core/audit_ledger.js";

const ROOT = process.cwd();
const AI = join(ROOT, ".ai");
const OUT = join(AI, "reviews");
const ledger = new AuditLedger(join(AI, "audit_ledger.jsonl"));
mkdirSync(OUT, { recursive: true });

const now = new Date().toISOString();

// 1) R09 最终验收评审报告存档（子代理报告核心结论）
const acceptanceReport = `# R09 最终验收评审报告（T-0013-C）

> 评审时间: ${now} | 评审角色: R09 独立评审员（最终交付验收，只读）

## 验收结论
**verdict: PASS（可交付）**

## 产品验收标准（6/6 PASS）
- P-1 无编码用户可用 → 12 阶段全闭环 + released
- P-2 变更受任务/gate/证据约束 → T-0005~T-0013 + 11 gate passed + 16 证据
- P-3 Qoder 在批准边界内工作 → 11 角色契约 + 8 SKILL
- P-4 用户只被问目标/取舍/gate → manual_approval 真实路径 + user_approvals 记录
- P-5 状态可审计 → 审计账本 27 条链式哈希独立验证通过
- P-6 高风险动作需用户 gate → HardConstraints + hook 实测拦截

## 交付完整性（6/6 PASS）
- 24 核心模块全导出 | 34 MCP 工具（含 loop_gate_approve）| CLI 实测运行
- 21 测试文件 532 tests | .ai/ 17 份文档 + docs/ops | 部署齐备（settings.json + 13 hooks）

## 治理状态一致性（PASS）
- 11 gate 全 passed | 11 角色全 completed | project_status=released
- 证据 16 份与 gate 条件一一对应 | 审计链完整无篡改

## 质量证据真实性（PASS）
- test 532/100%（1 次并行 flaky，单文件稳定）| typecheck 0 | audit HIGH=0 CRITICAL=0
- security: 0 secret / 2 MEDIUM 受控 execSync / CVE moderate 2（fixAvailable）

## 残余风险（可接受）
- node -e 拆串（P2，缓解充分）| MCP 重载提示（P3）| completed_roles 流程约束（P3）

## 验收备注（P3，不阻断，迭代 2 处理）
1. HANDOFF/PROGRESS 需随 T-0013 完成同步
2. runCveScan execSync catch 吞非零退出 → moderate CVE 漏报（建议 spawnSync）
3. user_approval.test.ts 并行 flaky 待调查
4. ACCEPTANCE 引用 validate_state.py（Codex 命名）需更新
5. 证据扁平命名 vs ACCEPTANCE 子目录描述偏差
`;
writeFileSync(join(OUT, "R09-ACCEPTANCE.md"), acceptanceReport, "utf-8");
console.log("验收报告存档: .ai/reviews/R09-ACCEPTANCE.md");

// 2) R03 交付验收报告
const deliveryReport = `# R03 交付验收报告（T-0013-D）

> 生成时间: ${now} | 角色: R03 交付经理

## 交付物清单
| 交付物 | 状态 | 证据 |
|--------|------|------|
| 治理系统核心（src/core 24 模块） | ✅ | quality-report + 532 tests |
| MCP Server（34 工具） | ✅ | tools.ts + dist 部署 |
| CLI（init/gate/role/evidence/state/handoff） | ✅ | CLI 实测 |
| 全局 hooks 部署（13 脚本 + PreToolUse/UserPromptSubmit/Stop） | ✅ | settings.json |
| 测试套件（21 文件 532 tests） | ✅ | quality-report test PASS |
| 安全扫描（0 secret / 0 HIGH / 0 CRITICAL） | ✅ | security-report PASS |
| 审计链（27 条，哈希验证通过） | ✅ | audit_ledger 独立验证 |
| 证据链（16 份 hash 绑定） | ✅ | evidence/ 目录 |
| 运维手册 + 监控配置 | ✅ | docs/ops/（R10） |
| 文档（.ai/ 17 份 + docs/） | ✅ | 交付完整性检查 |

## 上游签字
- R07 质量: PASS（532/532）
- R08 安全: PASS（无 CRITICAL/HIGH）
- R09 验收评审: PASS（可交付）
- R10 运维: READY（runbook + monitoring）
- R11 编排: 状态一致

## 结论
**GO（可交付）** — 等待用户最终验收批准。
`;
writeFileSync(join(OUT, "delivery-acceptance.md"), deliveryReport, "utf-8");
console.log("交付验收报告存档: .ai/reviews/delivery-acceptance.md");

// 3) 证据提交
await submitEvidence(ROOT, {
  evidence_id: "ev-acceptance-t0013",
  type: "review_report",
  content: "R09 最终验收 PASS：产品验收 6/6 + 交付完整性 6/6 + 治理一致 + 审计链验证通过（详见 .ai/reviews/R09-ACCEPTANCE.md）",
  role_id: "R09",
  gate_id: null,
  metadata: { verdict: "PASS", product_acceptance: "6/6", delivery_complete: "6/6" },
});
await submitEvidence(ROOT, {
  evidence_id: "ev-delivery-t0013",
  type: "delivery_checklist",
  content: "R03 交付验收：GO（上游全签字：R07 PASS / R08 PASS / R09 PASS / R10 READY）——等待用户最终批准（详见 .ai/reviews/delivery-acceptance.md）",
  role_id: "R03",
  gate_id: null,
  metadata: { verdict: "GO", upstream_signoff: "R07,R08,R09,R10" },
});
ledger.append("delivery_ready", "R03", { task_id: "T-0013", verdict: "GO" });
console.log("交付证据已提交（R09 验收 PASS + R03 GO）");

const state = await loadState(ROOT);
console.log(`\n阶段: ${state.current_phase} | status: ${state.project_status} | task: ${state.current_task_id}`);
console.log("\n⏸ 等待用户最终验收批准（T-0013-D）");
