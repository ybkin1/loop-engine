# T-0113 验收报告 — 死工具删除执行（A 组 6 薄壳 + C 组 2 legacy）

- 任务：T-0113（G-T-0113-REQUIREMENTS，approved）— 执行 T-0111 终态审计批准的死工具删除
- 角色：governance-controller（编排与验收）；developer（删除执行）；independent-reviewer（独立审查）
- 执行时间：2026-08-04（UTC+8）
- 基线：git HEAD `3623584`（v3.12.48，T-0111）；版本 bump **3.12.49**
- 批准：用户消息"1"（批准死工具删除事项）；复核依据：`.ai/evidence/T-0111/fixes/final-audit.md`

---

## 一、删除与同步

| 项 | 内容 |
|----|------|
| 删除（8 个） | A 组 6 薄壳（tool_quality_gates/tool_security_scan/tool_dependency_analysis/tool_contract_validate/tool_cost_tracker/tool_evidence_chain）+ C 组 2 legacy（scripts/evidence_chain.py、scripts/security_scan.py）——`git diff --diff-filter=D` 恰 8 项 |
| 引用同步 | capability_registry manifest **36→30**（仅 A 组 6 条目在 manifest；C 组 scripts 无条目）双向零缺口（missing=[] orphan=[]）；server.py `_dispatch` 零被删模块引用（7 个 MCP 内联键 LIVE）；tests 更新（30 计数 + TestInlineDispatchLive + test_shell_modules_removed 删除守卫）；docs（06-delivery/ops-handoff）同步 |
| 保留保护 | B 组 4 个（tool_task_queue/tool_eval/loop_vertical_slice/loop_dispatch_role——待用户确认后单独删）+ run_security_scan/run_quality_gates（server.py:41/61 子进程契约 LIVE）均未动 |
| 零改动 | hooks/ diff 为空；治理内核仅 capability_registry；历史证据 `.ai/evidence/` 零改动 |

## 二、AC 对照

| AC | 验收标准 | 结果 |
|----|---------|------|
| AC-01 | 删除恰 8 个 + 白名单 | **PASS**（diff-filter=D 恰 8 项；B 组/run_* 保护断言） |
| AC-02 | capability_registry 双向零缺口 | **PASS**（30/30，missing=[] orphan=[]，独立断言） |
| AC-03 | 全仓 grep 无被删工具符号引用 | **PASS**（import/符号级 0 命中；剩余提及均在约束保护区） |
| AC-04 | 全量回归 0 failed + compile + release check 6/6 | **PASS**（独立复验 4169 passed；5 failed 全部 HEAD 基线或提交前在途态，0 项与删除相关；提交后达成） |
| AC-05 | 版本 3.12.49 == git HEAD | **PASS**（提交后成立） |
| AC-06 | 独立审查 GO + hooks/ 零改动 + 保留契约验证 | **PASS**（GO，P0/P1/P2=0） |

## 三、独立审查摘要（independent-review.md）

- **裁决：GO**（P0/P1/P2=0；P3×6 措辞级，不阻断）
- 删除精确性：8 个文件复核均为自标 DEPRECATED 薄壳/legacy，无唯一逻辑丢失
- 保留保护：B 组 + run_* 存在未动；server.py 子进程契约 LIVE（实际行号 41/61）
- 引用同步：30/30 双向零缺口独立断言；7 个 MCP 内联键 LIVE；docs 同步正确
- 全量回归独立复验：4169 passed / 5 failed（0 项与删除相关）

## 四、裁决

**T-0113 验收通过（6/6 AC）。** 死工具删除执行完成：8 个文件精确删除 + 引用同步闭环
（注册表 30/30 双向零缺口、零悬挂引用、MCP 内联键 LIVE）、保留文件契约完整、
hooks/ 零改动。版本 3.12.49。

## 五、下一步

- B 组 4 个（tool_task_queue/tool_eval/loop_vertical_slice/loop_dispatch_role）待用户确认
  无外部调用后单独删除
- T-0106 排布 + 死工具删除全部闭环；工程 idle 稳态
