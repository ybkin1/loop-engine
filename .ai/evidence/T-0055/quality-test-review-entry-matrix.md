# T-0055 基线审计：质量、测试、评审入口

| 能力 | 当前入口 | 基线缺口 |
|---|---|---|
| 单元/回归测试 | `scripts/regression_runner.py`、pytest | 未证明与完整质量 gate 同一执行链 |
| 质量门 | `agents/quality-engineer/scripts/run_quality_gates.py` | 缺失命令、0/0、coverage 解析和 skip/unavailable 语义需统一 |
| 阈值判断 | `agents/quality-engineer/scripts/check_thresholds.py` | 未知检查项和缺失结果需 fail-closed 复核 |
| 独立评审 | `agents/independent-reviewer/` | 当前合同限制执行测试/扫描，无法独立核验全部上游证据 |
| 版本一致性 | `tests/test_version_consistency.py` | 当前 version manifest 与 3.11.2 实际文件漂移 |
| 治理状态 | `validate_state.py`、`governor_lib.py`、`continuity_auditor.py` | 当前切换 T-0055 后需重新建立 HANDOFF/compile evidence |
| 负面路径 | 多个 tests 文件 | 跨 reader、未知枚举、缓存失效、同步冲突仍需专项覆盖 |

## 能力提升方向

- QE：每项命令必须记录真实命令、退出码、stdout/stderr、hash、工具可用性和解析状态。
- TE：增加异常可观测性、未知枚举、跨层状态、TOCTOU、缓存失效和测试有效性。
- IR：保持不可写独立性，同时核验关键证据真实性；无法验证必须 `NOT_VERIFIED`。
- 所有角色：统一 PASS/FAIL/BLOCKED/UNAVAILABLE/NOT_VERIFIED/ABSTAIN 语义，避免以长文掩盖能力缺失。
