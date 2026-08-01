# T-0095 Commands

任务：遗留清理包 — P3 技术遗留系统性清理
Gate：G-T-0095-REQUIREMENTS（approved 2026-08-02，approval_text="批准T-0095、96、97"）

## 登记与启动

1. 批量登记（T-0095/96/97 三任务 + 三 gate + 边链 T-0094→95→96→97）；state 串行指向 T-0095
2. 创建 approval/execution-evidence.json；compile_gate 生成 compile-evidence.json
3. 修复 gates.yaml YAML_DUPLICATE_KEY（T-0094 尾部 high_risk_flags 被新 gate 块挤到 G-T-0097 后 —— 移回 T-0094 块）
4. `repair_continuity.py` + `close_session.py` + `validate_state.py` — [ok] state is usable
5. 顺手修复：`.ai/tasks/T-0094.md` 双 status 位 → completed

## 实现（developer 子代理 agent_a3bfd86b，10 项清理）

6. **死导入**：capability_registry.py 删除 `field`（ruff F401 0 命中）
7. **slo.yaml 显式化**：.ai/slo.yaml 程序化生成（14 条 SLI + budget 100 + fee 5，与 B2 内置逐字段一致）+ load_slo_config fail-closed 校验（9 类非法配置拒绝）
8. **guard-events 轮转**：GuardEventRecorder max_lines=10000/max_bytes=10MB/max_archives=3（.1/.2/.3 链 + read_events 含归档 + 失败静默）
9. **env 链统一**：keys.py KEY_TIERS 规范表（LLM→ANTHROPIC→OPENAI→ZCODE，key/base_url/protocol 成对）+ resolve_api_base_url；ENV_TIERS = KEY_TIERS 同一对象
10. **引用修复边界**：repair_truncated_references 跳过"更长已解析 token 子串"（测试抓到首版漏记缺陷并修复）
11. **metrics_view 顶层非对象** → NOT_AVAILABLE
12. **SLO 双重检查去重**：check_slo_gate 单次开关检查（禁用先短路）
13. **豁免口径统一**：hook_common 单一判定源 is_readonly_exempt（path_guard/loop_enforcement 删除本地内联，写入拦截零放宽）
14. **gate_lesson 锁**：threading.Lock 包 RMW
15. **HANDOFF 模板引用**：创建 .ai/evidence/T-0095/evidence-manifest.v1.yaml（verify_evidence_manifest OK）
16. 测试 43 项新用例；证据：cleanup/design.md（含 4 项归档记录）

## 治理同步（主会话）

17. 独立审查（agent_73cfa080）：CONDITIONAL_GO — 7/7 AC PASS；写入拦截逐行 diff 零放宽；P1（HANDOFF 块过期）+ P3（acceptance 待补）
18. P1 修复：close_session 重建 HANDOFF（manifest 创建后）→ [ok] state is usable
19. 落盘 commands.md + acceptance/acceptance-report.md

## 验收

20. 全量测试：3521 passed / 63 skipped / 12 xfailed / 0 failed（基线 3476 + 45）
21. 状态收敛（task_graph T-0095 completed + state idle）+ close_session
22. git 提交 v3.12.34

## 发现（归档记录，不改代码）

- Bash 反斜杠路径 shlex tokenizer（Windows 路径损坏，改造风险高）
- 粘性不继承 loop_mode（设计语义）
- dev.py POSIX 分支真机验证（无 POSIX 主机）
- 未知任务 id 边展示语义（设计语义）
- hooks 两文件 11 处既有 F401（本次零引入）
