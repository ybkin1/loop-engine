"""
implementation_design_diff.py — Compare code structure vs architecture design.

T-0108 F4 (D5-7 消解): the DRIFT verdict is determined ONLY by the explicit
``designed_files:`` declaration in the architecture document front-matter.
The legacy backtick-regex inference (which mis-classified explanatory code
references in prose/diagrams as design declarations) is retained solely as a
``hint`` field and never influences the verdict.

Declaration semantics:
- ``designed_files:`` is a YAML front-matter list at the top of
  ``docs/02-architecture.md`` (``--- ... ---`` block).
- File entries (no trailing ``/``) declare one exact file; the file must
  exist under the project (relative to repo root).
- Directory entries (trailing ``/``) declare the whole layer; any .py file
  under that directory is considered designed.
- DRIFT == designed-but-missing OR actual-but-undesigned, where "actual"
  only considers .py files under the declared design domains (directories
  named by the declaration).  Code outside the declared domains is out of
  scope for this document and does not produce false drift.

Legacy fallback: when the document has no ``designed_files`` declaration,
the old regex inference is used and marked ``"declaration": "regex-fallback"``
so consumers can tell the verdict was not explicit-declaration-driven.
"""
import json
import re
import sys
from pathlib import Path

# Backtick inference (legacy heuristic — hint only, never a verdict input).
_FILE_RE = re.compile(r'`([a-zA-Z_][\w/]*\.py)`')
_DIR_RE = re.compile(r'`([a-zA-Z_][\w/]+/)`')


def _parse_front_matter(text: str) -> dict | None:
    """Parse a leading ``--- ... ---`` YAML front-matter block, else None."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None
    end = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end = i
            break
    if end is None:
        return None
    block = "\n".join(lines[1:end])
    try:
        import yaml
        data = yaml.safe_load(block)
        return data if isinstance(data, dict) else None
    except ImportError:
        pass
    except Exception:
        pass
    try:
        data = json.loads(block)
        return data if isinstance(data, dict) else None
    except Exception:
        return None


def _regex_infer(text: str) -> set[str]:
    """Legacy backtick inference — hint only (D5-7: no longer a verdict input)."""
    designed: set[str] = set()
    for m in _FILE_RE.finditer(text):
        designed.add(m.group(1))
    for m in _DIR_RE.finditer(text):
        designed.add(m.group(1))
    return designed


def _declared_designed(text: str) -> tuple[set[str] | None, str]:
    """Read the explicit ``designed_files:`` declaration.

    Returns (entries, source_label).  Entries are None when no usable
    declaration exists (caller falls back to regex inference).
    """
    front_matter = _parse_front_matter(text)
    if front_matter is None:
        return None, "regex-fallback (no designed_files declaration)"
    declared = front_matter.get("designed_files")
    if not isinstance(declared, list):
        return None, "regex-fallback (designed_files missing/invalid)"
    entries = {str(item).strip() for item in declared if str(item).strip()}
    if not entries:
        return None, "regex-fallback (designed_files empty)"
    return entries, "front-matter designed_files"


def _design_domains(entries: set[str]) -> set[str]:
    """Top-level design domains: every entry contributes its first path segment."""
    domains: set[str] = set()
    for entry in entries:
        first = entry.split("/", 1)[0]
        if first:
            domains.add(first)
    return domains


def _covered(entry: str, actual: set[str]) -> bool:
    """Whether a designed entry is covered by the actual file tree."""
    if entry.endswith("/"):
        prefix = entry
        return any(a.startswith(prefix) for a in actual)
    return any(a == entry or a.startswith(entry.rstrip("/") + "/") for a in actual)


def diff(root):
    r = Path(root)
    arch = r / "docs/02-architecture.md"
    if not arch.exists():
        return {"status": "NO_DESIGN"}
    text = arch.read_text(encoding="utf-8")

    declared, source_label = _declared_designed(text)
    if declared is None:
        designed = _regex_infer(text)
    else:
        designed = declared
    hint = sorted(_regex_infer(text) - (designed if declared is not None else set()))

    # Actual .py files under the declared design domains only.
    domains = _design_domains(designed)
    actual: set[str] = set()
    for d in domains:
        base = r / d
        if base.is_dir():
            for f in base.rglob("*.py"):
                if "__pycache__" not in str(f) and ".git" not in str(f):
                    actual.add(str(f.relative_to(r)).replace("\\", "/"))

    only_designed = sorted(
        {d for d in designed if not _covered(d, actual)}
    )
    only_actual = sorted(
        {a for a in actual if not any(
            a == d.rstrip("/") or a.startswith(d.rstrip("/") + "/")
            for d in designed
        )}
    )
    return {
        "status": "DRIFT" if only_designed or only_actual else "OK",
        "declaration": source_label,
        "designed_but_missing": only_designed[:10],
        "actual_but_undesigned": only_actual[:10],
        "hint_regex_inferred": hint[:10],
    }


if __name__ == "__main__":
    print(json.dumps(diff(sys.argv[1] if len(sys.argv) > 1 else "."), indent=2))
