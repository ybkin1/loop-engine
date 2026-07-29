"""Tests for MCP Agent Runtime — LLM-based agent dispatch (v3.10.1)."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tools.mcp_agent_runtime import (
    AgentCallResult,
    DispatchResult,
    LLMClient,
    MCPAgentRuntime,
    _sanitize_error,
    load_role_skill,
)


# ── LLMClient ──────────────────────────────────────────────────────────

class TestLLMClient:
    def test_requires_api_key(self):
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(RuntimeError, match="API_KEY"):
                LLMClient(api_key=None)

    def test_uses_env_key(self):
        with patch.dict(os.environ, {"DEEPSEEK_API_KEY": "sk-test"}):
            assert LLMClient().api_key == "sk-test"

    def test_extract_text_valid(self):
        resp = {"choices": [{"message": {"content": "Hello"}}], "usage": {"total_tokens": 10}}
        assert LLMClient.extract_text(resp) == "Hello"

    def test_extract_text_error(self):
        assert "[ERROR]" in LLMClient.extract_text({"error": "fail", "choices": []})

    def test_chat_mock(self):
        with patch.dict(os.environ, {"DEEPSEEK_API_KEY": "sk-test"}):
            client = LLMClient()
            with patch.object(client, "chat", return_value={"choices": [{"message": {"content": "X"}}]}):
                assert client.chat("s", "u")["choices"][0]["message"]["content"] == "X"


# ── Error sanitization ─────────────────────────────────────────────────

class TestSanitizeError:
    def test_strips_urls(self):
        assert "https://api.example.com/key" not in _sanitize_error(
            "failed https://api.example.com/key connection"
        )

    def test_strips_ips(self):
        assert "192.168.1.1" not in _sanitize_error("connect 192.168.1.1:443")

    def test_truncates_long(self):
        assert len(_sanitize_error("x" * 500)) <= 200


# ── Role skill loading ────────────────────────────────────────────────

class TestLoadRoleSkill:
    def test_exact_match(self, tmp_path):
        (d := tmp_path / "developer").mkdir()
        (d / "SKILL.md").write_text("# Developer Role", encoding="utf-8")
        assert "Developer Role" in load_role_skill(tmp_path, "developer")

    def test_word_boundary_match(self, tmp_path):
        (d := tmp_path / "system-architect").mkdir()
        (d / "SKILL.md").write_text("# Architect", encoding="utf-8")
        # "architect" should match "system-architect" (word boundary)
        assert "Architect" in load_role_skill(tmp_path, "architect")

    def test_no_false_match_on_partial_word(self, tmp_path):
        (d := tmp_path / "developer").mkdir()
        (d / "SKILL.md").write_text("# Dev", encoding="utf-8")
        # "dev" should NOT match "developer" (no word boundary)
        result = load_role_skill(tmp_path, "dev")
        assert "dev" in result  # fallback message
        assert "Dev" not in result  # not the loaded skill

    def test_fallback(self, tmp_path):
        result = load_role_skill(tmp_path, "nonexistent")
        assert "nonexistent" in result


# ── MCPAgentRuntime ────────────────────────────────────────────────────

class TestMCPAgentRuntime:
    def make_runtime(self, tmp_path):
        agents = tmp_path / "agents"
        agents.mkdir()
        for role in ["developer", "independent-reviewer"]:
            (d := agents / role).mkdir()
            (d / "SKILL.md").write_text(f"# {role} Role", encoding="utf-8")
        return MCPAgentRuntime(agents_dir=agents, api_key="sk-test")

    def _ok_resp(self, text="OK"):
        return {"choices": [{"message": {"content": text}}], "usage": {"total_tokens": 10}}

    def test_run_agent_mocked(self, tmp_path):
        runtime = self.make_runtime(tmp_path)
        with patch.object(runtime.client, "chat", return_value=self._ok_resp("Done\n\nINPUT_HASH:" + "a" * 64)):
            result = runtime.run_agent("dev-1", "developer", "Code",
                                       expected_hash="a" * 64)
            assert result.status == "completed"
            assert result.hash_verified is True
            assert "INPUT_HASH" not in result.output

    def test_input_hash_mismatch(self, tmp_path):
        runtime = self.make_runtime(tmp_path)
        resp = self._ok_resp("Done\n\nINPUT_HASH:" + "b" * 64)
        with patch.object(runtime.client, "chat", return_value=resp):
            result = runtime.run_agent("dev-1", "developer", "Code",
                                       expected_hash="a" * 64)
            assert result.hash_verified is False

    def test_input_hash_no_expected_accepts_any(self, tmp_path):
        runtime = self.make_runtime(tmp_path)
        resp = self._ok_resp("Done\n\nINPUT_HASH:" + "c" * 64)
        with patch.object(runtime.client, "chat", return_value=resp):
            result = runtime.run_agent("dev-1", "developer", "Code")
            assert result.hash_verified is True

    def test_run_agent_error(self, tmp_path):
        runtime = self.make_runtime(tmp_path)
        with patch.object(runtime.client, "chat", return_value={"error": "timeout", "choices": []}):
            result = runtime.run_agent("dev-1", "developer", "Code")
            assert result.status == "failed"

    def test_dispatch_single(self, tmp_path):
        runtime = self.make_runtime(tmp_path)
        manifest = {"manifest_id": "T1", "subagents": [
            {"subagent_id": "dev-1", "role_hint": "developer", "prompt": "Code"}
        ]}
        with patch.object(runtime.client, "chat", return_value=self._ok_resp("Done")):
            result = runtime.dispatch_manifest(manifest)
            assert result.total == 1 and result.completed == 1

    def test_dispatch_with_retry(self, tmp_path):
        runtime = self.make_runtime(tmp_path)
        manifest = {"manifest_id": "T2", "subagents": [
            {"subagent_id": "dev-1", "role_hint": "developer", "prompt": "Code"}
        ]}
        fail = {"error": "transient", "choices": []}
        with patch.object(runtime.client, "chat", side_effect=[fail, self._ok_resp("Recovered")]):
            result = runtime.dispatch_manifest(manifest, max_retries=1)
            assert result.completed == 1

    def test_budget_exceeded_stops_dispatch(self, tmp_path):
        runtime = MCPAgentRuntime(agents_dir=tmp_path, api_key="sk-test",
                                  max_total_tokens=5)
        manifest = {"manifest_id": "T3", "subagents": [
            {"subagent_id": "a", "role_hint": "developer", "prompt": "A"},
            {"subagent_id": "b", "role_hint": "developer", "prompt": "B"},
        ]}
        # First agent uses 10 tokens > budget of 5
        with patch.object(runtime.client, "chat", return_value={
            "choices": [{"message": {"content": "X"}}], "usage": {"total_tokens": 10}
        }):
            result = runtime.dispatch_manifest(manifest)
            assert result.budget_exceeded is True
            assert result.failed >= 1

    def test_empty_manifest(self, tmp_path):
        runtime = self.make_runtime(tmp_path)
        result = runtime.dispatch_manifest({"manifest_id": "E"})
        assert result.total == 0

    def test_no_file_writes(self, tmp_path):
        """SAFETY: MCPAgentRuntime writes zero files."""
        runtime = self.make_runtime(tmp_path)
        before = set(str(p) for p in tmp_path.rglob("*") if p.is_file())
        manifest = {"manifest_id": "SAFE", "subagents": [
            {"subagent_id": "dev-1", "role_hint": "developer", "prompt": "test"}
        ]}
        with patch.object(runtime.client, "chat", return_value=self._ok_resp("result")):
            runtime.dispatch_manifest(manifest)
        after = set(str(p) for p in tmp_path.rglob("*") if p.is_file())
        assert before == after

    def test_retry_count_tracked(self, tmp_path):
        runtime = self.make_runtime(tmp_path)
        manifest = {"manifest_id": "T4", "subagents": [
            {"subagent_id": "dev-1", "role_hint": "developer", "prompt": "Code"}
        ]}
        fail = {"error": "fail", "choices": []}
        with patch.object(runtime.client, "chat", side_effect=[fail, fail, self._ok_resp("OK")]):
            result = runtime.dispatch_manifest(manifest, max_retries=2)
            assert result.completed == 1
            assert result.results[0].retry_count == 2

    def test_dispatch_batches_format(self, tmp_path):
        runtime = self.make_runtime(tmp_path)
        manifest = {"manifest_id": "T5", "batches": [
            {"batch_index": 0, "steps": [
                {"subagent_id": "dev-1", "role_hint": "developer", "prompt": "A"}
            ]}
        ]}
        with patch.object(runtime.client, "chat", return_value=self._ok_resp("OK")):
            result = runtime.dispatch_manifest(manifest)
            assert result.total == 1
