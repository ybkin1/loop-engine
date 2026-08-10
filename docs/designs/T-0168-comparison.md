# T-0168 附录二：Pi Loop vs ZCode Loop 优劣 + 本机软件项目能力深度比较

> 日期：2026-08-10 | 基于实际代码实现（非理论）
> 对象：zcode loop-engine v3.12.67（.zcode/tools + loop_core + hooks）
>       pi-agent-extensions（mini-loop v2 + 质量环 P0/P1/P2 + subagent-v2）
> 结论先行：**两者不是替代关系，是互补关系**——zcode 强在"机器强制 + 完整
> 治理闭环"，pi 强在"真·多代理执行 + 深度递归 + 质量环自动返工"。

---

## 第一部分：Pi Loop vs ZCode Loop 优劣比较

### 1.1 机制对照表（实际实现）

| 机制 | ZCode loop-engine | Pi mini-loop v2+ | 优势方 |
|------|------------------|------------------|--------|
| **执行拓扑** | 主会话执行 + 单层审查子代理（宿主限制） | **3 层递归子代理**（subagent-v2）+ 并行委派 + 会诊 | **Pi**（能构建执行树） |
| **gate 生命周期** | gates.yaml 完整生命周期 + allowed_paths/forbidden_actions + 证据要求 | gates.json 同一事实源 + 同语义 scope | 平（Pi 移植自 ZCode） |
| **审批模型** | 每任务 REQUIREMENTS gate，人批准 | 同（人批准启动）；**执行中无卡点，质量达标自动放行** | **Pi**（流程更轻） |
| **状态校验** | validate_state.py 16 文件 + 8 不变式 + continuity 双哈希 | validateProject 6 项校验链（对齐） | ZCode 更全（continuity/事务写） |
| **证据链** | SHA256 三重锚定 + TOCTOU + 不可变 manifest | 评审记录哈希 + verification 证据 + 事件 stateSha256 | ZCode 更硬（不可变 manifest） |
| **事件溯源** | event_log.py 8 类型 + state_sha256 + replay-check | 20 类型 + stateSha256 + replay-check + 回放 | 平 |
| **HANDOFF** | 4 个 JSON 块投影 + 逐字段审计 | handoff.md + JSON 块 + 注入 | 平 |
| **质量环** | quality_pair + 独立审查 + CHECK_RECOMPUTE + 变异 M1/M2 | **L1 确定性规则 9 条 + L2 可执行验证 + L3 五 auditor 会诊 + 追溯矩阵 + 质量仪表盘** | **Pi**（验证自动执行 + 自动返工闭环） |
| **反幻觉** | subagent_evidence_verifier + 反幻觉闸门 + 评审必须调工具 | 同语义 + **FAIL 分支也拦 + 必须引用验证证据** | Pi 稍强 |
| **角色体系** | 12 角色 × 4 文件契约（纸面角色，同模型） | 5 auditor + 执行角色（同模型，但**有角色级记忆**） | Pi（记忆补盲点） |
| **记忆** | memory_service（规则式提取/注入） | **角色级记忆 + 缺陷模式库（defects.jsonl 结构化）** | **Pi** |
| **委托链** | C-001~C-005 授权拓扑（防自授） | 无（授权拓扑未移植） | **ZCode** |
| **事务写/防死锁** | journal + 幂等表 + stale 恢复 + 治理文件豁免 | 原子写（.tmp+rename）+ 迁移备份 | ZCode 更完善 |
| **审计账本** | ledger 链哈希 + guard-events + 变异报告 | audit 报告 + events + quality 仪表盘 | ZCode 更完善 |
| **机器强制** | **hooks 进程级拦截（不可绕过）** | tool_call 钩子（扩展层，可被禁用） | **ZCode**（强制力更强） |
| **测试** | 4404 全量 + 变异 M1/M2 + guard_health 正负控制 | 56 测试（node+bun）+ M1 9/9 | ZCode 更厚（规模） |
| **质量门禁** | release check 7 门禁（含 mypy 新增） | quality 门（验证+审计） | ZCode（发布级） |

### 1.2 各自优劣（诚实）

**ZCode Loop 优势**：
1. **机器强制力**——hooks 进程级拦截不可绕过（Pi 的 tool_call 钩子是扩展层）
2. **治理数据面更厚**——continuity 双哈希/事务写/幂等/不可变 manifest/ledger 链
3. **自我验证体系**——4404 测试 + 变异测试 + guard_health 正负控制（守卫活着）
4. **发布级门禁**——release check 7 门禁（现在含 mypy）

**ZCode Loop 劣势**：
1. **执行拓扑受限**——子代理不能拉子孙，无法构建执行树（宿主约束，非设计缺陷）
2. **"12 角色同模型"**——角色是纸面角色，无角色级记忆/立场演化
3. **流程偏重**——每任务 gate 批准 + 审批点多（用户批评点，部分已缓解但 approve 仍在）

**Pi Loop 优势**：
1. **真·多代理执行**——3 层递归 + 并行委派（delegate）+ 并行会诊（3 auditor）
2. **质量环自动闭环**——L2 机器验证自动执行 + 失败自动返工 + 达标自动放行（人不卡流程）
3. **角色级记忆 + 缺陷模式库**——经验跨会话积累（zcode 没有）
4. **可验证性设计**——产出必须自带验证方案（防偷懒/编造的最硬机制）
5. **追溯矩阵自动化**——AC↔实现↔测试断链机器检测

**Pi Loop 劣势**：
1. **强制力弱**——扩展钩子可被禁用/绕过（无进程级强制）
2. **数据面薄**——无 continuity/事务 journal/不可变 manifest/ledger
3. **无委托链**——授权拓扑未移植
4. **测试薄**——56 vs 4404；无 guard_health 正负控制
5. **单机单用户**——无发布级门禁

---

## 第二部分：本机 ZCode vs Pi 软件项目能力深度比较

### 2.1 环境事实

| 维度 | ZCode（loop-engine 宿主） | Pi agent（本机） |
|------|--------------------------|------------------|
| 模型 | deepseek-v4-flash（本会话）/ 配置可换 | deepseek-v4-pro（规划）/ flash（执行），1M 上下文 |
| 工具 | 文件/搜索/Bash/Agent（子代理）/MCP/WebFetch/技能系统 | 文件/搜索/Bash/subagent（3 层递归）/扩展插件/记忆库 |
| 扩展 | 插件 + hooks（进程级） + skills（13 角色） | TS 扩展（tool_call/before_agent_start 钩子）+ agents（5 auditor+执行）+ memory |
| 记忆 | MemPalace（跨会话宫殿）+ 项目 .ai/ | .pi/memory（目录即记忆库，项目+用户+角色级） |
| 治理 | loop-engine 全套（gate/证据/阶段机/委托链） | mini-loop v2（gate/质量环/事件/追溯） |
| 外部接入 | GitHub 推送/WebFetch/MCP | agent-bridge（微信 iLink）/pi-web |
| 会话 | 每任务一个会话，HANDOFF 交接 | --session 持久会话 + before_agent_start 注入 |

### 2.2 软件项目能力对照（能做/做不了）

| 能力 | ZCode | Pi | 说明 |
|------|-------|-----|------|
| **需求→设计→实现→测试全链** | ✅ 阶段机 S0~S11 强制 | ✅ 任务+质量环 | 都具备；ZCode 流程化，Pi 自动返工 |
| **多文件重构** | ✅ 主会话执行 | ✅ executor 委派 | Pi 可委派 worker 隔离执行 |
| **深度任务分解** | ⚠️ 单层子代理 | ✅ 3 层递归（planner→scout→worker） | Pi 强（能分层侦察+执行） |
| **质量保障** | ✅ 确定性检查器+变异测试+独立审查 | ✅ 质量环 L1/L2/L3+追溯+会诊 | 机制不同但都全；Pi 的验证是机器执行的 |
| **防 AI 编造** | ✅ 反幻觉+证据锚定 | ✅ 更硬（验证方案必须机器执行通过） | Pi 稍强（L2 自动执行） |
| **长任务自治** | ⚠️ 每任务人批准 gate | ✅ 批准后自动闭环（验证/返工/放行） | Pi 自治度高 |
| **跨会话经验** | ⚠️ MemPalace + .ai 记忆 | ✅ 角色级记忆+缺陷模式库 | Pi 强（缺陷模式注入评审） |
| **真实业务项目** | ⚠️ 需单独 gate（治理限制） | ⚠️ 无沙箱（文档明示需容器化） | 都需人工边界 |
| **发布/部署** | ✅ release check + 版本体系 | ❌ 无 | ZCode 强 |
| **外部协作** | ✅ git/GitHub | ✅ git + 微信接入 | 平 |
| **进程级强制** | ✅ hooks 不可绕过 | ❌ 扩展层 | ZCode 强（防绕过） |
| **性能** | ⚠️ 校验链有成本 | ⚠️ 每层 spawn 完整进程（线性成本） | 平（都有成本） |

### 2.3 组合使用建议（当前最优分工）

```
ZCode = 治理中枢 + 发布门禁 + 机器强制
  ├─ 管大项目（gate/阶段机/证据链/发布）
  ├─ 管"不可绕过"的边界（hooks 强制）
  └─ 管长期记忆（MemPalace + .ai）
Pi = 执行引擎 + 质量环
  ├─ 干深度活（3 层递归子代理/并行委派/会诊）
  ├─ 跑质量环（验证自动执行/自动返工/追溯矩阵）
  └─ 积累缺陷模式（角色级记忆跨会话）
协作模式：ZCode 定范围（gate 批准）→ Pi 执行+质量环闭环 → 产物回 ZCode 验收
```

---

## 第三部分：结论

1. **机制级**：ZCode 的"强制力/数据面/自我验证"和 Pi 的"执行拓扑/质量环/记忆"
   各占一边——差距主要来自**宿主能力**（hooks 强制 vs 扩展钩子；子代理递归 vs
   单层），不是设计意图差距
2. **能力级**：本机两 agent 组合后覆盖了"深度执行 + 质量闭环 + 强制治理 +
   发布门禁"完整链；单用任何一个都有明显短板（ZCode 执行浅、Pi 强制弱）
3. **质量环是 Pi 的差异化优势**：L2 机器验证 + 自动返工 + 追溯矩阵 + 缺陷模式
   记忆——这是 zcode 没有的，也是"防 90% 屎山"的主力
4. **下一步最优投入**：把 Pi 的验证证据（verification-evidence）回灌 zcode
   验收流程（ZCode 收口时引用），形成"Pi 执行→质量证据→ZCode 验收"闭环

---

## 第四部分：ZCode 与 Pi 联动指南（2026-08-10 补充）

> 回答"两者能否联动 / 是否只能各自开会话"——**能联动，三条通道**：

### 通道 1：git 中转（异步，已在用）
双方操作同一 git 仓库（loop-engine / pi-agent-extensions），提交即交接：
Pi 完成 → push → ZCode 会话拉取验收；反之亦然。零成本，人工切换会话时自动接上。

### 通道 2：文件握手（异步，闭环载体）
Pi 侧质量环证据（verification-evidence / audit 记录 / 追溯矩阵）落盘
`~/.pi/agent/loop/<project>/` → ZCode 侧跑
`.zcode/tools/pi_evidence_import.py` 导入 `.ai/evidence/<task>/`
（防篡改校验 + 格式对齐）→ ZCode 收口引用。**已实现并演示**（`5442de7`）。

### 通道 3：进程互调（实时，双向）
- **Pi → ZCode 治理**：Pi 的 Bash 工具可直接运行 zcode 治理 CLI（纯 Python）：
  `C:/Python312/python.exe <loop-engine>/.zcode/tools/validate_state.py <root>`
  （先例：sync_configs.py 已由 Pi 侧调用，把 ~/.pi/agent 镜像回 pi-agent-config）
- **ZCode → Pi 执行**：ZCode 的 Bash 可调 pi headless 模式：
  `pi --mode json -p --append-system-prompt <prompt.md> "<任务>"`
  （pi 支持无交互执行——spawnPiJson 内部就是这种调用；ZCode 把 pi 当外部执行器，
  用于"深度执行"委派：ZCode 定范围 → pi 递归执行 → 证据回灌验收）

### 推荐工作流（无需手动切会话的联动形态）
```
1. ZCode 会话：登记任务 + gate 批准 → 生成任务包（AC/验证要求/范围）
2. （可选）ZCode 调 pi CLI 派发执行，或用户到 pi 会话执行（--session 持久化）
3. Pi 质量环：L1/L2/L3 自动闭环 → 证据落盘 Pi 侧
4. ZCode 会话（下次启动）：pi_evidence_import.py 导入证据 → 收口验收
5. git push/pull 保持两侧同步
```

### 限制（诚实）
- 实时互调（通道 3）目前是"命令行级"（zcode 调 pi 无 UI/交互确认；pi 调
  zcode 只有治理工具 CLI）——完整双向 agent 协议需另行设计（P2 候选）
- 通道 2 的 import 是"证据复制"，不是"状态同步"——ZCode 侧状态仍以 .ai/ 为准
