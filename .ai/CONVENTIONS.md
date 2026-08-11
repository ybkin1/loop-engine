# Conventions

## 命名

- 任务 ID：`T-XXXX`（四位数字）
- Gate ID：`G-T-XXXX-...`
- 阶段：`S0` ~ `S11`
- 角色 ID：kebab-case（`main-thread`, `quality-engineer`）
- Gate ID 中的阶段段（如 `S1-requirements`）作为完整段出现；近似 ID
  （`S1-requirements-backup`）不得用于通过阶段约束匹配（T-0177 H3 段边界规则）。

## 文件组织

- `.ai/` — 治理数据（state, gates, tasks, evidence）
- `.zcode/` — ZCode 运行时（tools, skills）
- `loop_core/` — 宿主无关协议
- `src/loop_engine/` — Python 核心库 + 适配器（T-0158 迁入 src 布局）
- 宿主适配器：`src/loop_engine/adapters/_host_base.py`（共享实现）+
  `zcode_adapter.py`（.zcode/）/ `claude_adapter.py`（.claude/）各自独立声明
  （T-0177 M1 多宿主）。

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

## 逃生开关（T-0177 H2 加固）

- env `LOOP_ENGINE_EMERGENCY=1`：宿主进程级，立即生效（仅人可触发）
- 文件 `~/.loop-engine-emergency`：内容必须是标记（`1`/`active`/`on`），
  24h TTL 自动失效；触发留痕到 `~/.loop-engine-emergency.log`
- 逃生判定永远 fail-open（读取异常视为激活，逃生不可被阻断）

## Git 操作（T-0177 C3 收窄）

- 治理必需豁免：`git add/commit/diff/status/log/branch/show/tag/config`
- 破坏性操作不豁免：`git reset` / `git checkout <path>` / `git restore`
  即使有 task_id 也需逐文件判定（可覆盖受保护文件）
- 网络操作（push/pull/fetch/clone）始终需 task scope 检查

## 退化与能力声明（T-0177 H1）

- 宿主能力统一由 `src/loop_engine/degradation.py`（DEGRADATION_TABLE +
  get_adapter_info）与 adapters 声明，两处必须一致（禁止互斥结论共存）。
- hook 运行时启动时输出宿主 enforcement level 诊断（stderr），
  不改变拦截行为。
