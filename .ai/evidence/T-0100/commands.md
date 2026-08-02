# T-0100 执行命令记录（修复前状态 → 修复后状态）

环境：Windows 10 x64 / Git Bash / C:/Python312/python.exe（Python 3.12.10）
基线：git HEAD `387c7be`（v3.12.38 T-0099）；pyproject=3.12.36（漂移）。

## 修复前基线

```bash
$ python -m pytest tests/test_release.py tests/test_version_consistency.py tests/test_capability_registry.py -q
# 1 failed, 53 passed, 1 skipped
# FAILED TestAC01VersionSync::test_pyproject_version_matches_git_head
#   pyproject=3.12.36 vs git HEAD=3.12.38（F-03 漂移现场）

$ python tools/tool_registry_status.py --json ; echo $?
# 1（--json 打印合法 JSON 后 UnboundLocalError 'death'，F-01 现场）

$ python agents/security-engineer/scripts/run_security_scan.py --project-root .   # T-0099 记录
# overall BLOCKED：dependency H:1（pip-audit 缺 venv 崩溃合成，F-04）、
# secret 7、injection HIGH:26/MEDIUM:4（规则表/夹具/文档误报，F-06）
```

## 修复实施与复验

### F-03 版本同步（bump + 对齐 3.12.39）

```bash
$ python scripts/release.py bump --to 3.12.39 --title "T-0100: 质量验收 findings 修复包（F-03~F-06）"
# 已更新 pyproject.toml / CHANGELOG.md / loop_core/__init__.py /
#   src/loop_engine/__init__.py / README.md / docs/06-delivery.md /
#   .zcode-plugin/plugin.json / .ai/version-manifest.yaml -> 3.12.39
# bump 完成。约定：先 bump 再提交……
$ python -m pytest tests/test_release_bump.py tests/test_version_consistency.py tests/test_release.py -q
# 41 passed, 1 skipped, 1 failed（唯一失败 = git HEAD 同步用例，提交后通过）
$ python scripts/release.py check
# [FAIL] version_sync: 版本漂移：pyproject=3.12.39 vs git HEAD=3.12.38（提交前预期）
# 其余 5 步（validate_state/compile/guard_health/slo_gate/key_tests）全部 PASS
$ python scripts/release.py check --dry-run ; echo $?   # 0（兼容子命令后置标志）
```

注：`.zcode-plugin/plugin.json` 不在任务 allowed_paths 字面清单，但为
test_version_consistency（release check key_tests）强制校验的版本载体，
已随 bump 更新（单行 version）并如实记录于 fixes/f-03.md。

### F-01 registry --json

```bash
$ python tools/tool_registry_status.py --json > reg.json; echo $?   # 0（修复前 1）
$ python -m pytest tests/test_tool_registry_status.py -q             # 3 passed
```

### F-04 dependency SKIPPED

```bash
$ python -m pytest tests/test_security_dependency_scan.py -q         # 9 passed
```

### F-05 SLO 口径 + advisory

```bash
$ python tools/loop_metrics.py --report
# status: PASS（修复前 NOT_VERIFIED）| error budget HEALTHY 100.0/100.0
# missing: 0 | advisories: 14（未接线数据源/未落盘项，不影响 computed 判定）
$ python -m pytest tests/test_slo_consistency.py tests/test_governance_metrics.py tests/test_slo_gate.py -q
# 92 passed
```

### F-06 白名单

```bash
$ python -m pytest tests/test_security_scan_whitelist.py -q          # 13 passed
$ python agents/security-engineer/scripts/run_security_scan.py --project-root . \
    --output-dir .ai/evidence/T-0100/security-scan ; echo $?
# 0；overall PASS：dependency=skipped（附原因）、secret 0、injection 0/0、permission pass
# （修复前 BLOCKED：H:1 + secret 7 + injection 26/4）
```

## 全量回归与编译

```bash
$ python -m pytest tests/ -q            # 全量（约 3700 例）
$ python .ai/checkers/compile_gate.py . --output .ai/evidence/T-0100/compile-evidence.json
# {"status": "pass", "compiled_files": 68, "failed_count": 0}
```

（全量结果见最终报告；预期唯一失败 = test_pyproject_version_matches_git_head，
提交 v3.12.39 后自愈。）

## P2 追加修复（独立审查条件：split-literal SQL + bracket HTML sink）

```bash
$ python -m pytest tests/test_security_scan_whitelist.py tests/test_security_dependency_scan.py -q
# 27 passed（白名单文件 13 → 18 例，新增 5 例 P2 用例）
$ python -m pytest tests/ -q -k "security"
# 100 passed, 23 skipped（既有环境性跳过）
$ python agents/security-engineer/scripts/run_security_scan.py --project-root . \
    --output-dir <tmp>/t0100-p2-scan ; echo $?
# 0；overall PASS：dependency=skipped（附原因）、secret 0、injection 0/0、permission pass
# （P2 新规则对真实仓库零新增误报）
$ python agents/security-engineer/scripts/run_security_scan.py --project-root <tmp>/t0100-p2-proj \
    --output-dir <tmp>/t0100-p2-scan/proj ; echo $?
# 2；overall BLOCKED by injection_scan —— 端到端验证修复形态：
#   HIGH 8（split-literal SELECT/UPDATE/DELETE/DROP/INSERT + %；DELETE/DROP/INSERT
#   与旧 + 规则叠加）、MEDIUM 3（obj["innerHTML"]/el['outerHTML']/target["insertAdjacentHTML"] 赋值）、
#   只读索引访问与 "SELECT color"/"[loop-update]" 标签 0 误报
$ python -m py_compile agents/security-engineer/scripts/run_security_scan.py \
    tests/test_security_scan_whitelist.py   # 编译通过
```
