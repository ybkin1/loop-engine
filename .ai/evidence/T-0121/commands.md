# T-0121 commands

## 执行命令记录

```bash
# 1. 实现（loop_core/subagent_evidence_verifier.py）
#    + _zcode_session_exec_dir()：运行时读 ZCODE_SESSION_EXEC_DIR env（默认 ~/.zcode/cli/exec）
#    + session_dir_exists()：sess_<uuid> 目录存在核验（OSError → False，fail-safe）
#    + session_source_label()：verified-zcode / unverified-zcode / external / unavailable
#    + verify_review_evidence 4 个 return 点 + session_source 字段（add-only）

# 2. 测试
C:/Python312/python.exe -m pytest tests/test_t0121_session_check.py -q   # 12 passed
C:/Python312/python.exe -m pytest tests/test_t0118_seven_state.py -q      # 21 passed（既有基线零破坏）
C:/Python312/python.exe -m pytest tests/test_t0109_f1_eval_model.py -q    # 29 passed

# 3. KNOWN_ISSUES 更新
#    session-source-disabled：标注 T-0121 已落地存在性核验

# 4. 全量回归 + compile + bump
C:/Python312/python.exe -m pytest tests/ -q
C:/Python312/python.exe .ai/checkers/compile_gate.py . --output .ai/evidence/T-0121/compile-evidence.json
C:/Python312/python.exe scripts/release.py bump --to 3.12.56 --title "T-0121: ZCode 会话存在性核验（T-0120 方案 A 落地，呈现层）"
```

## 设计说明

- session_source 为独立呈现字段（非 reason 文本）：reason/checks/valid 与
  T-0118 基线逐字节一致（既有断言零破坏）
- 环境变量注入：`ZCODE_SESSION_EXEC_DIR`（测试/部署可覆盖默认 ~/.zcode/cli/exec）

## 遗留观察

- `test_manifest_t0095`：active 在途态，closeout 自愈。
- `test_release version_sync`：HEAD 3.12.55 vs 载体 3.12.56，提交后自愈（F-03）。

## 审查 closeout 补记

- bump 后 continuity 漂移（version-manifest.yaml）→ `validate_state --repair` +
  HANDOFF 重生成 → t0108 34 passed（T-0118 同款模式，提交后全量 0 failed）。
