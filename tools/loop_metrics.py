#!/usr/bin/env python3
"""tools/loop_metrics.py — Loop-DORA metrics report CLI (T-0090 D2, B2 §2.4).

Builds the SLO/error-budget + DORA metrics report from the repository's
governance artifacts (read-only) and writes it to the evidence directory:

    .ai/evidence/observability/metrics-report.json   (machine output)
    .ai/evidence/observability/metrics-report.md     (human-readable summary)

Usage:
    python tools/loop_metrics.py --report
    python tools/loop_metrics.py --report --window 2026-07-01..2026-09-30
    python tools/loop_metrics.py --report --json-out <path> --md-out <path>
    python tools/loop_metrics.py --report --releases 3

The report never writes to its data sources (gates.yaml / task_graph.yaml /
guard-events.jsonl / ledgers are read-only inputs).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def _find_root() -> Path:
    """Project root = nearest ancestor (or cwd) containing .ai/gates.yaml."""
    here = Path.cwd()
    for candidate in (here, *here.parents):
        if (candidate / ".ai" / "gates.yaml").exists():
            return candidate
    if (Path(__file__).resolve().parent.parent / ".ai" / "gates.yaml").exists():
        return Path(__file__).resolve().parent.parent
    return here


def _parse_window(text: str) -> tuple[str, str] | None:
    if not text or text in ("all", "quarterly"):
        return None
    parts = text.split("..")
    if len(parts) != 2:
        raise SystemExit(f"bad --window {text!r}; expected 'all' or "
                         "YYYY-MM-DD..YYYY-MM-DD")
    return (parts[0].strip(), parts[1].strip())


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--report", action="store_true",
                        help="build and write the metrics report")
    parser.add_argument("--window", default="all",
                        help="window: 'all' (data bounds) or "
                             "YYYY-MM-DD..YYYY-MM-DD")
    parser.add_argument("--slo", default=None,
                        help="path to an .ai/slo.yaml override (default: "
                             ".ai/slo.yaml, falls back to B2 defaults)")
    parser.add_argument("--releases", type=int, default=0,
                        help="release count for the release fee (0 = not "
                             "assessed; no release ledger exists yet)")
    parser.add_argument("--json-out", default=None,
                        help="report JSON output path (default: "
                             ".ai/evidence/observability/metrics-report.json)")
    parser.add_argument("--md-out", default=None,
                        help="report markdown output path (default: same dir "
                             "as JSON, .md suffix)")
    args = parser.parse_args(argv)

    if not args.report:
        parser.print_help()
        return 0

    from loop_core.governance_metrics import build_report, render_markdown

    root = _find_root()
    window = _parse_window(args.window)
    report = build_report(root, window=window, slo_path=args.slo,
                          releases=args.releases)

    json_out = Path(args.json_out) if args.json_out else (
        root / ".ai" / "evidence" / "observability" / "metrics-report.json"
    )
    md_out = Path(args.md_out) if args.md_out else json_out.with_suffix(".md")

    json_out.parent.mkdir(parents=True, exist_ok=True)
    json_out.write_text(
        json.dumps(report.to_dict(), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    md_out.write_text(render_markdown(report), encoding="utf-8")

    print(f"root:          {root}")
    print(f"window:        {report.window[0]} -> {report.window[1]}")
    print(f"status:        {report.status}")
    print(f"error budget:  {report.budget['status']} "
          f"(remaining {report.budget['remaining_units']} / "
          f"{report.budget['total_units']} units)")
    print(f"missing:       {len(report.missing)} item(s)")
    for m in report.missing[:10]:
        print(f"  - {m}")
    print(f"json:          {json_out}")
    print(f"markdown:      {md_out}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(130)
