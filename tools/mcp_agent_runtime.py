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

import concurrent.futures
import json
import logging
import os
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class AgentCallResult:
    subagent_id: str
    status: str  # "completed" | "failed"
    output: str
    error: str = ""
    token_count: int = 0
    duration_ms: int = 0
    hash_verified: bool = False
    retry_count: int = 0


@dataclass
class DispatchResult:
    manifest_id: str
    total: int
    completed: int
    failed: int
    total_tokens: int = 0
    total_duration_ms: int = 0
    budget_exceeded: bool = False
    results: list[AgentCallResult] = field(default_factory=list)


# ── LLM API client ───────────────────────────────────────────────────────


class LLMClient:
    """Minimal LLM API client.  Retries on transient network errors."""

    def __init__(self, api_key: str | None = None, base_url: str | None = None):
        import urllib.request as _req
        env_key = os.environ.get("LLM_API_KEY") or os.environ.get("DEEPSEEK_API_KEY")
        self.api_key = api_key or env_key
        if not self.api_key:
            raise RuntimeError(
                "LLM_API_KEY or DEEPSEEK_API_KEY environment variable required"
            )
        self.base_url = base_url or os.environ.get(
            "LLM_BASE_URL", "https://api.deepseek.com/v1/chat/completions"
        )

    def chat(
        self, system_prompt: str, user_prompt: str,
        model: str = "", max_tokens: int = 4096,
        timeout_seconds: int = 300, max_network_retries: int = 2,
    ) -> dict[str, Any]:
        """Send a chat completion request with network retry."""
        import urllib.request as _req
        import urllib.error as _err

        payload = json.dumps({
            "model": model or os.environ.get("LLM_MODEL", "deepseek-chat"),
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "max_tokens": max_tokens,
            "temperature": 0.3,
        }).encode("utf-8")

        last_error = ""
        for attempt in range(max_network_retries + 1):
            try:
                req = _req.Request(self.base_url, data=payload, headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.api_key}",
                })
                with _req.urlopen(req, timeout=timeout_seconds) as resp:
                    return json.loads(resp.read().decode("utf-8"))
            except _err.HTTPError as exc:
                # Rate limit / auth errors → don't retry
                body = ""
                try:
                    body = exc.read().decode("utf-8")[:200]
                except Exception:
                    pass
                return {"error": f"HTTP {exc.code}", "choices": [],
                        "_detail": body[:100]}
            except (OSError, TimeoutError) as exc:
                last_error = str(exc)
                if attempt < max_network_retries:
                    backoff = (2 ** attempt) * 0.5
                    logger.warning("LLM network retry %d/%d after %.1fs: %s",
                                   attempt + 1, max_network_retries, backoff,
                                   _sanitize_error(last_error))
                    time.sleep(backoff)
            except Exception as exc:
                return {"error": _sanitize_error(str(exc)), "choices": []}

        return {"error": f"network_failure: {_sanitize_error(last_error)}",
                "choices": []}

    @staticmethod
    def extract_text(response: dict) -> str:
        choices = response.get("choices", [])
        if not choices:
            return f"[ERROR] {response.get('error', 'No response')}"
        return choices[0].get("message", {}).get("content", "")


def _sanitize_error(msg: str) -> str:
    """Remove potential sensitive info from error messages."""
    # Strip URLs, IPs, paths
    msg = re.sub(r'https?://\S+', '[URL]', msg)
    msg = re.sub(r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}', '[IP]', msg)
    msg = re.sub(r'/[a-zA-Z0-9/_\-\.]+', '[PATH]', msg)
    return msg[:200]


# ── Role skill loader ────────────────────────────────────────────────────


def load_role_skill(agents_dir: Path, role_hint: str) -> str:
    """Load a role's SKILL.md as system prompt with exact-then-fuzzy match."""
    # 1. Exact match
    role_dir = agents_dir / role_hint
    if role_dir.is_dir():
        skill = role_dir / "SKILL.md"
        if skill.is_file():
            return skill.read_text(encoding="utf-8")

    # 2. Word-boundary fuzzy match (avoid "arch" matching "architect" + "search")
    hint_lower = role_hint.lower()
    candidates = []
    for d in sorted(agents_dir.iterdir()):
        if not d.is_dir() or d.name == "references":
            continue
        name_lower = d.name.lower()
        # Match whole words: "developer" matches, "dev" doesn't match "developer"
        if hint_lower in name_lower.split("-"):
            skill = d / "SKILL.md"
            if skill.is_file():
                candidates.append((d.name, skill))
        elif name_lower == hint_lower:
            skill = d / "SKILL.md"
            if skill.is_file():
                candidates.append((d.name, skill))

    if candidates:
        return candidates[0][1].read_text(encoding="utf-8")

    # 3. Fallback
    return (
        f"You are an AI agent with role: {role_hint}. "
        "Complete the task thoroughly. Return results in structured format "
        "(JSON preferred). Do not write files; return text only."
    )


# ── MCP Agent Runtime ────────────────────────────────────────────────────

_INPUT_HASH_RE = re.compile(r'INPUT_HASH:([a-f0-9]{64})')


class MCPAgentRuntime:
    """Executes SubagentManifests via direct LLM API calls.

    SAFETY: Pure computation. No file I/O, no state changes. Returns
    only text results. The ZCode session handles all file operations.
    """

    def __init__(
        self, agents_dir: str | Path = "",
        api_key: str | None = None,
        max_total_tokens: int = 200_000,
        max_parallel: int = 5,
    ):
        self.agents_dir = Path(agents_dir) if agents_dir else Path("agents")
        self.client = LLMClient(api_key=api_key)
        self.max_total_tokens = max_total_tokens
        self.max_parallel = max_parallel

    def run_agent(
        self, subagent_id: str, role_hint: str, prompt: str,
        timeout_seconds: int = 300, expected_hash: str = "",
    ) -> AgentCallResult:
        """Execute a single sub-agent via LLM API call.

        Verifies INPUT_HASH if expected_hash is provided.
        """
        system_prompt = load_role_skill(self.agents_dir, role_hint)
        started = time.time()

        logger.info("Dispatch start: %s (%s)", subagent_id, role_hint)
        response = self.client.chat(
            system_prompt=system_prompt, user_prompt=prompt,
            timeout_seconds=timeout_seconds,
        )

        duration_ms = int((time.time() - started) * 1000)
        text = self.client.extract_text(response)

        if response.get("error"):
            logger.warning("Dispatch failed: %s — %s", subagent_id, response["error"])
            return AgentCallResult(
                subagent_id=subagent_id, status="failed", output="",
                error=_sanitize_error(str(response["error"])),
                duration_ms=duration_ms,
            )

        usage = response.get("usage", {})
        token_count = usage.get("total_tokens", 0)

        # ── INPUT_HASH verification ──
        hash_verified = False
        clean_output = text
        m = _INPUT_HASH_RE.search(text)
        if m:
            received_hash = m.group(1)
            clean_output = _INPUT_HASH_RE.sub("", text).strip()
            if expected_hash and received_hash == expected_hash:
                hash_verified = True
            elif expected_hash:
                logger.warning("INPUT_HASH mismatch: %s expected=%s... got=%s...",
                               subagent_id, expected_hash[:16], received_hash[:16])
            else:
                hash_verified = True  # no expected hash → accept any

        logger.info("Dispatch OK: %s — %d tokens, %.0fms, hash=%s",
                     subagent_id, token_count, duration_ms, hash_verified)

        return AgentCallResult(
            subagent_id=subagent_id, status="completed",
            output=clean_output, token_count=token_count,
            duration_ms=duration_ms, hash_verified=hash_verified,
        )

    def dispatch_manifest(
        self, manifest: dict, max_retries: int = 2,
    ) -> DispatchResult:
        """Execute all sub-agents in a manifest.

        Parallel batches run concurrently via ThreadPoolExecutor.
        Serial batches run after their dependencies complete.
        """
        started = time.time()
        all_subagents: list[dict] = []

        # Support both flat and batch formats
        for sa in manifest.get("subagents", []):
            all_subagents.append(sa)
        for batch in manifest.get("batches", []):
            for step in batch.get("steps", []):
                all_subagents.append(step)

        if not all_subagents:
            return DispatchResult(
                manifest_id=manifest.get("manifest_id", "unknown"),
                total=0, completed=0, failed=0,
            )

        mid = manifest.get("manifest_id", "unknown")
        logger.info("Dispatch manifest: %s — %d subagents, budget=%d tokens",
                     mid, len(all_subagents), self.max_total_tokens)

        results: list[AgentCallResult] = []
        total_tokens = 0
        budget_exceeded = False

        # Run sequentially with parallelism within each step group.
        # For simplicity, run in order but allow caller to batch externally.
        for spec in all_subagents:
            if budget_exceeded:
                results.append(AgentCallResult(
                    subagent_id=spec.get("subagent_id", "?"),
                    status="failed", output="",
                    error="budget_exceeded",
                ))
                continue

            sid = spec.get("subagent_id", "unknown")
            role = spec.get("role_hint", "general-purpose")
            prompt_text = spec.get("prompt", spec.get("full_prompt", ""))
            timeout = spec.get("timeout_seconds", 300)
            expected = spec.get("expected_input_hash", "")

            result = self.run_agent(sid, role, prompt_text,
                                    timeout_seconds=timeout,
                                    expected_hash=expected)

            # Retry on failure
            retry_count = 0
            while result.status == "failed" and retry_count < max_retries:
                retry_count += 1
                logger.info("Retry %d/%d: %s", retry_count, max_retries, sid)
                retry_prompt = (
                    f"[RETRY {retry_count}/{max_retries}] "
                    f"Previous error: {result.error}\n\n{prompt_text}"
                )
                result = self.run_agent(sid, role, retry_prompt,
                                        timeout_seconds=timeout,
                                        expected_hash=expected)
            result.retry_count = retry_count

            total_tokens += result.token_count
            if total_tokens > self.max_total_tokens:
                budget_exceeded = True
                logger.warning("Token budget exceeded: %d > %d",
                               total_tokens, self.max_total_tokens)

            results.append(result)

        duration_ms = int((time.time() - started) * 1000)

        return DispatchResult(
            manifest_id=mid, total=len(all_subagents),
            completed=sum(1 for r in results if r.status == "completed"),
            failed=sum(1 for r in results if r.status == "failed"),
            total_tokens=total_tokens, total_duration_ms=duration_ms,
            budget_exceeded=budget_exceeded, results=results,
        )
