"""loop_contract_parser.py — 任务卡契约解析（T-0110 批 C 从 loop_enforcement 外提）。

T-0107 D5-2：``hooks/scripts/loop_enforcement.py`` 与
``loop_core/context_controller.py`` 原先各自维护一套任务卡 front-matter
前缀推断解析器；T-0107 落地共享契约解析模块 ``loop_core/front_matter.py``
为唯一实现，本文件承载 loop_enforcement 侧的接线：

- ``_SHARED_FRONT_MATTER_PARSER``：共享解析器（loop_core 可用时）；
- ``_parse_task_front_matter_legacy``：本地同逻辑副本（与 front_matter.py
  逐行一致，仅作插件缓存等退化环境的韧性兜底）；
- ``_front_matter_parser()``：选择器——共享可用用共享，否则告警回退本地副本；
- ``load_task_contract()``：读取任务卡 markdown 并解析契约；
- ``_task_mcp_allowed_tools()``：任务卡的 MCP 工具白名单；
- ``_read_task_max_files()``：任务卡的 max_files 字段（C11 文件写入上限）。

本文件代码逐字迁移自 loop_enforcement.py（行为等价拆分，语义零变化），
零依赖 hook_common（仅 Path + 可选的 loop_core.front_matter）。
"""
from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)


# T-0107 D5-2: 共享契约解析模块（与 loop_core/context_controller 同源）。
# 主路径统一调用 loop_core.front_matter.parse_task_front_matter，消除
# 双解析器行为分歧；插件缓存等退化环境（loop_core 缺失/陈旧副本无该
# 模块）下回退到本文件内的同逻辑副本 _parse_task_front_matter_legacy
# （代码与 front_matter.py 保持一致，仅作韧性兜底）。
try:
    from loop_core.front_matter import (
        parse_task_front_matter as _SHARED_FRONT_MATTER_PARSER,  # noqa: E402, N812
    )
except Exception:
    _SHARED_FRONT_MATTER_PARSER = None  # type: ignore[assignment]


def _front_matter_parser():
    """返回共享 front-matter 契约解析函数；不可用时回退到本地同逻辑副本。"""
    if _SHARED_FRONT_MATTER_PARSER is not None:
        return _SHARED_FRONT_MATTER_PARSER
    logger.warning(
        "loop_core.front_matter 不可用（退化环境）；使用本地同逻辑副本解析任务卡契约"
    )
    return _parse_task_front_matter_legacy


def _parse_task_front_matter_legacy(text: str) -> dict:
    """D5-2 韧性兜底：与 loop_core/front_matter.py 保持一致的契约解析。

    仅在共享模块不可导入（陈旧插件缓存等）时使用；语义与共享模块
    逐行一致（allowed_paths / developer_agent_id / reviewer_agent_id /
    mcp_allowed_tools，含 markdown 表格形态）。
    """
    contract = {
        "allowed_paths": [],
        "developer_agent_id": None,
        "reviewer_agent_id": None,
        "mcp_allowed_tools": [],
    }
    in_allowed_section = False
    in_mcp_section = False
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("allowed_paths:") or line.startswith("allowed_actions:"):
            in_allowed_section = True
            in_mcp_section = False
            continue
        if line.startswith("mcp_allowed_tools:") or line.startswith("| mcp_allowed_tools"):
            in_allowed_section = False
            rest = line.split(":", 1)[1].strip() if ":" in line else ""
            if line.startswith("| mcp_allowed_tools") and not rest:
                parts = line.split("|")
                rest = parts[2].strip() if len(parts) > 2 else ""
            if rest:
                in_mcp_section = False
                inner = rest[1:-1] if rest.startswith("[") and rest.endswith("]") else rest
                for item in inner.split(","):
                    item = item.strip().strip("'\"").strip()
                    if item:
                        contract["mcp_allowed_tools"].append(item)
                continue
            in_mcp_section = True
            continue
        if in_allowed_section and line.startswith("- "):
            path = line[2:].strip().strip('"')
            contract["allowed_paths"].append(path)
        elif in_mcp_section and line.startswith("- "):
            tool = line[2:].strip().strip('"')
            contract["mcp_allowed_tools"].append(tool)
        elif (in_allowed_section or in_mcp_section) and not line.startswith("- "):
            in_allowed_section = False
            in_mcp_section = False
        if line.startswith("developer_agent_id:"):
            contract["developer_agent_id"] = line.split(":", 1)[1].strip().strip('"')
        elif line.startswith("reviewer_agent_id:"):
            contract["reviewer_agent_id"] = line.split(":", 1)[1].strip().strip('"')
    return contract


def load_task_contract(root: Path, task_id: str) -> dict | None:
    """Load the task contract to check allowed paths and MCP tool allow-list.

    T-0107 D5-2: 统一调用共享契约解析模块 loop_core.front_matter（与
    context_controller._load_task_contract 同源），支持 mcp_allowed_tools
    的 markdown 表格 / 内联 / 列表形态；退化环境回退本地同逻辑副本。
    """
    task_path = root / ".ai" / "tasks" / f"{task_id}.md"
    if not task_path.exists():
        return None

    text = task_path.read_text(encoding="utf-8")
    return _front_matter_parser()(text)


def _task_mcp_allowed_tools(root: Path, task_id: str) -> list[str]:
    """B3 (T-0083): return the task contract's MCP tool allow-list.

    Parsed from the optional `mcp_allowed_tools` field in the task file.
    An empty list (field absent) means no MCP tools are allowed — the
    fail-closed default stays in force.
    """
    contract = load_task_contract(root, task_id)
    if contract is None:
        return []
    return contract.get("mcp_allowed_tools", [])


def _read_task_max_files(root: Path, task_id: str) -> int | None:
    """Parse max_files from the task contract markdown.

    Looks for 'max_files:' field in the task's .md file.
    Returns None if not specified (no limit).
    """
    task_path = root / ".ai" / "tasks" / f"{task_id}.md"
    if not task_path.is_file():
        return None

    try:
        text = task_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None

    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("max_files:"):
            value = stripped.split(":", 1)[1].strip().strip('"').strip("'")
            try:
                return int(value)
            except ValueError:
                return None

    return None
