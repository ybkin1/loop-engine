"""
Tests for the U5 routing upgrade (T-0088) in loop_core/intent_router.py.

Benchmark: StaffDeck backend/app/core/router.py (T-0086 staffdeck-benchmark
U5) — sticky routing (active task continuation), multi-intent task frames
(one round, ordered orchestration), and fail-safe degradation (keep the
status quo on internal errors — never raise, never guess new intents).

Covers:
  - AC-04a: sticky behaviour (active task exists -> no re-ask; explicit
    intent-switch / completion signals invalidate stickiness)
  - AC-04b: task frames (multi-intent input -> ordered frame list, main
    frame = first intent, frame shape compatible with task files)
  - AC-04c: fail-safe degradation (internal errors -> keep-status-quo
    result, no exception, no guessed intents)
  - Backward compatibility (existing analyze/route untouched; analyse_intent
    fills the inbox contract)
"""
from __future__ import annotations

import pytest

from loop_core.intent_router import (
    ActiveTaskSnapshot,
    ChangeType,
    IntentAnalysis,
    IntentBrief,
    IntentRouter,
    TaskFrame,
    analyse_intent,
    detect_intent_switch,
    route_user_input,
    split_intents,
)
from loop_core.router import LoopMode, RouteResult


@pytest.fixture
def router() -> IntentRouter:
    return IntentRouter()


@pytest.fixture
def active_task() -> ActiveTaskSnapshot:
    """An active task the routing should stick to."""
    return ActiveTaskSnapshot(
        task_id="T-0001",
        status="active",
        title="修复登录页面样式",
        domain="web",
        description="登录页样式问题",
        loop_mode=LoopMode.FULL,
    )


# ============================================================================
# AC-04a — Sticky routing
# ============================================================================

class TestStickyRouting:
    """AC-04a: with an active task, routing continues its domain instead of
    re-asking what to do; explicit switch/completion signals invalidate."""

    def test_sticky_applies_when_active_task_exists(self, router, active_task):
        result = router.route_upgrade("继续修复登录页面的样式问题", active_task=active_task)
        assert result.sticky is True
        assert result.sticky_task_id == "T-0001"
        assert result.degraded is False
        # Evidence of the decision is recorded in the output
        assert "T-0001" in result.sticky_basis
        assert "active" in result.sticky_basis.lower()

    def test_sticky_means_no_reask(self, router, active_task):
        """The sticky marker tells the caller the active task is continued,
        so no 'what do you want to do' clarification is needed."""
        result = router.route_upgrade("继续处理登录页的收尾", active_task=active_task)
        assert result.sticky is True
        assert "re-asking" in result.sticky_basis.lower() or "continuing" in result.sticky_basis.lower()

    def test_sticky_main_frame_targets_active_task(self, router, active_task):
        result = router.route_upgrade("继续修复登录页的样式", active_task=active_task)
        assert result.main_frame is not None
        assert result.main_frame.is_main is True
        assert result.main_frame.task_id == "T-0001"
        # Domain continues from the active task
        assert result.main_frame.domain == "web"

    def test_sticky_invalidated_by_new_task_keyword(self, router, active_task):
        result = router.route_upgrade("开始一个新任务：重构 CLI 工具", active_task=active_task)
        assert result.sticky is False
        assert "invalidated" in result.sticky_basis.lower()
        assert "switch" in result.sticky_basis.lower() or "marker" in result.sticky_basis.lower()
        # The main frame no longer targets the active task
        assert result.main_frame.task_id is None

    def test_sticky_invalidated_by_completion_keyword(self, router, active_task):
        result = router.route_upgrade("任务完成了，接下来要做什么", active_task=active_task)
        assert result.sticky is False
        assert result.sticky_task_id is None

    def test_sticky_invalidated_by_active_task_completion_marker(
        self, router, active_task
    ):
        """'mark T-0001 complete' closes the active task -> no stickiness."""
        result = router.route_upgrade("mark T-0001 complete", active_task=active_task)
        assert result.sticky is False
        assert "T-0001" in result.sticky_basis
        assert "complete" in result.sticky_basis.lower()

    def test_sticky_invalidated_by_other_task_reference(self, router, active_task):
        result = router.route_upgrade("T-0002 的需求也帮我处理一下", active_task=active_task)
        assert result.sticky is False
        assert "T-0002" in result.sticky_basis

    def test_no_sticky_when_task_completed(self, router, active_task):
        done = ActiveTaskSnapshot(
            task_id="T-0001", status="completed",
            title="旧任务", loop_mode=LoopMode.STANDARD,
        )
        result = router.route_upgrade("继续处理相关的事", active_task=done)
        assert result.sticky is False
        assert "not active" in result.sticky_basis.lower()

    def test_no_sticky_without_active_task(self, router):
        result = router.route_upgrade("修复登录页的样式问题")
        assert result.sticky is False
        assert result.sticky_task_id is None
        assert result.main_frame is not None
        assert result.main_frame.task_id is None

    def test_switch_detector_explicit_markers(self):
        switched, reason = detect_intent_switch("开始一个新任务")
        assert switched is True
        assert reason
        switched2, reason2 = detect_intent_switch("修复登录 bug")
        assert switched2 is False
        assert reason2 == ""


# ============================================================================
# AC-04b — Multi-intent task frames
# ============================================================================

class TestTaskFrames:
    """AC-04b: one round with several intents -> ordered frame list with a
    correct main frame; frame shape compatible with task files."""

    def test_multi_intent_produces_ordered_frames(self, router):
        result = router.route_upgrade("修复登录页的 500 错误；然后添加一个导出按钮")
        assert len(result.task_frames) == 2
        frames = result.task_frames
        assert frames[0].frame_id == 0 and frames[1].frame_id == 1
        assert frames[0].is_main is True
        assert frames[1].is_main is False
        # Ordered orchestration: main frame first, follow-up second
        assert "500" in frames[0].intent
        assert "导出" in frames[1].intent

    def test_main_frame_expresses_first_intent(self, router):
        result = router.route_upgrade("1. 修复登录 bug 2. 添加导出功能")
        assert len(result.task_frames) >= 2
        assert result.task_frames[0].is_main is True
        assert "修复" in result.task_frames[0].intent
        assert "导出" in result.task_frames[1].intent

    def test_english_connector_split(self, router):
        result = router.route_upgrade("Add a REST endpoint. Then write a CLI client for it")
        assert len(result.task_frames) == 2
        assert result.task_frames[0].is_main is True
        assert "endpoint" in result.task_frames[0].intent.lower()
        assert "cli" in result.task_frames[1].intent.lower()

    def test_single_intent_single_main_frame(self, router):
        result = router.route_upgrade("修复登录页的 500 错误")
        assert len(result.task_frames) == 1
        assert result.task_frames[0].is_main is True
        assert result.main_frame is result.task_frames[0]

    def test_frames_carry_routing_estimates(self, router):
        result = router.route_upgrade("写一个 CLI 工具；然后给它加单元测试")
        for frame in result.task_frames:
            assert isinstance(frame.domain, str) and frame.domain
            assert 0.0 <= frame.complexity_score <= 1.0
            assert isinstance(frame.recommended_mode, LoopMode)
            assert isinstance(frame.change_type, ChangeType)
            assert 0.0 <= frame.confidence <= 1.0
            assert frame.reasoning
            assert frame.suggested_phases

    def test_frame_to_task_dict_compatible(self, router, active_task):
        """Frame -> dict must fit the task_graph.yaml task-entry shape."""
        result = router.route_upgrade("继续修复登录页样式", active_task=active_task)
        frame = result.main_frame
        task_dict = frame.to_task_dict()
        for key in ("id", "title", "status", "phase", "loop_mode"):
            assert key in task_dict, f"missing task-compatible key {key!r}"
        assert task_dict["id"] == "T-0001"  # sticky main frame keeps the task
        assert task_dict["title"] == frame.intent
        assert task_dict["status"] == "planned"
        assert task_dict["loop_mode"] in ("LIGHTWEIGHT", "STANDARD", "FULL")
        assert "complexity_score" in task_dict
        assert "domains" in task_dict

    def test_followup_frames_are_new_tasks(self, router, active_task):
        """Even in a sticky round, follow-up frames are new tasks (no id)."""
        result = router.route_upgrade(
            "继续修复登录页；然后加导出按钮", active_task=active_task
        )
        assert result.sticky is True
        assert result.task_frames[0].task_id == "T-0001"
        assert result.task_frames[1].task_id is None

    def test_split_intents_caps_frames(self):
        parts = split_intents(
            "a；b；c；d；e；f；g", max_frames=5
        )
        assert len(parts) == 5

    def test_split_intents_empty_input(self):
        assert split_intents("") == []
        assert split_intents("   ") == []
        assert split_intents(None) == []

    def test_split_does_not_fragment_single_intent(self):
        # Temporal "之后" inside one intent must NOT split
        assert split_intents("修复登录之后的重定向 bug") == ["修复登录之后的重定向 bug"]
        # Plain sentence continuation must NOT split
        assert split_intents("修复登录 bug。它导致崩溃") == ["修复登录 bug。它导致崩溃"]


# ============================================================================
# AC-04c — Fail-safe degradation
# ============================================================================

class TestFailSafeDegradation:
    """AC-04c: internal routing errors -> keep-status-quo result; never
    raises; never guesses new intents."""

    def test_analyze_exception_keeps_active_task(self, router, active_task):
        def boom(*args, **kwargs):
            raise RuntimeError("analyzer exploded")

        router.analyze = boom  # type: ignore[method-assign]
        result = router.route_upgrade("完全无法解析的输入", active_task=active_task)
        assert result.degraded is True
        assert "RuntimeError" in result.degraded_reason
        # Status quo: keep the active task, keep its loop mode
        assert result.sticky is True
        assert result.sticky_task_id == "T-0001"
        assert result.route_result is not None
        assert result.route_result.mode == LoopMode.FULL
        # No new intents guessed
        assert result.task_frames == []
        assert result.intents == []
        assert result.analysis is None

    def test_analyze_exception_defaults_lightweight(self, router):
        def boom(*args, **kwargs):
            raise RuntimeError("analyzer exploded")

        router.analyze = boom  # type: ignore[method-assign]
        result = router.route_upgrade("完全无法解析的输入")
        assert result.degraded is True
        assert result.sticky is False
        assert result.route_result is not None
        assert result.route_result.mode == LoopMode.LIGHTWEIGHT
        assert result.task_frames == []
        assert result.analysis is None

    def test_non_string_input_degrades_no_raise(self, router, active_task):
        result = router.route_upgrade(None, active_task=active_task)
        assert result.degraded is True
        assert result.sticky is True
        assert result.sticky_task_id == "T-0001"
        assert result.task_frames == []

    def test_module_entry_degrades_no_raise(self, active_task):
        class ExplodingRouter(IntentRouter):
            def analyze(self, *args, **kwargs):
                raise ValueError("bad input")

        result = route_user_input(
            "garbage", active_task=active_task, router=ExplodingRouter()
        )
        assert result.degraded is True
        assert result.sticky is True
        assert result.route_result.mode == LoopMode.FULL
        assert result.task_frames == []
        assert result.main_frame is None

    def test_degraded_guesses_no_new_intents(self, router, active_task):
        def boom(*args, **kwargs):
            raise RuntimeError("exploded")

        router.analyze = boom  # type: ignore[method-assign]
        result = router.route_upgrade("随便什么内容", active_task=active_task)
        assert result.task_frames == []
        assert result.analysis is None
        assert result.main_frame is None
        # Sticky keeps the EXISTING task only — nothing new is created
        assert result.sticky_task_id == "T-0001"

    def test_degraded_result_is_routing_only(self, router, active_task):
        """The degraded result carries no relaxed constraint verdict: it is
        a status-quo routing recommendation (same task / default mode) with
        an explicit degraded flag — hook-level fail-closed adjudication is
        outside the router and untouched."""
        def boom(*args, **kwargs):
            raise RuntimeError("exploded")

        router.analyze = boom  # type: ignore[method-assign]
        result = router.route_upgrade("随便什么内容", active_task=active_task)
        assert isinstance(result.route_result, RouteResult)
        assert result.route_result.mode == LoopMode.FULL
        assert result.degraded is True
        # The status-quo reason explicitly says nothing was guessed
        assert "no new intent guessed" in result.route_result.reason


# ============================================================================
# Backward compatibility
# ============================================================================

class TestBackwardCompatibility:
    """U5 must be incremental: existing interfaces unchanged."""

    def test_existing_analyze_route_unchanged(self, router):
        analysis = router.analyze("Fix a typo in the README")
        assert isinstance(analysis, IntentAnalysis)
        assert analysis.recommended_mode == LoopMode.LIGHTWEIGHT
        result = router.route(analysis)
        assert isinstance(result, RouteResult)

    def test_upgraded_result_keeps_primary_analysis(self, router, active_task):
        result = router.route_upgrade("继续修复登录页", active_task=active_task)
        assert isinstance(result.analysis, IntentAnalysis)
        assert isinstance(result.route_result, RouteResult)
        # Primary analysis still describes the first intent
        assert "登录" in result.analysis.description

    def test_analyse_intent_fills_inbox_contract(self):
        """inbox.py imports analyse_intent and consumes .domains/.risk_level."""
        brief = analyse_intent("修复登录页的样式问题")
        assert isinstance(brief, IntentBrief)
        assert isinstance(brief.domains, list)
        assert brief.risk_level in ("LOW", "MEDIUM", "HIGH", "CRITICAL")
        assert isinstance(brief.recommended_mode, LoopMode)

    def test_analyse_intent_never_raises(self):
        brief = analyse_intent(None)  # type: ignore[arg-type]
        assert brief.domains == []
        assert brief.risk_level == "MEDIUM"

    def test_active_task_snapshot_from_task_dict(self):
        task = {
            "id": "T-0042",
            "title": "某任务",
            "status": "in_progress",
            "phase": "S4-implementation",
            "loop_mode": "FULL",
        }
        snap = ActiveTaskSnapshot.from_task(task)
        assert snap.task_id == "T-0042"
        assert snap.is_active is True
        assert snap.loop_mode == LoopMode.FULL

    def test_active_task_snapshot_from_task_unknown_mode(self):
        # T-0134 P4 AC-01: 未知 mode fail-closed 回退 FULL（绝不 LIGHTWEIGHT，
        # 否则会静默关闭 enforcement）
        snap = ActiveTaskSnapshot.from_task({"id": "T-9", "loop_mode": "weird"})
        assert snap.loop_mode == LoopMode.FULL

    def test_task_frame_default_shape(self):
        frame = TaskFrame(
            frame_id=0, intent="做某事", task_id=None, domain="unknown",
            complexity_score=0.1, recommended_mode=LoopMode.LIGHTWEIGHT,
            change_type=ChangeType.NEW_PROJECT, confidence=0.9,
            reasoning="r", is_main=True,
        )
        assert frame.is_main is True
        d = frame.to_task_dict()
        assert d["status"] == "planned"
        assert d["loop_mode"] == "LIGHTWEIGHT"
