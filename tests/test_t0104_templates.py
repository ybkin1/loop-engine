"""
Tests for T-0104 批 1 模板/文档改动（设计-1/2/4 落地内容的静态断言）。

Covers:
- task-card.md：盲点清单 / 信息完整度声明 + 象限判定 / 相关经验与不熟悉处
  三个必填节存在且顺序正确（基本信息 → 信息完整度 → 用户可见目标 →
  相关经验 → 范围与边界 → 盲点清单 → 验收标准）
- loop-governance SKILL.md：启动检查清单第 7 步"盲点简报"
- human-review-packet.md："六、理解确认"新增 + 原"六、下一步"顺延为"七"
- main-thread CONTRACT.yaml：R10/R11 原文零改动 + fixed_stance 增"象限判定先行"
- governance-lifecycle.md：USER_ACCEPTED 前须 user_comprehension_confirmed
- USER-PROMPTS.md：信息完整度说明
"""
from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

TASK_CARD = PROJECT_ROOT / "skills" / "loop-governance" / "templates" / "task-card.md"
LOOP_SKILL = PROJECT_ROOT / "skills" / "loop-governance" / "SKILL.md"
REVIEW_PACKET = (
    PROJECT_ROOT / "skills" / "loop-governance" / "templates" / "human-review-packet.md"
)
MAIN_THREAD_CONTRACT = PROJECT_ROOT / "agents" / "main-thread" / "CONTRACT.yaml"
LIFECYCLE = (
    PROJECT_ROOT / "skills" / "loop-governance" / "references" / "governance-lifecycle.md"
)
USER_PROMPTS = PROJECT_ROOT / "USER-PROMPTS.md"


class TestTaskCardSections:
    def test_three_new_sections_present(self):
        text = TASK_CARD.read_text(encoding="utf-8")
        assert "## 盲点清单（必填，≥3 条）" in text
        assert "## 信息完整度声明 + 象限判定（必填）" in text
        assert "## 相关经验与不熟悉处（必填）" in text

    def test_section_order(self):
        text = TASK_CARD.read_text(encoding="utf-8")
        order = [
            "## 基本信息",
            "## 信息完整度声明 + 象限判定（必填）",
            "## 用户可见目标",
            "## 相关经验与不熟悉处（必填）",
            "## 范围与边界",
            "## 盲点清单（必填，≥3 条）",
            "## 验收标准",
        ]
        positions = [text.index(marker) for marker in order]
        assert positions == sorted(positions), "节顺序错误"

    def test_blind_spot_requires_three(self):
        text = TASK_CARD.read_text(encoding="utf-8")
        assert "至少 3 条" in text
        assert "缺任何一条 = 任务卡不完整，主控验收打回" in text


class TestLoopGovernanceSkill:
    def test_step7_blind_spot_brief(self):
        text = LOOP_SKILL.read_text(encoding="utf-8")
        assert "7. **盲点简报（开工前，Q3）**" in text
        assert "不猜测直接开工" in text


class TestHumanReviewPacket:
    def test_comprehension_section_added(self):
        text = REVIEW_PACKET.read_text(encoding="utf-8")
        assert "## 六、理解确认（用户答对才算验收）" in text

    def test_next_step_renumbered_to_seven(self):
        text = REVIEW_PACKET.read_text(encoding="utf-8")
        assert "## 七、下一步" in text
        assert "## 六、下一步" not in text

    def test_comprehension_rules_present(self):
        text = REVIEW_PACKET.read_text(encoding="utf-8")
        assert "user_comprehension_confirmed: true" in text
        assert "user_comprehension_confirmed: false" in text


class TestMainThreadContract:
    R10 = (
        '- "R10_ai_judgment_first：遇到需决策的事项，先自己判断并标注 [AI判断]，'
        '只在真正无法确定时才问用户。"'
    )
    R11 = (
        '- "R11_reduce_questions：同一阶段内向用户提问不超过 3 次；'
        '非关键决策自行处理并标注。"'
    )

    def test_r10_r11_original_text_untouched(self):
        text = MAIN_THREAD_CONTRACT.read_text(encoding="utf-8")
        assert self.R10 in text
        assert self.R11 in text

    def test_quadrant_first_added_to_fixed_stance(self):
        text = MAIN_THREAD_CONTRACT.read_text(encoding="utf-8")
        assert "象限判定先行" in text


class TestGovernanceLifecycle:
    def test_user_accepted_prerequisite_note(self):
        text = LIFECYCLE.read_text(encoding="utf-8")
        assert "`USER_ACCEPTED` 前须完成 Human Review Packet" in text
        assert "user_comprehension_confirmed" in text


class TestUserPrompts:
    def test_information_completeness_explained(self):
        text = USER_PROMPTS.read_text(encoding="utf-8")
        assert "AI 会先声明信息完整度再决定是否提问" in text
