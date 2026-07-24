# Conventions

## 命名

- 任务 ID：`T-XXXX`（四位数字）
- Gate ID：`G-T-XXXX-...`
- 阶段：`S0` ~ `S11`
- 角色 ID：kebab-case（`main-thread`, `quality-engineer`）

## 文件组织

- `.ai/` — 治理数据（state, gates, tasks, evidence）
- `.zcode/` — ZCode 运行时（tools, skills）
- `loop_core/` — 宿主无关协议
- `loop_engine/` — Python 核心库 + 适配器

## 代码风格

- Python：PEP 8, ruff lint
- YAML：2 空格缩进，`schema_version: 1`
- Markdown：`##` 章节，中文内容

## 证据规则

- 每个 task 必须有 `commands.md`
- 证据只可 supersede，不可删除
- SHA256 绑定输入版本

## Gate 规则

- pending gate = 全停信号（gate_guard exit 2）
- 批准 ≠ 执行（需要精确执行请求）
- 用户批准不可替代（reviewer PASS 只是 evidence）
