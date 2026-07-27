# 决策规则：evidence、批准与三个 hook 的边界

## Evidence ≠ Approval

以下全部是 evidence，没有任何一个能构成用户批准：

- reviewer PASS、validator 退出码 0、测试全绿
- hook 放行（hook 只证明"没被阻断"，不证明"被授权"）
- AI 自己的推荐、分析、置信度

用户批准的唯一起源是**用户消息中的明确决策文本**。记录批准时必须留存
approval_text 与 approval_evidence，且 approval_actor = user、
approval_source = explicit_user_message。

## 批准与执行的双段确认

1. 用户说"批准 G-XXXX" → 只记录 decision = approved。
2. 用户说"执行已批准的 G-XXXX" → 才开始执行。

合在一句话里的（"批准并执行"）要拆成两步记录，防止滑坡。

## gate_guard 的决策记录豁免：为什么允许 pending 期间写 gates.yaml

死锁分析：

1. 创建 pending gate 需要写 `.ai/gates.yaml`（注册）。
2. 用户批准/拒绝后，需要写 `.ai/gates.yaml`（记录 decision）。

如果 pending 期间阻断一切写入，第 2 步永远无法完成——gate 永远 pending，
项目永久停机。因此 gate_guard 对 `.ai/gates.yaml` 豁免。

这不是漏洞而是设计：**写 gates.yaml 不等于批准生效**。决策记录的真实性由
后续检查保证（approval_text / approval_evidence 必须存在且指向真实用户消息；
validate_gate_register.py 会校验）。hook 防的是"pending 期间偷偷干别的"，
决策记录的真实性由审计防。两道防线职责不同。

## path_guard 的 ask 语义

保护区（AGENTS.md、stable/、registry/、.zcode/config.json、.zcode/tools/）
是治理体系的权威事实与执行层。历史事故（T-0030 直接修改正在使用的全局脚本）
证明：**AI 在"执行已授权任务"时仍可能漂移进这些路径**。

ask 模式把每次保护区写入变成用户的当场决策——这符合"用户即信任锚"：
对非技术用户，一个明确的客户端确认弹窗比一份 246 行的 YAML gate 请求更真实。

## Hook 放行的含义（重要）

hook 放行 ≠ 授权。hook 只检查两类硬不变量（pending gate、保护区），
任务范围、allowed_write、禁止动作等语义约束仍由 SKILL.md 程序与你的自律保证。
**hook 是地板，不是天花板。**
