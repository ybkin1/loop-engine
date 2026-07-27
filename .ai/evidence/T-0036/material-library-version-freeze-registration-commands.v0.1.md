# T-0036 素材库版本冻结 Gate 注册命令 v0.1

Gate: `G-T-0036-VERSION-FREEZE-RESEARCH-BASELINE-V0-1`

## 注册前检查

```powershell
python C:\Users\Administrator\.codex\skills\project-governor\scripts\validate_state.py C:\Users\Administrator\.codex\loop-engine-lab
```

结果：exit `0`；`[ok] state is usable`；注册前 pending Gate=`0`。

已读取 `.ai/state.yaml`、`.ai/HANDOFF.md`、`.ai/tasks/T-0036.md`、`.ai/gates.yaml`、`.ai/task_graph.yaml` 和用户指定的四份 T-0036 证据。输入 manifest 独立复核结果：declared/parsed/unique/matched=`65/65/65/65`；mismatches=`0`；manifest=`9835` bytes / `DEF89CBB72A5A910CCC0A8C519F03C2B4E8F1526962B2415DB4DE893DFA13CFC`。

## 注册写入

实际注册写入仅允许 `material-library-version-freeze-scope.v0.1.md` 所列八个注册阶段路径。注册只创建 pending Gate，不执行版本冻结。

## 注册后验证命令

```powershell
python C:\Users\Administrator\.codex\skills\project-governor\scripts\validate_state.py C:\Users\Administrator\.codex\loop-engine-lab
python C:\Users\Administrator\.codex\skills\project-governor\scripts\audit_handoff.py C:\Users\Administrator\.codex\loop-engine-lab
git diff --check
```

注册后还需重新验证输入 manifest 的 65/65 path、size、SHA-256，确认唯一 pending Gate 和 `current_gate_id` 均为目标 Gate，并依据注册前 preimage 证明本次实际 changed paths 严格落在八路径 allowlist 内。

## 实际结果

- UTF-8 YAML 解析：`.ai/state.yaml`、`.ai/gates.yaml`、`.ai/task_graph.yaml` 全部 `PASS`。
- Gate 投影：pending count=`1`；唯一 ID 和 `current_gate_id` 均为 `G-T-0036-VERSION-FREEZE-RESEARCH-BASELINE-V0-1`；目标 Gate 记录数=`1`。
- 输入 manifest 注册后复核：declared/parsed/unique/matched=`65/65/65/65`；mismatches=`0`；size/SHA-256 保持 `9835` / `DEF89CBB72A5A910CCC0A8C519F03C2B4E8F1526962B2415DB4DE893DFA13CFC`。
- 注册 changed paths：五个原本 absent 的 Gate 证据现已新增，三个治理 preimage 均已更新；实际归属路径正好是八路径注册 allowlist，无越界路径。
- 四个执行阶段证据路径均保持 absent；最终 version-freeze manifest 和冻结记录尚未创建。
- `validate_state.py`：exit `1`；唯一错误为 pending Gate 需要用户决定，属于预期治理停止。
- `audit_handoff.py`：语义投影修正后 exit `1`；唯一错误为 pending Gate 未解决，属于预期治理停止。
- `git diff --check`：exit `0`；无输出。

结论：注册完成并停止。Gate 创建没有冻结版本；用户批准也不会执行冻结，批准后仍需后续单独精确执行请求。
