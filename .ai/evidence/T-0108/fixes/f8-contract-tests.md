# F8 治理契约测试（T-0108 线 4）— 证据

- 目标文件：`tests/test_ai_doc_links.py`（新增）、`tests/test_projection_freshness.py`（新增）、`tests/test_t0108_fixes.py`（新增）
- 依据：design-bh-integration.md F8（仿 BH doc-link-graph：遍历 .ai/ 文档引用链接，断链 → FAIL；投影新鲜度：state.yaml 权威 vs 投影视图一致性 + mtime 新鲜度）

## 改动

1. **tests/test_ai_doc_links.py（8 用例）**
   - 扫描对象：`.ai/README.md` + 顶层 `*.md`（排除 evidence/archive/handoffs 生成区）
   - 引用类型：markdown 链接 `[t](path)` + 反引号路径引用（已知根前缀 .ai/docs/loop_core/tools/scripts/hooks/agents/.zcode/tests/archive/skills；占位符 `<...>` 与裸文件名不判定）
   - 白名单机制（F8 设计）：`.ai/plans`（归档后清空的历史位置说明）免判
   - 断言：README 三节/四态/归类表存在；仓库全链接可解析（全绿）；归档文件无悬挂引用（archive 存在 + 原位置已移）；路由表可被 context_loader 解析
   - **断链用例 FAIL**：markdown 断链夹具 + 反引号断链夹具（临时仓库，monkeypatch REPO_ROOT）→ 检查器必须报告断链

2. **tests/test_projection_freshness.py（8 用例）**
   - 视图 = state.yaml 派生：字段逐项断言 + 确定性（同一输入逐字段一致）+ task_status 派生自 task_graph + 缺 state 抛 FileNotFoundError
   - mtime 新鲜度：无视图不 stale / 新视图不 stale / 伪造旧 mtime → stale（age 断言）
   - validate_state 集成（AC-04）：伪造旧 mtime 视图 → stdout 含 `[warn] stale view`；移除视图 → 无 stale 告警；**error 集合与 exit code 完全一致**（既有判定零变化实证）

3. **tests/test_t0108_fixes.py（34 用例）**：AC-01~AC-06 各一条可验证测试 + F6/F7/D5-6/D5-7/F2-1 逐线覆盖（详见各 fixes/*.md）

## 测试结果

```
tests/test_t0108_fixes.py ..............34 passed
tests/test_projection_freshness.py ..... 8 passed
tests/test_ai_doc_links.py ............. 8 passed
（合计 50 passed，新增）
```

## 约束自查

- 测试只读：全部夹具在 pytest tmp_path 内自建，不写 `.ai/`（不触发 repair/自愈路径）；真实仓库断言仅读
- fail-closed：断链 → 断言 FAIL（不降级 warning）；测试失败即门禁失败
- 防篡改：链接测试不修改任何哈希/清单（continuity 断言只读 load_yaml）
- 白名单只豁免归档位置说明（.ai/plans），真实链接全部校验
