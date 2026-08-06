# T-0124 拆分记录：loop_core 7 模块拆分（行为等价）

## 拆分总表

| 模块 | 拆分前 | 拆分后 | 外部模块 | 移出内容 |
|------|--------|--------|----------|----------|
| executor | 838 | 772 | executor_compile.py | `_run_compile_gate_check` 方法体（executor_compile_check 函数） |
| context_loader | 839 | 796 | context_loader_contracts.py | `_parse_yaml`/`_extract_fixed_stance`/`_extract_contract_extras` |
| second_failure | 858 | 720 | second_failure_gate.py | `_disabled_result`/`_data_insufficient`/`_linked_retro`/`second_failure_block` |
| evals | 905 | 799 | evals_builtin.py | `_BUILTIN_CASE_DATA`/`_FAKE_SECRET_CONTENT`/`builtin_cases`/`_navigate_json`/`_coerce_text` |
| intent_router | 965 | 746 | intent_router_modes.py | `_phases_for_mode`/`_analysis_to_profile`/`ActiveTaskSnapshot`/`TaskFrame`/`RoutedIntent`/`_status_quo_route_result`/`_degraded_result` |
| hard_constraints | 1107 | 785 | hard_constraints_checks.py | C8-C11 四个方法 + `_parse_allowed_paths_from_markdown` |
| dashboard_views | 1108 | 792 | dashboard_status.py | `ProjectStatus`/`Dashboard`/`write_snapshot_files` |

## 等价机制

1. **壳文件保留全部公共符号**：方法/函数保留同名（函数内延迟 import 委托）；
   类用同名 re-export（dir() 逐名一致，含私有名）。
2. **函数内延迟 import**：避免循环导入（外部模块运行时才 import 壳符号），
   且不污染壳模块 dir()。
3. **外部模块原样提取**：方法体/函数体逐字节移动（仅注入必要的延迟 import 行），
   无逻辑修改。
4. **验证**：deep_probe 274 passed（模块大小项从白名单 PASS 转真实 PASS）+
   相关测试全绿（executor 82/constraint 187/evals 111/intent 138/dashboard 152/
   second_failure 44）。

## 关键修复记录（过程中）

- intent_router `_degraded_result` 签名与壳委托初版不一致（description 参数）→
  对照 git HEAD 原版修正。
- dashboard_views 外部模块别名（_dataclass/_field/_datetime/_Optional）→
  统一替换为原名 import。
- dashboard_views re-export 误删（块删除波及）→ 文件尾恢复。
- hard_constraints check_c11 引用壳辅助 → 延迟 import 注入。

## KNOWN_ISSUES

Large-module-split-candidates：7 个 loop_core 模块拆分完成（<800 行）；
`hooks/scripts/hook_common.py`(831) 归 T-0125。deep_probe 白名单基线更新
（行数下降自动 PASS，无人工白名单残留）。
