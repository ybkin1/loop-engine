# F6 上下文打包升级（T-0108 线 1）— 证据

- 显式覆盖 P3：D1-3（extra_files `[:2000]` 截断无标记）、D2-8（git timeout 5/10/5 字面量）、D4-4（knowledge cases 损坏静默丢弃）
- 接续 T-0107：token 预算/AC 节/git diff 缓存主体已在 T-0107 落地，本线外提纯函数模块 + 回归确认
- 目标文件：`loop_core/context_budget.py`（新增）、`loop_core/context_packager.py`

## 改动

1. **`loop_core/context_budget.py`（新增，design F6 定义的计算器）**
   - `estimate_tokens(text)`：字符→token 启发式（≈CHARS_PER_TOKEN=4 字符/token，无 tokenizer 依赖）
   - `split_sections(text)`：markdown `## ` 节切分（T-0107 同款逻辑外提）
   - `is_ac_section(heading)`：AC/验收节识别（TASK_CARD_AC_HEADING_MARKERS）
   - `slice_with_marker(text, limit)`：截断 + 显式 `…[truncated N chars]` 标记（D1-3 结构化标记，绝不静默）
   - `format_task_card(text, budget=None)`：按 token 预算分配，AC 节永不切，超预算节整体丢弃，丢弃/截断带 `…[task card truncated ...]` 结构化标记
   - 常量：TASK_CARD_TOKEN_BUDGET=1500、CHARS_PER_TOKEN=4、TASK_CARD_BUDGET_CHARS、TASK_CARD_HEADER_MAX_CHARS=400、TASK_CARD_AC_HEADING_MARKERS、TRUNCATED_MARKER/TASK_CARD_TRUNCATED_MARKER_PREFIX（标记契约）

2. **`loop_core/context_packager.py`（外提 + 委托）**
   - 原 `_estimate_tokens/_slice_with_marker/_split_task_sections/_is_ac_section/_format_task_card` 实现移至 context_budget，context_packager 保留同名别名（内部调用方与潜在外部引用兼容）
   - 常量 re-export（TASK_CARD_* 等），既有测试直接属性访问零改动
   - EXTRA_FILE_MAX_CHARS/MAX_EXTRA_FILES/KNOWLEDGE_CASES_MAX_CHARS/MAX_KNOWLEDGE_CASES/GIT_TIMEOUT_* 保持原位

3. **P3 显式覆盖确认（T-0107 落地 + T-0108 回归）**
   - D1-3：`build_context` extra_files 分支 `_slice_with_marker(c, EXTRA_FILE_MAX_CHARS)`（截断带 `…[truncated N chars]`）
   - D2-8：GIT_TIMEOUT_DIFF_STAT=5 / GIT_TIMEOUT_DIFF_CODE=10 / GIT_TIMEOUT_DIFF_NAME=5 / GIT_TIMEOUT_REV_PARSE=5 命名常量
   - D4-4：knowledge cases 读取失败 → `logger.warning("[context_packager] knowledge cases 读取失败...")`，不静默丢弃

## 测试

- `tests/test_t0108_fixes.py` TestContextBudget（7 用例）：估算启发式、AC 节永不切、截断标记结构化、packager↔budget 黄金一致、D2-8 timeout 常量、D1-3 extra_files 截断标记
- 回归：`tests/test_t0107_fixes.py` + `tests/test_context_compression.py` 79 passed（packager 行为零变化）

## 约束自查

- fail-closed：git diff/记忆召回失败不静默吞错（T-0107 D4-1 占位 + warning 保持）
- 防篡改：context 打包只读，不写任何治理文件（context_budget 纯函数零 IO）
- 审批闭环：不引入任何跳过 gate 的上下文指令
- 预算常量可调（模块级常量，无 config 依赖）
