"""
Loader section selection — framework titles + role-relevant section routing.

T-0110 批 B-2 拆分（行为等价，纯外提 re-export）：
- 原 loop_core/context_loader.py 的文档节选择/框架标题（_extract_framework_titles /
  _select_relevant_sections）及 T-0108 F4（D5-3）路由表逻辑（_parse_front_matter_yaml /
  _load_section_routing / _ROUTING_CACHE）逐字迁移至此（design-common-weakness.md
  1.5 拆分边界表 :1268-1324 + T-0108 接入的 .ai/README.md section_routing 路由表）。
- 本模块是依赖图叶子：仅标准库（json/logging/re/Path）。
- 壳文件 re-export 保持公开面（含私有名与 _ROUTING_CACHE 同一 dict 对象）
  逐名一致；路由缓存语义不变（key = (path, mtime_ns, size)）。
"""
from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:  # 仅类型检查：运行时零导入（避免与壳循环导入）
    from loop_core.context_loader import DocumentIndex

logger = logging.getLogger(__name__)


def _extract_framework_titles(framework_path: Path) -> str | None:
    """Extract Step 1-4 titles from THINKING_FRAMEWORK.md.

    Returns a compact summary with just the step names, not the full
    content.  This is used for STANDARD-level loading (~300 additional
    tokens vs ~1200 for the full framework).
    """
    raw = framework_path.read_text(encoding="utf-8")
    lines = raw.splitlines()

    titles: list[str] = []
    in_step = False
    for line in lines:
        stripped = line.strip()
        # Match "### Step N: ..." headings
        if re.match(r'^###\s+Step\s+\d+:', stripped):
            titles.append(stripped)
            in_step = True
        elif stripped.startswith("## ") and in_step:
            # We've gone past the steps into a new top-level section
            break

    if not titles:
        return None

    result_lines = ["## Thinking Framework (Summary)"]
    for t in titles:
        result_lines.append(f"- {t}")
    return "\n".join(result_lines)


def _select_relevant_sections(
    role_id: str, doc_index: DocumentIndex, project_root: Path | str | None = None
) -> list[str]:
    """Select document sections relevant to a given role.

    T-0108 F4 (D5-3 消解): when *project_root* is given, section selection
    is driven by the Switchboard routing table in ``.ai/README.md``
    (front-matter ``section_routing:`` — role → keyword list, substring
    match on lowercased section names, same semantics as the legacy
    heuristic so golden snapshots are unchanged).  If the routing table is
    missing/unparseable, falls back to the legacy keyword heuristic and
    logs a warning (fail-closed: never silently return an empty context).

    Falls back to returning the first 3 section names when no match is
    found (the caller can decide how many to include).
    """
    available = list(doc_index.sections.keys())
    if not available:
        return []

    routing = _load_section_routing(project_root)
    if routing is not None:
        keywords = routing.get(role_id, routing.get("default", []))
        if not isinstance(keywords, list):
            keywords = []
        keywords = [str(k) for k in keywords]
        if not keywords:
            return available[:3]
        matched = [s for s in available if any(kw in s.lower() for kw in keywords)]
        return matched if matched else available[:3]

    if project_root is not None:
        logger.warning(
            "[context_loader] .ai/README.md section_routing missing — "
            "falling back to legacy keyword heuristic (D5-3)"
        )

    # ── Legacy keyword heuristic (fallback, kept byte-for-byte) ─────────
    # Map role keywords to likely section-name keywords
    role_keywords: dict[str, list[str]] = {
        "quality-engineer": ["test", "quality", "coverage", "lint", "gate"],
        "security-engineer": ["security", "auth", "encrypt", "vulnerab"],
        "frontend": ["frontend", "ui", "component", "page", "style"],
        "developer": ["implement", "code", "module", "build"],
        "architect": ["architect", "design", "pattern", "structure"],
        "system-architect": ["architect", "design", "pattern", "structure", "system"],
        "module-architect": ["architect", "design", "module", "pattern"],
        "project-manager": ["plan", "schedule", "milestone", "risk"],
        "product-manager": ["requirement", "feature", "user", "story"],
        "delivery-manager": ["deploy", "release", "delivery", "ship"],
        "release-engineer": ["deploy", "release", "ci", "pipeline"],
    }

    keywords = role_keywords.get(role_id, [])

    if not keywords:
        # Generic fallback: return first 3 sections
        return available[:3]

    matched: list[str] = []
    for section_name in available:
        lower = section_name.lower()
        if any(kw in lower for kw in keywords):
            matched.append(section_name)

    return matched if matched else available[:3]


# T-0108 F4: Switchboard routing-table loader (D5-3).
# key = (readme_path, mtime_ns, size) → routing dict or None (missing/invalid).
_ROUTING_CACHE: dict[tuple[str, int, int], dict | None] = {}


def _parse_front_matter_yaml(text: str) -> Any:
    """Parse a leading ``--- ... ---`` YAML front-matter block, else None."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None
    end = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end = i
            break
    if end is None:
        return None
    block = "\n".join(lines[1:end])
    try:
        import yaml
        return yaml.safe_load(block)
    except ImportError:
        pass
    except Exception:
        pass
    try:
        return json.loads(block)
    except Exception:
        return None


def _load_section_routing(project_root: Path | str | None) -> dict | None:
    """Load the ``section_routing`` table from ``.ai/README.md``.

    Returns None when the README is missing or has no usable
    ``section_routing`` mapping — the caller falls back to the legacy
    heuristic.  Never raises.
    """
    if project_root is None:
        return None
    readme = Path(project_root) / ".ai" / "README.md"
    try:
        stat = readme.stat()
    except OSError:
        return None
    key = (str(readme), stat.st_mtime_ns, stat.st_size)
    if key in _ROUTING_CACHE:
        return _ROUTING_CACHE[key]
    result: dict | None = None
    try:
        front_matter = _parse_front_matter_yaml(readme.read_text(encoding="utf-8"))
        if isinstance(front_matter, dict):
            routing = front_matter.get("section_routing")
            if isinstance(routing, dict):
                result = routing
    except Exception:
        result = None
    _ROUTING_CACHE[key] = result
    return result
