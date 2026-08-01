#!/usr/bin/env python3
"""tools/loop_dashboard.py — AutoPlan dashboard visualization CLI (T-0094 D4).

Renders the four dashboard views (task graph / gates / metrics / guard
health) from the governance data sources and can write a snapshot report:

    .ai/evidence/observability/dashboard-snapshot.md      (text report)
    .ai/evidence/observability/dashboard-snapshot.html    (self-contained HTML)
    .ai/evidence/observability/dashboard-snapshot.json    (optional machine output)

Usage:
    python tools/loop_dashboard.py                 # text snapshot to stdout
    python tools/loop_dashboard.py --text          # same
    python tools/loop_dashboard.py --html          # self-contained HTML to stdout
    python tools/loop_dashboard.py --json          # JSON snapshot to stdout
    python tools/loop_dashboard.py --snapshot      # write md + html snapshots
    python tools/loop_dashboard.py --snapshot --out <dir>
    python tools/loop_dashboard.py --snapshot --out <file.md|file.html|file.json>

The dashboard is read-only: task_graph.yaml / gates.yaml / metrics-report.json
/ guard-events.jsonl are never modified; the snapshot records their sha256
hashes as a read-only proof.  A missing or unparseable source renders as
NOT_AVAILABLE — never guessed.
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


def main(argv: list[str] | None = None) -> int:
    from loop_core.dashboard_views import DashboardViews, write_snapshot_files

    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--text", action="store_true",
                        help="render the text (markdown) snapshot to stdout")
    parser.add_argument("--html", action="store_true",
                        help="render the self-contained HTML snapshot to stdout")
    parser.add_argument("--json", action="store_true",
                        help="render the JSON snapshot to stdout")
    parser.add_argument("--snapshot", action="store_true",
                        help="write snapshot files (md + html) to the "
                             "observability evidence dir or --out")
    parser.add_argument("--out", default=None,
                        help="for --snapshot: output directory, or an explicit "
                             "file ending in .md/.html/.json (default: "
                             ".ai/evidence/observability)")
    args = parser.parse_args(argv)

    root = _find_root()
    views = DashboardViews(root)

    if args.snapshot:
        if args.out:
            out = Path(args.out)
            suffix = out.suffix.lower()
            if suffix in (".md", ".html", ".json"):
                out.parent.mkdir(parents=True, exist_ok=True)
                snapshot = views.build_snapshot()
                if suffix == ".md":
                    out.write_text(views.render_text(snapshot), encoding="utf-8")
                elif suffix == ".html":
                    out.write_text(views.render_html(snapshot), encoding="utf-8")
                else:
                    out.write_text(
                        json.dumps(snapshot, ensure_ascii=False, indent=2),
                        encoding="utf-8",
                    )
                print(f"wrote {out}")
                return 0
            # directory base: write md + html into it
            written = write_snapshot_files(root, out_dir=out)
        else:
            written = write_snapshot_files(root)
        for kind in ("text", "html"):
            print(f"wrote {written[kind]}")
        return 0

    if args.html:
        sys.stdout.write(views.render_html())
        return 0
    if args.json:
        sys.stdout.write(json.dumps(views.build_snapshot(), ensure_ascii=False, indent=2) + "\n")
        return 0
    sys.stdout.write(views.render_text())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
