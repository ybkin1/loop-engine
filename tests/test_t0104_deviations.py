"""
Tests for T-0104 设计-3 deviations 数组格式校验（提示词层规则的可执行化）。

Covers:
- developer SKILL.md §5.1 产出 JSON Schema 含新增可选数组 `deviations`，
  且既有 known_deviations / unimplemented / clarification_requests 原样保留
- 字段规则（D-03 §3.3.1）：缺 reason → 无效；ai_decisions 缺 why_not_ask
  / impact_if_wrong → 无效；合法样例 → 无错误
- main-thread SKILL.md 含偏离摘要呈现模板（§5.2）与条数匹配自检规则（§5.3）
"""
from __future__ import annotations

import json
import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEVELOPER_SKILL = PROJECT_ROOT / "agents" / "developer" / "SKILL.md"
MAIN_THREAD_SKILL = PROJECT_ROOT / "agents" / "main-thread" / "SKILL.md"


def _extract_json_schema(text: str) -> dict:
    """Extract the first ```json block from the SKILL.md text."""
    match = re.search(r"```json\n(.*?)\n```", text, re.DOTALL)
    assert match, "no ```json block found"
    return json.loads(match.group(1))


def _validate_deviations(deviations: list) -> list[str]:
    """Replicate D-03 §3.3.1 field rules. Returns a list of error strings.

    - reason 必填（new_situation / plan_change 可为空数组）
    - ai_decisions_made_for_user 每条必须同时填 decision / why_not_ask /
      impact_if_wrong
    """
    errors: list[str] = []
    for i, dev in enumerate(deviations):
        if not isinstance(dev, dict):
            errors.append(f"deviations[{i}]: not an object")
            continue
        for required in ("deviation_id", "phase", "reason"):
            if not str(dev.get(required) or "").strip():
                errors.append(
                    f"deviations[{i}]: missing required field '{required}'"
                )
        for j, ad in enumerate(dev.get("ai_decisions_made_for_user", [])):
            if not isinstance(ad, dict):
                errors.append(
                    f"deviations[{i}].ai_decisions_made_for_user[{j}]: not an object"
                )
                continue
            for required in ("decision", "why_not_ask", "impact_if_wrong"):
                if not str(ad.get(required) or "").strip():
                    errors.append(
                        f"deviations[{i}].ai_decisions_made_for_user[{j}]: "
                        f"missing '{required}'"
                    )
    return errors


def _valid_deviation() -> dict:
    return {
        "deviation_id": "DEV-S4-001",
        "phase": "S4-implementation",
        "task_id": "T-0104",
        "new_situation": ["契约未声明的依赖缺失"],
        "plan_change": "改为先实现无依赖部分",
        "reason": "依赖缺失迫使调整实现顺序",
        "ai_decisions_made_for_user": [
            {
                "decision": "[AI判断] 选择了 X 而不是 Y",
                "why_not_ask": "低风险且可在既有批准范围内兜底",
                "impact_if_wrong": "错误则影响性能而非正确性，可在 S5 质量门发现",
                "needs_user_review": True,
            }
        ],
    }


class TestDeveloperSchema:
    def test_schema_contains_deviations_array(self):
        schema = _extract_json_schema(DEVELOPER_SKILL.read_text(encoding="utf-8"))
        assert "deviations" in schema
        assert isinstance(schema["deviations"], list)

    def test_legacy_fields_preserved(self):
        """known_deviations/unimplemented/clarification_requests 原样保留。"""
        schema = _extract_json_schema(DEVELOPER_SKILL.read_text(encoding="utf-8"))
        for field in ("known_deviations", "unimplemented", "clarification_requests"):
            assert field in schema, f"{field} 必须保留"
            assert isinstance(schema[field], list)

    def test_deviation_entry_fields(self):
        schema = _extract_json_schema(DEVELOPER_SKILL.read_text(encoding="utf-8"))
        dev = schema["deviations"][0]
        for field in ("deviation_id", "new_situation", "plan_change", "reason",
                      "ai_decisions_made_for_user"):
            assert field in dev
        ad = dev["ai_decisions_made_for_user"][0]
        for field in ("decision", "why_not_ask", "impact_if_wrong",
                      "needs_user_review"):
            assert field in ad


class TestDeviationFormatValidation:
    def test_valid_deviation_passes(self):
        assert _validate_deviations([_valid_deviation()]) == []

    def test_empty_array_valid(self):
        """deviations 为可选数组，缺省 [] 合法。"""
        assert _validate_deviations([]) == []

    def test_missing_reason_invalid(self):
        dev = _valid_deviation()
        del dev["reason"]
        errors = _validate_deviations([dev])
        assert any("'reason'" in e for e in errors)

    def test_empty_reason_invalid(self):
        dev = _valid_deviation()
        dev["reason"] = ""
        errors = _validate_deviations([dev])
        assert any("'reason'" in e for e in errors)

    def test_ai_decision_missing_why_not_ask_invalid(self):
        dev = _valid_deviation()
        del dev["ai_decisions_made_for_user"][0]["why_not_ask"]
        errors = _validate_deviations([dev])
        assert any("'why_not_ask'" in e for e in errors)

    def test_ai_decision_missing_impact_if_wrong_invalid(self):
        dev = _valid_deviation()
        del dev["ai_decisions_made_for_user"][0]["impact_if_wrong"]
        errors = _validate_deviations([dev])
        assert any("'impact_if_wrong'" in e for e in errors)

    def test_empty_new_situation_and_plan_change_allowed(self):
        """new_situation / plan_change 可为空数组，不判无效。"""
        dev = _valid_deviation()
        dev["new_situation"] = []
        dev["plan_change"] = []
        assert _validate_deviations([dev]) == []


class TestMainThreadGatePresentationRules:
    def test_s52_deviation_summary_template_present(self):
        text = MAIN_THREAD_SKILL.read_text(encoding="utf-8")
        assert "### 本阶段偏离摘要" in text
        assert "替您做的决定" in text
        assert "needs_user_review" in text

    def test_s53_count_matching_self_check_present(self):
        text = MAIN_THREAD_SKILL.read_text(encoding="utf-8")
        assert "needs_user_review: true" in text
        assert "不匹配 = 打回" in text
