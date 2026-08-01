#!/usr/bin/env python3
"""tool_eval.py — Agent eval suite runner CLI (T-0092, B1 §1).

Usage:
  python tools/tool_eval.py                          # run builtin guard sample set
  python tools/tool_eval.py --cases cases.yaml       # run an authored suite
  python tools/tool_eval.py --report                 # write eval-report.json
                                                     # (.ai/evidence/observability/)
  python tools/tool_eval.py --json                   # JSON to stdout
  python tools/tool_eval.py --llm [--provider X]     # enable optional LLM judge
                                                     # (env/config; unavailable -> SKIP)

Exit code: 0 when the suite passes (SKIP never blocks), 2 on any FAIL.
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from loop_core.evals import (  # noqa: E402
    DEFAULT_EVAL_REPORT,
    DEFAULT_SUITE_ID,
    EvalReport,
    EvalRunner,
    build_llm_driver,
    builtin_cases,
    load_cases,
)
from loop_core.verdicts import Verdict  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Agent eval suite runner")
    parser.add_argument("--cases", metavar="PATH", default=None,
                        help="case file (.yaml/.yml/.json); default: builtin set")
    parser.add_argument("--report", metavar="PATH", nargs="?", const=DEFAULT_EVAL_REPORT,
                        default=None, help="write the ReportBinding eval report")
    parser.add_argument("--json", action="store_true", help="JSON to stdout")
    parser.add_argument("--llm", action="store_true",
                        help="enable the optional LLM judge (fail-safe: "
                             "unavailable -> SKIPPED, never blocks)")
    parser.add_argument("--provider", metavar="ID", default=None)
    parser.add_argument("--model", metavar="NAME", default=None)
    args = parser.parse_args()

    cases = load_cases(args.cases) if args.cases else builtin_cases()
    driver = build_llm_driver(provider=args.provider, model=args.model) if args.llm else None
    runner = EvalRunner(cases, llm_driver=driver, llm_model=args.model)
    result = runner.run()

    if args.report:
        report = EvalReport(result, task_id="T-0092", phase="S6-delivery",
                            gate_id="G-T-0092-S5-AGENT-EVAL",
                            git_commit_sha=None)
        out = report.write(args.report)
        print(f"report written: {out}", file=sys.stderr)

    if args.json:
        print(json.dumps(result.to_dict(), indent=2, ensure_ascii=False))
    else:
        s = result.stats
        print(f"Suite: {result.suite_id} v{result.suite_version} "
              f"({len(result.results)} cases)")
        print(f"  PASS:  {s['passed']}")
        print(f"  FAIL:  {s['failed']}")
        print(f"  SKIP:  {s['skipped']}")
        for r in result.results:
            if r.verdict.value != "PASS":
                print(f"  [!] {r.case_id} [{r.severity}] {r.verdict.value}: {r.reason}")
        print(f"Overall: {result.overall.value}")
    return 0 if result.overall is Verdict.PASS else 2


if __name__ == "__main__":
    sys.exit(main())
