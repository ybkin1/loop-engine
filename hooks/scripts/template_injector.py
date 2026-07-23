#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
template_injector.py — ZCode SessionStart hook：根据当前阶段自动注入对应模板。

读取 .ai/state.yaml 确定当前阶段，根据阶段→模板映射加载模板内容，
作为 additionalContext 注入会话，使角色 Agent 启动时自动获得所需模板。

阶段→模板映射：
  S1-requirements → requirements/*.md
  S2-architecture  → architecture/*.md
  S3-interface     → design/*.md + architecture/interface-contract.md
  S4-implementation → coding/*.md + design/*.md
  S5-quality       → testing/*.md + security/*.md
  S6-delivery      → deployment/*.md

本 hook 永不阻断：任何失败都 exit 0（非治理项目则完全静默）。
输出为 SessionStart JSON：{"hookSpecificOutput": {"hookEventName":
"SessionStart", "additionalContext": ...}}。
"""

import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True

sys.path.insert(0, str(Path(__file__).resolve().parent))
from hook_common import (  # noqa: E402
    is_governance_project,
    load_state,
    project_root,
    read_stdin_json,
)

# 相对于项目根的模板目录
TEMPLATES_DIR = Path("skills") / "loop-governance" / "templates"

# 阶段→模板路径列表映射（相对于 TEMPLATES_DIR）
PHASE_TEMPLATE_MAP = {
    "S1-requirements": [
        "requirements",
    ],
    "S2-architecture": [
        "architecture",
    ],
    "S3-interface": [
        "design",
        "architecture/interface-contract.md",
    ],
    "S4-implementation": [
        "coding",
        "design",
    ],
    "S5-quality": [
        "testing",
        "security",
    ],
    "S6-delivery": [
        "deployment",
    ],
}

# 每个阶段注入的最大模板内容字符数（防止上下文过长）
MAX_TEMPLATE_CHARS = 8000


def _resolve_templates(root: Path, phase: str) -> list[Path]:
    """根据阶段解析出需要注入的模板文件绝对路径列表。"""
    template_dir = root / TEMPLATES_DIR
    if not template_dir.exists():
        return []

    specifiers = PHASE_TEMPLATE_MAP.get(phase, [])
    if not specifiers:
        return []

    files: list[Path] = []
    seen: set[str] = set()

    for spec in specifiers:
        candidate = template_dir / spec
        if candidate.is_dir():
            for md_file in sorted(candidate.glob("*.md")):
                key = md_file.name
                if key not in seen:
                    seen.add(key)
                    files.append(md_file)
        elif candidate.is_file() and candidate.suffix == ".md":
            key = candidate.name
            if key not in seen:
                seen.add(key)
                files.append(candidate)

    return files


def _read_template_content(file_path: Path) -> str:
    """读取单个模板文件的内容，失败返回空字符串。"""
    try:
        return file_path.read_text(encoding="utf-8")
    except Exception:
        return ""


def build_template_context(root: Path, phase: str) -> str | None:
    """构建模板注入上下文；无匹配模板时返回 None。"""
    files = _resolve_templates(root, phase)
    if not files:
        return None

    lines: list[str] = [
        "[loop-governance] 模板自动注入（template_injector hook）",
        f"当前阶段: {phase}",
        f"已加载 {len(files)} 个模板:",
    ]
    for f in files:
        rel = str(f.relative_to(root)).replace("\\", "/")
        lines.append(f"  - {rel}")

    lines.append("")
    lines.append("--- 模板内容 ---")
    lines.append("")

    total_chars = len("\n".join(lines))
    for f in files:
        content = _read_template_content(f)
        if not content:
            continue
        rel = str(f.relative_to(root)).replace("\\", "/")
        header = f"### BEGIN TEMPLATE: {rel}"
        footer = f"### END TEMPLATE: {rel}"
        block = f"{header}\n\n{content}\n\n{footer}"

        if total_chars + len(block) > MAX_TEMPLATE_CHARS:
            lines.append(f"### TEMPLATE TRUNCATED: {rel}（超出 {MAX_TEMPLATE_CHARS} 字符限制）")
            break

        lines.append(block)
        total_chars += len(block)

    return "\n".join(lines)


def main():
    hook_input = read_stdin_json()
    root = project_root(hook_input)

    if not is_governance_project(root):
        return 0

    try:
        state = load_state(root)
        phase = state.get("current_phase", "")
    except Exception:
        return 0

    if not phase:
        return 0

    try:
        context = build_template_context(root, phase)
        if context is None:
            return 0

        output = {
            "hookSpecificOutput": {
                "hookEventName": "SessionStart",
                "additionalContext": context,
            }
        }
        sys.stdout.write(json.dumps(output, ensure_ascii=False))
    except Exception as e:
        # 注入失败不阻断会话
        print(f"[template_injector] WARN: 模板注入失败（{e}）。", file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())
