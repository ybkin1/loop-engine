from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from continuity_auditor import audit_handoff_model
from governor_lib import ai_dir, governance_invariant_errors, project_root_arg, read_text


REQUIRED_HEADINGS = [
    "## Product Direction And Authority", "## Current Phase", "## Current Task",
    "## Allowed Scope", "## Forbidden Scope", "## Verified", "## Unverified",
    "## Evidence", "## Integration Impact", "## Structured Lifecycle",
    "## Structured Next Action", "## Checkpoint", "## Next Session First Step",
]


def main() -> int:
    args = project_root_arg().parse_args()
    root = Path(args.project_root).resolve()
    text = read_text(ai_dir(root) / "HANDOFF.md")
    errors = []
    if not text:
        errors.append("Missing or empty .ai/HANDOFF.md")
    errors.extend(f"HANDOFF.md missing heading: {heading}" for heading in REQUIRED_HEADINGS if heading not in text)
    errors.extend(governance_invariant_errors(root))
    errors.extend(audit_handoff_model(root, text))
    errors = list(dict.fromkeys(errors))
    for error in errors:
        print(f"[error] {error}")
    if errors:
        return 2
    print("[ok] handoff audit passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
