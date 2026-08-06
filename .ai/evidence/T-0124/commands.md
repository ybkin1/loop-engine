# T-0124 commands

## 执行命令记录

```bash
# 1. 拆分 7 模块（壳 + 外部模块，行为等价）
#    executor 838→772（executor_compile.py：_run_compile_gate_check 方法体）
#    context_loader 839→796（context_loader_contracts.py：_parse_yaml/_extract_*）
#    second_failure 858→720（second_failure_gate.py：判定链 4 函数）
#    evals 905→799（evals_builtin.py：内置样例 + builtin_cases + 辅助）
#    intent_router 965→746（intent_router_modes.py：模式/快照类型/降级）
#    hard_constraints 1107→785（hard_constraints_checks.py：C8-C11 + 解析辅助）
#    dashboard_views 1108→792（dashboard_status.py：ProjectStatus/Dashboard/写快照）

# 2. 等价验证
C:/Python312/python.exe tests/deep_probe_v35.py      # 274 passed 0 failed（模块大小项全转真实 PASS）
C:/Python312/python.exe -m pytest tests/ -q          # 4226 passed（仅 manifest 在途 + version_sync 提交前）

# 3. 静态注册表适配（拆分后位置变化）
#    test_t0109_f2_write_convergence：写路径注册表 dashboard_views→dashboard_status（+NON_STATE_WRITERS）
#    test_t0110_batch_a：timeout 字面量 executor×2 → executor/executor_compile 各 1

# 4. compile + bump
C:/Python312/python.exe .ai/checkers/compile_gate.py . --output .ai/evidence/T-0124/compile-evidence.json
C:/Python312/python.exe scripts/release.py bump --to 3.12.59 --title "T-0124: loop_core 7 模块拆分（行为等价，全部 <800 行）"
```

## 等价机制要点

- 壳文件保留全部公共符号（函数/方法同名委托；类同名 re-export——dir() 逐名一致）
- 函数内延迟 import（避免循环导入 + 不污染壳 dir()）
- 外部模块原样提取（仅注入延迟 import 行）

## 遗留观察

- `test_manifest_t0095`：active 在途态，closeout 自愈。
- `test_release version_sync`：HEAD 3.12.58 vs 载体 3.12.59，提交后自愈（F-03）。
- `hooks/scripts/hook_common.py`(831)：归 T-0125 拆分。
