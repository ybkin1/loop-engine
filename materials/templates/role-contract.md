# Role Contract

```yaml
role_id: "ROLE-<id>"
role_name: "<产品经理|架构师|质量工程师...>"
identity_and_experience: "<required capability, not marketing label>"
fixed_position: ["<role's non-negotiable concern>"]
responsibilities: ["<in-scope responsibility>"]
forbidden_actions: ["<out-of-scope action>"]
inputs: ["<approved artifact or evidence>"]
outputs: ["<named artifact>"]
quality_standards: ["<checkable standard>"]
veto_conditions: ["<condition that blocks handoff>"]
evidence_required: ["<tool output|test|trace|review finding>"]
admission_checks: ["<capability probe>"]
runtime_checks: ["<runtime behavior probe>"]
effectiveness_checks: ["<outcome probe independent of self-report>"]
handoff_in:
  required: ["<upstream artifact/version>"]
  reject_if_missing: ["<missing condition>"]
handoff_out:
  consumer: "<next role>"
  package: "<review packet or work packet>"
  unresolved_items: "<required format>"
```

门禁：角色不能同时担任自己的独立评审员；`PASS` 必须由证据和独立检查得出。
