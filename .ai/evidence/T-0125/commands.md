# T-0125 commands

## 执行命令记录

```bash
# 1. 拆分 hook_common.py（831 → 727 行）
#    _extract_paths_from_bash_command（8 类写入模式，118 行）→ _hook_common_paths.py
#    壳保留同名委托 stub：函数内延迟导入（from _hook_common_paths import ... as _impl）
#    拆分后 hook_common.py 727 行 < 800；新外部模块 133 行（仅 import re/shlex）

# 2. 等价验证
C:/Python312/python.exe -m pytest tests/test_bypass_matrix.py -q   # 250 passed, 12 xfailed
C:/Python312/python.exe tests/deep_probe_v35.py .                  # 275 passed 0 failed
C:/Python312/python.exe -m pytest tests/test_hook_integration.py tests/test_bypass_matrix.py -q  # 280 passed
C:/Python312/python.exe -m pytest tests/ -q --ignore=tests/test_deployment_quality_checker.py    # 4220 passed

# 3. hooks 白名单测试适配（T-0119 先例）
#    test_t0109_f5_tool_capability.py：allowed 加入 hook_common.py + _hook_common_paths.py
#    注释级断言收窄至 loop_enforcement_constants.py；拆分文件断言 <800 行

# 4. continuity 修复（task_graph T-0125 → in_progress 触发 drift）
C:/Python312/python.exe .zcode/tools/validate_state.py . --repair
C:/Python312/python.exe -c "import sys; sys.path.insert(0,'.zcode/tools'); from pathlib import Path; from continuity_producer import render_handoff; from governor_lib import safe_project_path; import yaml as _y; root=Path('.').resolve(); h,s=render_handoff(root); (root/'.ai'/'HANDOFF.md').write_text(h,encoding='utf-8'); _y.safe_dump(s, open(safe_project_path(root,'.ai/state.yaml'),'w',encoding='utf-8'), allow_unicode=True, sort_keys=False)"

# 5. compile + bump
C:/Python312/python.exe .ai/checkers/compile_gate.py . --output .ai/evidence/T-0125/compile-evidence.json  # 94/94 pass
C:/Python312/python.exe scripts/release.py bump --to 3.12.60 --title "T-0125 — hook_common 拆分（行为等价，<800 行）"

# 6. 独立审查（fresh context 子代理）
#    结论 GO：AST 归一化函数体逐行 IDENTICAL（109=109）、dir() 58→58 无增减、
#    无循环导入、改动面仅授权两文件、280/275 套件全绿、state usable
```

## 等价机制要点

- 壳文件保留全部公共符号（同名委托 stub，函数内延迟 import）
- 外部模块原样提取（8 类模式完整：重定向/touch/mkdir/cp/mv/tee/cat>/echo|printf>）
- 保留 `import shlex`（拆分前后都存在，dir() 一致性要求，低优先级清理项）

## 遗留观察

- `test_manifest_t0095`：active 在途态，closeout 后自愈。
- `test_release version_sync`：HEAD 3.12.59 vs 载体 3.12.60，提交后自愈（F-03）。
- KNOWN_ISSUES Large-module-split-candidates：hook_common 项随本任务关闭（T-0126 收口复核）。
