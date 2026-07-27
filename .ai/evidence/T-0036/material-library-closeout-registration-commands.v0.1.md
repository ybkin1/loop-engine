# T-0036 行政收口 Gate 注册命令 v0.1

Gate: `G-T-0036-CLOSEOUT-DECISION-AND-EXECUTION-V0-1`

## 启动校验

```powershell
python C:\Users\Administrator\.codex\skills\project-governor\scripts\validate_state.py C:\Users\Administrator\.codex\loop-engine-lab
```

结果：exit `0`；`[ok] state is usable`；注册前无 pending Gate。

## 前置冻结复核

已核对候选基线接受记录、验证记录及版本冻结 record、manifest、validation、changed-path manifest。最终 manifest 为 `10202` bytes / SHA-256 `24DDC5434B0FFE3D078AED5B8A2101CF6A0A4C97DF73553E949FB668BDE98F20`；新旧 subject triples `65/65` 一致，磁盘 `65/65` 匹配，零漂移。

## 本次注册允许路径

1. `.ai/evidence/T-0036/material-library-closeout-gate-request.v0.1.md`
2. `.ai/evidence/T-0036/material-library-closeout-decision-packet.v0.1.md`
3. `.ai/evidence/T-0036/material-library-closeout-changed-path-baseline.v0.1.md`
4. `.ai/evidence/T-0036/material-library-closeout-registration-commands.v0.1.md`
5. `.ai/gates.yaml`
6. `.ai/state.yaml`
7. `.ai/HANDOFF.md`

## 注册后检查

```powershell
python C:\Users\Administrator\.codex\skills\project-governor\scripts\validate_state.py C:\Users\Administrator\.codex\loop-engine-lab
python C:\Users\Administrator\.codex\skills\project-governor\scripts\audit_handoff.py C:\Users\Administrator\.codex\loop-engine-lab
git diff --check
```

注册后应保持 `pending / user_decision_required` 并停止。不得在用户批准和后续精确执行请求前修改任务状态、task graph、DECISIONS、PROGRESS 或新增执行证据。

## 实际注册后结果

- `validate_state.py`：exit `2`；唯一阻断为 pending Gate `G-T-0036-CLOSEOUT-DECISION-AND-EXECUTION-V0-1` 等待用户决定。这是预期 Gate 阻断。
- `audit_handoff.py`：exit `2`；唯一阻断为该 pending Gate 尚未解决；HANDOFF 语义与当前状态投影一致。
- `git diff --check`：exit `0`；无输出。

注册后已停止；T-0036 仍为 `active`，未修改任务文件、task graph、DECISIONS、PROGRESS，未执行行政收口或任何下游动作。
