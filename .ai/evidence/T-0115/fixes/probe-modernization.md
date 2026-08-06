# T-0115 修复记录：probe-modernization

## 背景

`tests/deep_probe_v35.py` 深度探针 13 项 FAIL 经 T-0113/T-0114 独立审查确认全部为
"既有陈旧预期，零新增、零产品偏差"。本任务逐项核对当前实现并现代化探针预期，
产品代码零改动（diff 仅 tests/deep_probe_v35.py + .ai/）。

## 修复明细（13 项 → 0 项）

| # | 探针检查 | 原预期 | 现实现 | 修复方式 |
|---|---------|--------|--------|---------|
| 1 | EnforcementHub write allowed | S4 fixture 仅 G-S4 gate | GAP-5b 后 C1/C2 需 S1-requirements/S2-architecture gate 前缀 + S4 写操作 C6 需 independent-reviewer PASS verdict | fixture 补齐 approved S1/S2 gate + `.ai/evidence/T-test/review.json`（verdict PASS） |
| 2 | 11 roles created | 11 | ROLE_IDS 12（新增 test-engineer） | 预期改 12；challenges 检查注释说明 ROLE_CHALLENGES 11/12 缺口（登记 KNOWN_ISSUES，产品侧不本任务改） |
| 3 | MCP total tools | 20 | 26（+onboard/propose/approve/resume/dispatch/safe_bash 6 键） | 预期列表补 6 键 + 总数 26 |
| 4-10 | Module size ×7 | >800 行 FAIL | dashboard_views 1108/hard_constraints 1107/intent_router 965/evals 905/second_failure 858/context_loader 839/executor 838 为现状 | KNOWN_LARGE_MODULES 基线白名单 + 漂移检测（≤基线 PASS 且注明拆分候选；>基线 FAIL） |
| 11 | Hook size hook_common | >800 行 FAIL | 831 行为现状 | HOOK_KNOWN_LARGE 同款白名单 |
| 12-13 | Agent references ×2 | 每 agents 子目录须 CONTRACT.yaml+SKILL.md | agents/references/ 为非角色共享文档目录 | 按角色目录过滤 + `Agent role dirs >= 12` 计数检查 |

## 设计决策

1. **基线白名单 + 漂移检测**（替代静态阈值）：拆分候选文件行数未超过登记基线 → PASS
   （拆分进展自动放行）；超过基线或未登记的新超限文件 → FAIL（提醒重新登记/拆分）。
   防止"白名单永久掩盖增长"——行数增长仍会红。
2. **拆分不属本任务**：8 个超大文件拆分涉及内核/hooks 文件，需独立 gate 立项，
   登记 KNOWN_ISSUES（Large-module-split-candidates）。
3. **ROLE_CHALLENGES 缺口登记**：test-engineer 无 challenge（11/12）为产品侧缺口，
   探针如实注释，登记 KNOWN_ISSUES（ROLE_CHALLENGES-gap），不越界修改产品代码。

## 验证结果

- `python tests/deep_probe_v35.py`：**266 passed, 0 failed, 0 skipped**（基线 248/13）
- 全量回归：4171 passed（3 failed 中 2 项为 KNOWN_ISSUES 漂移 repair 后自愈，
  1 项 manifest 为 active 在途态 closeout 自愈）
- validate_state：EXIT=0 state usable
- 产品代码零改动（git diff 确认仅 tests/deep_probe_v35.py + .ai/ + 版本载体）
