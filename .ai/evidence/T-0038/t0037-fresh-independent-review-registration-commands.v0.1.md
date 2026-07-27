# T-0038 独立评审 Gate 登记命令记录 v0.1

登记时间：2026-07-23T12:15:38+08:00

## Preflight

1. 确认项目根目录：`C:\Users\Administrator\.codex\loop-engine-lab`。
2. 读取 `.ai/state.yaml`、`.ai/HANDOFF.md`、`.ai/tasks/T-0037.md`、`.ai/gates.yaml` 和 `.ai/task_graph.yaml`。
3. 使用 `$project-governor` 的 `validate_state.py`：通过，输出 `state is usable`。
4. 检查 pending Gate：无。
5. 检查 `T-0038`、`G-T-0038-T0037-FRESH-INDEPENDENT-REVIEW-V0-1`：登记前不存在。
6. 根据 T-0037 当前文件生成冻结清单，共 62 个对象；排除 `__pycache__` 和 `.pyc`。

## Registration change set

本次只登记独立评审任务和待决 Gate，新增/修改范围为：

- 新增 `.ai/tasks/T-0038.md`。
- 新增 `.ai/evidence/T-0038/` 下的 Gate 请求、冻结清单和本命令记录。
- 新增 `.ai/evidence/T-0038/commands.md` 作为当前任务证据入口。
- 追加 `.ai/gates.yaml` 中的一个 `pending` Gate。
- 更新 `.ai/state.yaml`、`.ai/task_graph.yaml`、`.ai/HANDOFF.md` 和 `.ai/DECISIONS.md` 的当前任务/待决 Gate 事实。

冻结清单中的 T-0037 对象不应发生任何内容变更；本次没有代码、测试、T-0037 证据或全局配置修改。

## Validation commands

- `python C:\Users\Administrator\.codex\skills\project-governor\scripts\validate_state.py C:\Users\Administrator\.codex\loop-engine-lab`
- `python C:\Users\Administrator\.codex\skills\project-governor\scripts\audit_handoff.py C:\Users\Administrator\.codex\loop-engine-lab`
- `git diff --check`
- 严格 UTF-8 读取新 Markdown、YAML 和冻结清单；逐项校验冻结对象路径、字节数和 SHA-256。
- 解析 `.ai/gates.yaml`、`.ai/state.yaml` 和 `.ai/task_graph.yaml`，确认 Gate 与当前任务唯一匹配。

登记完成后，`validate_state.py` 因本 Gate 的 `pending` 状态按设计返回阻断错误；这表示必须等待用户决定，不是登记失败。除该 pending Gate 外不得出现新的状态不一致。Gate 创建不执行评审，因而不会生成 review report、review validation 或 reviewer verdict。

## User decision boundary

- 当前 Gate：`pending / user_decision_required`。
- 批准短语：`批准 G-T-0038-T0037-FRESH-INDEPENDENT-REVIEW-V0-1`。
- 拒绝短语：`拒绝 G-T-0038-T0037-FRESH-INDEPENDENT-REVIEW-V0-1`。
- 即使批准，仍需后续精确执行短语：`执行 G-T-0038-T0037-FRESH-INDEPENDENT-REVIEW-V0-1`。
