# T-0087~T-0090 任务计划编排（task-plan）

> **T-0086 交付物 | 2026-08-01 | 输入：staffdeck-benchmark.md（D1-D10/U1-U9）**
> 本计划只编排，不创建任务文件/不登记 gate。各任务由用户单独发起并批准 REQUIREMENTS gate 后执行。

## 编排原则

1. **价值优先**：治理资产注册化（U1）与行为契约化（U2）先做 —— 直接服务"证据链完整可审计"与"约束无漂移"。
2. **依赖约束**：T-0087/T-0088 独立于 T-0089；T-0090 依赖前序（LLM 抽象是自举审计的前提）。
3. **规模可控**：每任务 ≤60 文件、有明确 AC、可独立验收（沿用 T-0085/T-0086 模式）。
4. **不弱化约束**：所有升级保持 fail-closed 语义，禁止放宽已激活检查。

## T-0087 — 运行时契约化（U1 + U2）

| 项 | 内容 |
|---|---|
| 主题 | CapabilityRegistry 化 + 契约平面化 |
| 范围 | ① `.ai/checkers/` 与 `.ai/guards/` 注册表化：显式注册 → seal() 冻结 → 确定性快照（sha256 snapshot_id）→ 只读映射；重水合 fail-closed（版本/契约不匹配抛错，不静默降级）；与 guard_health.py 正/负对照电池集成 ② `tests/vertical_slice/` 升级为多平面 golden 场景（domain/events/conversation/state 4 平面起步）+ 需求注册表 + conformance 报告 + gate_decision |
| 允许路径 | .ai/、loop_core/、tests/、docs/ |
| 依赖 | T-0086 |
| AC 概要 | AC-01 注册表 seal 后不可变且有快照指纹；AC-02 注册表与 guard_health 集成（死亡/遗漏均被检测）；AC-03 任一 checker/guard 版本漂移 → fail-closed 报告；AC-04 vertical_slice 契约平面 ≥4 + conformance 门禁；AC-05 全量测试无回归；AC-06 无约束弱化（diff 审查） |
| 风险 | 注册表化可能引入契约版本兼容负担（中）；golden 场景维护成本（低） |
| 承接 | StaffDeck capabilities/registry.py + contracts/agent/v1 模式 |

## T-0088 — 上下文与路由升级（U3 + U5 + U6）

| 项 | 内容 |
|---|---|
| 主题 | 上下文预算压缩 + 路由粘性/任务帧 + 人工接管 resume |
| 范围 | ① `loop_core/context_loader.py`：预算触发式压缩（如 70% 阈值）+ 摘要的摘要（层级压缩）+ evidence 引用截断修复（StaffDeck citations 邮箱前缀思路移植到 .ai/ 证据引用）② `loop_core/intent_router.py`：active 任务粘性规则（不重复问）+ 多意图回合内任务帧 + fail-safe 降级（异常保持现状；约束执行仍 fail-closed，两者不冲突）③ `loop_core/human_review_packet.py`：resume payload（gate 暂停 → 机器可恢复上下文，类似 StaffDeck HumanHandoffRequest） |
| 允许路径 | .ai/、loop_core/、tests/、docs/ |
| 依赖 | T-0086 |
| AC 概要 | AC-01 压缩有 token 预算触发测试；AC-02 路由粘性/任务帧有行为测试；AC-03 resume payload 可恢复 gate 决策上下文；AC-04 全量测试无回归；AC-05 无约束弱化 |
| 风险 | 压缩可能丢信息（中，需保留证据链完整性）；粘性可能误延续任务（低，需降级路径测试） |
| 承接 | StaffDeck context_projection.py / router.py / human_handoff_service.py 模式 |

## T-0089 — 学习回路与工程化（U4 + U7 + U8 + U9）

| 项 | 内容 |
|---|---|
| 主题 | gate 决策反馈回路 + evidence 可靠投递 + 可观测性分层 |
| 范围 | ① gate 拒绝/修复请求 → 经验沉淀（可检索，改善 human_review_packet 与决策包质量）② `transactional_write_texts` 补幂等 + 退避重试 + 卡死重置（StaffDeck outbox 模式）③ guard 检查结果观测（耗时/频率/失败原因事件），事件/指标/日志三层分离，观测异常不阻断业务（安全裁决仍 fail-closed）④ scripts/ dev.py 生命周期（up/down/status + pid + 健康轮询），若 AutoPlan 产品化则作为前置 |
| 允许路径 | .ai/、loop_core/、hooks/、tools/、scripts/、tests/、docs/ |
| 依赖 | T-0087 或 T-0088 任一完成后 |
| AC 概要 | AC-01 反馈回路有沉淀与检索测试；AC-02 evidence 幂等/重试有测试；AC-03 观测事件落盘且异常不阻断业务；AC-04 全量测试无回归；AC-05 无约束弱化 |
| 风险 | 观测与裁决解耦需明确边界（中）；幂等改造可能影响现有证据写入（低） |
| 承接 | StaffDeck feedback/service.py + service_outbox.py + observability/ 模式 |

## T-0090+ — 新能力引入（D1/D5/D7/D2，规划）

| 项 | 内容 |
|---|---|
| 主题 | LLM 接入抽象层 + 工具执行器/MCP + 异步任务设施 + SLO/指标 |
| 范围 | ① LLM 客户端抽象（3 协议驱动起步：OpenAI 兼容必做，Anthropic/Gemini 可选；统一重试/JSON 修复/脱敏/输出钳制）—— 自举审计回路（B5）前置 ② 工具执行器 + MCP 客户端（B3 设计落地，含工具白名单/超时/错误码）③ 异步任务队列（AsyncJob 模式：后台执行治理长任务 + 租约领取防重复）④ SLO/指标子系统（B2 设计落地） |
| 允许路径 | 待任务发起时定义 |
| 依赖 | T-0089；D1 是 B5 自举审计的前置 |
| AC 概要 | 待任务发起时定义 |
| 风险 | 引入 LLM 层需密钥管理（禁止硬编码，环境变量 + 加密）；MCP 执行面扩大需白名单与审计 |
| 承接 | StaffDeck llm/client.py + tools/mcp_client.py + scheduled_tasks/ 模式；B1/B2/B3 设计文档为内部输入 |

## 执行建议

1. 用户逐任务发起（"批准 T-008X 需求"），每任务独立 REQUIREMENTS gate。
2. 每任务沿用 T-0086 流程：任务文件 → task_graph/gates/state 登记 → gate 展示 → 批准 → 启动证据 → 派发 developer → 验收证据 → 提交。
3. T-0087 与 T-0088 可并行（独立范围），但建议顺序执行以保持单线程治理记录清晰。
