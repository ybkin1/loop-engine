from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class PacketError(ValueError):
    """Raised when a functional design packet is incomplete."""


REQUIRED_SECTIONS = (
    "feature_id",
    "feature_name",
    "user_goal",
    "actors",
    "preconditions",
    "user_guide",
    "frontend",
    "backend",
    "security",
    "performance",
    "maintainability",
    "testing",
    "decisions",
    "risks",
    "user_decisions",
)

REQUIRED_NESTED_FIELDS = {
    "user_guide": ("entry", "steps", "success", "failure", "navigation"),
    "frontend": ("pages", "elements", "states", "validation", "accessibility"),
    "backend": ("modules", "apis", "data_model", "state_transitions", "errors", "idempotency", "observability"),
    "security": ("boundaries", "authn_authz", "input_protection", "abuse_prevention", "data_protection", "audit"),
    "performance": ("budgets", "bottlenecks", "scaling", "degradation"),
    "maintainability": ("module_boundaries", "dependencies", "extension", "runbook"),
    "testing": ("unit", "component", "contract", "integration", "e2e", "security", "performance", "recovery"),
}


@dataclass(frozen=True)
class FunctionalDesignPacket:
    data: dict[str, Any]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "FunctionalDesignPacket":
        missing = [key for key in REQUIRED_SECTIONS if not data.get(key)]
        if missing:
            raise PacketError(f"missing functional design sections: {', '.join(missing)}")
        packet = cls(data)
        nested_missing = packet.validate()
        if nested_missing:
            raise PacketError(f"missing functional design fields: {', '.join(nested_missing)}")
        return packet

    def validate(self) -> list[str]:
        errors: list[str] = []
        for section in REQUIRED_SECTIONS:
            value = self.data.get(section)
            if value is None or value == "" or value == [] or value == {}:
                errors.append(section)
        for section, fields in REQUIRED_NESTED_FIELDS.items():
            value = self.data.get(section)
            if not isinstance(value, dict):
                errors.append(section)
                continue
            for field in fields:
                child = value.get(field)
                if child is None or child == "" or child == [] or child == {}:
                    errors.append(f"{section}.{field}")
        return errors

    def to_dict(self) -> dict[str, Any]:
        return self.data

    def write_json(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    def render_markdown(self) -> str:
        data = self.data
        lines = [
            f"# 功能设计包：{data['feature_name']}",
            "",
            f"- Feature ID: `{data['feature_id']}`",
            f"- 用户目标：{data['user_goal']}",
            f"- 参与角色：{_inline(data['actors'])}",
            f"- 前置条件：{_inline(data['preconditions'])}",
            "",
            "## 用户怎么使用",
            _section(data["user_guide"]),
            "",
            "## 前端设计",
            _section(data["frontend"]),
            "",
            "## 后端设计",
            _section(data["backend"]),
            "",
            "## 安全设计",
            _section(data["security"]),
            "",
            "## 性能设计",
            _section(data["performance"]),
            "",
            "## 可维护性与演进",
            _section(data["maintainability"]),
            "",
            "## 测试设计",
            _section(data["testing"]),
            "",
            "## 关键取舍",
            _section(data["decisions"]),
            "",
            "## 风险与未验证项",
            _section(data["risks"]),
            "",
            "## 用户需要决定",
            _section(data["user_decisions"]),
            "",
        ]
        return "\n".join(lines)


def _inline(value: Any) -> str:
    if isinstance(value, list):
        return ", ".join(str(item) for item in value)
    return str(value)


def _section(value: Any, indent: int = 0) -> str:
    prefix = "  " * indent
    if isinstance(value, dict):
        return "\n".join(f"{prefix}- **{key}**：{_section(item, indent + 1).lstrip()}" for key, item in value.items())
    if isinstance(value, list):
        return "\n".join(f"{prefix}- {item}" for item in value)
    return f"{prefix}{value}"
