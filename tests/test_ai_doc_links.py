"""
test_ai_doc_links.py — .ai 文档链接完整性测试（T-0108 F8，仿 BH doc-link-graph）。

覆盖（AC-01）：
- 遍历 `.ai/` 治理文档（README Switchboard + 顶层文档）中的引用链接
  （markdown 链接 ``[t](path)`` 与反引号路径引用 ```path``），校验目标存在；
- 断链 → 检查器报告（断链用例必须 FAIL —— 有专用断言）；
- README Switchboard 三节（Owns / Does Not Own / Read Next）存在性断言；
- 归档引用（.ai/archive/plans/...）解析（AC-06 无悬挂引用）。

约束（design F8 必须保持）：测试只读（不写 .ai/、不触发 repair）；
白名单机制：外链（http/mailto/#锚点）与无扩展名的单词不判定。
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

REPO_ROOT = Path(__file__).resolve().parent.parent
AI_DIR = REPO_ROOT / ".ai"

# 检查的目标文档：README + 顶层 *.md（排除 evidence/archive/handoffs 生成区）
LINK_SCAN_DOCS = [
    AI_DIR / "README.md",
    *sorted(
        p for p in AI_DIR.glob("*.md")
        if p.name != "HANDOFF.md"
    ),
]

# 反引号引用中视为"路径引用"的扩展名（否则是代码/命令示例）
_PATH_EXTENSIONS = (".md", ".yaml", ".yml", ".json", ".py", ".toml", ".csv")
_WHITELIST_PREFIXES = ("http://", "https://", "mailto:", "#")
# 反引号路径引用必须是这些已知根前缀之一（避免把 prose 里的示例文件名
# 当作链接）；含 <...> 占位符的引用不判定（模板说明）。
_PATH_ROOTS = (
    ".ai", "docs", "loop_core", "tools", "scripts", "hooks",
    "agents", ".zcode", "tests", "archive", "skills",
)

_MD_LINK_RE = re.compile(r"\[[^\]]*\]\(([^)]+)\)")
_BACKTICK_RE = re.compile(r"`([^`]+)`")

# 白名单（F8 设计：合法外链/动态路径/历史位置说明免判）：
# 值为引用目标（不含尾部 /）。
_WHITELIST_REFS = {
    # T-0108 归档后清空的历史位置（README 归档说明，非链接目标）
    ".ai/plans",
}


def _is_path_reference(ref: str) -> bool:
    """判断反引号引用是否像文件路径（含 / 或点扩展名）。"""
    ref = ref.strip()
    if ref.startswith(_WHITELIST_PREFIXES):
        return False
    if "<" in ref or ">" in ref:
        return False  # 占位符模板（如 <current_task_id>）不是真实路径
    if ref.endswith("/"):
        return True  # 目录引用
    if "/" not in ref:
        return False  # 无目录上下文的裸文件名 = 说明性引用，不判定
    ref2 = ref[2:] if ref.startswith("./") else ref
    first = ref2.split("/", 1)[0]
    return first in _PATH_ROOTS or first.endswith(_PATH_EXTENSIONS)


def collect_references(doc_path: Path) -> list[tuple[str, str, int]]:
    """收集文档中的引用 (target, kind, line_no)。kind: markdown|backtick。"""
    refs: list[tuple[str, str, int]] = []
    text = doc_path.read_text(encoding="utf-8", errors="replace")
    for lineno, line in enumerate(text.splitlines(), 1):
        for m in _MD_LINK_RE.finditer(line):
            target = m.group(1).strip()
            if not target.startswith(_WHITELIST_PREFIXES):
                refs.append((target.split("#")[0].strip(), "markdown", lineno))
        for m in _BACKTICK_RE.finditer(line):
            ref = m.group(1).strip()
            if _is_path_reference(ref):
                refs.append((ref.rstrip("/"), "backtick", lineno))
    return refs


def resolve_target(doc_path: Path, target: str) -> Path:
    """解析引用目标为绝对路径（.ai/ 内相对，否则相对仓库根）。"""
    target = target.strip()
    if target.startswith("./"):
        target = target[2:]
    candidate = doc_path.parent / target
    if candidate.exists():
        return candidate
    root_candidate = REPO_ROOT / target
    if root_candidate.exists():
        return root_candidate
    # 大小写不敏感兜底（Windows）
    if sys.platform == "win32":
        for base in (doc_path.parent, REPO_ROOT):
            cand = _case_insensitive_lookup(base, target)
            if cand is not None:
                return cand
    return candidate  # 不存在时返回期望路径（供断言信息展示）


def _case_insensitive_lookup(base: Path, target: str) -> Path | None:
    cur = base
    for part in target.split("/"):
        if part in ("", "."):
            continue
        matches = [p for p in cur.iterdir() if p.name.lower() == part.lower()]
        if not matches:
            return None
        cur = matches[0]
    return cur


def check_doc_links(docs: list[Path] | None = None) -> list[str]:
    """返回全部断链描述；空列表 = 全绿。只读，不写任何文件。"""
    broken: list[str] = []
    for doc in docs or LINK_SCAN_DOCS:
        if not doc.exists():
            continue
        for target, kind, lineno in collect_references(doc):
            if target.rstrip("/") in _WHITELIST_REFS:
                continue
            resolved = resolve_target(doc, target)
            if not resolved.exists():
                broken.append(
                    f"{doc.relative_to(REPO_ROOT).as_posix()}:{lineno} "
                    f"[{kind}] {target} → 目标不存在"
                )
    return broken


# ============================================================================
# 真实仓库：README Switchboard 三节存在 + 全链接可解析（AC-01 / AC-06）
# ============================================================================


class TestReadmeSwitchboard:
    def test_three_sections_present(self):
        """README 包含 Owns / Does Not Own / Read Next 三节（AC-01）。"""
        readme = (AI_DIR / "README.md").read_text(encoding="utf-8")
        for section in ("## Owns", "## Does Not Own", "## Read Next"):
            assert section in readme, f"Switchboard 缺少 {section} 节"

    def test_directory_four_states_present(self):
        """目录四态标注存在（active/generated/target/candidate）。"""
        readme = (AI_DIR / "README.md").read_text(encoding="utf-8")
        for state in ("active", "generated", "target", "candidate", "archived"):
            assert state in readme, f"目录四态缺少 {state}"

    def test_doc_classification_table_present(self):
        """文档活/死归类表存在且归档指向 .ai/archive/plans/。"""
        readme = (AI_DIR / "README.md").read_text(encoding="utf-8")
        assert "PLAN-20260729-001.yaml" in readme
        assert ".ai/archive/plans/" in readme


class TestAiDocLinks:
    def test_all_repo_links_resolve(self):
        """仓库 .ai 治理文档全部引用可解析（AC-01 doc-link 全绿）。"""
        broken = check_doc_links()
        assert broken == [], "\n".join(broken)

    def test_archived_plans_have_no_dangling_reference(self):
        """归档后无悬挂引用：归档文件存在且不在 .ai/plans/ 原位置。"""
        for name in ("PLAN-20260729-001.yaml", "PLAN-20260729-002.yaml"):
            archived = AI_DIR / "archive" / "plans" / name
            original = AI_DIR / "plans" / name
            assert archived.is_file(), f"归档文件缺失: {archived}"
            assert not original.exists(), f"原位置仍存在（未移动）: {original}"

    def test_routing_table_parseable(self):
        """README front-matter section_routing 可被 context_loader 解析。"""
        from loop_core.context_loader import _load_section_routing

        routing = _load_section_routing(REPO_ROOT)
        assert routing is not None
        assert "quality-engineer" in routing
        assert routing["quality-engineer"] == [
            "test", "quality", "coverage", "lint", "gate",
        ]


class TestBrokenLinkDetection:
    """断链用例：检查器必须 FAIL（AC-01：断链用例 FAIL）。"""

    def _make_tree(self, tmp_path: Path) -> Path:
        ai = tmp_path / ".ai"
        (ai / "sub").mkdir(parents=True)
        (ai / "state.yaml").write_text("schema_version: 1\n", encoding="utf-8")
        return ai

    def test_broken_markdown_link_detected(self, tmp_path):
        ai = self._make_tree(tmp_path)
        (ai / "README.md").write_text(
            "# Switchboard\n\n## Owns\n\n- [状态](state.yaml)\n"
            "- [断链](missing-file.yaml)\n",
            encoding="utf-8",
        )
        # 用临时目录自建文档集检查（避免污染真实仓库断言）
        docs = [ai / "README.md"]
        # 检查器需要 REPO_ROOT 指向临时仓库 → 临时 monkeypatch 路径解析
        import test_ai_doc_links as mod

        orig_root, orig_ai = mod.REPO_ROOT, mod.AI_DIR
        mod.REPO_ROOT, mod.AI_DIR = tmp_path, ai
        try:
            broken = mod.check_doc_links(docs)
        finally:
            mod.REPO_ROOT, mod.AI_DIR = orig_root, orig_ai
        assert len(broken) == 1, broken
        assert "missing-file.yaml" in broken[0]

    def test_broken_backtick_path_detected(self, tmp_path):
        ai = self._make_tree(tmp_path)
        (ai / "README.md").write_text(
            "# Switchboard\n\n## Owns\n\n- `.ai/state.yaml`\n- `.ai/ghost.yaml`\n",
            encoding="utf-8",
        )
        import test_ai_doc_links as mod

        orig_root, orig_ai = mod.REPO_ROOT, mod.AI_DIR
        mod.REPO_ROOT, mod.AI_DIR = tmp_path, ai
        try:
            broken = mod.check_doc_links([ai / "README.md"])
        finally:
            mod.REPO_ROOT, mod.AI_DIR = orig_root, orig_ai
        assert len(broken) == 1, broken
        assert ".ai/ghost.yaml" in broken[0]
