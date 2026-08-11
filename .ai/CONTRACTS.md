# Contracts

## Frozen Contracts

- Project root is `C:\Users\Administrator\ZCodeProject\loop-engine`.
- The user owns goals, key tradeoffs, and gate approvals.
- AI owns technical execution details inside approved task and gate boundaries.
- For implementation, review, debugging, design, or handoff work, AI must invoke the `loop-governance` skill, read current `.ai` context, and run `.zcode/tools/validate_state.py` before continuing.
- User gates are authority boundaries. Reviewer PASS, validator success, tests, and AI recommendations are evidence only; they do not replace user approval.
- Artifact lifecycle states must stay separate: `candidate`, `reviewed`, `user-approved`, `approved`, `active`, and `installed`.
- `unified-governance-architecture.v0.2.1` is `approved: true`, `active: true`, and `installed: true` only as this project's local `AGENTS.md` startup instruction file.
- `active` means governance/process reference for this project's `.ai` records only.
- `installed` required a separate installation gate naming exact target paths, expected diffs, validation, rollback, and residual risks; the current installed state was approved by `G-T-0005-INSTALL-AGENTS-MD`.
- Further `AGENTS.md` installation or modification, and any skill, MCP, agent, automation, or protocol surface installation or enablement, requires a separate explicit user gate.
- Real business projects must not be entered without a separate real-project-application gate.
- Deployment, rollback, database, permission, secret, payment, production data, and migration actions require separate explicit user approval.
- Evidence history should be superseded rather than deleted unless the user approves a destructive action.
- Loop Core (`loop_core/`) defines host-independent protocols. Host Adapter (`src/loop_engine/adapters/`) implements them for ZCode (STRONG enforcement level；T-0158 迁入 src 布局；T-0177 修正 MEDIUM→STRONG)。
- Role isolation is enforced: developer != reviewer, each role via isolated Agent call.
- ZCode 插件 hooks 已登记（T-0174 bundled-marketplace.json），PreToolUse 拦截
  Write/Edit/Bash/ApplyPatch/Agent + exit 2 deny 语义 → enforcement level = STRONG
  （与 zcode_adapter.py / degradation.py 声明一致，T-0177 H1 统一）。
  前提：重启 ZCode 验证 hookCount > 0 后为机器级确认（T-0177 收口项）。

## Completion Flow Conventions

- T-0105 B-4-3 (evidence-manifest 时序约定): 主会话收尾顺序固定为——先创建/重生成
  evidence-manifest（create-only）→ 再更新 HANDOFF 中的 manifest 引用 → 最后才跑
  `test_manifest_t0095`。HANDOFF 引用先于清单生成会导致 `test_manifest_t0095`
  暂时失败（悬挂引用），属时序错误而非清单缺陷；按本约定执行可避免该时序失败复现。

## Open Contract Questions

- T-0022~T-0030 completed the full S0~S6 lifecycle. Project is at S6-delivery.
- Seeded defect validation confirmed independent review catches P0 defects (3/3 planted + 6 bonus).
- Bash 命令拦截由 loop_enforcement PreToolUse 全命令文本检查覆盖（T-0177 C3 已收窄 git 破坏性操作豁免）；enforcement level = STRONG（T-0177 修正，原 MEDIUM 留档为历史）。
- No real-project discovery gate has been approved.
