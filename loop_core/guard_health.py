"""
Guard Health Check — verifies that governance guards are ALIVE and EFFECTIVE.

The T-0082 audit proved guards can die silently (bash_content_guard 100% dead,
content_guard crashed at startup) while the test suite stayed green. This
subsystem runs a fixed battery of positive/negative control operations against
the guard chain and reports per-guard health.

- Negative controls MUST be blocked (guard denies the violation).
- Positive controls MUST be allowed (guard does not over-block).
- A guard that blocks zero negative controls is flagged DORMANT.
- A guard that crashes (exception/exit!=0/import error) is flagged BROKEN.
- Any BROKEN or DORMANT guard makes the overall verdict FAIL (AC-05): a guard
  that blocks zero negative controls is a dead guard even if it does not crash.

T-0087 U1: three-way integrity. Death (above) stays FAIL-CLOSED; the capability
registry (loop_core.capability_registry) adds two REPORT-level detections that
never block:
- MISSING: an implementation file exists in .ai/checkers/ or .ai/guards/ but is
  not registered in the capability registry (omitted governance asset).
- DRIFT: a registered implementation's file hash/version no longer matches the
  binding recorded at registration time.
integrity_check() combines all three; the overall verdict is driven by death
only — missing/drift are surfaced as reports, never as a silent pass-through.
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from loop_core.capability_registry import (
    CapabilityRegistry,
    build_default_registry,
    sha256_file,
)
from loop_core.observability import (
    CHECK_DEATH,
    CHECK_DRIFT,
    CHECK_HEALTH,
    CHECK_INTEGRITY,
    CHECK_MISSING,
    CHECK_RECOMPUTE,
    RESULT_FAIL,
    RESULT_PASS,
    RESULT_REPORT,
    GuardCheckEvent,
    GuardEventRecorder,
)

# T-0089 U8: guard-check observability — side-channel event recording that
# never blocks the health check (observability failures are swallowed by the
# recorder; the safety adjudication in enforcement_hub/hard_constraints has
# zero dependency on it).

# ── Guard registry: which guard owns which negative control ──
# Each guard declares which fixture it must kill. Zero kills = DORMANT.

@dataclass
class GuardControl:
    """One positive/negative control operation against a guard."""
    control_id: str
    guard: str            # guard name (hook script basename)
    description: str
    kind: str             # "negative" (must block) | "positive" (must pass)
    tool_input: dict      # simulated PreToolUse tool_input
    expect_block: bool    # True = guard must deny
    # Optional fixture project: rel_path -> file content. When set, the runner
    # materializes a temporary project directory, writes the fixture files, and
    # runs the hook script with cwd=fixture_dir so the guard evaluates against
    # the fixture state (e.g. a pending gate) instead of the real governance
    # state of the repository.
    fixture: dict | None = None

@dataclass
class GuardHealthResult:
    guard: str
    status: str           # ALIVE | DORMANT | BROKEN | NOT_VERIFIED
    blocked: int          # negative controls blocked
    negative_total: int
    allowed: int          # positive controls allowed
    positive_total: int
    errors: list[str] = field(default_factory=list)
    checked_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict:
        return {
            "guard": self.guard,
            "status": self.status,
            "blocked": self.blocked,
            "negative_total": self.negative_total,
            "allowed": self.allowed,
            "positive_total": self.positive_total,
            "errors": self.errors,
            "checked_at": self.checked_at,
        }


class GuardHealth:
    """Runs the fixture battery against the live hook chain.

    registry: injected capability registry (default: build_default_registry for
    the project root) — the baseline for missing/drift detection.
    """

    def __init__(self, project_root: str | Path,
                 registry: CapabilityRegistry | None = None,
                 observability: GuardEventRecorder | bool | None = None):
        self.root = Path(project_root).resolve()
        self.hooks_dir = self.root / "hooks" / "scripts"
        self.registry = registry if registry is not None else build_default_registry(self.root)
        # T-0089 U8: guard-check observability — a旁路 side-channel recorder,
        # default ON (writes .ai/evidence/observability/guard-events.jsonl,
        # lazily: no file is touched until the first event).  Pass
        # observability=False to disable, or a GuardEventRecorder to override
        # the default path.  Observation failures never reach this class's
        # callers — they are swallowed inside the recorder (_observe adds a
        # belt-and-braces guard).
        if observability is None:
            observability = GuardEventRecorder(
                self.root / ".ai" / "evidence" / "observability" / "guard-events.jsonl"
            )
        self.observability = observability

    # ── T-0089 U8: observation helpers (never raise into the business path) ──

    # T-0133 P3 / D-02 M4: 抽查复算默认比例（配置化；0.1 = 10% 报告被机器抽样复算）
    RECOMPUTE_RATE_DEFAULT = 0.1
    RECOMPUTE_EVENTS_PATH = ".ai/evidence/observability/recompute-events.jsonl"

    def run_sampled_recompute(self, reports: list[dict], task_id: str,
                              rate: float | None = None,
                              seed: int | None = None) -> int:
        """D-02 M4 抽样复算执行器。

        reports: [{report_ref, repro_command, repro_hash, repro_norm?}]；
        按 rate 抽样，对抽中报告执行 repro_command → 规范化输出（T-0144
        repro_norm 可选）→ 比对输出哈希 → 追加写 recompute-events.jsonl
        （{ts, task_id, report_ref, result}）。返回执行的复算次数。

        repro_norm（T-0144 4.3）: 报告可选声明规范化规则
        （["strip-timestamps", "strip-absolute-paths"]）——去耗时/绝对路径
        后哈希，保证同一逻辑输出的复算哈希稳定；未声明时保持原始哈希
        约定（向后兼容）。
        """
        import hashlib
        import random
        import re
        import subprocess
        rate = self.RECOMPUTE_RATE_DEFAULT if rate is None else float(rate)
        events_path = self.root / self.RECOMPUTE_EVENTS_PATH
        if rate >= 1.0 or not reports:
            sample = reports
        elif rate <= 0.0:
            sample = []
        else:
            rng = random.Random(seed)
            sample = rng.sample(reports, max(1, int(len(reports) * rate)))
        n_run = 0
        for rep in sample:
            cmd = rep.get("repro_command")
            expect = rep.get("repro_hash", "")
            if not cmd:
                # T-0143 4.1: 缺 repro_command 不得静默跳过——不可复算报告
                # 逃过复算 = fail-closed 漏洞；写 FAIL 事件让检测层可见。
                n_run += 1
                events_path.parent.mkdir(parents=True, exist_ok=True)
                with events_path.open("a", encoding="utf-8") as f:
                    f.write(json.dumps({
                        "ts": datetime.now(timezone.utc).isoformat(),
                        "task_id": task_id,
                        "report_ref": rep.get("report_ref", ""),
                        "result": "FAIL",
                        "reason": "missing repro_command (not recomputable)",
                    }) + "\n")
                continue
            try:
                proc = subprocess.run(
                    cmd, shell=True, capture_output=True, text=True,
                    timeout=60, cwd=str(self.root))
                output = proc.stdout + proc.stderr
                norm = rep.get("repro_norm") or []
                if norm:
                    output = self._normalize_output(output, norm)
                out_hash = hashlib.sha256(output.encode("utf-8")).hexdigest()
                result = "PASS" if out_hash == expect else "FAIL"
            except Exception:  # noqa: BLE001 — 复算失败 = FAIL（fail-safe）
                result = "FAIL"
            n_run += 1
            events_path.parent.mkdir(parents=True, exist_ok=True)
            with events_path.open("a", encoding="utf-8") as f:
                f.write(json.dumps({
                    "ts": datetime.now(timezone.utc).isoformat(),
                    "task_id": task_id,
                    "report_ref": rep.get("report_ref", ""),
                    "result": result,
                }) + "\n")
        return n_run

    # T-0144 4.3: repro_norm 规范化规则（D-02 M1 承诺落地）。
    # 支持规则：
    #   strip-timestamps   — ISO8601 时间戳 / epoch 秒 → <TS>（输出含耗时）
    #   strip-absolute-paths — 绝对路径 → <ABS>（输出含路径）
    # 未知规则忽略（向后兼容，不报错）。
    @staticmethod
    def _normalize_output(output: str, norm: list) -> str:
        import re as _re
        text = output
        if "strip-timestamps" in norm:
            # ISO8601（含 T/Z/时区偏移）与 epoch 秒（10/13 位）
            text = _re.sub(
                r"\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})?",
                "<TS>", text)
            text = _re.sub(r"\b\d{10}(?:\.\d+)?\b", "<TS>", text)
            text = _re.sub(r"\b\d{13}\b", "<TS>", text)
        if "strip-absolute-paths" in norm:
            # Windows 盘符路径 与 POSIX 绝对路径 → <ABS>
            text = _re.sub(r"[A-Za-z]:[\\/][^\s<>\"']+", "<ABS>", text)
            text = _re.sub(r"(?<![\w/])/[^\s<>\"']+(?:/[^\s<>\"']*)*", "<ABS>", text)
        return text

    def _registry_source(self) -> str:
        """Deterministic fingerprint of the registry the check runs against."""
        try:
            return f"registry:{self.registry.snapshot().snapshot_id[:12]}"
        except Exception:
            return "registry:unknown"

    def _observe(self, event: GuardCheckEvent) -> None:
        """Record one event.  The recorder already swallows write failures;
        this guard additionally ensures a bug in the observation layer can
        never reach the health-check (business) path."""
        try:
            if self.observability:
                self.observability.record(event)
        except Exception:  # pragma: no cover - belt-and-braces, record() never raises
            pass

    # ── The fixture battery ──
    def battery(self) -> list[GuardControl]:
        return [
            # gate_guard: pending-gate write must block — runs in an isolated
            # fixture project (the real repo has no pending gate, so the guard's
            # pending-block logic can only be exercised against fixture state).
            GuardControl("GC-001", "gate_guard", "pending gate blocks write",
                         "negative",
                         {"tool_name": "Write", "tool_input": {"file_path": ".ai/tasks/X.md"}}, True,
                         fixture={
                             ".ai/state.yaml": "current_gate_id: G-PENDING\ncurrent_task_id: T-X\ncurrent_phase: S1-requirements\nloop_mode: FULL\n",
                             ".ai/gates.yaml": "schema_version: 1\ngates:\n- id: G-PENDING\n  task_id: T-X\n  status: pending\n",
                         }),
            # gate_guard: approved gate allows write (positive control, same
            # fixture isolation) — must NOT over-block on an in-scope approved
            # gate. Target .ai/tasks/X.md is outside the decision-recording
            # exemption list, so the guard evaluates it normally.
            GuardControl("GC-008", "gate_guard", "approved gate allows write",
                         "positive",
                         {"tool_name": "Write", "tool_input": {"file_path": ".ai/tasks/X.md"}}, False,
                         fixture={
                             ".ai/state.yaml": "current_gate_id: G-APPROVED\ncurrent_task_id: T-X\ncurrent_phase: S1-requirements\nloop_mode: FULL\n",
                             ".ai/gates.yaml": "schema_version: 1\ngates:\n- id: G-APPROVED\n  task_id: T-X\n  status: approved\n  execution_status: in_progress\n",
                         }),
            # content_guard: hardcoded secret in write must block
            # NOTE: The fake secret is assembled at runtime via string
            # concatenation — it is never written literally in source, so the
            # security scanner rule SS-001 (hardcoded-secret regex) does not
            # flag this fixture. content_guard still receives the full
            # assembled value at runtime and must block it (negative control).
            GuardControl("GC-002", "content_guard", "secret in content blocks",
                         "negative",
                         {"tool_name": "Write", "tool_input": {"file_path": "tests/tmp_secret_test.py",
                          "content": 'password = "' + 'hunter2' + 'secret123"'}}, True),
            # content_guard: clean write passes
            # NOTE: content ends with "\n" — ruff W292 ("No newline at end of file")
            # would otherwise reject the fixture itself and fail the positive control
            # for a lint artifact, not a guard defect.
            GuardControl("GC-003", "content_guard", "clean content passes",
                         "positive",
                         {"tool_name": "Write", "tool_input": {"file_path": "tests/tmp_clean_test.py",
                          "content": "x = 1\n"}}, False),
            # bash_content_guard: redirect write must block
            GuardControl("GC-004", "bash_content_guard", "redirect write blocks",
                         "negative",
                         {"tool_name": "Bash", "tool_input": {"command": 'echo "evil" > tests/tmp_evil.txt'}}, True),
            # bash_content_guard: readonly passes
            GuardControl("GC-005", "bash_content_guard", "readonly command passes",
                         "positive",
                         {"tool_name": "Bash", "tool_input": {"command": "ls -la"}}, False),
            # ledger_guard: ledger edit must block
            GuardControl("GC-006", "ledger_guard", "ledger edit blocks",
                         "negative",
                         {"tool_name": "Edit", "tool_input": {"file_path": ".ai/ledger/executions.jsonl"}}, True),
            # path_guard: outside-root write blocks
            GuardControl("GC-007", "path_guard", "outside-root write blocks",
                         "negative",
                         {"tool_name": "Write", "tool_input": {"file_path": "C:/Windows/tmp/evil.py"}}, True),
        ]

    def run(self) -> list[GuardHealthResult]:
        """Run every control against the corresponding hook script via stdin simulation."""
        controls = self.battery()
        by_guard: dict[str, list[GuardControl]] = {}
        for c in controls:
            by_guard.setdefault(c.guard, []).append(c)

        results: list[GuardHealthResult] = []
        source = self._registry_source()
        for guard, ctrls in sorted(by_guard.items()):
            script = self.hooks_dir / f"{guard}.py"
            blocked = allowed = 0
            errors: list[str] = []
            crashed = False
            t_guard = time.perf_counter()
            for c in ctrls:
                t0 = time.perf_counter()
                rc: int | None = None
                control_error: str | None = None
                try:
                    # Simulate PreToolUse: pass hook_input JSON to script stdin.
                    # When the control carries a fixture, materialize an
                    # isolated temp project (write the fixture files), run the
                    # hook with cwd=fixture_dir, and point hook_input["cwd"] at
                    # the fixture dir so project_root() resolves to it.
                    if c.fixture:
                        with tempfile.TemporaryDirectory(prefix="guard_health_fixture_") as td:
                            td_path = Path(td)
                            for rel_path, content in c.fixture.items():
                                fp = td_path / rel_path
                                fp.parent.mkdir(parents=True, exist_ok=True)
                                fp.write_text(content, encoding="utf-8")
                            payload = json.dumps({
                                "tool_name": c.tool_input.get("tool_name", ""),
                                "tool_input": c.tool_input.get("tool_input", {}),
                                "cwd": str(td_path),
                            })
                            p = subprocess.run(
                                [sys.executable, str(script)],
                                input=payload, capture_output=True, text=True,
                                timeout=20, cwd=str(td_path),
                            )
                    else:
                        payload = json.dumps({
                            "tool_name": c.tool_input.get("tool_name", ""),
                            "tool_input": c.tool_input.get("tool_input", {}),
                            "cwd": str(self.root),
                        })
                        p = subprocess.run(
                            [sys.executable, str(script)],
                            input=payload, capture_output=True, text=True,
                            timeout=20,
                        )
                    rc = p.returncode
                    if rc not in (0, 2):
                        # Hooks contract is 0=allow / 2=deny; anything else means
                        # the hook script crashed (traceback, import error, ...).
                        crashed = True
                        control_error = (
                            f"{c.control_id} {c.description}: hook crashed (rc={rc})"
                        )
                        errors.append(control_error)
                    elif c.kind == "negative":
                        if rc == 2:
                            blocked += 1
                        else:
                            control_error = (
                                f"{c.control_id} {c.description}: expected BLOCK got pass (rc={rc})"
                            )
                            errors.append(control_error)
                    else:
                        if rc == 0:
                            allowed += 1
                        else:
                            control_error = (
                                f"{c.control_id} {c.description}: expected PASS got block (rc={rc})"
                            )
                            errors.append(control_error)
                except subprocess.TimeoutExpired:
                    crashed = True
                    control_error = f"{c.control_id}: TIMEOUT"
                    errors.append(control_error)
                except Exception as e:
                    crashed = True
                    control_error = f"{c.control_id}: ERROR {e}"
                    errors.append(control_error)
                finally:
                    # T-0089 U8: per-control health event (side channel — a
                    # recording failure never alters the control outcome above).
                    self._observe(GuardCheckEvent(
                        guard_id=guard,
                        check_type=CHECK_HEALTH,
                        result=RESULT_FAIL if control_error is not None else RESULT_PASS,
                        duration_ms=(time.perf_counter() - t0) * 1000,
                        failure_reason=control_error,
                        timestamp=datetime.now(timezone.utc).isoformat(),
                        source=source,
                    ))

            # Status determination:
            # - a crash (exception / timeout / unexpected exit code) => BROKEN
            # - ran cleanly but blocked zero negative controls => DORMANT
            #   (a guard that simply doesn't fire is a dead guard, even if the
            #   process exits 0 — exactly the T-0082 bash_content_guard failure)
            # - ran and blocked something, but a control misbehaved => BROKEN
            if crashed:
                status = "BROKEN"
            elif blocked == 0 and any(c.kind == "negative" for c in ctrls):
                status = "DORMANT"
            elif errors:
                status = "BROKEN"
            else:
                status = "ALIVE"
            results.append(GuardHealthResult(
                guard=guard, status=status,
                blocked=blocked, negative_total=sum(1 for c in ctrls if c.kind == "negative"),
                allowed=allowed, positive_total=sum(1 for c in ctrls if c.kind == "positive"),
                errors=errors,
            ))
            # T-0089 U8: per-guard death event (PASS iff ALIVE — a dead guard
            # is the fail-closed FAIL; reason carries the first error / the
            # dormant explanation).  Observation only — the verdict above is
            # untouched by the recording.
            death_fail_reason = None if status == "ALIVE" else (
                errors[0] if errors else self._death_reason(status)
            )
            self._observe(GuardCheckEvent(
                guard_id=guard,
                check_type=CHECK_DEATH,
                result=RESULT_PASS if status == "ALIVE" else RESULT_FAIL,
                duration_ms=(time.perf_counter() - t_guard) * 1000,
                failure_reason=death_fail_reason,
                timestamp=datetime.now(timezone.utc).isoformat(),
                source=source,
            ))
        return results

    @staticmethod
    def _death_reason(status: str) -> str:
        if status == "DORMANT":
            return "guard blocked zero negative controls (DORMANT)"
        if status == "NOT_VERIFIED":
            return "guard not verified (NOT_VERIFIED)"
        return f"guard is {status}"

    # ── T-0087 U1: missing / drift detection (REPORT level, never blocks) ──
    _GOVERNANCE_IMPL_DIRS = (("checkers", "checker"), ("guards", "guard"))

    def missing_detection(self) -> list[dict]:
        """Scan .ai/checkers/ and .ai/guards/ *.py against the registry.

        A *.py implementation file that exists on disk but is NOT registered is
        an omitted governance asset (a guard can be alive yet absent from the
        governance surface). Report-level finding, never flips the verdict.
        """
        findings: list[dict] = []
        source = self._registry_source()
        registered_paths = {
            b.implementation_path
            for b in self.registry.snapshot().entries.values()
        }
        t0 = time.perf_counter()
        for dirname, provider in self._GOVERNANCE_IMPL_DIRS:
            impl_dir = self.root / ".ai" / dirname
            if not impl_dir.is_dir():
                continue
            for fp in sorted(impl_dir.glob("*.py")):
                if fp.name == "__init__.py":
                    continue
                rel = fp.relative_to(self.root).as_posix()
                if rel not in registered_paths:
                    findings.append({
                        "finding": "MISSING",
                        "severity": "report",
                        "provider_id": provider,
                        "capability_id": None,
                        "implementation_path": rel,
                        "message": (
                            f"implementation file exists in .ai/{dirname}/ but "
                            "is not registered in the capability registry"
                        ),
                    })
        # T-0089 U8: one REPORT event per finding — inform, never block.
        for f in findings:
            self._observe(GuardCheckEvent(
                guard_id=f["implementation_path"],
                capability_id=f["capability_id"],
                check_type=CHECK_MISSING,
                result=RESULT_REPORT,
                duration_ms=(time.perf_counter() - t0) * 1000,
                failure_reason=f["message"],
                timestamp=datetime.now(timezone.utc).isoformat(),
                source=source,
            ))
        return findings

    def drift_detection(self) -> list[dict]:
        """Compare registered bindings against the current implementation files.

        DRIFT = the implementation file's sha256 no longer matches the hash
        recorded at registration (or the file is gone). A drifted guard may
        still pass its battery — this detection surfaces the change instead of
        relying on the battery alone. Report-level, never flips the verdict.
        """
        findings: list[dict] = []
        source = self._registry_source()
        t0 = time.perf_counter()
        for binding in sorted(
            self.registry.snapshot().entries.values(),
            key=lambda b: b.capability_id,
        ):
            fp = (self.root / binding.implementation_path
                  if not Path(binding.implementation_path).is_absolute()
                  else Path(binding.implementation_path))
            if not fp.exists():
                findings.append({
                    "finding": "DRIFT",
                    "severity": "report",
                    "provider_id": binding.provider_id,
                    "capability_id": binding.capability_id,
                    "implementation_path": binding.implementation_path,
                    "registered_version": binding.version,
                    "actual_hash": "",
                    "expected_hash": binding.implementation_hash,
                    "message": "registered implementation file is missing from disk",
                })
                continue
            actual_hash = sha256_file(fp)
            if actual_hash != binding.implementation_hash:
                findings.append({
                    "finding": "DRIFT",
                    "severity": "report",
                    "provider_id": binding.provider_id,
                    "capability_id": binding.capability_id,
                    "implementation_path": binding.implementation_path,
                    "registered_version": binding.version,
                    "actual_hash": actual_hash,
                    "expected_hash": binding.implementation_hash,
                    "message": (
                        "implementation file hash changed since registration "
                        "(file drifted from the registered binding)"
                    ),
                })
        # T-0089 U8: one REPORT event per finding — inform, never block.
        for f in findings:
            self._observe(GuardCheckEvent(
                guard_id=f["implementation_path"],
                capability_id=f["capability_id"],
                check_type=CHECK_DRIFT,
                result=RESULT_REPORT,
                duration_ms=(time.perf_counter() - t0) * 1000,
                failure_reason=f["message"],
                timestamp=datetime.now(timezone.utc).isoformat(),
                source=source,
            ))
        return findings

    def recompute_detection(self) -> list[dict]:
        """T-0133 P3 / D-02 M4: 抽查复算检测。

        读取 .ai/evidence/observability/recompute-events.jsonl（追加式，
        {ts, task_id, report_ref, result: PASS|FAIL}），按任务粒度统计
        末位连续 FAIL（24h 时间窗）：
        - 单次 FAIL            → REPORT（只报告，不翻转 verdict）
        - 连续 >= 3 次 FAIL    → BROKEN（升级 fail-closed：质量线程疑似
          系统性虚报，暂停走恢复路径）
        """
        findings: list[dict] = []
        source = self._registry_source()
        events_path = self.root / ".ai" / "evidence" / "observability" / "recompute-events.jsonl"
        if not events_path.is_file():
            return findings
        events: list[dict] = []
        try:
            for line in events_path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    events.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
        except OSError:
            return findings
        from datetime import timedelta
        cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
        per_task: dict[str, list[dict]] = {}
        for ev in events:
            ts = ev.get("ts", "")
            try:
                ts_dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            except (ValueError, AttributeError):
                ts_dt = None
            if ts_dt is not None and ts_dt < cutoff:
                continue
            per_task.setdefault(str(ev.get("task_id", "?")), []).append(ev)
        for task_id, evs in per_task.items():
            evs.sort(key=lambda e: str(e.get("ts", "")))
            trailing_fail = 0
            for ev in reversed(evs):
                if ev.get("result") == "FAIL":
                    trailing_fail += 1
                else:
                    break
            if trailing_fail >= 3:
                findings.append({
                    "finding": "RECOMPUTE_BROKEN",
                    "severity": "fail-closed",
                    "provider_id": "recompute",
                    "capability_id": task_id,
                    "implementation_path": "recompute-events.jsonl",
                    "message": (
                        f"quality thread '{task_id}' failed recompute "
                        f"{trailing_fail} consecutive times within 24h — "
                        "systematic misreport suspected, pause for recovery"
                    ),
                })
                self._observe(GuardCheckEvent(
                    guard_id=f"recompute:{task_id}",
                    capability_id=task_id,
                    check_type=CHECK_RECOMPUTE,
                    result=RESULT_FAIL,
                    duration_ms=0.0,
                    failure_reason=findings[-1]["message"],
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    source=source,
                ))
            elif trailing_fail > 0:
                findings.append({
                    "finding": "RECOMPUTE_REPORT",
                    "severity": "report",
                    "provider_id": "recompute",
                    "capability_id": task_id,
                    "implementation_path": "recompute-events.jsonl",
                    "message": f"recompute failed {trailing_fail} time(s) — report level",
                })
                # T-0143 4.2: 单次 FAIL 也追加 GuardCheckEvent（check_type=recompute
                # 侧信道），不再只等 3 次 BROKEN 升级才可见。
                self._observe(GuardCheckEvent(
                    guard_id=f"recompute:{task_id}",
                    capability_id=task_id,
                    check_type=CHECK_RECOMPUTE,
                    result=RESULT_FAIL,
                    duration_ms=0.0,
                    failure_reason=findings[-1]["message"],
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    source=source,
                ))
        return findings

    def integrity_check(self) -> dict:
        """Three-way integrity: death (fail-closed) + missing + drift (report).

        The overall verdict is driven by DEATH ONLY (BROKEN/DORMANT -> FAIL,
        unchanged fail-closed semantics). MISSING/DRIFT findings are attached as
        REPORT-level evidence — they inform but never block (T-0087 AC-02).
        T-0133: RECOMPUTE joins as a fourth dimension — single failure reports,
        >=3 consecutive failures escalates to fail-closed (quality thread pause).
        """
        t0 = time.perf_counter()
        death = self.summary()
        missing = self.missing_detection()
        drift = self.drift_detection()
        recompute = self.recompute_detection()
        overall = death["overall"]
        # T-0133: RECOMPUTE_BROKEN（连续 >=3 次复算失败）升级 fail-closed
        if overall == "PASS" and any(f["severity"] == "fail-closed" for f in recompute):
            overall = "FAIL"
        # T-0089 U8: one integrity event per check — side channel, never
        # blocks.  The overall verdict above is unchanged by the recording.
        dead_guards = [r["guard"] for r in death["results"] if r["status"] != "ALIVE"]
        self._observe(GuardCheckEvent(
            guard_id="guard_health",
            check_type=CHECK_INTEGRITY,
            result=RESULT_PASS if overall == "PASS" else RESULT_FAIL,
            duration_ms=(time.perf_counter() - t0) * 1000,
            failure_reason=None if overall == "PASS" else (
                "dead guards: " + ", ".join(dead_guards) if dead_guards else "integrity FAIL"
            ),
            timestamp=datetime.now(timezone.utc).isoformat(),
            source=self._registry_source(),
        ))
        return {
            "death": death,
            "missing": missing,
            "drift": drift,
            "recompute": recompute,
            # missing/drift are report-level: overall must NOT flip because of
            # them — only a dead guard fails the loop (recompute BROKEN counts).
            "overall": overall,
            "checked_at": death["checked_at"],
        }

    def summary(self) -> dict:
        results = self.run()
        alive = sum(1 for r in results if r.status == "ALIVE")
        dormant = sum(1 for r in results if r.status == "DORMANT")
        broken = sum(1 for r in results if r.status == "BROKEN")
        return {
            "guards_checked": len(results),
            "alive": alive,
            "dormant": dormant,
            "broken": broken,
            "results": [r.to_dict() for r in results],
            # DORMANT counts as FAIL (AC-05): a guard that blocks zero negative
            # controls is dead even though it did not crash.
            "overall": "FAIL" if (broken > 0 or dormant > 0) else "PASS",
            "checked_at": datetime.now(timezone.utc).isoformat(),
        }

    def write_report(self, out_path: str | Path) -> Path:
        out = Path(out_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        data = self.summary()
        out.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        return out
