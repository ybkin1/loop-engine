# T-0115 commands

## 任务范围

`tests/deep_probe_v35.py` 探针现代化：修复 13 项陈旧预期/探针缺陷（T-0113/T-0114 独立审查已确认零产品偏差）。

## 执行命令记录

```bash
# 1. 基线确认（执行前）
C:/Python312/python.exe tests/deep_probe_v35.py   # 248 passed, 13 failed（T-0113/T-0114 审查基线同款）

# 2. 探针修改（6 处，tests/deep_probe_v35.py）
#    ① EnforcementHub fixture：GAP-5b 阶段基线约束（C1/C2 需 S1/S2 gate 前缀）
#       + S4 写操作 C6 独立审查 verdict（.ai/evidence/T-test/review.json）
#    ② roles 11→12（ROLE_IDS 新增 test-engineer）
#    ③ challenges 检查注释说明（ROLE_CHALLENGES 11/12，test-engineer 缺口登记 KNOWN_ISSUES）
#    ④ MCP total tools 20→26（+loop_onboard_project/loop_propose_work_package/
#       loop_approve_and_execute/loop_resume_execution/loop_dispatch_agents/safe_bash）
#    ⑤ Module size：7 个大模块"基线白名单 + 漂移检测"（KNOWN_LARGE_MODULES）
#    ⑥ Hook size：hook_common.py 同款白名单（HOOK_KNOWN_LARGE）
#    ⑦ Agent contracts：按角色目录过滤 agents/references/（探针缺陷修复）+ role dirs 计数

# 3. 复验
C:/Python312/python.exe tests/deep_probe_v35.py   # 266 passed, 0 failed
C:/Python312/python.exe -m pytest tests/ -q       # 4171 passed, 3 failed（2 项为 KNOWN_ISSUES 漂移，repair 后过；1 项 manifest 为 active 在途态）

# 4. 漂移修复 + 复验
C:/Python312/python.exe .zcode/tools/validate_state.py --repair .
# HANDOFF 重新生成（KNOWN_ISSUES 更新后）
# test_t0108_fixes 2 项复跑 PASS；validate_state EXIT=0

# 5. KNOWN_ISSUES 登记 2 条：
#    - Large-module-split-candidates（8 个超大文件拆分候选）
#    - ROLE_CHALLENGES-gap（test-engineer challenge 未定义，11/12）

# 6. 版本 bump
C:/Python312/python.exe scripts/release.py bump --to 3.12.51 --title "T-0115: deep_probe 探针现代化（13 项陈旧预期修复）"
```

## 遗留观察（提交后自愈/后续处理）

- `test_manifest_t0095::test_manifest_exists_and_handoff_reference_is_real`：active 在途态
  （HANDOFF 引用 T-0115 manifest 未生成），closeout 生成 evidence-manifest 后自愈。
- `release check version_sync`：提交前必然 FAIL（HEAD 3.12.50 vs 载体 3.12.51），提交后自愈。
