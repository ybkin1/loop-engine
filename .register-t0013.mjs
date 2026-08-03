import { mkdirSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { parseDocument, stringify } from "yaml";
import { loadState, saveState } from "./dist/src/core/state-machine.js";

const ROOT = process.cwd();
const AI = join(ROOT, ".ai");

const state = await loadState(ROOT);
state.current_task_id = "T-0013";
await saveState(ROOT, state);
console.log("state.current_task_id → T-0013");

const graphFile = join(AI, "task_graph.yaml");
const graph = parseDocument(await (await import("node:fs/promises")).readFile(graphFile, "utf-8")).toJSON();
graph.tasks = graph.tasks ?? [];
graph.tasks.push({
  id: "T-0013",
  title: "loop 工程自身质量验收（安全扫描 + 质量门禁 + 最终验收评审 + 交付批准）",
  status: "active",
  priority: "P0",
  created_at: "2026-08-02",
  acceptance_criteria: [
    "AC1: 安全扫描真实运行（secrets/注入/CVE），无 CRITICAL/HIGH",
    "AC2: 质量门禁真实运行（lint/typecheck/test/build/audit）全 PASS",
    "AC3: R09 最终验收评审（交付完整性 + ACCEPTANCE 逐项）PASS",
    "AC4: R03 交付验收报告 + 用户最终批准",
  ],
  subtasks: [
    { id: "T-0013-A", title: "R08 安全验收扫描", status: "pending" },
    { id: "T-0013-B", title: "R07 质量门禁验收", status: "pending" },
    { id: "T-0013-C", title: "R09 最终验收评审", status: "pending" },
    { id: "T-0013-D", title: "R03 交付验收 + 用户批准", status: "pending" },
  ],
});
graph.edges = graph.edges ?? [];
graph.edges.push({ from: "T-0012", to: "T-0013" });
writeFileSync(graphFile, stringify(graph), "utf-8");
console.log("task_graph: T-0013 registered");

const card = `# Task Card T-0013

\`\`\`yaml
task_id: T-0013
run_id: RUN-0013
role: R08（安全）+ R07（质量）+ R09（验收评审）+ R03（交付）+ R11（编排）
objective: 将 loop 工程自身作为已完成开发的项目，执行最终质量验收

must_read:
  - .ai/ACCEPTANCE.md
  - .ai/PROJECT.md
  - .ai/KNOWN_ISSUES.md
  - scripts/security-scan.ts
  - scripts/quality-gates.ts

allowed_write:
  - .ai/
  - docs/

required_output:
  - 安全扫描报告（真实运行）
  - 质量门禁报告（真实运行）
  - R09 最终验收评审报告
  - R03 交付验收报告
  - 用户最终批准

pass_condition:
  - 安全无 CRITICAL/HIGH + 质量全 PASS + R09 验收 PASS + 用户批准

stop_conditions:
  - 验收证据不真实
\`\`\`
`;
mkdirSync(join(AI, "task-cards"), { recursive: true });
writeFileSync(join(AI, "task-cards", "T-0013.md"), card, "utf-8");
console.log("任务卡: .ai/task-cards/T-0013.md");
