# T-0118 修复记录：seven-state-consumption

## 背景

T-0109 遗留 #1：`loop_core/subagent_evidence_verifier.py` 输出 7 个布尔 checks
（file_exists/valid_json/not_simulated/has_session_id/independent_session/
required_fields/files_covered），未消费 `loop_core/schemas/evidence_state.py`
的 EvidenceState 七态（coerce 入口 T-0109 已就绪）。设计约束：七态仅供
呈现/度量，不进 gate 判定。

## 修改清单

| 文件 | 修改 |
|------|------|
| `loop_core/subagent_evidence_verifier.py` | +`checks_to_evidence_state()` 映射函数（模块顶层文档映射表）+ `verify_review_evidence` 全部 4 个 return 点增加 `evidence_state` 字段 + 模块顶层项目根 sys.path 注入（独立脚本运行加固，本机 python312._pth 隔离模式） |
| `tests/test_t0118_seven_state.py` | 新增 21 项测试（映射表/集成/既有行为零变化/呈现层静态断言） |

## 映射规则（checks → EvidenceState，阶梯）

```
file_exists=False                          → Missing（应存在但缺失）
valid_json=False                           → Present（存在但不可解析）
not_simulated/has_session_id/
independent_session/required_fields 任一失败 → Present（存在但未达可信/溯源标准）
全部通过但 files_covered 未检查或失败      → Exercised（已执行，覆盖未完全验证）
全部通过                                   → Outcome-supported（结果支撑结论）
Wired / N-A / Unobserved 不由此路径产生（接线/适用性/观测性由消费方上下文判定）
```

## 验证

- test_t0118_seven_state 21/21 PASS；test_t0109_f1_eval_model 58 PASS（coerce 消费方零变化）
- test_ai_doc_links 8 PASS（KNOWN_ISSUES 反引号行号措辞修正）
- 全量回归 4205 passed（仅 manifest 在途态 + t0108 漂移 repair 后 34 passed）
- hooks/ 零改动：gate_evidence_checks.py trace-only 调用点未触碰
