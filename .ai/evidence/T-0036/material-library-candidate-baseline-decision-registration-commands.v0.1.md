# T-0036 候选素材基线决策 Gate 注册命令 v0.1

Gate: `G-T-0036-CANDIDATE-BASELINE-DECISION-V0-1`

## 启动与证据核对

```powershell
python C:\Users\Administrator\.codex\skills\project-governor\scripts\validate_state.py C:\Users\Administrator\.codex\loop-engine-lab
```

结果：exit `0`；`[ok] state is usable`；注册前既有 pending Gate 为 `0`。

已读取并核对用户指定的 `.ai` 状态文件、T-0036 任务文件、三份 fresh rereview 证据、唯一冻结清单、`materials/material-library-review-packet.md` 和 `materials/README.md`。唯一冻结清单注册前为 `9835` bytes / `DEF89CBB72A5A910CCC0A8C519F03C2B4E8F1526962B2415DB4DE893DFA13CFC`，并由 rereview 证据确认 `65/65`、零漂移。

## 注册写入

实际注册写入只允许以下路径：

1. `.ai/evidence/T-0036/material-library-candidate-baseline-decision-gate-request.v0.1.md`
2. `.ai/evidence/T-0036/material-library-candidate-baseline-decision-packet.v0.1.md`
3. `.ai/evidence/T-0036/material-library-candidate-baseline-decision-changed-path-baseline.v0.1.md`
4. `.ai/evidence/T-0036/material-library-candidate-baseline-decision-registration-commands.v0.1.md`
5. `.ai/gates.yaml`
6. `.ai/state.yaml`
7. `.ai/HANDOFF.md`

## 注册后验证

```powershell
python C:\Users\Administrator\.codex\skills\project-governor\scripts\validate_state.py C:\Users\Administrator\.codex\loop-engine-lab
python C:\Users\Administrator\.codex\skills\project-governor\scripts\audit_handoff.py C:\Users\Administrator\.codex\loop-engine-lab
git diff --check
```

实际结果：

- 冻结清单独立复核：exit `0`；manifest `9835` bytes / SHA-256 `DEF89CBB72A5A910CCC0A8C519F03C2B4E8F1526962B2415DB4DE893DFA13CFC`；declared/parsed/matched=`65/65/65`；mismatches=`0`。
- `validate_state.py`：exit `2`；唯一信息为 pending Gate `G-T-0036-CANDIDATE-BASELINE-DECISION-V0-1` 需要用户决定。这是新 Gate 的预期阻断，不是 YAML 或状态结构错误。
- `audit_handoff.py`：exit `2`；HANDOFF 语义与下一步投影已一致，唯一信息为该 pending Gate 尚未解决。这是审计器对 pending Gate 的确定性预期结果。
- `git diff --check`：exit `0`；无输出。

注册后状态保持 `pending / user_decision_required`。尚未新增决策后证据，尚未接受基线、版本冻结、关闭 T-0036 或启动 T-0037，也未执行任何下游动作。
