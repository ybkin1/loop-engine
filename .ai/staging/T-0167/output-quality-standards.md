# Output Quality Standards — OQA-4D 四维产出质量标准

> 版本 1.0 | 与 `loop-engine-lab/src/core/output_quality.ts` 引擎同步
> 本文件是 **任意产出（代码/文档/配置）交付前的质量判定依据**。
> 机器执行：MCP 工具 `loop_output_quality`（深度四维验证）+ PreToolUse hook
> `output_quality_guard.js`（写入前轻量预检）。
> 判定语义：**BLOCKER 阻断交付 / WARNING 记档建议 / INFO 观察**。

---

## 0. 适用范围与总则

1. **适用对象**：Loop 治理项目内任意产出的文件/目录（`src/` 代码、`docs/`
   文档、配置、测试），在 Gate 推进与角色交接前必须通过本标准的四维验证。
2. **机器优先**：所有检查项均可被 `output_quality.ts` 确定性执行（纯函数、
   同输入同输出、报告含内容 SHA-256）。
3. **人工复核兜底**：机器验证是 evidence，不替代用户 gate 批准；任何 BLOCKER
   未清零不得宣称产出合格（对齐 EVIDENCE_ONLY_BOUNDARY）。
4. **分级处置**：
   - `BLOCKER` — 阻断交付；修复后重新验证。
   - `WARNING` — 建议修复；记录在报告中，交付时可带说明。
   - `INFO` — 观察项，不阻断。

---

## 1. 维度一：需求符合性（REQUIREMENTS）

**目标**：产出必须可回溯到任务与验收标准，任何产出都能回答"它满足哪个
需求、对应哪条 AC"。

| 检查器 | 判定规则 | 违规级别 |
|--------|---------|---------|
| RQ-01 task-card-binding | 验证时未传 task_id → BLOCKER；任务卡不存在 → BLOCKER；产出路径不在任务卡 allowed_paths → BLOCKER（每条） | BLOCKER |
| RQ-02 ac-reference | 任务卡含 AC 且产出集合中 ≥1 个文件引用该 AC id → 覆盖；未引用的 AC 数 >0 → WARNING（附覆盖率） | WARNING |
| RQ-03 requirement-traceability | 产出集合含 requirements/acceptance 类文档或文档正文提及"验收标准/AC-xx" → PASS；否则 INFO（不可验证） | INFO |

**验收口径**：交付前 `RQ-01` 必须零违规；`RQ-02` 覆盖率 ≥ 100%（无遗漏 AC）。

---

## 2. 维度二：编码规范（CODING）

**目标**：产出符合工程编码纪律——无密钥泄漏、无调试残留、规模可控、
命名与结构可维护。

| 检查器 | 判定规则 | 违规级别 |
|--------|---------|---------|
| CD-01 secret-scan | 命中 4 类密钥模式（api_key/secret/token/password ≥16 位、私钥块、AKIA、sk-*）→ BLOCKER（每条） | BLOCKER |
| CD-02 debug-residue | console.log / print(DEBUG / debugger 残留 → WARNING（每条）；无 BLOCKER | WARNING |
| CD-03 file-scale | 代码文件 >1200 行 → BLOCKER；>400 行 → WARNING | BLOCKER / WARNING |
| CD-04 magic-numbers | 代码中裸 3+ 位数字常量 → INFO（建议命名常量） | INFO |
| CD-05 toolchain-clean | 项目缺 package.json/pyproject → INFO（lint/typecheck 不可用）；有清单 → INFO 提示需跑 loop_quality_run | INFO |

**验收口径**：`CD-01` 零命中；`CD-02`/`CD-03` WARNING 数 ≤ 可接受值（默认 0
为交付门槛，可在报告中附修复计划）。

---

## 3. 维度三：设计理念（DESIGN）

**目标**：产出遵循架构设计——模块在架构清单内、依赖无环、分层正确、
文档与实现一致。

| 检查器 | 判定规则 | 违规级别 |
|--------|---------|---------|
| DS-01 architecture-alignment | 产出代码文件未在架构文档 designed_files 清单（front-matter 或代码块）→ WARNING；架构文档缺失 → INFO | WARNING |
| DS-02 no-circular-imports | TS/JS 文件间检测到循环 import → BLOCKER（每条环） | BLOCKER |
| DS-03 layering-tests | 测试文件直接 import src 内部实现（`../src/...`）→ WARNING | WARNING |
| DS-04 doc-impl-consistency | 新代码目录未在产出集文档中提及 → INFO | INFO |

**验收口径**：`DS-02` 零环；`DS-01` 新模块必须声明进架构清单（或经独立 gate
批准扩展）。

---

## 4. 维度四：软件工程（ENGINEERING）

**目标**：产出具备工程完整性——有测试、有证据、可复算、可评审。

| 检查器 | 判定规则 | 违规级别 |
|--------|---------|---------|
| EN-01 test-existence | 新源码文件无对应测试文件（同基名）→ WARNING（每条） | WARNING |
| EN-02 evidence-binding | 任务无 `.ai/evidence/<task_id>/` 证据 → WARNING | WARNING |
| EN-03 replayability | 产出含 >5 个绝对时间戳 → INFO（可复算噪声） | INFO |
| EN-04 review-readiness | 任务无独立评审产物（.ai/reviews/ 或 evidence/review-report）→ WARNING | WARNING |
| EN-05 scope-scale | 目录产出 >50 文件 → WARNING（评审负担） | WARNING |

**验收口径**：交付前 `EN-01`（新代码必有测试）与 `EN-02`（证据链）为强建议项，
Gate 推进前应清零或附明确修复计划。

---

## 5. 报告与证据绑定

1. **报告 schema**：`output_quality_report/v1`
   ```json
   {
     "schema": "output_quality_report/v1",
     "project_root": "...",
     "target": "src/xxx.ts",
     "target_kind": "file",
     "content_hash": "sha256...",
     "context": {"task_id": "T-0001", "phase": "S4", "role": "R06"},
     "dimensions": [
       {"dimension": "REQUIREMENTS", "status": "PASS|WARNING|BLOCKED", "...": "..."}
     ],
     "overall": "PASS|WARNING|BLOCKED",
     "blocked_by": ["CODING(1)"],
     "generated_at": "ISO8601",
     "engine_version": "1.0.0"
   }
   ```
2. **证据绑定**：报告可通过 `loop_evidence_submit`（type: `quality`）写入
   `.ai/evidence/<task_id>/`，内容哈希由引擎计算，防篡改。
3. **Gate 联动**：`loop_quality_gate` 工具判定 `overall !== "BLOCKED"` 时
   才允许推进；Gate 条件中可引用本报告作为 evidence。

---

## 6. 角色职责对照

| 角色 | 对产出质量的责任 |
|------|-----------------|
| R06 开发 | 写代码前跑 `loop_output_quality` 自检；交付前 CD/EN 清零 |
| R07 QA | 以本标准的四维报告复核质量（机器报告 + 人工抽查） |
| R09 评审 | 审查报告发现是否全部有对应修复/说明，BLOCKER=0 才可 PASS |
| R11 编排 | Gate 推进前核验 `loop_quality_gate` 返回 PASS |

---

## 7. 与既有体系的边界

- **本标准的"编码规范"维度** ≠ `.ai/CODING_STANDARDS.md`：前者是机器可执行
  检查器的判定表，后者是人工写作规范；两者互补（机器先拦，规范供人写）。
- **深度引擎**（output_quality.ts）≠ 质量门禁脚本（quality-gates.ts）：
  后者跑 lint/test/build 出 `quality_report.json`，前者做四维产出验证；
  `CD-05` 会提示补充运行后者。
- **Hook 预检**（output_quality_guard.js）≠ gate-guard.js：前者是内容质量
  第一道防线（仅告警 + 密钥硬拒），后者是 Gate 状态机阻断；两者串联在
  PreToolUse 链中。
