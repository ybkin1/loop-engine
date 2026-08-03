"""
Audit Ledger — Chain-hashed append-only JSONL audit log (v3.4).

Every entry:
- Is appended to .ai/audit_ledger.jsonl
- Contains the SHA256 hash of the previous entry (chain integrity)
- Records event type, actor, timestamp, and structured details

Verification detects tampering by walking the chain and comparing hashes.
Pattern adapted from Qoder's AuditLedger + ZCode's execution_ledger.

T-0107 fixes:
- D3-1: 追加前按行数/字节阈值轮转，保留 N 份归档（.1~.N，与
  observability 同一策略）；轮转不破坏链哈希——_load 按"归档（旧→新）→
  主文件"顺序读入，链哈希跨文件延续，verify_integrity 依然完整校验。
- D4-5: 损坏行不再静默跳过——逐行计数并告警（corrupt_line_count /
  AuditIntegrity.corrupt_lines），verify 可区分"已清理"与"被篡改"。
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# T-0107 D3-1: 轮转阈值（对齐 observability 的 10k 行 / 10MB / 3 档归档）
DEFAULT_MAX_LINES = 10_000
DEFAULT_MAX_BYTES = 10 * 1024 * 1024
DEFAULT_MAX_ARCHIVES = 3


@dataclass
class AuditEntry:
    """A single audit log entry with chain hash."""
    seq: int
    timestamp: str
    event: str           # e.g., "gate_advance", "role_activate", "veto", "handoff"
    actor: str           # role_id or "system"
    details: dict[str, Any] = field(default_factory=dict)
    chain_hash: str = ""  # SHA256 of previous entry's JSON


@dataclass
class AuditIntegrity:
    """Result of verifying the audit ledger chain."""
    valid: bool
    total_entries: int
    first_invalid_seq: int | None = None
    message: str = ""
    corrupt_lines: int = 0  # T-0107 D4-5: 加载时跳过的损坏行数（0 = 无）


class AuditLedger:
    """Chain-hashed append-only JSONL audit log."""

    def __init__(
        self,
        filepath: str | Path,
        *,
        max_lines: int = DEFAULT_MAX_LINES,
        max_bytes: int = DEFAULT_MAX_BYTES,
        max_archives: int = DEFAULT_MAX_ARCHIVES,
    ):
        self._path = Path(filepath)
        self._entries: list[AuditEntry] = []
        self._corrupt_lines: list[int] = []  # T-0107 D4-5: 损坏行行号（1-based）
        self.max_lines = max_lines
        self.max_bytes = max_bytes
        self.max_archives = max_archives
        self._load()

    @property
    def corrupt_line_count(self) -> int:
        """T-0107 D4-5: 加载时跳过的损坏行数（0 = 无损坏行）。

        verify_integrity 的调用方可借此区分"已清理的账本"（0）与
        "含被篡改/损坏行的账本"（>0）。
        """
        return len(self._corrupt_lines)

    @property
    def corrupt_lines(self) -> list[int]:
        """T-0107 D4-5: 损坏行行号（1-based，仅主文件内行号）。"""
        return list(self._corrupt_lines)

    # ── Load（含轮转归档）─────────────────────────────────────────────

    def _archive_paths(self) -> list[Path]:
        """归档路径列表（旧 → 新）：.N ... .2 .1。"""
        return [Path(f"{self._path}.{i}") for i in range(self.max_archives, 0, -1)]

    def _load(self) -> None:
        self._entries = []
        self._corrupt_lines = []
        # 归档（旧→新）+ 主文件按序读入：链哈希跨文件延续，verify 可校验。
        for path in self._archive_paths():
            self._load_file(path)
        self._load_file(self._path)

    def _load_file(self, path: Path) -> None:
        if not path.exists():
            return
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except OSError as exc:
            logger.warning("audit_ledger: 读取 %s 失败: %s", path, exc)
            return
        for idx, line in enumerate(lines, start=1):
            if not line.strip():
                continue
            try:
                data = json.loads(line)
                if not isinstance(data, dict):
                    raise ValueError("entry must be a JSON object")
                self._entries.append(AuditEntry(**data))
            except (json.JSONDecodeError, TypeError, ValueError, KeyError) as exc:
                # T-0107 D4-5: 损坏行计数 + 告警（was 静默跳过整个文件）
                self._corrupt_lines.append(idx)
                logger.warning(
                    "audit_ledger: %s 第 %d 行损坏跳过（%s）；"
                    "corrupt_line_count=%d（区分已清理与被篡改）",
                    path.name, idx, exc, len(self._corrupt_lines),
                )

    @property
    def length(self) -> int:
        return len(self._entries)

    # ── Append（含轮转）───────────────────────────────────────────────

    def append(self, event: str, actor: str, details: dict[str, Any] | None = None) -> AuditEntry:
        """Append a new entry with chain hash."""
        prev_hash = ""
        if self._entries:
            prev_json = json.dumps(self._entries[-1].__dict__, sort_keys=True, ensure_ascii=False)
            prev_hash = hashlib.sha256(prev_json.encode()).hexdigest()

        entry = AuditEntry(
            seq=len(self._entries),
            timestamp=datetime.now(timezone.utc).isoformat(),
            event=event,
            actor=actor,
            details=details or {},
            chain_hash=prev_hash,
        )

        self._entries.append(entry)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        line = json.dumps(entry.__dict__, ensure_ascii=False) + "\n"
        # T-0107 D3-1: 达到行/字节阈值先轮转再追加（best-effort）
        self._rotate_if_needed()
        with open(self._path, "a", encoding="utf-8") as f:
            f.write(line)

        return entry

    def _rotate_if_needed(self) -> None:
        """T-0107 D3-1: 主文件达到行/字节阈值时归档轮转（保留 N 份）。

        Best-effort：任何失败保持文件原样（append 继续，审计不因轮转失败
        中断）。轮转保留链哈希连续性——最后一个归档的末条与主文件首条
        前后衔接，_load 按序读入后 verify 依然通过。
        """
        if not self._path.exists():
            return
        try:
            size = self._path.stat().st_size
            lines = 0
            if size < self.max_bytes:
                with open(self._path, "rb") as f:
                    lines = sum(1 for _ in f)
            if lines < self.max_lines and size < self.max_bytes:
                return
        except OSError:
            return
        for index in range(self.max_archives - 1, 0, -1):
            src = Path(f"{self._path}.{index}")
            dst = Path(f"{self._path}.{index + 1}")
            if src.exists():
                try:
                    os.replace(src, dst)
                except OSError:
                    pass
        try:
            os.replace(self._path, Path(f"{self._path}.1"))
        except OSError:
            pass

    # ── Verify ─────────────────────────────────────────────────────────

    def verify_integrity(self) -> AuditIntegrity:
        """Verify chain integrity by recomputing all hashes."""
        if not self._entries:
            return AuditIntegrity(
                valid=True, total_entries=0,
                corrupt_lines=self.corrupt_line_count,
                message="Empty ledger",
            )

        prev_hash = ""
        for i, entry in enumerate(self._entries):
            expected_hash = entry.chain_hash
            if expected_hash != prev_hash:
                return AuditIntegrity(
                    valid=False,
                    total_entries=len(self._entries),
                    first_invalid_seq=i,
                    corrupt_lines=self.corrupt_line_count,
                    message=f"Chain broken at seq {i}: expected {prev_hash[:12]}..., got {expected_hash[:12]}...",
                )
            entry_json = json.dumps(entry.__dict__, sort_keys=True, ensure_ascii=False)
            prev_hash = hashlib.sha256(entry_json.encode()).hexdigest()

        if self._corrupt_lines:
            message = (
                f"All {len(self._entries)} entries verified; "
                f"{len(self._corrupt_lines)} corrupt line(s) skipped during load "
                f"(lines: {self._corrupt_lines[:5]})"
            )
        else:
            message = f"All {len(self._entries)} entries verified"
        return AuditIntegrity(
            valid=True,
            total_entries=len(self._entries),
            corrupt_lines=self.corrupt_line_count,
            message=message,
        )

    def recent(self, n: int = 10) -> list[AuditEntry]:
        return self._entries[-n:] if self._entries else []
