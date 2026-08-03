# Loop Engineering 运行手册（R10 产出）

> 生成时间: 2026-08-02T02:17:09.534Z | 角色: R10 发布运维

## 构建
```
npm install          # 安装依赖（@modelcontextprotocol/sdk, yaml, commander）
npm run build        # tsc 编译 → dist/
```

## 测试
```
npm test             # vitest 全量（当前 532 tests）
npx tsc --noEmit     # 类型检查（0 错误门槛）
```

## 启动（MCP Server）
```
npm start            # node dist/src/server/index.js（stdio JSON-RPC）
```
MCP 配置: settings.json → mcpServers.loop-engineering.args 指向 dist/src/server/index.js

## 治理运维命令
```
node scripts/governance-health-check.cjs [root]   # 治理健康检查（exit 0/1/2）
node scripts/sync-state-docs.cjs [root]           # HANDOFF/PROGRESS 单一事实源同步
node scripts/rebuild-governance-state.mjs [root]  # 状态合法化重建（--force 需显式）
node scripts/auto-orchestrate.cjs                 # 自动编排指令（UserPromptSubmit hook）
```

## 回滚
- 治理状态: .ai/backup-*/ 保留重建前快照；git 回滚 .ai/ 变更
- settings.json: settings.json.bak-20260731 可回退 MCP 配置
- hooks: ~/.qoder-cn/hooks/scripts/*.bak-t0010 保留 hook 修改前版本
- 数据库: 无（YAML 持久化，原子写 + rename 防损坏）

## 故障排查
| 症状 | 处理 |
|------|------|
| 自动编排无输出 | 验证 ~/.qoder-cn/hooks/scripts/ 存在 + state.yaml 可读 |
| 健康检查 BLOCKED | 查看 blockers 明细，解决 gate/证据/审计缺口 |
| MCP 工具缺失 | 确认 settings.json 指向项目 dist 并重载 Qoder |
| 测试失败 | 先跑 npx tsc --noEmit 定位类型错误 |

## 发布检查（上线前）
- [ ] npm test 全量通过
- [ ] 健康检查无 BLOCKER
- [ ] 审计账本链完整（loop_audit_verify）
- [ ] 证据链验证（loop_evidence_chain）
- [ ] 回滚方案就绪（备份存在）
