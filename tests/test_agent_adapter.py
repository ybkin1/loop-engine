"""Tests for loop_core.agent_adapter — Agent 抽象接口 + 三个替代方案 + 工作流。"""
from __future__ import annotations

import re

import pytest
from loop_core.agent_adapter import (
    AgentAdapter,
    AgentInput,
    AgentOutput,
    AgentStatus,
    AgentUnavailableError,
    AgentCapabilityProbe,
    DelegationRequest,
    ZCodeAgentAdapter,
    probe_agent_capability,
)




class TestDelegationContract:
    def test_role_child_is_read_only_by_default(self):
        request = DelegationRequest(
            parent_execution_id="exec-1", parent_role_id="main-thread",
            task_id="T-1", phase="S2-architecture", gate_id="G-1",
            child_role_id="system-architect", allowed_paths=("docs/",),
        )
        assert request.validate() == (True, "AUTHORIZED")
        assert request.read_only is True
        assert request.delegation_allowed is False

    def test_nested_delegation_requires_explicit_permission(self):
        request = DelegationRequest(
            parent_execution_id="exec-1", parent_role_id="developer",
            task_id="T-1", phase="S4-implementation", gate_id="G-1",
            child_role_id="helper", allowed_paths=("src/",), depth=2,
        )
        assert request.validate() == (False, "DELEGATION_NOT_ALLOWED")

    def test_developer_cannot_spawn_reviewer(self):
        request = DelegationRequest(
            parent_execution_id="exec-1", parent_role_id="developer",
            task_id="T-1", phase="S4-implementation", gate_id="G-1",
            child_role_id="independent-reviewer", allowed_paths=("src/",),
        )
        assert request.validate() == (False, "REVIEWER_MUST_NOT_BE_DEVELOPER_CHILD")


class TestAgentCapabilityProbe:
    def test_probe_is_conservative_without_host_visibility(self):
        result = probe_agent_capability(agent_tool_visible=False)
        assert isinstance(result, AgentCapabilityProbe)
        assert result.status == "CAPABILITY_UNAVAILABLE"
        assert result.recursive_launch is None

    def test_visible_tool_still_requires_live_fire(self):
        result = probe_agent_capability(agent_tool_visible=True)
        assert result.status == "NOT_VERIFIED"
        assert result.governed_recursive_launch is None

class TestAgentInput:
    def test_fingerprint_deterministic(self):
        a = AgentInput(role_id="dev", task_id="T-1", prompt="hello")
        b = AgentInput(role_id="dev", task_id="T-1", prompt="hello")
        assert a.fingerprint() == b.fingerprint()

    def test_fingerprint_differs_on_prompt_change(self):
        a = AgentInput(role_id="dev", task_id="T-1", prompt="hello")
        b = AgentInput(role_id="dev", task_id="T-1", prompt="world")
        assert a.fingerprint() != b.fingerprint()

    def test_fingerprint_differs_on_role_change(self):
        a = AgentInput(role_id="dev", task_id="T-1", prompt="hello")
        b = AgentInput(role_id="qa", task_id="T-1", prompt="hello")
        assert a.fingerprint() != b.fingerprint()

    def test_fingerprint_includes_input_files(self):
        a = AgentInput(role_id="dev", task_id="T-1", prompt="x", input_files=["a.txt"])
        b = AgentInput(role_id="dev", task_id="T-1", prompt="x", input_files=["b.txt"])
        assert a.fingerprint() != b.fingerprint()

    def test_fingerprint_hex_format(self):
        fp = AgentInput(role_id="dev", task_id="T-1", prompt="x").fingerprint()
        assert len(fp) == 64
        assert all(c in "0123456789abcdef" for c in fp)

    def test_defaults(self):
        ai = AgentInput(role_id="dev", task_id="T-1", prompt="x")
        assert ai.input_files == []
        assert ai.session_id is None
        assert ai.actor_id is None
        assert ai.allowed_tools is None
        assert ai.forbidden_tools is None
        assert ai.start_time is None


# ═══════════════════════════════════════════════════════════════════════
# AgentOutput
# ═══════════════════════════════════════════════════════════════════════

class TestAgentOutput:
    def test_input_integrity_ok_matching(self):
        out = AgentOutput(
            actor_id="a", session_id="s", role_id="r", task_id="t",
            status=AgentStatus.COMPLETED,
            input_fingerprint="abc123", reported_input_hash="abc123",
        )
        assert out.input_integrity_ok() is True

    def test_input_integrity_ok_mismatch(self):
        out = AgentOutput(
            actor_id="a", session_id="s", role_id="r", task_id="t",
            status=AgentStatus.COMPLETED,
            input_fingerprint="abc123", reported_input_hash="xyz789",
        )
        assert out.input_integrity_ok() is False

    def test_input_integrity_ok_empty_sent(self):
        out = AgentOutput(
            actor_id="a", session_id="s", role_id="r", task_id="t",
            status=AgentStatus.COMPLETED,
            input_fingerprint="", reported_input_hash="abc",
        )
        assert out.input_integrity_ok() is False

    def test_input_integrity_ok_empty_reported(self):
        out = AgentOutput(
            actor_id="a", session_id="s", role_id="r", task_id="t",
            status=AgentStatus.COMPLETED,
            input_fingerprint="abc", reported_input_hash="",
        )
        assert out.input_integrity_ok() is False

    def test_is_clean_all_green(self):
        out = AgentOutput(
            actor_id="a", session_id="s", role_id="r", task_id="t",
            status=AgentStatus.COMPLETED,
            input_fingerprint="abc", reported_input_hash="abc",
            contract_violated=False,
        )
        assert out.is_clean is True

    def test_is_clean_failed_status(self):
        out = AgentOutput(
            actor_id="a", session_id="s", role_id="r", task_id="t",
            status=AgentStatus.FAILED,
            input_fingerprint="abc", reported_input_hash="abc",
            contract_violated=False,
        )
        assert out.is_clean is False

    def test_is_clean_bad_integrity(self):
        out = AgentOutput(
            actor_id="a", session_id="s", role_id="r", task_id="t",
            status=AgentStatus.COMPLETED,
            input_fingerprint="abc", reported_input_hash="xyz",
            contract_violated=False,
        )
        assert out.is_clean is False

    def test_is_clean_violated(self):
        out = AgentOutput(
            actor_id="a", session_id="s", role_id="r", task_id="t",
            status=AgentStatus.COMPLETED,
            input_fingerprint="abc", reported_input_hash="abc",
            contract_violated=True,
        )
        assert out.is_clean is False


# ═══════════════════════════════════════════════════════════════════════
# AgentUnavailableError
# ═══════════════════════════════════════════════════════════════════════

class TestAgentUnavailableError:
    def test_is_runtime_error(self):
        err = AgentUnavailableError("dev", "zcode")
        assert isinstance(err, RuntimeError)

    def test_message_contains_real_agent_unavailable(self):
        err = AgentUnavailableError("dev", "zcode")
        assert "REAL_AGENT_UNAVAILABLE" in str(err)

    def test_message_contains_role_and_host(self):
        err = AgentUnavailableError("developer", "zcode", "test reason")
        assert "developer" in str(err)
        assert "zcode" in str(err)
        assert "test reason" in str(err)

    def test_attributes_preserved(self):
        err = AgentUnavailableError("qa", "test-host")
        assert err.role_id == "qa"
        assert err.host == "test-host"


# ═══════════════════════════════════════════════════════════════════════
# 替代方案 #1：本地 session_id / actor_id + fingerprint
# ═══════════════════════════════════════════════════════════════════════

class TestAlternative1LocalIds:
    def test_generate_session_id_format(self):
        sid = ZCodeAgentAdapter.generate_session_id("T-1", "dev")
        assert sid.startswith("zcode-sess-")
        assert len(sid) == len("zcode-sess-") + 16

    def test_generate_session_id_unique(self):
        sids = {ZCodeAgentAdapter.generate_session_id("T-1", "dev") for _ in range(10)}
        assert len(sids) == 10

    def test_generate_actor_id_format(self):
        aid = ZCodeAgentAdapter.generate_actor_id("developer")
        assert aid.startswith("zcode-actor-")
        assert len(aid) == len("zcode-actor-") + 12

    def test_generate_actor_id_deterministic(self):
        a = ZCodeAgentAdapter.generate_actor_id("dev")
        b = ZCodeAgentAdapter.generate_actor_id("dev")
        assert a == b

    def test_generate_actor_id_differs_by_role(self):
        a = ZCodeAgentAdapter.generate_actor_id("dev")
        b = ZCodeAgentAdapter.generate_actor_id("qa")
        assert a != b

    def test_developer_neq_reviewer(self):
        dev_id = ZCodeAgentAdapter.generate_actor_id("developer")
        rev_id = ZCodeAgentAdapter.generate_actor_id("independent-reviewer")
        assert dev_id != rev_id


# ═══════════════════════════════════════════════════════════════════════
# 替代方案 #2：工具白名单 — System Prompt + 事后扫描
# ═══════════════════════════════════════════════════════════════════════

class TestAlternative2ToolConstraints:
    def test_build_prompt_allowed_only(self):
        result = ZCodeAgentAdapter.build_tool_constraint_prompt(["read", "write"], None)
        assert "TOOL_CONSTRAINT" in result
        assert "read" in result
        assert "write" in result

    def test_build_prompt_forbidden_only(self):
        result = ZCodeAgentAdapter.build_tool_constraint_prompt(None, ["deploy", "rollback"])
        assert "TOOL_CONSTRAINT" in result
        assert "deploy" in result

    def test_build_prompt_both(self):
        result = ZCodeAgentAdapter.build_tool_constraint_prompt(["read"], ["deploy"])
        assert "只能使用以下工具" in result
        assert "禁止使用以下工具" in result
        assert "CONTRACT_VIOLATION" in result

    def test_build_prompt_none(self):
        result = ZCodeAgentAdapter.build_tool_constraint_prompt(None, None)
        assert result == ""

    def test_scan_violations_detect_deploy(self):
        violations = ZCodeAgentAdapter.scan_tool_violations(
            "I will execute deploy now", ["deploy", "rollback"]
        )
        assert "deploy" in violations

    def test_scan_violations_case_insensitive(self):
        violations = ZCodeAgentAdapter.scan_tool_violations(
            "Execute DEPLOY Now", ["deploy"]
        )
        assert "deploy" in violations

    def test_scan_violations_no_match(self):
        violations = ZCodeAgentAdapter.scan_tool_violations(
            "I will read the file", ["deploy", "rollback"]
        )
        assert violations == []

    def test_scan_violations_none_forbidden(self):
        violations = ZCodeAgentAdapter.scan_tool_violations("execute deploy", None)
        assert violations == []


# ═══════════════════════════════════════════════════════════════════════
# 替代方案 #3：输入冻结 — hash 比对
# ═══════════════════════════════════════════════════════════════════════

class TestAlternative3InputIntegrity:
    def test_verify_match(self):
        assert ZCodeAgentAdapter.verify_input_integrity("abc", "abc") is True

    def test_verify_mismatch(self):
        assert ZCodeAgentAdapter.verify_input_integrity("abc", "xyz") is False

    def test_verify_empty_sent(self):
        assert ZCodeAgentAdapter.verify_input_integrity("", "abc") is False

    def test_verify_empty_reported(self):
        assert ZCodeAgentAdapter.verify_input_integrity("abc", "") is False

    def test_verify_both_empty(self):
        assert ZCodeAgentAdapter.verify_input_integrity("", "") is False

    def test_full_sha256_fingerprint(self):
        fp = AgentInput(role_id="x", task_id="y", prompt="z").fingerprint()
        assert ZCodeAgentAdapter.verify_input_integrity(fp, fp) is True
        assert ZCodeAgentAdapter.verify_input_integrity(fp, "0" * 64) is False


# ═══════════════════════════════════════════════════════════════════════
# prepare_launch() — 替代方案 #1 + #2 + #3 注入
# ═══════════════════════════════════════════════════════════════════════

class TestPrepareLaunch:
    def test_generates_session_id(self):
        adapter = ZCodeAgentAdapter()
        ai = AgentInput(role_id="developer", task_id="T-1", prompt="test")
        result = adapter.prepare_launch(ai)
        assert result.session_id is not None
        assert result.session_id.startswith("zcode-sess-")

    def test_generates_actor_id(self):
        adapter = ZCodeAgentAdapter()
        ai = AgentInput(role_id="developer", task_id="T-1", prompt="test")
        result = adapter.prepare_launch(ai)
        assert result.actor_id is not None
        assert result.actor_id.startswith("zcode-actor-")

    def test_records_start_time(self):
        adapter = ZCodeAgentAdapter()
        ai = AgentInput(role_id="dev", task_id="T-1", prompt="test")
        result = adapter.prepare_launch(ai)
        assert result.start_time is not None
        assert "T" in result.start_time  # ISO 8601

    def test_injects_tool_constraints_into_prompt(self):
        adapter = ZCodeAgentAdapter()
        ai = AgentInput(
            role_id="reviewer", task_id="T-1",
            prompt="Review the code.",
            allowed_tools=["Read"],
            forbidden_tools=["Write", "Edit"],
        )
        result = adapter.prepare_launch(ai)
        assert "TOOL_CONSTRAINT" in result.prompt
        assert "Read" in result.prompt
        assert "Write" in result.prompt

    def test_injects_hash_report_instruction(self):
        adapter = ZCodeAgentAdapter()
        ai = AgentInput(role_id="dev", task_id="T-1", prompt="Implement X.")
        result = adapter.prepare_launch(ai)
        assert "INPUT_HASH:" in result.prompt
        assert "[PROTOCOL]" in result.prompt

    def test_no_constraint_when_no_tools_specified(self):
        adapter = ZCodeAgentAdapter()
        ai = AgentInput(role_id="dev", task_id="T-1", prompt="test")
        result = adapter.prepare_launch(ai)
        # 仍应有 hash 指令，但不含 TOOL_CONSTRAINT
        assert "INPUT_HASH:" in result.prompt
        assert "TOOL_CONSTRAINT" not in result.prompt

    def test_developer_reviewer_different_ids(self):
        adapter = ZCodeAgentAdapter()
        dev = adapter.prepare_launch(
            AgentInput(role_id="developer", task_id="T-1", prompt="dev task")
        )
        rev = adapter.prepare_launch(
            AgentInput(role_id="independent-reviewer", task_id="T-1", prompt="review task")
        )
        assert dev.actor_id != rev.actor_id
        assert dev.session_id != rev.session_id

    def test_developer_reviewer_different_fingerprints(self):
        """不同 prompt → 不同 fingerprint → 证明看到的是不同内容"""
        adapter = ZCodeAgentAdapter()
        dev = AgentInput(role_id="developer", task_id="T-1", prompt="dev task")
        rev = AgentInput(role_id="independent-reviewer", task_id="T-1", prompt="review task")
        adapter.prepare_launch(dev)
        adapter.prepare_launch(rev)
        assert dev.fingerprint() != rev.fingerprint()

    def test_returns_same_object(self):
        adapter = ZCodeAgentAdapter()
        ai = AgentInput(role_id="dev", task_id="T-1", prompt="test")
        result = adapter.prepare_launch(ai)
        assert result is ai  # 修改并返回同一个对象


# ═══════════════════════════════════════════════════════════════════════
# collect_result() — 事后收集 + 校验
# ═══════════════════════════════════════════════════════════════════════

class TestCollectResult:
    def test_extracts_reported_hash(self):
        adapter = ZCodeAgentAdapter()
        ai = AgentInput(role_id="dev", task_id="T-1", prompt="test")
        adapter.prepare_launch(ai)
        fp = ai.fingerprint()
        raw = f"Task completed successfully.\n\nINPUT_HASH:{fp}"

        output = adapter.collect_result(ai, raw)
        assert output.reported_input_hash == fp
        assert output.input_integrity_ok() is True

    def test_cleans_hash_marker_from_output(self):
        adapter = ZCodeAgentAdapter()
        ai = AgentInput(role_id="dev", task_id="T-1", prompt="test")
        adapter.prepare_launch(ai)
        fp = ai.fingerprint()
        raw = f"Result text.\n\nINPUT_HASH:{fp}"

        output = adapter.collect_result(ai, raw)
        assert "INPUT_HASH:" not in output.stdout
        assert "Result text." in output.stdout

    def test_handles_missing_hash_gracefully(self):
        adapter = ZCodeAgentAdapter()
        ai = AgentInput(role_id="dev", task_id="T-1", prompt="test")
        adapter.prepare_launch(ai)
        raw = "No hash marker in this output."

        output = adapter.collect_result(ai, raw)
        assert output.reported_input_hash == ""
        assert output.input_integrity_ok() is False

    def test_detects_tool_violations(self):
        adapter = ZCodeAgentAdapter()
        ai = AgentInput(
            role_id="reviewer", task_id="T-1", prompt="Review.",
            forbidden_tools=["Write", "Edit", "Deploy"],
        )
        adapter.prepare_launch(ai)
        raw = "I decided to execute deploy to production."

        output = adapter.collect_result(ai, raw)
        # scan 返回 forbidden_tools 中的原始值（大小写保留），匹配是大小写不敏感的
        assert any(v.lower() == "deploy" for v in output.tool_violations)
        assert output.contract_violated is True

    def test_no_violations_when_clean(self):
        adapter = ZCodeAgentAdapter()
        ai = AgentInput(
            role_id="reviewer", task_id="T-1", prompt="Review.",
            forbidden_tools=["deploy"],
        )
        adapter.prepare_launch(ai)
        raw = "I read the code and found no issues."

        output = adapter.collect_result(ai, raw)
        assert output.tool_violations == []
        assert output.contract_violated is False

    def test_sets_end_time(self):
        adapter = ZCodeAgentAdapter()
        ai = AgentInput(role_id="dev", task_id="T-1", prompt="test")
        adapter.prepare_launch(ai)
        output = adapter.collect_result(ai, "done")
        assert output.end_time is not None
        assert "T" in output.end_time

    def test_preserves_start_time(self):
        adapter = ZCodeAgentAdapter()
        ai = AgentInput(role_id="dev", task_id="T-1", prompt="test")
        adapter.prepare_launch(ai)
        st = ai.start_time
        output = adapter.collect_result(ai, "done")
        assert output.start_time == st

    def test_failed_exit_code(self):
        adapter = ZCodeAgentAdapter()
        ai = AgentInput(role_id="dev", task_id="T-1", prompt="test")
        adapter.prepare_launch(ai)
        output = adapter.collect_result(ai, "error", exit_code=1)
        assert output.status == AgentStatus.FAILED

    def test_actor_session_carried_to_output(self):
        adapter = ZCodeAgentAdapter()
        ai = AgentInput(role_id="qa", task_id="T-42", prompt="test")
        adapter.prepare_launch(ai)
        output = adapter.collect_result(ai, "result")
        assert output.actor_id == ai.actor_id
        assert output.session_id == ai.session_id
        assert output.role_id == "qa"
        assert output.task_id == "T-42"

    def test_explicit_start_time_override(self):
        adapter = ZCodeAgentAdapter()
        ai = AgentInput(role_id="dev", task_id="T-1", prompt="test")
        output = adapter.collect_result(ai, "done", start_time="2026-07-23T10:00:00Z")
        assert output.start_time == "2026-07-23T10:00:00Z"

    def test_output_files_passed_through(self):
        adapter = ZCodeAgentAdapter()
        ai = AgentInput(role_id="dev", task_id="T-1", prompt="test")
        output = adapter.collect_result(
            ai, "done", output_files=["src/a.py", "tests/test_a.py"]
        )
        assert output.output_files == ["src/a.py", "tests/test_a.py"]


# ═══════════════════════════════════════════════════════════════════════
# ZCodeAgentAdapter — 桩行为
# ═══════════════════════════════════════════════════════════════════════

class TestZCodeAgentAdapterStub:
    def test_host_name(self):
        assert ZCodeAgentAdapter().host_name == "zcode"

    def test_launch_agent_raises(self):
        adapter = ZCodeAgentAdapter()
        ai = AgentInput(role_id="dev", task_id="T-1", prompt="test")
        with pytest.raises(AgentUnavailableError) as exc:
            adapter.launch_agent(ai)
        assert "REAL_AGENT_UNAVAILABLE" in str(exc.value)
        assert "prepare_launch" in str(exc.value)

    def test_get_status_returns_unavailable(self):
        assert ZCodeAgentAdapter().get_status("any") == AgentStatus.UNAVAILABLE

    def test_collect_output_raises(self):
        adapter = ZCodeAgentAdapter()
        with pytest.raises(AgentUnavailableError):
            adapter.collect_output("any")


# ═══════════════════════════════════════════════════════════════════════
# AgentAdapter ABC
# ═══════════════════════════════════════════════════════════════════════

class TestAgentAdapterABC:
    def test_cannot_instantiate_abc(self):
        with pytest.raises(TypeError):
            AgentAdapter()  # type: ignore[abstract]

    def test_zcode_adapter_is_instance(self):
        assert isinstance(ZCodeAgentAdapter(), AgentAdapter)


# ═══════════════════════════════════════════════════════════════════════
# 端到端工作流
# ═══════════════════════════════════════════════════════════════════════

class TestEndToEndWorkflow:
    def test_full_prepare_collect_cycle_clean(self):
        """完整 prepare → collect 工作流，一切正常。"""
        adapter = ZCodeAgentAdapter()
        ai = AgentInput(
            role_id="developer",
            task_id="T-0034",
            prompt="Implement feature X",
            input_files=["spec.md"],
            allowed_tools=["Read", "Write", "Edit"],
            forbidden_tools=["deploy", "rollback"],
        )

        # 准备
        prepared = adapter.prepare_launch(ai)
        assert prepared.session_id is not None
        assert prepared.actor_id is not None
        fp = prepared.fingerprint()

        # 模拟 Agent 输出（带 hash 回报）
        raw_output = f"Feature X implemented.\n\nINPUT_HASH:{fp}"

        # 收集 + 校验
        output = adapter.collect_result(prepared, raw_output)

        assert output.status == AgentStatus.COMPLETED
        assert output.input_integrity_ok() is True
        assert output.contract_violated is False
        assert output.is_clean is True
        assert output.actor_id == prepared.actor_id
        assert output.session_id == prepared.session_id

    def test_tampered_input_detected(self):
        """输入被篡改 → is_clean = False。"""
        adapter = ZCodeAgentAdapter()
        ai = AgentInput(role_id="dev", task_id="T-1", prompt="original")
        adapter.prepare_launch(ai)
        fp = ai.fingerprint()

        # 回报不同的 hash
        raw = f"Done.\n\nINPUT_HASH:{'0' * 64}"
        output = adapter.collect_result(ai, raw)

        assert output.input_integrity_ok() is False
        assert output.is_clean is False

    def test_violation_detected_in_output(self):
        """输出包含违规 → contract_violated = True, is_clean = False。"""
        adapter = ZCodeAgentAdapter()
        ai = AgentInput(
            role_id="reviewer", task_id="T-1", prompt="Review.",
            forbidden_tools=["deploy"],
        )
        adapter.prepare_launch(ai)
        fp = ai.fingerprint()

        raw = f"I decided to execute deploy to production.\n\nINPUT_HASH:{fp}"
        output = adapter.collect_result(ai, raw)

        assert "deploy" in output.tool_violations
        assert output.contract_violated is True
        assert output.is_clean is False

    def test_developer_reviewer_independent(self):
        """Developer 和 Reviewer 独立：不同 actor_id + 不同 fingerprint。"""
        adapter = ZCodeAgentAdapter()

        dev = AgentInput(role_id="developer", task_id="T-1", prompt="Implement X")
        rev = AgentInput(role_id="independent-reviewer", task_id="T-1", prompt="Review X")

        adapter.prepare_launch(dev)
        adapter.prepare_launch(rev)

        assert dev.actor_id != rev.actor_id
        assert dev.session_id != rev.session_id
        assert dev.fingerprint() != rev.fingerprint()

    def test_hash_marker_not_in_clean_output(self):
        """collect_result 后 stdout 不应包含协议标记。"""
        adapter = ZCodeAgentAdapter()
        ai = AgentInput(role_id="dev", task_id="T-1", prompt="test")
        adapter.prepare_launch(ai)
        fp = ai.fingerprint()

        raw = f"Normal output text.\n\nINPUT_HASH:{fp}\n"
        output = adapter.collect_result(ai, raw)

        assert "INPUT_HASH:" not in output.stdout
        assert "Normal output text." in output.stdout
