"""
Execution Ledger — 链式 hash 追加写 Agent 执行账本。

设计原则：
  - JSONL 格式，每行一个执行记录，物理追加（不修改已有行）
  - 每条记录的 chain_hash = SHA256(上一条.chain_hash || 本条数据)
  - 链完整 → 整个账本不可篡改；改任何一行 → chain_hash 断裂 → 可检测
  - Hook 负责强制校验：只允许 append，chain_hash 必须连续
  - cross_validate() 直接读取账本比对 Dev vs Reviewer，不靠 Agent 自报

文件：.ai/ledger/executions.jsonl
"""
from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any


class ExecutionStatus(str, Enum):
    LAUNCHED = "LAUNCHED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    VIOLATED = "VIOLATED"


@dataclass
class ExecutionRecord:
    """单条 Agent 执行记录。chain_hash 由 Ledger 管理，不在此结构体中。"""

    execution_id: str
    session_id: str
    actor_id: str
    role_id: str
    task_id: str
    prompt_fingerprint: str
    input_files_hash: str
    status: ExecutionStatus
    launched_at: str
    completed_at: str | None = None
    exit_code: int | None = None
    output_hash: str | None = None
    tool_constraints: list[str] = field(default_factory=list)
    tool_violations: list[str] = field(default_factory=list)
    cross_references: list[dict[str, str]] = field(default_factory=list)

    def to_json_row(self) -> str:
        return json.dumps({
            "execution_id": self.execution_id,
            "session_id": self.session_id,
            "actor_id": self.actor_id,
            "role_id": self.role_id,
            "task_id": self.task_id,
            "prompt_fingerprint": self.prompt_fingerprint,
            "input_files_hash": self.input_files_hash,
            "status": self.status.value,
            "launched_at": self.launched_at,
            "completed_at": self.completed_at,
            "exit_code": self.exit_code,
            "output_hash": self.output_hash,
            "tool_constraints": self.tool_constraints,
            "tool_violations": self.tool_violations,
            "cross_references": self.cross_references,
        }, sort_keys=True, ensure_ascii=False)

    @classmethod
    def from_json_row(cls, data: dict[str, Any]) -> ExecutionRecord:
        return cls(
            execution_id=data["execution_id"],
            session_id=data["session_id"],
            actor_id=data["actor_id"],
            role_id=data["role_id"],
            task_id=data["task_id"],
            prompt_fingerprint=data["prompt_fingerprint"],
            input_files_hash=data["input_files_hash"],
            status=ExecutionStatus(data["status"]),
            launched_at=data["launched_at"],
            completed_at=data.get("completed_at"),
            exit_code=data.get("exit_code"),
            output_hash=data.get("output_hash"),
            tool_constraints=data.get("tool_constraints", []),
            tool_violations=data.get("tool_violations", []),
            cross_references=data.get("cross_references", []),
        )


class ChainBrokenError(ValueError):
    def __init__(self, line_no: int, expected: str, actual: str):
        self.line_no = line_no
        self.expected = expected
        self.actual = actual
        super().__init__(
            f"CHAIN_BROKEN at line {line_no}: "
            f"expected {expected[:16]}..., got {actual[:16]}..."
        )


class ExecutionLedger:
    """Agent 执行账本：链式 hash、追加写、不可篡改。

    chain_hash = SHA256(上一条.chain_hash || 本条 JSON 行)
    改任何一行 → 后续 chain_hash 全部断裂 → Hook 可以检测并阻断后续写入。

    自动 checkpoint：超过 _MAX_ENTRIES 条后，归档旧文件并重置。
    """

    CHAIN_HASH_KEY = "chain_hash"
    _ROOT_SEED = b"LOOP_ENGINE_EXECUTION_LEDGER_V1_ROOT"
    _MAX_ENTRIES = 200  # 超过此数自动归档重置

    def __init__(self, project_root: Path | str):
        self._root = Path(project_root)
        self._ledger_path = self._root / ".ai" / "ledger" / "executions.jsonl"

    @property
    def exists(self) -> bool:
        return self._ledger_path.exists()

    def _ensure_dir(self) -> None:
        self._ledger_path.parent.mkdir(parents=True, exist_ok=True)

    # ── 读取 ──────────────────────────────────────────────────────────

    def read_all(self) -> list[dict[str, Any]]:
        if not self.exists:
            return []
        entries: list[dict[str, Any]] = []
        with open(self._ledger_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                entries.append(json.loads(line))
        return entries

    def read_records(self) -> list[ExecutionRecord]:
        return [ExecutionRecord.from_json_row(e) for e in self.read_all()]

    def _root_hash(self) -> str:
        return hashlib.sha256(self._ROOT_SEED).hexdigest()

    def _last_chain_hash(self) -> str:
        entries = self.read_all()
        if entries:
            return entries[-1][self.CHAIN_HASH_KEY]
        return self._root_hash()

    def _compute_chain_hash(self, prev_hash: str, row_json: str) -> str:
        return hashlib.sha256(
            prev_hash.encode() + row_json.encode("utf-8")
        ).hexdigest()

    # ── 写入 ──────────────────────────────────────────────────────────

    def append_entry(self, record: ExecutionRecord) -> str:
        """追加一条执行记录。返回 chain_hash。物理追加（open("a")），不改已有行。"""
        self._ensure_dir()
        row_json = record.to_json_row()
        prev = self._last_chain_hash()
        ch = self._compute_chain_hash(prev, row_json)

        row_data = json.loads(row_json)
        row_data[self.CHAIN_HASH_KEY] = ch
        full = json.dumps(row_data, sort_keys=True, ensure_ascii=False)

        with open(self._ledger_path, "a", encoding="utf-8") as f:
            f.write(full + "\n")
            f.flush()
            os.fsync(f.fileno())

        # 自动 checkpoint：超过阈值后归档旧文件，重置链
        self._auto_checkpoint()
        return ch

    def _auto_checkpoint(self) -> None:
        """超过 _MAX_ENTRIES 条后，归档旧文件并重置。"""
        entries = self.read_all()
        if len(entries) < self._MAX_ENTRIES:
            return

        now = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
        archive_path = self._ledger_path.with_suffix(f".{now}.jsonl")
        self._ledger_path.rename(archive_path)
        # 新文件从空开始，链自动重置为 root_hash

    def record_launch(self, record: ExecutionRecord) -> str:
        if record.status != ExecutionStatus.LAUNCHED:
            raise ValueError(f"record_launch expects LAUNCHED, got {record.status.value}")
        return self.append_entry(record)

    def record_completion(
        self,
        execution_id: str,
        status: ExecutionStatus,
        exit_code: int = 0,
        output_hash: str | None = None,
        tool_violations: list[str] | None = None,
    ) -> str:
        launched = self.find_by_execution_id(execution_id)
        if launched is None:
            raise ValueError(f"No LAUNCHED entry for execution_id={execution_id}")

        close = ExecutionRecord(
            execution_id=execution_id,
            session_id=launched.session_id,
            actor_id=launched.actor_id,
            role_id=launched.role_id,
            task_id=launched.task_id,
            prompt_fingerprint=launched.prompt_fingerprint,
            input_files_hash=launched.input_files_hash,
            status=status,
            launched_at=launched.launched_at,
            completed_at=datetime.now(timezone.utc).isoformat(),
            exit_code=exit_code,
            output_hash=output_hash,
            tool_constraints=list(launched.tool_constraints),
            tool_violations=list(tool_violations or []),
            cross_references=list(launched.cross_references),
        )
        return self.append_entry(close)

    # ── 查询 ──────────────────────────────────────────────────────────

    def find_by_execution_id(self, execution_id: str) -> ExecutionRecord | None:
        for r in self.read_records():
            if r.execution_id == execution_id:
                return r
        return None

    def find_by_task(self, task_id: str) -> list[ExecutionRecord]:
        return [r for r in self.read_records() if r.task_id == task_id]

    def find_by_role(self, task_id: str, role_id: str) -> list[ExecutionRecord]:
        return [
            r for r in self.read_records()
            if r.task_id == task_id and r.role_id == role_id
        ]

    # ── 验证 ──────────────────────────────────────────────────────────

    def verify_chain(self) -> tuple[bool, str]:
        """验证全链 hash。返回 (valid, reason)。"""
        entries = self.read_all()
        if not entries:
            return True, "empty ledger"

        prev = self._root_hash()
        for i, entry in enumerate(entries, 1):
            stored = entry.pop(self.CHAIN_HASH_KEY, None)
            if stored is None:
                return False, f"line {i}: missing chain_hash"
            row_json = json.dumps(entry, sort_keys=True, ensure_ascii=False)
            computed = self._compute_chain_hash(prev, row_json)
            if computed != stored:
                return False, (
                    f"line {i}: mismatch — "
                    f"computed {computed[:16]}..., stored {stored[:16]}..."
                )
            prev = stored
        return True, f"chain verified ({len(entries)} entries)"

    def cross_validate(self, task_id: str) -> dict[str, Any]:
        """跨 Agent 校验 Dev vs Reviewer。从账本读取，不靠 Agent 自报。"""
        devs = self.find_by_role(task_id, "developer")
        revs = self.find_by_role(task_id, "independent-reviewer")

        result: dict[str, Any] = {
            "valid": True,
            "developer_actor_id": None,
            "reviewer_actor_id": None,
            "actors_differ": False,
            "fingerprints_differ": False,
            "violations": [],
        }

        if not devs:
            result["valid"] = False
            result["violations"].append("No developer record")
        else:
            result["developer_actor_id"] = devs[-1].actor_id

        if not revs:
            result["valid"] = False
            result["violations"].append("No reviewer record")
        else:
            result["reviewer_actor_id"] = revs[-1].actor_id

        if devs and revs:
            d, r = devs[-1], revs[-1]
            result["actors_differ"] = d.actor_id != r.actor_id
            if not result["actors_differ"]:
                result["valid"] = False
                result["violations"].append(
                    "Same actor_id for dev and reviewer — not independent"
                )
            result["fingerprints_differ"] = (
                d.prompt_fingerprint != r.prompt_fingerprint
            )
            if not result["fingerprints_differ"]:
                result["violations"].append(
                    "Identical fingerprints — input freeze may have failed"
                )
        return result
