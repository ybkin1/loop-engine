# -*- coding: utf-8 -*-
"""
test_ledger_guard.py — ledger_guard.py hook 的端到端测试。

每个测试用临时目录搭一个最小项目，以子进程方式运行 ledger_guard.py，
断言退出码与输出——与 ZCode 实际调用方式一致
（process 类型 + args 数组 + stdin JSON + ZCODE_PROJECT_DIR 环境变量）。
"""

import hashlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent.parent / "hooks" / "scripts"
LEDGER_GUARD = str(SCRIPTS / "ledger_guard.py")

ROOT_SEED = b"LOOP_ENGINE_EXECUTION_LEDGER_V1_ROOT"


def _root_hash() -> str:
    return hashlib.sha256(ROOT_SEED).hexdigest()


def _compute_chain_hash(prev_hash: str, row_json: str) -> str:
    return hashlib.sha256(
        prev_hash.encode() + row_json.encode("utf-8")
    ).hexdigest()


def _build_ledger_line(entry: dict, prev_hash: str) -> str:
    """Build a single JSONL line with a valid chain_hash."""
    row_json = json.dumps(entry, sort_keys=True, ensure_ascii=False)
    ch = _compute_chain_hash(prev_hash, row_json)
    entry_with_hash = dict(entry)
    entry_with_hash["chain_hash"] = ch
    return json.dumps(entry_with_hash, sort_keys=True, ensure_ascii=False)


def _build_valid_ledger(entries: list[dict]) -> str:
    """Build valid ledger content from a list of entry dicts (without chain_hash)."""
    lines = []
    prev = _root_hash()
    for entry in entries:
        line = _build_ledger_line(entry, prev)
        lines.append(line)
        # parse back to get the chain_hash for next iteration
        parsed = json.loads(line)
        prev = parsed["chain_hash"]
    return "\n".join(lines) + "\n"


def _make_sample_entry(execution_id: str) -> dict:
    return {
        "execution_id": execution_id,
        "session_id": "sess-test",
        "actor_id": "actor-test",
        "role_id": "developer",
        "task_id": "T-0001",
        "prompt_fingerprint": "a" * 64,
        "input_files_hash": "b" * 64,
        "status": "LAUNCHED",
        "launched_at": "2026-07-23T10:00:00Z",
        "completed_at": None,
        "exit_code": None,
        "output_hash": None,
        "tool_constraints": [],
        "tool_violations": [],
        "cross_references": [],
    }


def _run_ledger_guard(project_root: str, tool_input: dict) -> subprocess.CompletedProcess:
    """Run ledger_guard.py as a subprocess, mimicking ZCode hook invocation."""
    hook_input = json.dumps({
        "cwd": project_root,
        "tool_name": tool_input.get("tool_name", "Write"),
        "tool_input": tool_input,
    })
    env = {**os.environ, "ZCODE_PROJECT_DIR": project_root}
    return subprocess.run(
        [sys.executable, LEDGER_GUARD],
        input=hook_input, capture_output=True, text=True, timeout=10, env=env,
    )


# ═══════════════════════════════════════════════════════════════
# Tests
# ═══════════════════════════════════════════════════════════════

class TestLedgerGuard:
    """End-to-end tests for ledger_guard.py hook."""

    # ── Scenario 1: Valid append to ledger file passes (exit 0) ──

    def test_valid_append_passes(self):
        """Appending a new valid entry to an existing ledger should pass."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ledger_dir = root / ".ai" / "ledger"
            ledger_dir.mkdir(parents=True)

            # Create existing ledger with one valid entry
            existing_content = _build_valid_ledger([_make_sample_entry("exec-001")])
            ledger_path = ledger_dir / "executions.jsonl"
            ledger_path.write_text(existing_content, encoding="utf-8")

            # Build new content: existing + one new entry
            existing_entries = json.loads(existing_content.strip().split("\n")[0])
            # Rebuild full content with proper chain
            all_entries_raw = [
                _make_sample_entry("exec-001"),
                _make_sample_entry("exec-002"),
            ]
            new_content = _build_valid_ledger(all_entries_raw)

            r = _run_ledger_guard(str(root), {
                "tool_name": "Write",
                "file_path": str(ledger_path),
                "content": new_content,
            })
            assert r.returncode == 0, f"expected exit 0, got {r.returncode}: {r.stderr}"

    # ── Scenario 2: Edit tool on ledger file is blocked (exit 2) ──

    def test_edit_tool_blocked(self):
        """Edit tool on a ledger file should always be blocked."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ledger_dir = root / ".ai" / "ledger"
            ledger_dir.mkdir(parents=True)

            existing_content = _build_valid_ledger([_make_sample_entry("exec-001")])
            ledger_path = ledger_dir / "executions.jsonl"
            ledger_path.write_text(existing_content, encoding="utf-8")

            r = _run_ledger_guard(str(root), {
                "tool_name": "Edit",
                "file_path": str(ledger_path),
                "old_string": "exec-001",
                "new_string": "exec-HACKED",
            })
            assert r.returncode == 2, f"expected exit 2, got {r.returncode}"
            assert "Edit" in r.stderr

    # ── Scenario 3: Truncation/overwrite is blocked (exit 2) ──

    def test_truncation_blocked(self):
        """Writing shorter content than existing (truncation) should be blocked."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ledger_dir = root / ".ai" / "ledger"
            ledger_dir.mkdir(parents=True)

            existing_content = _build_valid_ledger([
                _make_sample_entry("exec-001"),
                _make_sample_entry("exec-002"),
            ])
            ledger_path = ledger_dir / "executions.jsonl"
            ledger_path.write_text(existing_content, encoding="utf-8")

            # Write only one entry (shorter than existing two)
            new_content = _build_valid_ledger([_make_sample_entry("exec-001")])

            r = _run_ledger_guard(str(root), {
                "tool_name": "Write",
                "file_path": str(ledger_path),
                "content": new_content,
            })
            assert r.returncode == 2, f"expected exit 2, got {r.returncode}"
            assert "truncation" in r.stderr.lower() or "overwrite" in r.stderr.lower()

    # ── Scenario 4: Non-append write is blocked (exit 2) ──

    def test_non_append_write_blocked(self):
        """Writing content that does not preserve existing lines should be blocked."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ledger_dir = root / ".ai" / "ledger"
            ledger_dir.mkdir(parents=True)

            existing_content = _build_valid_ledger([_make_sample_entry("exec-001")])
            ledger_path = ledger_dir / "executions.jsonl"
            ledger_path.write_text(existing_content, encoding="utf-8")

            # Build content that starts differently (same length, different prefix)
            tampered_content = _build_valid_ledger([_make_sample_entry("exec-HACKED")])

            r = _run_ledger_guard(str(root), {
                "tool_name": "Write",
                "file_path": str(ledger_path),
                "content": tampered_content,
            })
            assert r.returncode == 2, f"expected exit 2, got {r.returncode}"
            assert "non-append" in r.stderr.lower() or "append" in r.stderr.lower()

    # ── Scenario 5: Broken chain_hash in write content is blocked (exit 2) ──

    def test_broken_chain_hash_blocked(self):
        """Content with an invalid chain_hash should be blocked."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ledger_dir = root / ".ai" / "ledger"
            ledger_dir.mkdir(parents=True)

            # Create existing ledger with one valid entry
            existing_content = _build_valid_ledger([_make_sample_entry("exec-001")])
            ledger_path = ledger_dir / "executions.jsonl"
            ledger_path.write_text(existing_content, encoding="utf-8")

            # Build content that looks like an append but has wrong chain_hash
            # Re-use existing line but add a second line with intentionally wrong hash
            entry2 = _make_sample_entry("exec-002")
            row_json = json.dumps(entry2, sort_keys=True, ensure_ascii=False)
            entry2_bad = dict(entry2)
            entry2_bad["chain_hash"] = "0" * 64  # deliberately wrong
            bad_line = json.dumps(entry2_bad, sort_keys=True, ensure_ascii=False)
            bad_content = existing_content.rstrip("\n") + "\n" + bad_line + "\n"

            r = _run_ledger_guard(str(root), {
                "tool_name": "Write",
                "file_path": str(ledger_path),
                "content": bad_content,
            })
            assert r.returncode == 2, f"expected exit 2, got {r.returncode}"
            assert "chain" in r.stderr.lower()

    # ── Scenario 6: Empty/non-existent ledger accepts first write (exit 0) ──

    def test_first_write_to_empty_ledger_passes(self):
        """Writing to a non-existent ledger file for the first time should pass."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ledger_dir = root / ".ai" / "ledger"
            ledger_dir.mkdir(parents=True)
            # Do NOT create executions.jsonl — it doesn't exist yet
            ledger_path = ledger_dir / "executions.jsonl"

            new_content = _build_valid_ledger([_make_sample_entry("exec-001")])

            r = _run_ledger_guard(str(root), {
                "tool_name": "Write",
                "file_path": str(ledger_path),
                "content": new_content,
            })
            assert r.returncode == 0, f"expected exit 0, got {r.returncode}: {r.stderr}"

    # ── Scenario 7: Internal exception fails open (exit 0) ──

    def test_internal_exception_fails_open(self):
        """Malformed stdin JSON should trigger internal exception -> fail-open (exit 0)."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ledger_dir = root / ".ai" / "ledger"
            ledger_dir.mkdir(parents=True)
            ledger_path = ledger_dir / "executions.jsonl"
            ledger_path.write_text("", encoding="utf-8")

            env = {**os.environ, "ZCODE_PROJECT_DIR": str(root)}
            # Send malformed JSON (not valid JSON at all)
            r = subprocess.run(
                [sys.executable, LEDGER_GUARD],
                input="this is not valid json {{{",  # malformed stdin
                capture_output=True, text=True, timeout=10, env=env,
            )
            assert r.returncode == 0, f"expected fail-open exit 0, got {r.returncode}"

    # ── Scenario 8: Non-ledger file passes through (exit 0) ──

    def test_non_ledger_file_passes_through(self):
        """Writing to a non-ledger file should pass through without blocking."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            src_dir = root / "src"
            src_dir.mkdir(parents=True)
            normal_file = src_dir / "app.py"

            r = _run_ledger_guard(str(root), {
                "tool_name": "Write",
                "file_path": str(normal_file),
                "content": "print('hello world')\n",
            })
            assert r.returncode == 0, f"expected exit 0, got {r.returncode}: {r.stderr}"
