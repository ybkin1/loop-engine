"""
MCP Agent Runtime — LLM-based agent execution for MCP tools.

Runs as part of the MCP server process (tools/server.py).  Receives a
SubagentManifest, dispatches each sub-agent by calling an LLM API directly,
and returns aggregated results as pure text.

SAFETY: This module does NOT import or use any file-writing tools.
All file operations remain in the ZCode session, protected by hooks.

API key: read from environment variable (LLM_API_KEY or DEEPSEEK_API_KEY).
"""
from __future__ import annotations

import json
import os
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class AgentCallResult:
    subagent_id: str
    status: str
    output: str
    error: str = ""
    token_count: int = 0
    duration_ms: int = 0


@dataclass
class DispatchResult:
    manifest_id: str
    total: int
    completed: int
    failed: int
    results: list[AgentCallResult] = field(default_factory=list)


class LLMClient:
    """Minimal LLM API client. Zero dependencies beyond stdlib."""

    def __init__(self, api_key: str | None = None, base_url: str | None = None):
        env_key = os.environ.get("LLM_API_KEY") or os.environ.get("DEEPSEEK_API_KEY")
        self.api_key = api_key or env_key
        if not self.api_key:
            raise RuntimeError("LLM_API_KEY or DEEPSEEK_API_KEY env var required")
        self.base_url = base_url or os.environ.get(
            "LLM_BASE_URL", "https://api.deepseek.com/v1/chat/completions"
        )

    def chat(self, system_prompt: str, user_prompt: str,
             model: str = "", max_tokens: int = 4096,
             timeout_seconds: int = 300) -> dict[str, Any]:
        import urllib.request as _req
        payload = json.dumps({
            "model": model or os.environ.get("LLM_MODEL", "deepseek-chat"),
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "max_tokens": max_tokens,
            "temperature": 0.3,
        }).encode("utf-8")
        req = _req.Request(self.base_url, data=payload, headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        })
        try:
            with _req.urlopen(req, timeout=timeout_seconds) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as exc:
            return {"error": str(exc), "choices": []}

    @staticmethod
    def extract_text(response: dict) -> str:
        choices = response.get("choices", [])
        if not choices:
            return f"[ERROR] {response.get('error', 'No response')}"
        return choices[0].get("message", {}).get("content", "")


def load_role_skill(agents_dir: Path, role_hint: str) -> str:
    """Load a role's SKILL.md as system prompt."""
    role_dir = agents_dir / role_hint
    if role_dir.is_dir():
        skill = role_dir / "SKILL.md"
        if skill.is_file():
            return skill.read_text(encoding="utf-8")
    for d in sorted(agents_dir.iterdir()):
        if not d.is_dir() or d.name == "references":
            continue
        if role_hint.lower() in d.name.lower():
            skill = d / "SKILL.md"
            if skill.is_file():
                return skill.read_text(encoding="utf-8")
    return f"You are an AI agent with role: {role_hint}. Return results in structured format."


class MCPAgentRuntime:
    """Executes SubagentManifests via direct LLM API calls.

    SAFETY: Pure computation. No file I/O, no state changes.
    """

    def __init__(self, agents_dir: str | Path = "", api_key: str | None = None):
        self.agents_dir = Path(agents_dir) if agents_dir else Path("agents")
        self.client = LLMClient(api_key=api_key)

    def run_agent(self, subagent_id: str, role_hint: str, prompt: str,
                  timeout_seconds: int = 300) -> AgentCallResult:
        system_prompt = load_role_skill(self.agents_dir, role_hint)
        started = time.time()
        response = self.client.chat(system_prompt=system_prompt, user_prompt=prompt,
                                    timeout_seconds=timeout_seconds)
        duration_ms = int((time.time() - started) * 1000)
        text = self.client.extract_text(response)
        if response.get("error"):
            return AgentCallResult(subagent_id=subagent_id, status="failed",
                                   output="", error=str(response["error"]),
                                   duration_ms=duration_ms)
        usage = response.get("usage", {})
        hash_match = re.search(r"INPUT_HASH:([a-f0-9]{64})", text)
        clean = re.sub(r"INPUT_HASH:[a-f0-9]{64}", "", text).strip() if hash_match else text
        return AgentCallResult(subagent_id=subagent_id, status="completed",
                               output=clean, token_count=usage.get("total_tokens", 0),
                               duration_ms=duration_ms)

    def dispatch_manifest(self, manifest: dict, max_retries: int = 2) -> DispatchResult:
        subagents = manifest.get("subagents", [])
        for batch in manifest.get("batches", []):
            for step in batch.get("steps", []):
                subagents.append(step)
        if not subagents:
            return DispatchResult(manifest_id=manifest.get("manifest_id", "unknown"),
                                  total=0, completed=0, failed=0)
        results: list[AgentCallResult] = []
        for spec in subagents:
            sid = spec.get("subagent_id", "unknown")
            role = spec.get("role_hint", "general-purpose")
            prompt_text = spec.get("prompt", spec.get("full_prompt", ""))
            timeout = spec.get("timeout_seconds", 300)
            result = self.run_agent(sid, role, prompt_text, timeout_seconds=timeout)
            retries = 0
            while result.status == "failed" and retries < max_retries:
                retries += 1
                result = self.run_agent(sid, role,
                    f"[RETRY {retries}/{max_retries}] {result.error}\n\n{prompt_text}",
                    timeout_seconds=timeout)
            results.append(result)
        return DispatchResult(
            manifest_id=manifest.get("manifest_id", "unknown"),
            total=len(subagents),
            completed=sum(1 for r in results if r.status == "completed"),
            failed=sum(1 for r in results if r.status == "failed"),
            results=results,
        )
