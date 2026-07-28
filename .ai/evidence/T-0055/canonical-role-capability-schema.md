# Canonical Role Capability Schema v0.1

## 目标

为 11 个 Loop 角色提供统一、精简、高能力密度的设计结构。通用治理语义只定义一次；角色文件只填写差异化内容。

## 必填字段（12 个）

1. `mission`：一句话使命与交付边界。
2. `authority`：可决定、必须升级、禁止决定。
3. `inputs`：必需输入、完整性检查、不可信输入处理。
4. `outputs`：唯一主 artifact、schema、必填证据字段。
5. `core_checks`：按风险排序的 5–8 项核心检查。
6. `failure_semantics`：`PASS | FAIL | BLOCKED | UNAVAILABLE | NOT_VERIFIED | ABSTAIN` 的触发规则。
7. `tools`：工具、最低调用要求、工具不可用语义。
8. `challenges`：最多 2–3 个高信息量 challenge，覆盖关键正向/负向/证据风险。
9. `veto_escalation`：否决条件、升级对象、用户决策触发器。
10. `handoff`：上游验收、下游交接字段、finding 关联。
11. `freshness`：证据有效期、重新验证触发条件。
12. `known_blind_spots`：明确不负责的领域，防止重叠和漏检。

## 通用结果语义

- `PASS`：所有必需检查已执行且证据可复核。
- `FAIL`：检查已执行，发现可定位问题。
- `BLOCKED`：安全、治理、契约或用户决策阻断，不能继续。
- `UNAVAILABLE`：必需工具/输入不可用，不能声称检查通过。
- `NOT_VERIFIED`：证据不足或未完成独立验证。
- `ABSTAIN`：超出角色权威边界，必须转交专业角色或用户。

## 设计反臃肿规则

- 通用字段、状态、finding 和 evidence schema 不在角色文件重复。
- 每条核心检查必须对应动作、判定或证据字段；口号删除。
- 每个角色最多 3 个 challenge；优先选择能同时暴露多个失效模式的 challenge。
- 角色差异必须可追踪到职责、工具、否决权或交接要求。
- 角色设计完成不等于角色认证完成。
