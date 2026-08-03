# T-0109 hook 白名单门禁 — 修复证据（AC-05 / AC-08）

日期：2026-08-03
范围：`hooks/scripts/loop_enforcement.py` **仅** `GOVERNANCE_TOOL_DIRS`
白名单常量表同步；其余 hook 文件零改动（独立门禁）。

## 改动（单文件、常量表注释级最小 diff）

`hooks/scripts/loop_enforcement.py` `GOVERNANCE_TOOL_DIRS`（:407）：
- 常量表 6 目录**逐项原样**（`.zcode/tools/`、`.ai/checkers/`、`.ai/guards/`、
  `scripts/`、`hooks/`、`tools/`）——功能零改动（目录级白名单，工具变更
  无需逐文件同步）。
- 注释同步为 T-0109 合并后的工具清单语义：`tools/` 条目注明 36 工具
  capability 化清单落点（`loop_core/capability_registry.py`
  `TOOL_CAPABILITY_MANIFEST`）+ AC-05 一致性测试指针。

**diff 统计**：1 文件，仅注释行变更（`git diff HEAD -- hooks/` 实证）。

## 白名单一致性（AC-05，tests/test_t0109_f5_tool_capability.py）

- `_extract_governance_tool_dirs()`：AST 提取常量表（不执行 hook 代码）。
- **TestWhitelistConsistency**：
  - 注册表 36 工具模块路径全部落在白名单目录内（`tools/` 覆盖全部；
    目录级覆盖 → 工具增删不破坏白名单）。
  - 常量表仍为既有 6 目录（T-0109 仅注释同步，功能零改动）。
  - **hooks/ 仅 loop_enforcement.py 一处改动**（`git diff HEAD --name-only
    -- hooks/` 断言 == `["hooks/scripts/loop_enforcement.py"]`，AC-08 实证）。

## 约束自查

| 硬约束 | 实证 |
|--------|------|
| hooks/ 仅白名单常量表一处改动 | `git diff HEAD --name-only -- hooks/` == 仅 loop_enforcement.py；diff 内容仅注释（常量表逐项原样） |
| 其余 hook 文件零改动 | git diff hooks/ 无其他文件；F1 静态断言亦确认 hooks/ 无 advisory 符号 |
| fail-closed 语义不变 | 白名单判定逻辑（_script_in_governance_dirs/_is_governance_tool_segment）零触碰；仅注释变化 |
| 门禁范围最小 | 单文件单常量表，无行为 diff |

## 回归

- test_enforcement / test_hooks / test_hook_guards / test_t0105_batch3
  （hook 相关）+ test_t0109_f5_tool_capability 白名单三测：全绿。

## 遗留

- 无（白名单按目录级覆盖，工具删除 gate 通过后无需再改白名单；若未来
  工具迁出 tools/ 目录，需同步本常量表——已由 AC-05 一致性测试兜底）。
