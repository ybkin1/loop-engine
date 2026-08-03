# Loop Engine 交接文档（继续完善版）

更新时间：2026-07-23
项目根目录：`C:\Users\Administrator\ZCodeProject\loop-engine`

## 1. 交接结论

当前 Loop Engine 不能宣称已经达到生产级，也不能宣称真实 ZCode 宿主全链路已验证。

准确定位：

```text
较完整的 Loop Core 治理框架
+ ZCode 插件与 Hook 配置
+ Hook/状态机/证据/认证等本地测试
+ 部分任务范围阻断
+ 模拟角色执行路径已开始收紧

但真实 Agent 调度、独立 Reviewer、用户 Approval/Gate 闭环、
真实宿主 live-fire、通用 Bash 命令拦截、生产交付验证仍未完成。
```

当前必须保持诚实标记：

```text
ENFORCEMENT_LEVEL: MEDIUM
Verified: none（真实宿主全链路尚未形成可复现证据）
Installation eligibility: BLOCKED
Production authority lifecycle: false
```

## 2. 用户最终目标

用户是非技术人员，不应被要求审核代码或编写代码。

Loop Engine 的目标是：

```text
用户描述业务目标
→ AI 判断风险和规模
→ 需求/架构/详细设计/实现/测试/评审/修复/交付逐阶段推进
→ 未满足硬条件自动阻断
→ 用户只负责目标、范围、业务取舍、风险接受和阶段 Gate
```

目标是全面超越 `C:\Users\Administrator\.qoder-cn\loop-engine-lab`，但必须用可验证工程指标证明，不能用文档数量或角色报告自评证明。

## 3. 本轮已经完成的 P0 修复

### 3.1 无活动任务不再触发 traceback

修改：

```text
.zcode/tools/continuity_auditor.py
```

原问题：

```text
current_task_id: null
→ 读取 .ai/tasks/None.md
→ FileNotFoundError
```

现在返回结构化错误（T-0101 起分流为独立 exit code 3，不再与治理损坏共用 exit 2）：

```text
[info] NO_ACTIVE_TASK: state.current_task_id is null（合法阻塞态：等待任务发起；state 不可开工）
```

`validate_state.py` 的 rc=3 是**合法的 idle 阻塞态**（非损坏、非成功）；新会话必须继续处理 `NO_ACTIVE_TASK` 的基线状态——先创建/恢复一个明确的、用户批准范围内的任务，而不是直接开工。rc=2 才表示真实治理损坏（fail-closed 阻断）。

### 3.2 生产路径禁止自动模拟 Agent PASS

修改：

```text
loop_core/executor.py
```

现在 `PhaseExecutor` 默认：

```python
fixture_mode=False
```

当缺少：

```text
agents/<role_id>/run.py
```

时，不再自动调用 `_simulate_role_output()`，而是失败：

```text
REAL_AGENT_UNAVAILABLE
```

只有测试显式使用：

```python
PhaseExecutor(fixture_mode=True)
```

才允许 fixture 模拟输出。

注意：这只是关闭了生产路径的虚假 PASS，尚未接通真实 ZCode Agent。

### 3.3 任务范围缺失改为 fail-closed

修改：

```text
hooks/scripts/loop_enforcement.py
```

原逻辑：

```text
allowed_paths 为空 → allow
```

现在：

```text
allowed_paths 为空 → deny / BLOCKED
```

后续应补充明确错误码 `TASK_SCOPE_MISSING`，并增加对应测试。

### 3.4 高风险项目不能被强制降级

修改：

```text
loop_core/router.py
```

当前最低模式：

```text
LOW      → LIGHTWEIGHT
MEDIUM   → STANDARD
HIGH     → FULL
CRITICAL → FULL
```

用户可以提高模式，但不能把高风险项目强制降为 LIGHTWEIGHT。

## 4. 本轮测试结果

本轮运行：

```text
executor + loop_core：82 passed
hooks + enforcement：35 passed
Hook 专项历史结果：15 passed
```

此前完整回归基线：

```text
246 passed, 1 skipped, 75 subtests passed
```

注意：测试通过只证明本地逻辑/子进程/fixture 行为，不能替代真实 ZCode 会话 live-fire。

## 5. ZCode 插件与 Hook 当前事实

插件 ID：

```text
loop-governance@zcode-plugins-official
```

全局配置：

```text
C:\Users\Administrator\.zcode\cli\config.json
```

插件缓存根：

```text
C:\Users\Administrator\.zcode\cli\plugins\cache\zcode-plugins-official\loop-governance\1.0.0
```

实际插件 Hook 入口：

```text
...\loop-governance\1.0.0\hooks\hooks.json
```

插件列表此前已显示：

```text
enabled=true
hookDetails=7
runnable=true
```

Hook 事件：

- `SessionStart`：loop_auto_activate、template_injector、session_brief
- `PreToolUse`：loop_enforcement、gate_guard、role_isolation、path_guard
- matcher：`Write|Edit|Bash|ApplyPatch`
- Hook 类型：Windows 可靠的 `process + args + timeoutMs`

项目配置：

```text
C:\Users\Administrator\ZCodeProject\loop-engine\.zcode\config.json
```

当前项目配置 Hook 已关闭，避免和插件 Hook 重复执行：

```json
{"hooks": {"enabled": false}}
```

不要重新创建 `.zcode/hooks.json`，也不要再次复制第三套 Hook 配置。

## 6. 真实宿主验证边界

目前日志最多证明：

```text
hooks.loadHooks OK
```

尚未取得以下真实证据：

- 新 ZCode 会话实际触发 `SessionStart`；
- 真实 `PreToolUse` 执行脚本；
- 普通 Write/Edit 被宿主显示为拒绝；
- Bash 写文件被宿主阻断；
- `permissionDecision=ask` 真实显示用户确认；
- ZCode MCP server 真实启动；
- ZCode Agent 真实启动并返回 session/actor 身份。

因此新会话不能把插件列表中的 `runnable=true` 当作 live-fire 通过。

## 7. 与 Qoder Loop Engine Lab 的比较结论

Qoder Lab 的优势：

- TypeScript 类型化 Core 更干净；
- `state-machine`、`role-engine`、`evidence`、`freshness`、`handoff`、`certification` 模型清晰；
- MCP/CLI/Core 统一入口方向较好；
- Evidence TTL 和因果链值得吸收。

Qoder Lab 的关键缺口：

- Guard 没有统一接入 MCP/CLI 执行入口；
- manual approval 没有完整闭环；
- 角色权限主要是描述性数据；
- Handoff hash 不是实际 artifact 内容 hash；
- 质量/security checker 有吞错或覆盖不足；
- 当前仍是 Candidate/S1 实验态，没有真实交付证据。

ZCode 当前优势：

- 有真实 ZCode 插件/Hook 接入方向；
- 有 `exit 2` 阻断机制；
- 有任务合同和 allowed paths；
- 有更深的安全、事务、路径和证据测试；
- 有安装、卸载、部署、回滚和运维资产。

ZCode 当前关键缺口：

- executor 过去会模拟 Agent，目前已禁止生产路径模拟，但真实 Agent 仍未接通；
- developer/reviewer 独立身份未证实；
- Approval/Gate/人类决策闭环未完成；
- Bash 不是通用命令拦截；
- MCP/CLI/executor 尚未统一经过 Runtime Controller；
- 状态、文档、历史报告和插件副本存在漂移；
- 真实垂直切片尚未完成。

最终方向：

```text
吸收 Qoder 的干净 Core、类型化 Role/Evidence/Freshness/Handoff
保留 ZCode 的 Hook、任务范围、宿主能力分级、交付和回滚
新增真正的 Runtime Controller、Approval、Agent Adapter 和 conformance suite
```

## 8. 下一阶段必须按 P0 顺序推进

### P0-A：建立统一 Runtime Controller

新增宿主无关授权入口，至少覆盖：

```text
Write / Edit / ApplyPatch / Bash
MCP tools/call
CLI command
executor role launch
evidence submit
state/gate transition
install / upgrade / rollback
```

任何入口绕过 Controller 都应被标记为 P0。

### P0-B：实现 Approval Record

至少绑定：

- approval_id；
- gate_id；
- human actor；
- decision；
- source；
- packet_hash；
- scope_hash；
- input fingerprint；
- recorded_at；
- expiration。

只有真实用户批准才能推进 Gate。

### P0-C：真实 Agent Adapter

真实 Agent 不可用只能：

```text
BLOCKED(REAL_AGENT_UNAVAILABLE)
```

必须记录：

- actor_id；
- session_id；
- role_id；
- task_id；
- input snapshot；
- prompt fingerprint；
- read/write scope；
- exit code；
- output artifact；
- start/end time。

### P0-D：角色独立性

必须证明：

```text
developer_actor_id != reviewer_actor_id
developer_session_id != reviewer_session_id
reviewer 不可写业务代码
developer 无法签署自己的实现
```

### P0-E：Gate 真实读取和推进

不能仅凭 `current_gate_id` 推断 pending，必须读取 `.ai/gates.yaml` 中实际状态：

```text
pending / approved / rejected / blocked / superseded
```

### P0-F：命令/脚本绕过矩阵

至少验证：

- Write；
- Edit；
- ApplyPatch；
- Bash 重定向；
- cp/mv/tee/cat；
- PowerShell；
- Python/Node 脚本内部写入；
- git；
- 外部进程；
- 未识别命令。

无法可靠识别目标时必须 fail-closed，不能放行。

## 9. 真实垂直切片验收

最终必须完成一条非生产、隔离、可观察的真实样例：

```text
真实需求
→ 需求 Gate
→ 架构
→ 详细设计
→ 任务包
→ 真实 Developer Agent
→ 代码和测试
→ 独立 Reviewer Agent
→ 预埋业务缺陷/架构缺陷/安全缺陷
→ 阻断错误交付
→ Repair Task
→ 修复
→ 回归
→ 构建
→ 运行
→ 用户可观察结果
→ Human Review Packet
→ 用户 Gate
```

没有这条链，不能宣称全面超过 Qoder。

## 10. 当前禁止事项

没有新的明确 Gate 之前，不得：

- 进入真实业务项目；
- 部署或发布；
- 修改数据库、权限、密钥、支付、生产数据或迁移；
- 把 reviewer PASS、测试通过、validator 成功、角色 GO 当作用户批准；
- 把 fixture/simulated 输出当作真实 Agent 证据；
- 把 Hook 静态注册当作真实 live-fire 证据；
- 把 Qoder 的设计能力当作已运行的生产能力。

## 11. 新会话启动检查清单

新会话必须先读取：

```text
AGENTS.md
.ai/state.yaml
.ai/HANDOFF.md
.ai/HANDOFF-NEXT.md
.ai/KNOWN_ISSUES.md
.ai/gates.yaml
.ai/task_graph.yaml
当前任务文件（若 current_task_id 非空）
```

然后运行：

```text
C:\Python312\python.exe .zcode\tools\validate_state.py C:\Users\Administrator\ZCodeProject\loop-engine
```

当前预期结果（T-0101 起）：

```text
[info] NO_ACTIVE_TASK: state.current_task_id is null（合法阻塞态：等待任务发起；state 不可开工）
```
退出码 3（idle 合法阻塞态，与治理损坏 exit 2 分流；不输出 usable）。

这不是成功状态、也不是损坏；新会话应先创建或恢复一个明确的、用户批准范围内的任务，而不是直接进入大规模实现。

## 12. 本交接的第一步建议

先创建一个新的、明确的治理任务，专门处理：

```text
P0：Runtime Controller + Approval/Gate + 真实 Agent Adapter
```

然后按以下顺序执行：

```text
1. 修复并验证任务/状态/审批 Schema
2. 建立 RuntimeController.authorize()
3. 禁止所有非 fixture 模拟 PASS
4. 接通真实 ZCode Agent
5. 实现 developer/reviewer 隔离
6. 完成 Hook conformance
7. 完成真实 Gate/Review Packet
8. 完成真实垂直切片
9. 再更新交付状态和发布文档
```

交接原则：

```text
无法证明就保持 BLOCKED。
失败只能停住，不能包装成 PASS。
用户只批准目标和 Gate，不承担代码审核责任。
```