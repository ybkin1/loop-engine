# Prompt Contract

```yaml
prompt_id: "PROMPT-<id>"
version: "0.1.0"
owner_role: "<role>"
purpose: "<one measurable purpose>"
source_materials: ["<material_id>"]
inputs:
  required: ["<input>"]
  forbidden: ["<secret or untrusted input>"]
instructions:
  - "<observable instruction>"
constraints:
  must: ["<MUST rule>"]
  should: ["<SHOULD rule>"]
  must_not: ["<prohibited behavior>"]
output_contract:
  format: "<markdown|yaml|json|patch>"
  schema: "<path or schema id>"
  required_fields: ["<field>"]
evidence_required: ["<command/result/reference>"]
failure_behavior: "<block|ask|degrade|handoff>"
reviewer: "<independent role>"
freshness_policy: "<when source/context must be reloaded>"
```

门禁：提示词必须有可验证输出、失败行为和外部证据；不能以“请像专家一样”作为能力证明。
