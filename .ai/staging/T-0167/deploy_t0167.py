#!/usr/bin/env python3
"""deploy_t0167.py — T-0167 OQA-4D 部署脚本（幂等，可重复运行）

将 .ai/staging/T-0167/ 下的资产部署到 .qoder-cn 目标位置，并接线：
1. output_quality.ts        → loop-engine-lab/src/core/output_quality.ts
2. output_quality_guard.js  → hooks/scripts/output_quality_guard.js
3. output-quality-standards.md → skills/loop-engineering/references/
4. output_quality.test.ts   → loop-engine-lab/tests/
5. core/index.ts 追加导出
6. server/tools.ts 注册 loop_output_quality + loop_quality_gate
7. skills/loop-engineering/SKILL.md 加 OQA 节
8. skills/loop-engineering/roles/R06-developer.md 产出自检更新

幂等策略：已存在目标文件且内容一致 → 跳过；插入文本带哨兵标记 → 重复运行不重复插入。
"""
import hashlib
import shutil
import sys
from pathlib import Path

QODER_CN = Path(r"C:\Users\Administrator\.qoder-cn")
STAGING = Path(r"C:\Users\Administrator\ZCodeProject\loop-engine\.ai\staging\T-0167")

OQA_R06_BLOCK = """
## 产出质量自检（OQA-4D，T-0167 强制）

交付代码前必须调用 `loop_output_quality`（target = 本次产出路径，
task_id = 当前任务）并满足：

- [ ] **REQUIREMENTS**：产出在任务卡 allowed_paths 内；全部 [AC-xx] 有引用
- [ ] **CODING**：无密钥/调试残留；文件 ≤ 400 行（>1200 行直接 BLOCKER）
- [ ] **DESIGN**：无循环依赖；新模块已声明进架构 designed_files
- [ ] **ENGINEERING**：新源码有对应测试；任务有证据提交
- [ ] `loop_quality_gate` 返回 `gateable: true`

任一 BLOCKER → 修复后重新验证，不得自行宣布合格（P5 生成者不能自审）。
标准依据：`../references/output-quality-standards.md`

"""

def sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()

def deploy_copy(src_name: str, dst: Path) -> bool:
    src = STAGING / src_name
    if not src.exists():
        print(f"[skip] staging missing: {src_name}")
        return False
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists() and sha256(dst) == sha256(src):
        print(f"[same] {dst.relative_to(QODER_CN)}")
        return False
    shutil.copy2(src, dst)
    print(f"[copy] {dst.relative_to(QODER_CN)}")
    return True

def patch_file(path: Path, sentinel: str, block: str, after: str) -> bool:
    """在 after 之后插入 block（带 sentinel 防重复）。"""
    if not path.exists():
        print(f"[skip] missing target: {path}")
        return False
    text = path.read_text(encoding="utf-8")
    if sentinel in text:
        print(f"[same] {path.relative_to(QODER_CN)} (sentinel present)")
        return False
    if after not in text:
        print(f"[warn] anchor not found in {path.relative_to(QODER_CN)}")
        return False
    text = text.replace(after, after + block, 1)
    path.write_text(text, encoding="utf-8")
    print(f"[patch] {path.relative_to(QODER_CN)}")
    return True

def main() -> int:
    deploy_copy("output_quality.ts", QODER_CN / "loop-engine-lab/src/core/output_quality.ts")
    deploy_copy("output_quality_guard.js", QODER_CN / "hooks/scripts/output_quality_guard.js")
    deploy_copy("output-quality-standards.md", QODER_CN / "skills/loop-engineering/references/output-quality-standards.md")
    deploy_copy("output_quality.test.ts", QODER_CN / "loop-engine-lab/tests/output_quality.test.ts")

    # ── 5. core/index.ts 导出（幂等：先清后插）──
    idx = QODER_CN / "loop-engine-lab/src/core/index.ts"
    if "OQA-4D Output Quality Engine" in idx.read_text(encoding="utf-8"):
        print(f"[same] {idx.relative_to(QODER_CN)} (sentinel present)")
    else:
        # 插入到 loop_discovery 导出块之后
        anchor = "} from \"./loop_discovery.js\";"
        block = """\n// ── Output Quality Engine (OQA-4D, T-0167) ──────────────────────────\nexport {\n  OutputQualityEngine,\n  renderReportSummary,\n  DIMENSION_ORDER,\n  ENGINE_VERSION,\n} from \"./output_quality.js\";\nexport type {\n  DimensionId,\n  QualityFinding,\n  QualityCheck,\n  DimensionReport,\n  OutputQualityReport,\n  VerifyContext,\n} from \"./output_quality.js\";\n"""
        patch_file(idx, "OQA-4D Output Quality Engine", block, anchor)

    # ── 6. server/tools.ts 注册工具 ──
    patch_file(
        QODER_CN / "loop-engine-lab/src/server/tools.ts",
        "OQA-4D Output Quality tools",
        """
      // ── T-0167 OQA-4D Output Quality tools ──
      { name: "loop_output_quality", description: "Four-dimension output quality verification (REQUIREMENTS/CODING/DESIGN/ENGINEERING). Returns structured report with BLOCKER/WARNING/INFO findings.", inputSchema: { type: "object", properties: { project_root: { type: "string" }, target: { type: "string", description: "File or directory to verify (relative to project_root)" }, task_id: { type: "string", description: "Task ID for requirement binding (from state.yaml)" }, phase: { type: "string" }, role: { type: "string" }, dimensions: { type: "array", items: { type: "string" } } }, required: ["target"] } },
      { name: "loop_quality_gate", description: "Gate decision for an artifact: true when overall != BLOCKED. Call before gate advance / role handoff.", inputSchema: { type: "object", properties: { project_root: { type: "string" }, target: { type: "string", description: "File or directory to verify" }, task_id: { type: "string" } }, required: ["target"] } },
""",
        "    ],\n  }));",
    )
    patch_file(
        QODER_CN / "loop-engine-lab/src/server/tools.ts",
        "OQA-4D handlers",
        """
        // ── T-0167 OQA-4D handlers ──
        case "loop_output_quality": {
          const { OutputQualityEngine, renderReportSummary } = await import("../core/output_quality.js");
          const engine = new OutputQualityEngine(root);
          const report = engine.verifyTarget(args!.target as string, {
            task_id: args?.task_id as string | undefined,
            phase: args?.phase as string | undefined,
            role: args?.role as string | undefined,
            dimensions: args?.dimensions as Array<"REQUIREMENTS" | "CODING" | "DESIGN" | "ENGINEERING"> | undefined,
          });
          return textReply(JSON.stringify(report, null, 2) + "\\n\\n" + renderReportSummary(report));
        }

        case "loop_quality_gate": {
          const { OutputQualityEngine } = await import("../core/output_quality.js");
          const engine = new OutputQualityEngine(root);
          const report = engine.verifyTarget(args!.target as string, {
            task_id: args?.task_id as string | undefined,
          });
          const gateable = report.overall !== "BLOCKED";
          return textReply(JSON.stringify({
            tool: "loop_quality_gate",
            target: report.target,
            overall: report.overall,
            gateable,
            blocked_by: report.blocked_by,
            content_hash: report.content_hash,
            evidence_ref: report.overall === "BLOCKED" ? null : `quality:${report.content_hash.slice(0, 12)}`,
          }, null, 2));
        }

""",
        "        default:\n          return textReply(`Unknown tool: ${name}`);",
    )

    # ── 7. SKILL.md 加 OQA 节 ──
    patch_file(
        QODER_CN / "skills/loop-engineering/SKILL.md",
        "OQA-4D",
        """
---

## 产出质量保障（OQA-4D，T-0167）

**任何产出（代码/文档/配置）交付前必须通过四维质量验证**，机器判定依据
见 `references/output-quality-standards.md`：

| 维度 | 检查器 | 机器入口 |
|------|--------|---------|
| REQUIREMENTS 需求符合性 | RQ-01 任务卡绑定 / RQ-02 AC 覆盖 / RQ-03 需求溯源 | `loop_output_quality` |
| CODING 编码规范 | CD-01 密钥 / CD-02 调试残留 / CD-03 文件规模 / CD-04 魔法数 / CD-05 工具链 | 同上 |
| DESIGN 设计理念 | DS-01 架构对齐 / DS-02 循环依赖 / DS-03 分层 / DS-04 文档一致 | 同上 |
| ENGINEERING 软件工程 | EN-01 测试存在 / EN-02 证据绑定 / EN-03 可复算 / EN-04 评审就绪 / EN-05 规模 | 同上 |

**执行纪律（不可协商）：**
1. R06 写代码前/后调用 `loop_output_quality` 自检，交付前 CD/EN 清零。
2. 写操作 PreToolUse 时 `output_quality_guard.js` 做轻量预检（密钥硬拒 + 告警）。
3. Gate 推进前 R11 必须调用 `loop_quality_gate` 且返回 `gateable: true`。
4. 任一 BLOCKER 未清零 → 不得宣称产出合格（对齐 EVIDENCE_ONLY_BOUNDARY）。
5. 报告内容哈希由引擎计算，作为证据提交（type: quality）绑定任务。

""",
        "## 约束条件",
    )

    # ── 8. R06-developer.md 产出自检 ──
    r06_target = QODER_CN / "skills/loop-engineering/roles/R06-developer.md"
    r06_anchor = "## 角色能力档案"
    if not r06_target.exists():
        # 退化为独立 skill 形态
        r06_target = QODER_CN / "skills/loop-r06-developer/SKILL.md"
        r06_anchor = "## 产出质量"
    if r06_target.exists() and r06_anchor not in r06_target.read_text(encoding="utf-8"):
        # 锚点不存在时退化为文件尾追加
        r06_anchor = None
    if r06_anchor is None:
        text = r06_target.read_text(encoding="utf-8")
        if "OQA-4D" in text:
            print(f"[same] {r06_target.relative_to(QODER_CN)} (sentinel present)")
        else:
            r06_target.write_text(text.rstrip() + "\n\n" + OQA_R06_BLOCK, encoding="utf-8")
            print(f"[append] {r06_target.relative_to(QODER_CN)}")
    else:
        patch_file(
            r06_target,
            "OQA-4D",
            OQA_R06_BLOCK,
            r06_anchor,
        )

    print("\n[deploy] T-0167 OQA-4D deployment complete.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
