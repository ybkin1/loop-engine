# T-0123 修复记录：role-challenge-completion

## 背景

消解 2 项 KNOWN_ISSUES：ROLE_CHALLENGES 缺 test-engineer（11/12）+ 
certification_runner schema 字面量（pre-existing 夹具）。

## 修改清单

| 文件 | 修改 |
|------|------|
| `loop_core/role_capability.py` | ROLE_CHALLENGES 补 `test-engineer`（CHALLENGE-TE-001：pytest 测试工程挑战，SD-020 边界 off-by-one/SD-021 异常未处理，3 条 pass_conditions）——12/12 覆盖 |
| `scripts/certification_runner.py` | +项目根 sys.path 注入（脚本独立运行）+ `from loop_core.security_scanner import SECURITY_REPORT_V1_SCHEMA`；L613 `"security_report/v1"` 字面量 → 共享常量 |
| `tests/deep_probe_v35.py` | challenges 检查补 test-engineer（12/12）+ 注释更新 |
| `tests/test_t0123_challenge_completion.py` | 新增 8 项测试（覆盖 12/12/可认证/challenge_id 唯一/既有 11 项零变化/共享常量/单数据源/导入） |

## 设计决策

1. **CHALLENGE-TE-001 风格对齐**：既有 11 项同款结构（required_tools/required_inputs/
   seeded_defects/pass_conditions）；seed 缺陷延续 SD 编号（SD-020/021）。
2. **既有 11 项零修改**：只新增条目（测试 test_existing_challenges_unchanged 锁定）。
3. **schema 单数据源**：certification_runner 与 run_security_scan 同源引用
   loop_core（test_schema_literal_single_source 断言全仓无第二处字面量）。

## 验证

- test_t0123_challenge_completion 8/8 PASS
- deep_probe：challenges 检查 12/12（探针运行确认）
- 全量回归结果见 commands.md；hooks/ 零改动
