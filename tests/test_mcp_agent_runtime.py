"""Tests for MCP Agent Runtime — LLM-based agent dispatch."""
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
    load_role_skill,
)


class TestLLMClient:
    def test_requires_api_key(self):
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(RuntimeError, match="API_KEY"):
                LLMClient(api_key=None)

    def test_uses_env_key(self):
        with patch.dict(os.environ, {"DEEPSEEK_API_KEY": "sk-test"}):
            client = LLMClient()
            assert client.api_key == "sk-test"

    def test_extract_text_from_valid_response(self):
        response = {
            "choices": [{"message": {"content": "Hello, world!"}}],
            "usage": {"total_tokens": 10},
        }
        assert LLMClient.extract_text(response) == "Hello, world!"

    def test_extract_text_from_error_response(self):
        response = {"error": "Rate limited", "choices": []}
        assert "[ERROR]" in LLMClient.extract_text(response)

    def test_chat_mock(self):
        with patch.dict(os.environ, {"DEEPSEEK_API_KEY": "sk-test"}):
            client = LLMClient()
            mock_response = {
                "choices": [{"message": {"content": "Mocked response"}}],
                "usage": {"total_tokens": 5},
            }
            with patch.object(client, "chat", return_value=mock_response):
                resp = client.chat("system", "user")
                assert resp["choices"][0]["message"]["content"] == "Mocked response"


class TestLoadRoleSkill:
    def test_loads_existing_role(self, tmp_path):
        role_dir = tmp_path / "developer"
        role_dir.mkdir()
        (role_dir / "SKILL.md").write_text("# Developer Role", encoding="utf-8")

        result = load_role_skill(tmp_path, "developer")
        assert "Developer Role" in result

    def test_fuzzy_match(self, tmp_path):
        role_dir = tmp_path / "system-architect"
        role_dir.mkdir()
        (role_dir / "SKILL.md").write_text("# Architect", encoding="utf-8")

        result = load_role_skill(tmp_path, "architect")
        assert "Architect" in result

    def test_fallback_when_no_match(self, tmp_path):
        result = load_role_skill(tmp_path, "nonexistent")
        assert "nonexistent" in result
        assert "structured format" in result


class TestMCPAgentRuntime:
    def make_runtime(self, tmp_path):
        agents = tmp_path / "agents"
        agents.mkdir()
        for role in ["developer", "independent-reviewer"]:
            d = agents / role
            d.mkdir()
            (d / "SKILL.md").write_text(f"# {role} Role", encoding="utf-8")
        return MCPAgentRuntime(agents_dir=agents, api_key="sk-test")

    def test_run_agent_mocked(self, tmp_path):
        runtime = self.make_runtime(tmp_path)
        mock_resp = {
            "choices": [{"message": {"content": "Code complete.\n\nINPUT_HASH:" + "a" * 64}}],
            "usage": {"total_tokens": 50},
        }
        with patch.object(runtime.client, "chat", return_value=mock_resp):
            result = runtime.run_agent("dev-1", "developer", "Write code")
            assert result.status == "completed"
            assert "Code complete" in result.output
            assert "INPUT_HASH" not in result.output  # stripped
            assert result.token_count == 50

    def test_run_agent_error(self, tmp_path):
        runtime = self.make_runtime(tmp_path)
        with patch.object(runtime.client, "chat", return_value={"error": "timeout", "choices": []}):
            result = runtime.run_agent("dev-1", "developer", "Write code")
            assert result.status == "failed"
            assert "timeout" in result.error

    def test_dispatch_single_agent(self, tmp_path):
        runtime = self.make_runtime(tmp_path)
        manifest = {
            "manifest_id": "TEST-001",
            "subagents": [
                {"subagent_id": "dev-1", "role_hint": "developer", "prompt": "Write code"}
            ],
        }
        mock_resp = {
            "choices": [{"message": {"content": "Done"}}],
            "usage": {"total_tokens": 10},
        }
        with patch.object(runtime.client, "chat", return_value=mock_resp):
            result = runtime.dispatch_manifest(manifest)
            assert result.total == 1
            assert result.completed == 1
            assert result.failed == 0

    def test_dispatch_with_retry(self, tmp_path):
        runtime = self.make_runtime(tmp_path)
        manifest = {
            "manifest_id": "TEST-002",
            "subagents": [
                {"subagent_id": "dev-1", "role_hint": "developer", "prompt": "Code"}
            ],
        }
        fail_resp = {"error": "transient", "choices": []}
        ok_resp = {
            "choices": [{"message": {"content": "Recovered"}}],
            "usage": {"total_tokens": 10},
        }
        with patch.object(runtime.client, "chat", side_effect=[fail_resp, ok_resp]):
            result = runtime.dispatch_manifest(manifest, max_retries=1)
            assert result.completed == 1
            assert result.failed == 0

    def test_dispatch_batches_format(self, tmp_path):
        runtime = self.make_runtime(tmp_path)
        manifest = {
            "manifest_id": "TEST-003",
            "batches": [
                {"batch_index": 0, "steps": [
                    {"subagent_id": "dev-1", "role_hint": "developer", "prompt": "A"}
                ]},
            ],
        }
        mock_resp = {
            "choices": [{"message": {"content": "OK"}}],
            "usage": {"total_tokens": 5},
        }
        with patch.object(runtime.client, "chat", return_value=mock_resp):
            result = runtime.dispatch_manifest(manifest)
            assert result.total == 1

    def test_empty_manifest(self, tmp_path):
        runtime = self.make_runtime(tmp_path)
        result = runtime.dispatch_manifest({"manifest_id": "E"})
        assert result.total == 0

    def test_no_file_writes(self, tmp_path):
        """Safety: MCPAgentRuntime must not write any files."""
        runtime = self.make_runtime(tmp_path)
        before = set(str(p) for p in tmp_path.rglob("*") if p.is_file())
        manifest = {
            "manifest_id": "SAFE",
            "subagents": [
                {"subagent_id": "dev-1", "role_hint": "developer", "prompt": "test"}
            ],
        }
        mock_resp = {
            "choices": [{"message": {"content": "result"}}],
            "usage": {"total_tokens": 1},
        }
        with patch.object(runtime.client, "chat", return_value=mock_resp):
            runtime.dispatch_manifest(manifest)
        after = set(str(p) for p in tmp_path.rglob("*") if p.is_file())
        assert before == after  # zero new files
