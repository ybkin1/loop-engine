#!/usr/bin/env python3
"""update_standards_t171.py — standards.md 增 AI-03 行 + 模式库说明（T-0171）"""
from pathlib import Path

p = Path(r"C:\Users\Administrator\.qoder-cn\skills\loop-engineering\references\output-quality-standards.md")
t = p.read_text(encoding="utf-8")

if "AI-03" in t:
    print("[same] AI-03 already present")
else:
    old = "| AI-02 state-artifact-drift | state 声称任务活跃但目标无产物 → WARNING | WARNING |"
    new = old + "\n| AI-03 ac-implementation | AC 语义关键词在实现中完全缺失 → BLOCKER；无实现文件/部分验证 → WARNING（需人工确认） | BLOCKER / WARNING |"
    assert t.count(old) == 1, f"anchor={t.count(old)}"
    t = t.replace(old, new)
    print("[patch] AI-03 row added")

if "模式库" not in t:
    block = """

## 9. OQA 模式库（T-0171）

项目级 `.ai/oqa-patterns.yaml` 可扩展 AI 偷懒/幻觉/编造检测模式，与内置模式
合并（同名覆盖）。内置模式：LAZY-FAKE-DATA / LAZY-SWALLOW-EXCEPTION /
LAZY-EMPTY-FUNCTION / HALLUCINATE-COMMENT-CLAIM / FABRICATE-HARDCODED-EXPECT。
MCP 工具 `loop_oqa_patterns`（list/add）管理模式库。
"""
    t = t.rstrip() + "\n" + block
    print("[patch] pattern library section added")

p.write_text(t, encoding="utf-8")
print("[ok] standards.md updated")
