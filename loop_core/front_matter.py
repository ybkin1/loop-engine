"""front_matter.py — Task card front-matter contract parsing (single source of truth).

T-0107 D5-2: ``hooks/scripts/loop_enforcement.py`` 与
``loop_core/context_controller.py`` 原先各自维护一套任务卡 front-matter
前缀推断解析器，行为分歧（enforcement 版支持 ``mcp_allowed_tools`` 的
markdown 表格格式，context_controller 版不支持）——同一契约两种解释，
路径放行决策取决于运行的是哪个解析器。本模块是唯一契约解析实现，
两处统一调用；格式演进只改这一处。

支持格式（契约化，解析器只认下列字段，不做启发式猜测）：
- ``allowed_paths:`` / ``allowed_actions:`` 节 + ``- path`` 列表项
- 内联流式 ``[a, b]`` / ``mcp__a``
- ``mcp_allowed_tools:`` 三种形态：
  - 内联 ``mcp_allowed_tools: [mcp__a, mcp__b]``
  - 列表 ``mcp_allowed_tools:`` 换行 ``- mcp__a``
  - markdown 表格行 ``| mcp_allowed_tools | mcp__a |``（基本信息表）
- ``developer_agent_id:`` / ``reviewer_agent_id:`` 标量键

语义（继承 enforcement 版既定行为，保持不变）：
- 未声明字段 → 契约默认值（``allowed_paths``/``mcp_allowed_tools`` 为空
  列表 = fail-closed 默认：无范围可验证 / 不允许任何 MCP 工具）。
"""
from __future__ import annotations

from typing import Any

# 契约默认值（fail-closed 语义）：空列表 = 无 allowed_paths 不可验证范围；
# 无 mcp_allowed_tools = 不允许任何 MCP 工具。注意：解析函数每次调用
# 必须新建列表（不可复用本默认值的可变对象，否则跨调用累积）。


def parse_task_front_matter(text: str) -> dict[str, Any]:
    """解析任务卡 front-matter 契约字段（见模块 docstring）。

    Args:
        text: 任务卡 markdown 全文。

    Returns:
        dict，键: ``allowed_paths`` / ``developer_agent_id`` /
        ``reviewer_agent_id`` / ``mcp_allowed_tools``。未知字段忽略。
    """
    contract: dict[str, Any] = {
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
        # mcp_allowed_tools — 三种形态（内联 / 列表 / markdown 表格行）
        if line.startswith("mcp_allowed_tools:") or line.startswith("| mcp_allowed_tools"):
            in_allowed_section = False
            rest = line.split(":", 1)[1].strip() if ":" in line else ""
            if line.startswith("| mcp_allowed_tools") and not rest:
                parts = line.split("|")
                rest = parts[2].strip() if len(parts) > 2 else ""
            if rest:
                # 内联形态：mcp_allowed_tools: [mcp__a, mcp__b] 或单个工具名
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
