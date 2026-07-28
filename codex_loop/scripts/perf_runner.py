"""
perf_runner.py — Basic performance testing for Loop Engine components.

Tests hook execution latency, state machine throughput, and file I/O patterns.
Does NOT require real load infrastructure — uses local benchmarking.

Usage:
    python perf_runner.py --project-root <path>
    python perf_runner.py --project-root <path> --iterations 100
"""
import argparse
import json
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path


@dataclass
class PerfResult:
    name: str
    iterations: int
    total_ms: float
    avg_ms: float
    min_ms: float
    max_ms: float
    p95_ms: float

    @property
    def verdict(self) -> str:
        # Hook scripts must complete within timeout (5000ms for gate_guard/path_guard)
        if "hook" in self.name.lower():
            return "PASS" if self.max_ms < 4000 else "WARN"
        return "PASS"


def benchmark_hook(project_root: Path, hook_script: str, hook_input: dict,
                   iterations: int = 50) -> PerfResult:
    """Benchmark a hook script's execution time."""
    times = []
    for _ in range(iterations):
        start = time.perf_counter()
        subprocess.run(
            [sys.executable, hook_script],
            input=json.dumps(hook_input),
            capture_output=True, text=True, timeout=10,
            env={**__import__('os').environ, 'ZCODE_PROJECT_DIR': str(project_root)},
        )
        elapsed = (time.perf_counter() - start) * 1000
        times.append(elapsed)

    times.sort()
    return PerfResult(
        name=Path(hook_script).stem,
        iterations=iterations,
        total_ms=sum(times),
        avg_ms=sum(times) / len(times),
        min_ms=times[0],
        max_ms=times[-1],
        p95_ms=times[int(len(times) * 0.95)],
    )


def benchmark_state_machine(iterations: int = 1000) -> PerfResult:
    """Benchmark state machine transition checks."""
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from codex_loop.core.state_machine import Phase, can_transition_phase, can_approve_gate, GateStatus

    times = []
    for _ in range(iterations):
        start = time.perf_counter()
        can_transition_phase(Phase.S0_INIT, Phase.S1_REQUIREMENTS)
        can_approve_gate(GateStatus.PENDING, {"rev": "BLOCKED", "arch": "PASS"}, ["rev", "arch"])
        elapsed = (time.perf_counter() - start) * 1000
        times.append(elapsed)

    times.sort()
    return PerfResult(
        name="state_machine",
        iterations=iterations,
        total_ms=sum(times),
        avg_ms=sum(times) / len(times),
        min_ms=times[0],
        max_ms=times[-1],
        p95_ms=times[int(len(times) * 0.95)],
    )


def run_all(project_root: Path, iterations: int = 50) -> list[PerfResult]:
    results = []

    hooks_dir = project_root / "hooks" / "scripts"
    hook_input = {"tool_input": {"file_path": "src/test.py"}}

    for hook in ["session_brief.py", "gate_guard.py", "path_guard.py", "loop_enforcement.py"]:
        script = hooks_dir / hook
        if script.exists():
            r = benchmark_hook(project_root, str(script), hook_input, iterations)
            results.append(r)

    results.append(benchmark_state_machine(min(iterations * 20, 10000)))
    return results


def main():
    parser = argparse.ArgumentParser(description="Loop Engine Performance Runner")
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--iterations", type=int, default=50)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    root = Path(args.project_root).resolve()
    results = run_all(root, args.iterations)

    if args.json:
        output = [{"name": r.name, "avg_ms": round(r.avg_ms, 2), "max_ms": round(r.max_ms, 2),
                    "p95_ms": round(r.p95_ms, 2), "verdict": r.verdict} for r in results]
        print(json.dumps(output, indent=2, ensure_ascii=False))
    else:
        for r in results:
            print(f"{r.name}: avg={r.avg_ms:.1f}ms max={r.max_ms:.1f}ms p95={r.p95_ms:.1f}ms → {r.verdict}")

    blocked = any(r.verdict == "WARN" for r in results)
    if blocked:
        print("\n[perf] WARN: Some hooks exceed performance threshold")
        sys.exit(1)
    else:
        print("\n[perf] PASS")


if __name__ == "__main__":
    main()
