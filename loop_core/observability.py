"""
Observability — layered guard-check event recording (T-0089 U8).

StaffDeck 对标 (backend/app/observability/: event_log.py + spans.py +
runtime_logging.py — "Observability must never turn a successful business
request into a failure") applied to loop-engine guard checks:

- Event layer: one GuardCheckEvent per guard check (health control run,
  per-guard death verdict, missing/drift REPORT finding, three-way integrity
  verdict), appended to .ai/evidence/observability/guard-events.jsonl
  (append-only — one JSON object per line, history is never rewritten).
  The span/log layers of the StaffDeck split are out of scope for U8 and are
  noted in .ai/evidence/T-0089/observability/design.md.
- Never blocks business: every write is wrapped in try/except — a failing
  observation is counted in-memory (recorder.failures / last_error) and
  logged, then execution continues.  The guard health run, and any business
  call site, never sees an observation exception.
- Safety adjudication untouched: this module is a side-channel recorder only.
  EnforcementHub/HardConstraints BLOCK/PASS semantics have zero dependency on
  it — the only consumer wiring is loop_core.guard_health (health checks are
  the observed business, the observation is the旁路记录).
"""
from __future__ import annotations

import json
import logging
import os
import uuid
from collections import Counter
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# ── Check types recorded by the guard health subsystem ─────────────────────
CHECK_HEALTH = "health"        # one positive/negative control execution
CHECK_DEATH = "death"          # per-guard verdict (ALIVE/DORMANT/BROKEN)
CHECK_MISSING = "missing"      # unregistered implementation file (REPORT)
CHECK_DRIFT = "drift"          # registered binding drifted from disk (REPORT)
CHECK_INTEGRITY = "integrity"  # overall three-way integrity verdict
# T-0111: 修复器触发点事件（validate_state REPAIR_MODE / close_session 收尾
# 动态修复写入；PASS = repair 后重新校验通过，FAIL = 修复失败/无物可修）。
# 枚举向后兼容：既有消费者只按已知 check_type 过滤，未知类型不影响其判定。
CHECK_REPAIR = "repair"        # continuity auto-repair trigger (T-0111)

# ── Event results ──────────────────────────────────────────────────────────
RESULT_PASS = "PASS"      # guard behaved as expected / verdict healthy
RESULT_FAIL = "FAIL"      # guard misbehaved / verdict unhealthy (failure_reason set)
RESULT_REPORT = "REPORT"  # informative finding — never flips any verdict

DEFAULT_EVENT_PATH = ".ai/evidence/observability/guard-events.jsonl"

# T-0095 rotation defaults: rotate when the event file reaches 10k lines or
# 10 MB; keep the 3 most recent archives (.1 newest, .3 oldest).
DEFAULT_MAX_LINES = 10000
DEFAULT_MAX_BYTES = 10 * 1024 * 1024
DEFAULT_MAX_ARCHIVES = 3


@dataclass(frozen=True)
class GuardCheckEvent:
    """One guard check observation — append-only recorded, never blocks."""
    guard_id: str                       # guard name (hook basename) or asset path
    check_type: str                     # health | death | missing | drift | integrity
    result: str                         # PASS | FAIL | REPORT
    duration_ms: float                  # wall-clock duration of the check
    timestamp: str                      # ISO-8601 UTC
    source: str                         # registry fingerprint the check ran against
    capability_id: str | None = None
    failure_reason: str | None = None
    event_id: str = field(default_factory=lambda: uuid.uuid4().hex[:16])

    def to_dict(self) -> dict[str, Any]:
        """Deterministic serialization for the JSONL line."""
        return {
            "event_id": self.event_id,
            "guard_id": self.guard_id,
            "capability_id": self.capability_id,
            "check_type": self.check_type,
            "result": self.result,
            "duration_ms": round(self.duration_ms, 3),
            "failure_reason": self.failure_reason,
            "timestamp": self.timestamp,
            "source": self.source,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> GuardCheckEvent:
        return cls(
            event_id=str(data.get("event_id", "")),
            guard_id=str(data.get("guard_id", "")),
            capability_id=data.get("capability_id"),
            check_type=str(data.get("check_type", "")),
            result=str(data.get("result", "")),
            duration_ms=float(data.get("duration_ms", 0.0) or 0.0),
            failure_reason=data.get("failure_reason"),
            timestamp=str(data.get("timestamp", "")),
            source=str(data.get("source", "")),
        )


class GuardEventRecorder:
    """Append-only JSONL recorder for guard check events (side channel).

    - Construction is inert: no filesystem access until the first record().
    - record() NEVER raises: a write failure is counted in `failures` /
      `last_error` and logged — the business path continues (StaffDeck rule:
      observability must never turn a successful request into a failure).
    - `enabled` can be toggled at runtime; a disabled recorder is a no-op and
      creates no file (switchable observation, default ON).
    - T-0095 rotation: when the event file reaches ``max_lines`` lines or
      ``max_bytes`` bytes, it is archived before the next append:
      ``guard-events.jsonl`` -> ``guard-events.jsonl.1``, ``.1`` -> ``.2``,
      ... keeping the most recent ``max_archives`` archives (older archives
      are dropped).  History is never lost while an archive slot remains:
      ``read_events`` reads the main file plus every retained archive.
      Rotation is best-effort and never raises — a failed rotation simply
      leaves the oversized file in place and the append proceeds.
    """

    def __init__(
        self,
        path: str | Path | None = None,
        enabled: bool = True,
        *,
        max_lines: int = DEFAULT_MAX_LINES,
        max_bytes: int = DEFAULT_MAX_BYTES,
        max_archives: int = DEFAULT_MAX_ARCHIVES,
    ):
        self._path = Path(path) if path is not None else Path(DEFAULT_EVENT_PATH)
        self.enabled = enabled
        self.failures = 0
        self.last_error: str | None = None
        self.max_lines = max_lines
        self.max_bytes = max_bytes
        self.max_archives = max_archives
        # T-0111 D4-6: 读侧损坏行计数（与写侧 failures 对称）——读历史时
        # 损坏行不再静默丢弃，逐行计数 + warning，并在 summary() 上报。
        self.read_corrupt_lines = 0

    @property
    def path(self) -> Path:
        return self._path

    def set_enabled(self, enabled: bool) -> None:
        self.enabled = enabled

    def record(self, event: GuardCheckEvent) -> bool:
        """Persist one event.  Returns True on success, False on a swallowed
        observation failure.  Never raises — observation must never block or
        break the business path."""
        if not self.enabled:
            return False
        try:
            line = json.dumps(event.to_dict(), ensure_ascii=False) + "\n"
            self._append_line(line)
            return True
        except Exception as e:  # noqa: BLE001 — observation failures are swallowed by design
            self.failures += 1
            self.last_error = f"{type(e).__name__}: {e}"
            logger.warning(
                "guard observability write failed (business continues): %s",
                self.last_error,
            )
            return False

    def _rotate_if_needed(self) -> None:
        """Archive the event file once it reaches the line/byte threshold.

        Best-effort only: any failure leaves the file untouched and is
        swallowed (the append still proceeds — observation never blocks).
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

    def _append_line(self, line: str) -> None:
        """Raw append — isolated so tests can force a write failure."""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._rotate_if_needed()
        with open(self._path, "a", encoding="utf-8") as f:
            f.write(line)

    def _read_file(self, path: Path) -> list[GuardCheckEvent]:
        """Read one event file.

        T-0111 D4-6: corrupt lines are counted (``read_corrupt_lines``) and
        logged, then skipped — a corrupt line must neither hide the readable
        prefix nor the readable suffix, and the count is surfaced in
        ``summary()`` instead of being silently dropped (读侧 warning/计数
        对称，与写侧 failures/last_error 同语义）。"""
        events: list[GuardCheckEvent] = []
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            return events
        for line in text.splitlines():
            if not line.strip():
                continue
            try:
                events.append(GuardCheckEvent.from_dict(json.loads(line)))
            except (json.JSONDecodeError, ValueError):
                self.read_corrupt_lines += 1
                logger.warning(
                    "guard-events corrupt line skipped (counted): %s", path
                )
        return events

    def read_events(self) -> list[GuardCheckEvent]:
        """Read the recorded history back — main file plus retained rotation
        archives (oldest first, so the returned order is chronological).
        Read-only — never modifies any file."""
        events: list[GuardCheckEvent] = []
        for index in range(self.max_archives, 0, -1):
            archive = Path(f"{self._path}.{index}")
            if archive.exists():
                events.extend(self._read_file(archive))
        if self._path.exists():
            events.extend(self._read_file(self._path))
        return events

    def summary(self) -> dict[str, Any]:
        """Aggregate query: per guard / per result — frequency, duration,
        failure counts (plus observation-layer failure counts)."""
        events = self.read_events()
        by_guard: dict[str, dict[str, Any]] = {}
        by_result: Counter[str] = Counter()
        for e in events:
            by_result[e.result] += 1
            g = by_guard.setdefault(e.guard_id, {
                "total": 0,
                "results": Counter(),
                "failures": 0,
                "duration_ms_total": 0.0,
                "duration_ms_max": 0.0,
            })
            g["total"] += 1
            g["results"][e.result] += 1
            g["duration_ms_total"] += e.duration_ms
            g["duration_ms_max"] = max(g["duration_ms_max"], e.duration_ms)
            if e.result == RESULT_FAIL:
                g["failures"] += 1
        aggregated: dict[str, Any] = {}
        for gid, g in sorted(by_guard.items()):
            count = max(g["total"], 1)
            aggregated[gid] = {
                "total": g["total"],
                "results": dict(g["results"]),
                "failures": g["failures"],
                "duration_ms": {
                    "total": round(g["duration_ms_total"], 3),
                    "avg": round(g["duration_ms_total"] / count, 3),
                    "max": round(g["duration_ms_max"], 3),
                },
            }
        return {
            "total_events": len(events),
            "by_guard": aggregated,
            "by_result": dict(by_result),
            "observability_failures": self.failures,
            # T-0111 D4-6: 读侧损坏行计数（非零时表明事件文件有行被跳过）
            "read_corrupt_lines": self.read_corrupt_lines,
        }
