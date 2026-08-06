# T-0121 修复记录：session-existence-check

## 背景

落地 T-0120 决策包推荐方案 A：ZCode 原生会话存在性核验（呈现层）。
`subagent_evidence_verifier` 校验 reviewer_session_id 时，sess_<uuid> 格式
会话目录在 `~/.zcode/cli/exec/` 的真实存在性本地可核验（T-0112 撤销的
Qoder 外部宿主不可核验缺口）。

## 修改清单

| 文件 | 修改 |
|------|------|
| `loop_core/subagent_evidence_verifier.py` | +`_zcode_session_exec_dir()`（运行时读 env，fail-safe）+`session_dir_exists()`（sess_ 格式 + 目录存在核验，异常→False）+`session_source_label()`（verified-zcode/unverified-zcode/external/unavailable）+ `verify_review_evidence` 4 个 return 点增加 `session_source` 字段 |
| `tests/test_t0121_session_check.py` | 新增 12 项测试（label 四类/目录核验/fail-safe/env 注入/集成/既有键保留） |
| `tests/test_t0118_seven_state.py` | 零改动（T-0118 基线断言 reason/checks/valid 不变——新增字段 add-only） |
| `.ai/KNOWN_ISSUES.md` | session-source-disabled 记录更新（T-0121 已落地存在性核验） |

## 设计决策

1. **呈现层字段**（`session_source`）而非 reason 文本标注：保持 reason/checks/
   valid 与 T-0118 基线逐字节一致（既有断言零破坏），存在性核验以独立字段呈现。
2. **fail-safe**：exec 目录不可探测（换机/未安装/权限）→ unverified-zcode 且
   不抛错；非 sess_ 格式 → external（既有语义）。
3. **边界保持**：不读取会话日志内容（存在性 ≠ 真实性）；verdict 判定、
   checks 数量（7）、gate 语义零变更——T-0112 边界实质保持。
4. **可配置**：`ZCODE_SESSION_EXEC_DIR` 环境变量注入（测试与部署可覆盖）。

## 验证

- test_t0121_session_check 12/12 PASS；test_t0118_seven_state 21/21 PASS
  （既有基线零破坏）；test_t0109_f1_eval_model 29 PASS
- 全量回归结果见 commands.md；hooks/ 零改动
