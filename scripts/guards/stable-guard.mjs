#!/usr/bin/env node
// stable-guard.mjs — PreToolUse hook (matcher: Write|Edit)
//
// Better-Harness finding "skill-constraints-unenforced" 的机械执行层：
// 阻断对 stable/ 目录的直接写入，除非通过 promotion gate 显式授权。
//
// 协议：从 stdin 读取 hook 事件 JSON（{ tool_name, tool_input: { file_path } }）。
//   exit 0 → 放行；exit 2 → 阻断（stderr 内容反馈给 agent）。
// 授权绕过（promotion gate 通过后使用）：设置环境变量 LOOP_STABLE_PROMOTION=1。
// 项目约定（SEC-005）：fail-close —— 输入无法解析时按阻断处理。

import { resolve, sep } from "node:path";
import { fileURLToPath } from "node:url";

const repoRoot = resolve(fileURLToPath(import.meta.url), "..", "..", "..");
const stablePrefix = resolve(repoRoot, "stable") + sep;

function block(reason) {
  process.stderr.write(`stable-guard: ${reason}\n`);
  process.exit(2);
}

let raw = "";
process.stdin.setEncoding("utf8");
process.stdin.on("data", (chunk) => { raw += chunk; });
process.stdin.on("end", () => {
  let event;
  try {
    event = JSON.parse(raw);
  } catch {
    block("输入不是合法 JSON（fail-close）。stable/ 写入必须通过 promotion gate。");
  }

  const toolName = String(event?.tool_name ?? "");
  // 只拦截写类工具；读取类工具直接放行
  if (!/^(Write|Edit|SearchReplace|MultiEdit)$/i.test(toolName)) {
    process.exit(0);
  }

  const filePath = event?.tool_input?.file_path;
  if (typeof filePath !== "string" || filePath.trim() === "") {
    process.exit(0);
  }

  const abs = resolve(filePath);
  const targetsStable = abs === stablePrefix.slice(0, -sep.length) || abs.startsWith(stablePrefix);
  if (!targetsStable) {
    process.exit(0);
  }

  if (process.env.LOOP_STABLE_PROMOTION === "1") {
    process.stderr.write("stable-guard: LOOP_STABLE_PROMOTION=1，promotion gate 授权放行。\n");
    process.exit(0);
  }

  block(
    `禁止直接写入 stable/（目标: ${filePath}）。` +
    "stable/ 仅可通过 promotion gate 更新（参见 .qoder/rules/governance-constraints.md）。" +
    "若 gate 已 PASSED 且获用户批准，使用 LOOP_STABLE_PROMOTION=1 授权本次写入。",
  );
});
