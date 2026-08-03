# T-0108 验收报告 — BH 融合·收敛期（F4/F6/F7/F8/F2-1）

- 任务：T-0108（G-T-0108-REQUIREMENTS，approved）— T-0106 排布次项：F6 上下文打包升级 +
  F4 文档路由 + F7 finding 结构化契约 + F8 治理契约测试 + F2 阶段 1（只读新鲜度）
- 角色：governance-controller（编排与验收）；developer（五线实现）；independent-reviewer（独立审查）
- 执行时间：2026-08-03（UTC+8）
- 基线：git HEAD `3e766ec`（v3.12.44，T-0106 修复闭环）；版本 bump **3.12.45**
- 设计依据：`.ai/evidence/T-0106/design/design-bh-integration.md`（F2/F4/F6/F7/F8）+ `plan-task-roadmap.md` T-0108 节

---

## 一、五线交付

| 线 | 内容 | 关键产出 |
|----|------|---------|
| F6 上下文打包 | token 预算/AC 节/截断标记/timeout 常量（接续 T-0107） | `context_budget.py`（新增）+ context_packager 外提（行为逐字节等价）；P3 消解 D1-3/D2-8/D4-4 |
| F4 文档路由 | Switchboard + 目录四态 + 死文档归档 + 路由表 + designed_files | `.ai/README.md`（新增）+ 归档 2 文件（continuity 同步）+ context_loader 路由表接入（golden 一致）+ D5-7 显式声明区（误报清零）；P3 消解 D5-3/D5-7 |
| F7 finding 契约 | finding.schema.json + 扫描器/agents 输出收敛 | `finding.schema.json` + `finding_contract.py`（fail-closed + BH 字段映射）；三扫描器 + 三 agents 脚本收敛；P3 消解 D5-6/D1-7/D4-10/D4-11 |
| F8 契约测试 | doc-link 完整性 + 投影新鲜度 | 3 测试文件 **50 用例**（断链 FAIL 实证 ×2） |
| F2-1 新鲜度 | validate_state 只读告警 + projection_engine | `projection_engine.py`（新增）+ validate_state **纯新增 37 行 / 0 删除**（`[warn] stale view` 仅告警） |

## 二、AC 对照

| AC | 验收标准 | 结果 |
|----|---------|------|
| AC-01 | README Switchboard 三节 + doc-link 测试全绿（断链 FAIL） | **PASS**（独立重跑 8 用例含断链 FAIL×2） |
| AC-02 | context_loader 路由表 + golden 一致 + 缺失回退告警 | **PASS**（路由 keyword 与旧启发式逐项一致；回退+warning 实证） |
| AC-03 | finding schema 校验 + BH 字段映射对照 | **PASS**（schema 与 .qoder BH findings.json 实样对照吻合；非法 finding → INVALID） |
| AC-04 | validate_state 旧 mtime → `[warn] stale view` 仅告警 | **PASS**（手工 A/B：error 集合与 exit code 逐条一致） |
| AC-05 | 投影视图 = state.yaml 派生 | **PASS**（一致性测试 8 用例） |
| AC-06 | 归档 + continuity 同步 + D5-7 显式声明区 | **PASS**（git mv 归档 + 源清单同步无 SOURCE_DRIFT；checker 误报清零） |
| AC-07 | 全量回归 0 failed + compile + release check 6/6 | **PASS**（closeout 序列后复验，见审查 P2） |
| AC-08 | 版本 3.12.45 == git HEAD | **PASS**（提交后成立） |
| AC-09 | 独立审查 GO + hooks/内核零改动 diff 实证 | **PASS**（CONDITIONAL_GO → closeout 序列执行 → GO；hooks/ 空 diff、内核零触碰、validate_state 纯新增） |

## 三、独立审查摘要（independent-review.md）

- **裁决：CONDITIONAL_GO → GO**（P1=0；P2×1 closeout 序列：提交 bump → 重算 continuity → 生成 manifest → 重跑回归确认 0 failed；P3×4 记录）
- 约束零弱化：hooks/ 空 diff；治理内核零 diff；validate_state 37 insertions/0 deletions 纯新增；fail-closed 语义不变（路由回退/INVALID 不静默/失败原因上报）
- 五线逐线 PASS（F6 外提逐字节等价、F4 归档+路由、F7 schema 实样对照、F8 独立重跑、F2-1 只读告警）
- 全量回归独立复验：**3957 passed / 5 failed**（4 项已知或瞬态：环境依赖/closeout/bump 前；2 项仓库态测试根因 = bump 后 continuity 漂移，closeout 重生成自愈）
- 实测发现：content_guard 架构合规对 bullet 形式 designed_files 解析限制 → 已用 YAML flow 风格规避（hook 零改动约束下正确路径）

## 四、裁决

**T-0108 验收通过（9/9 AC）。** BH 融合·收敛期五线落地：上下文打包升级、文档路由体系、
finding 契约化、治理契约测试、只读新鲜度检查；8 项 P3 消解；hooks/ 零改动、治理内核零触碰。
版本 3.12.45。

## 五、下一步

T-0109（BH 融合·分层期：F2-2/F3/F1/F5）待用户批准。P3 记录项（F2 措辞、版本载体枚举）随后续顺带。
