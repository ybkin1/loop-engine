#!/usr/bin/env python3
"""update_standards.py — standards.md 加第五维（OQA-5D）"""
from pathlib import Path

p = Path(r"C:\Users\Administrator\.qoder-cn\skills\loop-engineering\references\output-quality-standards.md")
t = p.read_text(encoding="utf-8")

if "维度五：真实性" in t:
    print("[same] standards.md already has dimension 5")
    raise SystemExit(0)

block = """## 5. 维度五：真实性（AUTHENTICITY）— AI 行为验证（OQA-5D，T-0168）

**目标**：防止 AI 幻觉、编造、偷懒、过度设计、前后偏差——验证产出是
"真的做了"，而非"形状像做了"。

| 检查器 | 判定规则 | 违规级别 |
|--------|---------|---------|
| AH-01 reference-existence | import/require 目标文件不存在 → BLOCKER（每条） | BLOCKER |
| AH-02 file-ref-existence | 文档/代码引用相对路径不存在 → WARNING | WARNING |
| AF-01 evidence-authenticity | evidence content_hash 与真实内容不符 / 声称的 artifact 不存在 → BLOCKER | BLOCKER |
| AF-02 completion-claims | 任务有 AC 但无证据目录 → WARNING | WARNING |
| AL-01 placeholder-detection | TODO/FIXME/NotImplemented/占位符 → BLOCKER（每条） | BLOCKER |
| AL-02 test-quality | 测试 0 断言 / 无失败路径用例 → WARNING | WARNING |
| AO-01 dead-code | 导出符号零引用（入口符号豁免）→ WARNING | WARNING |
| AO-02 ghost-interfaces | 接口无实现者无调用方 → WARNING | WARNING |
| AI-01 doc-impl-drift | 文档 @param 数与实际签名不符 → WARNING | WARNING |
| AI-02 state-artifact-drift | state 声称任务活跃但目标无产物 → WARNING | WARNING |

**验收口径**：AH/AF/AL-01 零命中（真实性红线，BLOCKER 阻断交付）；
AL-02/AO/AI WARNING 需在交付说明中附修复计划或明确豁免理由。

"""

anchor = "## 5. 报告与证据绑定"
assert t.count(anchor) == 1, f"anchor count={t.count(anchor)}"
t = t.replace(anchor, block + "## 6. 报告与证据绑定", 1)
# 后续节号顺延
t = t.replace("## 6. 角色职责对照", "## 7. 角色职责对照")
t = t.replace("## 7. 与既有体系的边界", "## 8. 与既有体系的边界")
p.write_text(t, encoding="utf-8")
print("[patch] standards.md dimension 5 added")
