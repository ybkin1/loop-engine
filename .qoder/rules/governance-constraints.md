---
trigger: always_on
---

# Loop 治理关键约束（Always-On）

本规则将各 Skill（loop-engine、loop-writer、loop-reviewer、loop-repair、tools-registry 等）
声明的关键约束提升为项目级 always-on 规则，不再仅依赖 prompt 遵从性。
机械执行层：`.qoder/settings.json` PreToolUse hooks + `.husky/pre-commit` + CI。

## 1. stable/ 保护（promotion gate）

- **禁止直接修改 `stable/` 目录下的任何文件**，除非已通过 promotion gate
  （state.yaml/gates.yaml 中对应的 gate 状态为 PASSED 且有用户批准记录）。
- `stable/current-loop-protocol.md` 与 `stable/user-origin.md` 是已批准产物，
  候选文档（candidates/）永远不能直接覆盖它们。
- 机械兜底：`scripts/guards/stable-guard.mjs`（PreToolUse Write|Edit hook，exit 2 阻断）。

## 2. 候选 ≠ 批准

- 不把候选文档（candidates/ 下的产物）说成已批准。
- reviewer PASS 仅表示可候选提升，**不等同于用户批准**。
- 不创建 Gate 或任务 without 用户授权。

## 3. 密钥安全（tools-registry 约束）

- 密钥永远不暴露给调用方（agent/CLI/代码）。
- 不在代码、文档、配置中硬编码任何密钥；一律使用环境变量引用（`${VAR}` / `env:` 形式）。
- 注册新工具需要用户 gate 审批。

## 4. 变更必须通过质量门禁

- 提交前必须通过 `npm run check`（lint + typecheck + test），由 `.husky/pre-commit` 强制执行。
- 禁止以 `--no-verify` 常规性绕过门禁；紧急绕过后必须尽快补跑检查。
- CI（.github/workflows/ci.yml）是最终门禁，push/PR 必须通过。

## 5. 数据完整性

- `outcomes.jsonl`、审计账本（audit_ledger.jsonl）等 append-only 数据不可修改已有记录。
- learnings 和 skill-proposals 只是建议，需用户批准才能生效；不自动修改任何 Skill 或治理文件。
