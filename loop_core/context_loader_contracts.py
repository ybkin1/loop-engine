"""context_loader_contracts.py — CONTRACT 解析辅助外部模块（T-0124 拆分）。

从 loop_core/context_loader.py 拆出：`_parse_yaml` / `_extract_fixed_stance` /
`_extract_contract_extras`（CONTRACT 文档解析与提取）。行为逐字节等价，
壳文件 import 后同命名空间可见（内部调用不变）。
"""
from __future__ import annotations

import json
import logging
from typing import Any


def _parse_yaml(raw: str) -> Any:
    """Parse YAML or JSON text, returning the deserialised object.

    Tries YAML first (more common for hand-authored files), falls back to
    JSON.  Returns the raw string if neither parser is available or both fail.
    """
    # Try YAML first
    try:
        import yaml
        return yaml.safe_load(raw)
    except ImportError:
        logging.getLogger("context_loader").debug(
            "YAML not available, falling back to JSON")
    except Exception as _e:
        logging.getLogger("context_loader").debug("Parse error: %s", _e)

    # Fall back to JSON
    try:
        return json.loads(raw)
    except Exception as _e:
        logging.getLogger("context_loader").debug("Parse error: %s", _e)

    # Last resort: return raw — the caller will handle it
    return raw


def _extract_fixed_stance(contract: dict, role_id: str) -> str:
    """Extract and format the fixed_stance section from a CONTRACT dict.

    Returns a compact, token-efficient string suitable for a system prompt.
    """
    stance = contract.get("fixed_stance")
    if not stance or not isinstance(stance, list):
        # Graceful fallback: return a placeholder
        identity = contract.get("identity", {})
        title = identity.get("title", role_id) if isinstance(identity, dict) else role_id
        return f"Role: {title}\nNo fixed_stance defined."

    lines = ["## Fixed Stance"]
    for item in stance:
        lines.append(f"- {item}")
    return "\n".join(lines)


def _extract_contract_extras(contract: dict) -> str | None:
    """Extract key non-stance sections from CONTRACT for FULL load level.

    Includes: responsibilities, prohibitions, veto_power (summarised).
    """
    parts: list[str] = []

    responsibilities = contract.get("responsibilities")
    if responsibilities and isinstance(responsibilities, list):
        lines = ["## Responsibilities"]
        for item in responsibilities:
            lines.append(f"- {item}")
        parts.append("\n".join(lines))

    prohibitions = contract.get("prohibitions")
    if prohibitions and isinstance(prohibitions, list):
        lines = ["## Prohibitions"]
        for item in prohibitions:
            lines.append(f"- {item}")
        parts.append("\n".join(lines))

    veto = contract.get("veto_power")
    if veto and isinstance(veto, list):
        lines = ["## Veto Power"]
        for item in veto:
            lines.append(f"- {item}")
        parts.append("\n".join(lines))

    return "\n\n".join(parts) if parts else None
