# 运维交接文档 — Loop Engine v1.0.0

## 交接对象

用户本人（Loop Engine 是本地插件，无团队交接需求）

## 日常运维

### 无需运维
Loop Engine 作为 ZCode 插件，安装后自动生效：
- SessionStart hook 自动注入治理摘要
- PreToolUse hook 自动拦截未授权文件写入
- 无需手动启动、无需定期维护、无需数据库管理

### 状态检查
```bash
# 检查项目治理状态
python .zcode/tools/validate_state.py <项目根目录>

# 查看治理技能是否可用
在 ZCode 中输入：/loop-validate

# 查看证据链完整性
/loop-verify-chain

# 查看 Token 成本
/loop-cost
```

### 配置调整
编辑 `.zcode/skills/loop-governance/config.yaml`：
- gate_guard：启用/禁用、失败策略
- path_guard：保护区列表、决策模式(ask/deny)
- quality_gates：各检查项阈值

编辑 `.ai/state.yaml`：
- loop_mode：FULL/STANDARD/LIGHTWEIGHT

## 监控和告警

- **代码质量监控**：`pytest` 测试套件（246 tests）
- **Lint 监控**：`ruff check` 零违规
- **安全监控**：`python scripts/security_scan.py --project-root .`
- **性能监控**：`python scripts/perf_runner.py --project-root .`
- **成本监控**：`.ai/evidence/costs/cost_log.jsonl`

## 已知限制

- Bash 命令写入不经过 hook 拦截（ZCode 架构限制，ENFORCEMENT_LEVEL: MEDIUM）
- 子 Agent 不能拉子孙 Agent（需主会话编排）
- 不提供 APM/基础设施级监控（插件项目不包含运行时服务）
