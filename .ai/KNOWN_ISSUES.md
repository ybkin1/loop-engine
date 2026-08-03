# Known Issues

## Open
- **moderate CVE（T-0014-D 评估结论）**：@hono/node-server（路径遍历）+ @modelcontextprotocol/sdk 受影响，共 2 个 moderate。`npm audit fix --dry-run` 显示升级面大（49 平台包 + 2 变更，含 vitest/rollup 链路）——**决策：不冒险 fix，随下轮依赖升级周期统一处理**（当前无 CRITICAL/HIGH，不阻断）。

- **node -e 拆串绕过（T-0010 残留，P2）**：`node -e "require('fs')['write'+'FileSync']('.ai/state.'+'yaml', ...)"` 可绕过 EVAL_WRITE_APIS 与 state.yaml 写保护检测（hook 静态正则无法对抗字符串拼接）。危害边界：Write 工具直写 .ai/state.yaml 本就放行（治理豁免），node -e 通道未突破能力边界；user_approvals 伪造仍被字符串级检查拦截。缓解责任：治理脚本/工具一律走 node scripts|dist 白名单路径，禁用 node -e 执行写操作。
- 全局 MCP server 已指向项目 dist（settings.json 已更新，备份 settings.json.bak-20260731）；需 Qoder 重载后新工具（loop_gate_approve 等）生效。
- 自动编排的 `completed_roles` 检测依赖 state.yaml 显式字段；角色完成后需通过 `completeRole`/hook 更新，否则编排器认为角色未完成。
- 本项目是 Codex loop-engine-lab 的 Qoder 适配版；部分设计模式（子代理模型、hook 语义）仍需在真实业务项目试运行中调优。

## Closed
- 2026-08-02: T-0013 质量验收发现 runCveScan/runAudit 吞 npm audit 非零退出 → 已改 spawnSync + shell（CVE 检测真实生效，2 moderate 如实报告）→ T-0014-A。
- 2026-08-02: quality-gates 的 npx 调用在 Windows 缓存解析不稳定 + lint 用 tsc 输出冒充 → 已改本地二进制（node_modules/typescript/vitest）+ eslint 存在性检查 → T-0014-A。
- 2026-08-02: user_approval.test.ts 并行 flaky（5s 默认超时不足）→ 已建 vitest.config.ts 全局 15s 超时 → T-0014-B。
- 2026-08-02: ACCEPTANCE 文档与实现对齐（validate_state.py 引用 + 证据扁平命名）→ T-0014-C。

- 2026-07-31: hook 层 gate 防护 fail-open（extractYamlObjectList 嵌套 conditions 解析截断 gate，pendingGates/blockedGates 恒空）→ 已按缩进层级修复 + SEC-009 回归（T-0010）。
- 2026-07-31: pending gate 无 phase 时阻断全部写入导致治理自我锁死 → 已改为无 phase 放行 + node scripts|dist 白名单 + Bash 写 state.yaml 阻断（T-0010）。
- 2026-07-31: gate-guard Bash 分支无 user_approvals 拦截（printf >> state.yaml 可伪造批准）→ 已补对称拦截 + SEC-007 回归（T-0009）。
- 2026-07-31: 自动编排静默退出（hook_common.js loadState 缺 current_task_id/completed_roles 字段）→ 已修复全局 hook_common.js + 项目内回退加载。
- 2026-07-31: 健康检查"假 HEALTHY"（gates 空/无证据/无审计/无活跃角色均报 PASS）→ 已改为缺失即 BLOCKED + 生命周期感知。
- 2026-07-31: manual_approval 无落地路径（S6 交付 gate 永远无法通过）→ 已实现 approveGate + CLI `loop gate approve` + MCP `loop_gate_approve`。
- 2026-07-31: 治理状态手工漂移（state=P6 但 gates 空、evidence 空、HANDOFF 不一致）→ 已通过 rebuild-governance-state.mjs 重建合法基线。
- 2026-07-18: Project initialized with adapted governance framework for Qoder.
