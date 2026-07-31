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

import hashlib
import json
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from loop_core.capability_registry import (
    CapabilityBinding,
    CapabilityRegistry,
    build_default_registry,
    sha256_file,
)

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
                 registry: Optional[CapabilityRegistry] = None):
        self.root = Path(project_root).resolve()
        self.hooks_dir = self.root / "hooks" / "scripts"
        self.registry = registry if registry is not None else build_default_registry(self.root)

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
        for guard, ctrls in sorted(by_guard.items()):
            script = self.hooks_dir / f"{guard}.py"
            blocked = allowed = 0
            errors: list[str] = []
            crashed = False
            for c in ctrls:
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
                        errors.append(
                            f"{c.control_id} {c.description}: hook crashed (rc={rc})"
                        )
                    elif c.kind == "negative":
                        if rc == 2:
                            blocked += 1
                        else:
                            errors.append(
                                f"{c.control_id} {c.description}: expected BLOCK got pass (rc={rc})"
                            )
                    else:
                        if rc == 0:
                            allowed += 1
                        else:
                            errors.append(
                                f"{c.control_id} {c.description}: expected PASS got block (rc={rc})"
                            )
                except subprocess.TimeoutExpired:
                    crashed = True
                    errors.append(f"{c.control_id}: TIMEOUT")
                except Exception as e:
                    crashed = True
                    errors.append(f"{c.control_id}: ERROR {e}")

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
        return results

    # ── T-0087 U1: missing / drift detection (REPORT level, never blocks) ──
    _GOVERNANCE_IMPL_DIRS = (("checkers", "checker"), ("guards", "guard"))

    def missing_detection(self) -> list[dict]:
        """Scan .ai/checkers/ and .ai/guards/ *.py against the registry.

        A *.py implementation file that exists on disk but is NOT registered is
        an omitted governance asset (a guard can be alive yet absent from the
        governance surface). Report-level finding, never flips the verdict.
        """
        findings: list[dict] = []
        registered_paths = {
            b.implementation_path
            for b in self.registry.snapshot().entries.values()
        }
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
        return findings

    def drift_detection(self) -> list[dict]:
        """Compare registered bindings against the current implementation files.

        DRIFT = the implementation file's sha256 no longer matches the hash
        recorded at registration (or the file is gone). A drifted guard may
        still pass its battery — this detection surfaces the change instead of
        relying on the battery alone. Report-level, never flips the verdict.
        """
        findings: list[dict] = []
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
        return findings

    def integrity_check(self) -> dict:
        """Three-way integrity: death (fail-closed) + missing + drift (report).

        The overall verdict is driven by DEATH ONLY (BROKEN/DORMANT -> FAIL,
        unchanged fail-closed semantics). MISSING/DRIFT findings are attached as
        REPORT-level evidence — they inform but never block (T-0087 AC-02).
        """
        death = self.summary()
        return {
            "death": death,
            "missing": self.missing_detection(),
            "drift": self.drift_detection(),
            # missing/drift are report-level: overall must NOT flip because of
            # them — only a dead guard fails the loop.
            "overall": death["overall"],
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
