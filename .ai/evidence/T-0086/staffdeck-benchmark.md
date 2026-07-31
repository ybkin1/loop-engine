# StaffDeck 对标分析证据（staffdeck-benchmark）

> **T-0086 交付物 | 2026-08-01 | 来源：本会话 3 个探索子代理深度源码研究（60+ 文件精读，raw.githubusercontent.com / GitHub API / jsdelivr CDN 实抓）+ loop-engine 本地盘点（276 py / 77,808 行 / 2,747 测试）**
> 结论分级：**事实** = 源码直接可见；**推断** = 基于源码的合理推论。

## 1. 对标对象

| 项 | 值 |
|---|---|
| 仓库 | OpenBMB/StaffDeck（企业数字员工平台，1.3k stars） |
| 技术栈 | Python 3.11+ / FastAPI / SQLite(SQLModel)；React 18+TS+Vite+Tailwind；自研轻量 MCP 客户端 |
| 规模 | backend ~3.5 万行（agent 核心 ~1.5 万 + 能力层 ~1 万 + 渠道/安全/API ~1 万）；contracts/agent/v1 契约工程 |
| 定位 | 面向企业员工的数字员工运行时产品（与 loop-engine 的"治理引擎"互补） |

## 2. StaffDeck 核心机制摘要（事实）

### 2.1 Agent 核心层（~1.5 万行）
- **AgentLoop（5824 行）**：非流式/流式共享 `_prepare_turn` 管线（选模型→Router→槽位水合→技能图激活→StepAgent→知识循环→工具循环→反思闸门→记忆捕获）；收尾三态 continued/completed/handoff；多任务帧（task_frames）单轮多 SOP 顺序执行。
- **Router（233 行）**：纯 LLM 分类 9 决策类型；粘性规则（active 技能沿用）；非法目标降级 clarify；`task_frames` 表达复合意图。
- **StepAgent（262 行）+ ReflectionAgent（136 行）**：执行器 + 异常闸门；正常路径零额外 LLM 成本（有 next_step 不反思）。
- **上下文工程**：单系统提示词 + 阶段化 user 消息（stage_protocol）；游标摘要（token 预算 70% 触发压缩，摘要的摘要）；操作级输出 token 钳制（19 类）；模型配置指纹（sha256）。
- **LLM 层（client.py 1396 行）**：3 协议驱动（OpenAI/Anthropic/Gemini）；统一错误码带 retryable；空响应重试；reasoning 截断自动翻倍 max_tokens；JSON 修复多候选 + 修复上下文重生成；敏感信息脱敏。

### 2.2 能力与工具层（~1 万行）
- **CapabilityRegistry**：显式注册 → seal() 冻结 → 确定性快照（sha256 snapshot_id）→ 只读映射；重水合 fail-closed（版本不匹配抛 LookupError，不静默降级）；Protocol 鸭子类型适配。
- **技能蒸馏（1174 行）**：生成→修复→分段生成→最小草稿自愈阶梯；SkillCard 状态机；7 维度 rubric 反思（3 轮）；工具引用清理。
- **工具层**：自研 MCP 客户端（586 行，stdio/http/SSE 三传输）；工具白名单（allowed_skills）+ 租户可见性 + 错误码体系。
- **知识检索（2374 行）**：九阶段入库 Job（可取消）；OKF 概念页体系；多阶段检索路由 → evidence_pack + 编号引用 + 邮箱前缀截断修复。
- **记忆与反馈闭环**：异步 LLM 提取（upsert/delete diff）；反馈归因 6 bucket → 技能健康度回流。

### 2.3 渠道/安全/部署层（~1 万行）
- **渠道内核**：Protocol 鸭子类型 + 导入即自注册适配器表；outbox 可靠投递（条件 UPDATE 领取、指数退避、120s 卡死重置、幂等键）；入站幂等（唯一约束 + client_turn_id 去重 + 处理器代次 + 崩溃清扫）。
- **安全**：Fernet 凭据加密（独立 CHANNEL_SECRET）、PBKDF2（120k 迭代）、常量时间比较、统一 404 防枚举、域名白名单防 SSRF、生产关 docs。
- **契约工程**：contracts/agent/v1 = 21 JSON Schema + 17 黄金场景（GT01-17）+ 5 观测平面（domain/sse/db-events/conversation/legacy-provider）+ 30 需求注册表 + conformance-report 带 gate_decision —— 用测试基础设施治理 legacy 行为漂移。
- **部署**：单端口（FastAPI 同服前端/API/Swagger）、dev.py 生命周期（up/down/status + pid + 健康轮询）、PyInstaller 桌面端、4 平台 CI 打包签名公证。

## 3. 差距清单（loop-engine 不足，D1-D10）

| # | 差距 | StaffDeck 现状 | loop-engine 现状 | 影响 | 优先级 |
|---|---|---|---|---|---|
| D1 | 无 LLM 接入抽象层 | 3 协议驱动 + 统一重试/JSON 修复/脱敏/输出钳制 | 依赖宿主（ZCode）；无自身 client | 自举审计回路（B5）需自己调 LLM | P1（T-0090） |
| D2 | 无运行时指标/SLO | EventLog + spans + llm_operation 观测 | evidence/ledger 审计链，无性能指标 | guard 只测"活不活"不测"质量" | P1（B2 设计就绪） |
| D3 | 无知识/记忆服务 | OKF 知识库 + 记忆提取/注入 | 无（.ai/ 文件 + HANDOFF 手写） | 跨任务经验无法沉淀 | P1（T-0089 部分） |
| D4 | 无前端产品层 | React 企业工作区（16 管理页） | AutoPlan dashboard 雏形 | 非技术用户可视化交付弱 | P2 |
| D5 | 无工具执行器/MCP | 自研 MCP 客户端 + 白名单 | B3 设计就绪未实现 | 治理无法直接执行外部检查器 | P1（T-0090） |
| D6 | 契约测试未覆盖运行时行为 | 5 平面 golden fixtures + conformance 门禁 | contract_verifier 静态验证 + vertical_slice 切片 | 行为漂移检测不够系统化 | P1（T-0087） |
| D7 | 无异步任务基础设施 | AsyncJobQueue + 租约式领取 | dispatch_lease 有租约；无通用异步/退避 | 长耗时治理操作无后台化 | P2（T-0090） |
| D8 | 无发布/产物体系 | 4 平台 CI 打包 + 桌面安装器 | install/uninstall 脚本 | 交付物无"产品"形态 | P3 |
| D9 | 无身份/多租户 | 租户隔离 + 渠道身份绑定 | 单用户本地 | 多人协作无模型 | P3 |
| D10 | 巨型文件 | agent_loop 5824 行（作者自认缺陷） | hard_constraints.py 45KB 同类问题 | 演进成本 | P2（持续） |

## 4. 可升级点（U1-U9，StaffDeck 借鉴映射）

| # | 升级 | StaffDeck 来源 | loop-engine 落地位置 | 价值 | 承接任务 |
|---|---|---|---|---|---|
| U1 | CapabilityRegistry 模式 | capabilities/registry.py（seal+快照+fail-closed 重水合） | .ai/checkers/ 与 .ai/guards/ 注册化 + snapshot_id + 契约版本握手 | 防 guard 遗漏/漂移（guard_health 已测死亡，注册表补遗漏） | T-0087 |
| U2 | 契约平面化 | contracts/agent/v1（5 平面 + 需求注册表 + conformance 门禁） | tests/vertical_slice/ 升级为多平面 golden 场景 + gate_decision | 行为漂移系统化检测 | T-0087 |
| U3 | 上下文预算压缩 | context_projection.py / conversation_context.py（游标摘要、70% 预算、摘要的摘要） | loop_core/context_loader.py 升级（预算触发压缩 + 层级摘要 + evidence 引用截断修复） | .ai/ 巨量治理记忆可压缩加载 | T-0088 |
| U4 | gate 决策反馈回路 | feedback/service.py（6 bucket 归因）+ skill 健康度 | 拒绝/修复请求 → 经验沉淀（human_review_packet 质量改进） | 服务 north star（非技术用户） | T-0089 |
| U5 | 路由粘性 + 任务帧 | router.py（9 决策 + 粘性 + task_frames + 降级 clarify） | loop_core/intent_router.py 升级（active 任务粘性、多意图回合内编排、fail-safe 降级） | 减少重复提问 | T-0088 |
| U6 | 人工接管 resume | human_handoff_service.py（resume payload 恢复 SOP 状态） | human_review_packet.py 升级（gate 暂停 → 可机器恢复上下文） | gate 决策连续性 | T-0088 |
| U7 | evidence 可靠投递 | service_outbox.py（幂等键 + 条件领取 + 退避 + 卡死重置） | transactional_write_texts 补幂等 + 重试队列 | 证据落盘可靠性 | T-0089 |
| U8 | 可观测性分层 | event_log.py / spans.py / runtime_logging.py（三层分离 + 异步队列不阻塞业务） | guard 检查结果补耗时/频率/失败原因观测 | 治理可观测 | T-0089 |
| U9 | dev.py 生命周期 | scripts/dev.py（up/down/status + detach + pid + 健康轮询） | scripts/ 升级（若 AutoPlan 产品化） | 产品化 | T-0090+ |

## 5. loop-engine 领先项（对等视角，StaffDeck 可学习）

1. **约束强制力**：C1-C11 机器硬约束 + BLOCKER 语义 + test_bypass_matrix.py 绕过矩阵 —— StaffDeck 无此层
2. **证据链**：approval_ledger（SHA256+TTL+scope 指纹）、audit_ledger（链式 hash JSONL）、evidence_chain（因果链）—— StaffDeck 只有契约 fixtures
3. **Guard 健康检查**：guard_health.py 正/负对照电池（T-0083）—— StaffDeck 无
4. **角色认证**：12 角色 + CONTRACT.yaml 9 字段 + 可验证挑战 —— StaffDeck 仅 admin/member
5. **阶段状态机**：S0-S11 + 每阶段门禁证据 —— StaffDeck 无阶段概念
6. **fail-closed 工程化深度**：17 hook 脚本 + 事务写入 + 文件指纹 —— 远超 StaffDeck

## 6. 借鉴落地映射（结论）

- **本任务（T-0086）**：hook 只读误伤修复（本会话实测复现：Read 项目外被 path_guard 当写入拦截）、PROGRESS 漂移、对标证据落盘、任务计划编排。
- **T-0087**：U1（CapabilityRegistry 化）+ U2（契约平面化）—— 治理资产注册化与行为契约化。
- **T-0088**：U3 + U5 + U6（上下文压缩、路由粘性/任务帧、人工接管 resume）。
- **T-0089**：U4 + U7 + U8（反馈回路、证据投递、可观测性）。
- **T-0090+**：D1/D5/D7/D2（LLM 抽象、MCP 执行器、异步设施、SLO）—— B1/B2/B3 设计就绪待落地。

## 7. 事实与推断标注

- 上述"事实"条目均来自子代理源码研究（行号与文件在报告中可追溯）；"影响/价值/优先级"为推断。
- StaffDeck 已知缺陷（推断/事实）：agent_loop 巨型文件、进程内取消不跨进程、路由纯 LLM 无兜底、上下文 token 估算对中文偏差、通用技能沙箱无容器级隔离、SQLite 单写者横向扩展受限、自研令牌无吊销机制、APP_SECRET 默认值风险。
- loop-engine 本会话发现（事实）：T-0085 完成时 PROGRESS.md 未同步（漂移，本任务已修）；hook 只读误伤（本任务已修，测试证明）；主会话 active task 下非治理读写需 runtime projection（既有设计）。
