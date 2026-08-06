# T-0115 验收报告

## 验收结论：PASS（6/6 AC）

| AC | 验收项 | 证据 | 结果 |
|----|--------|------|------|
| AC-01 | deep_probe 全 PASS | `python tests/deep_probe_v35.py` → **266 passed, 0 failed, 0 skipped**（基线 248/13） | ✅ |
| AC-02 | 全量回归 0 failed（除 2 项提交后自愈类）+ compile + release check | 全量 **4172 passed**；2 failed 为 manifest 在途态 + version_sync 提交前（F-03 约定）；compile_gate errors=[]；release check 提交后复验 6/6 | ✅ |
| AC-03 | 产品代码零改动 | 独立审查 git status/diff 确认：loop_core/hooks/tools/agents 零改动，仅 tests/deep_probe_v35.py + .ai/ + 版本载体 | ✅ |
| AC-04 | KNOWN_ISSUES 登记 8 大文件 | `.ai/KNOWN_ISSUES.md` Open 区新增 2 条：Large-module-split-candidates（8 文件行数）+ ROLE_CHALLENGES-gap | ✅ |
| AC-05 | 版本 3.12.51 与 git HEAD 一致 | 8 载体 bump 3.12.51；提交后 version_sync 自愈（F-03 约定） | ✅ |
| AC-06 | 独立审查 GO | review/independent-review.md：CONDITIONAL_GO → 阻断项全解决 → GO | ✅ |

## 关键事实

- 13 项 FAIL 分类：3 项计数类预期过时（roles/MCP/EnforcementHub fixture）、8 项模块大小类
  （7 module + 1 hook，白名单 + 漂移检测）、2 项探针缺陷（agents/references 目录过滤）
- 零产品代码变更；8 大文件拆分与 ROLE_CHALLENGES 缺口登记 KNOWN_ISSUES 留待独立任务
- 版本 3.12.51（bump 8 载体原子写 + CHANGELOG T-0115 条目）

## 提交说明

- 提交 subject：`v3.12.51: T-0115 — deep_probe 探针现代化（13 项陈旧预期修复，266 passed 0 failed，产品代码零改动）`
- 提交后复验：version_sync、manifest 引用、release check 6/6
