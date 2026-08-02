# F-02 rollback.py `_verify_state` rc=3 感知（AC-02）

## 根因（T-0101 独立审查 P3 观察项 #1）

`scripts/rollback.py` `_verify_state()`（L194 附近）：`result.returncode == 0` 才通过，
其余一律判失败。T-0101 起 validate_state 对 idle 合法阻塞态返回 rc=3（NO_ACTIVE_TASK
分流），导致 idle 稳态回滚被"状态验证未通过"误阻断（修复前 rc=2 判失败行为前后一致、
无回归，但属既有保守局限——P3）。

## 改动

`scripts/rollback.py` `_verify_state()`：

```python
if result.returncode in (0, 3):
    note = "（idle 合法阻塞态 rc=3）" if result.returncode == 3 else ""
    print(f"[rollback] validate_state.py 通过{note}。")
    return True
```

- rc=0：通过（原有语义）。
- rc=3：通过并标注"idle 合法阻塞态"（rc=3 唯一来源即 validate_state/audit_handoff 的
  idle 白名单分支，T-0101 独立审查已确认全库唯一）。
- rc=2 及其他非 0：**仍阻断**（else 分支原样，fail-closed 保持）；超时/异常分支未动。

## 测试

`tests/test_operations.py` 新增 4 项（monkeypatch `scripts.rollback.subprocess.run`）：

| 用例 | rc | 断言 |
|------|----|------|
| `test_verify_state_accepts_rc0` | 0 | `_verify_state(...) is True` |
| `test_verify_state_accepts_idle_rc3` | 3 | `is True`（idle 合法态放行） |
| `test_verify_state_blocks_rc2_corruption` | 2 | `is False`（损坏仍阻断） |
| `test_verify_state_blocks_other_nonzero` | 1 | `is False`（其他非 0 阻断） |

复验：`pytest tests/test_operations.py -k "verify_state"` → 4 passed；全量回归 0 新失败。

## 约束

仅放宽 rc=3（idle 合法态白名单）；rc=2 损坏阻断语义、fail-closed 均不变（AC-02/AC-06）。
未执行任何真实 rollback（只修 verify 语义 + 测试）。
