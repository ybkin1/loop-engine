# F4 文档路由（T-0108 线 2）— 证据

- 消解 P3：D5-3（context_loader 节选择正则/关键词启发式）、D5-7（implementation_design_diff 反引号正则推断）
- 目标文件：`.ai/README.md`（新增）、`.ai/archive/plans/`（迁移）、`loop_core/context_loader.py`、`docs/02-architecture.md`、`scripts/role_checkers/implementation_design_diff.py`、`.ai/project_continuity.yaml`（源清单同步）、`.ai/HANDOFF.md`（重生成）

## 改动

1. **Switchboard（`.ai/README.md` 新增）**
   - 三节：Owns（.ai 拥有什么）/ Does Not Own（不拥有什么）/ Read Next（新会话阅读顺序）
   - 目录四态：active（顶层权威文档）/ generated（evidence/runtime/HANDOFF）/ target（schemas/checkers/guards/policies）/ candidate→archived（历史 DRAFT 计划，已归档）/ archived（.ai/archive/）
   - 文档活/死归类表（20+ 顶层文档）：16 个 REQUIRED_FILES 文档 + README 均"活"；2 个历史 DRAFT 计划"死"→ 已归档
   - front-matter `section_routing:` 机器可读路由表（context_loader 消费，D5-3）

2. **死文档归档（T-0105 先例）**
   - 全库 grep 确认 `.ai/plans/PLAN-20260729-{001,002}.yaml` 无活动引用（仅 continuity manifest 自身；planner.py 只 glob 目录不引用具体文件；task_graph/gates 无引用）→ `git mv` 至 `.ai/archive/plans/`（非删除）
   - continuity 同步：source_manifest 移除 2 条 entries + 重算 `source_sha256`（C0D2AF9B... → 4FA31FC1...，semantic_sha256 不变）+ `render_handoff` 重生成 HANDOFF.md（嵌入投影含新 source_sha256）
   - 验证：`validate_state .` exit 0 `[ok] state is usable`；清单全部 441 条剩余路径存在

3. **context_loader 路由表（D5-3）**
   - `_select_relevant_sections(role_id, doc_index, project_root=None)`：project_root 给定时读 `.ai/README.md` front-matter `section_routing`（mtime+size 缓存 `_ROUTING_CACHE`）；缺失/不可解析 → 回退旧关键词启发式 + `logger.warning`（fail-closed：不静默返回空上下文）
   - 路由 keyword 语义与旧启发式一致（小写子串匹配；无匹配/无关键词 → 前 3 节）→ golden 快照一致（实测 docs/02-architecture.md developer 角色 routed==legacy）
   - `load_for_role` 调用点透传 `self._project_root`

4. **designed_files 显式声明区（D5-7）**
   - `docs/02-architecture.md` front-matter 新增 `designed_files:`（hooks 4 文件字面项 + tools/ agents/ .zcode/tools/ 目录前缀）
   - **实现约束（hook 零改动实测发现）**：清单必须使用 YAML flow 风格（单行内联列表）——`hooks/scripts/content_guard.py` 的架构合规检查按 `[-*] `path`` 行模式解析架构文档；bullet 形式会让 hook 把声明项当作架构模块，阻断范围外写入（实测 `tests/tmp_clean_test.py` 写入被 deny，guard_health ALIVE 测试 BROKEN）。hook 零改动约束下，文档侧以 flow 风格规避；该约束已写入 docs/02-architecture.md front-matter 注释
   - `implementation_design_diff.py` 重写：DRIFT 判定仅依据显式声明区；反引号正则推断输出为 `hint_regex_inferred`（提示，不参与判定）；无声明区时回退正则并标注 `declaration: regex-fallback`
   - 实证（stash 对照）：修复前误报 designed_but_missing=[agents/, evidence_chain.py, hook_common.py, server.py, validate_state.py]；修复后误报全部移入 hint

## 测试

- `tests/test_ai_doc_links.py`（8 用例）：三节/四态/归类表存在；全链接可解析；归档无悬挂；断链 FAIL 夹具×2
- `tests/test_t0108_fixes.py`：TestRoutingTable（golden 一致/缺失回退+告警/表驱动/default 键/load_for_role 端到端）、TestDesignedFiles（front-matter 存在/checker 读声明区/无声明回退）、TestArchiveAndContinuity（归档位置/清单同步/validate_state 全绿）

## 约束自查

- 归档决策经任务 gate（G-T-0108-REQUIREMENTS approved）批准，非静默移动
- 防篡改：语义哈希不重算（semantic_sha256 不变）；清单移除条目 + source_sha256 重算（T-0105 同款处置）；HANDOFF 由官方 render_handoff 重生成
- fail-closed：路由表缺失 → 回退 + 告警，绝不静默空上下文；doc-link 测试只读不写

## 遗留

- `.ai/plans/` 空目录由 planner.py 按需 mkdir 重建（README 已注明）
- implementation_design_diff 对 hooks/scripts 非 v1.0 声明 hook 文件仍报 undesigned（声明驱动正确行为，架构演进时扩充 designed_files）
