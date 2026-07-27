# Gate Request: G-T-0052-COMPREHENSIVE-REMEDIATION

## Decision required

是否批准启动 T-0052，修复 Loop 工程当前交接文档中列出的全部残余问题，并处理 63 个 legacy lab 回归失败？

## Included

- 统一 Read/Bash/Agent/MCP/Executor/Hook 治理入口
- Runtime Controller 与 legacy hook 合并语义
- Bootstrap/Proposal/Recovery 旁路和死锁修复
- GOVERNANCE_RECOVERY 最小恢复通道
- EnforcementHub 用户 Gate 接入
- 子代理委派边界与宿主能力验证
- legacy lab fixture 与兼容合同修复
- 完整负面路径和回归测试

## Excluded

- 真实业务项目
- 部署、回滚、数据库、权限、密钥、支付、生产数据、迁移
- 修改 AGENTS.md
- 在宿主不具备能力时伪造 ZCode Agent 递归 live-fire 成功

## Evidence boundary

测试通过、validator 成功、reviewer PASS、AI 建议均仅为 evidence，不替代用户批准。

当前 gate 状态：`pending`。
