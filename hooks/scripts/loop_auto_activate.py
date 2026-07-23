#!/usr/bin/env python3
"""
loop_auto_activate.py — SessionStart hook: auto-activate Loop mode.

On each session start:
1. Check if project has .ai/state.yaml (governance project)
2. If loop_mode is not set, auto-analyze project complexity
3. Auto-set loop_mode based on risk factors
4. Inject activation status into session

This ensures Loop is NEVER "opt-in" for projects that need it — it auto-activates
based on objective risk factors, not AI self-discipline.

Exit: always 0 (fail-open — activation failure should not block the session).
"""
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True

sys.path.insert(0, str(Path(__file__).resolve().parent))
from hook_common import (
    is_governance_project,
    load_state,
    project_root,
    read_stdin_json,
)

# Risk factors that auto-trigger FULL loop mode
AUTO_FULL_TRIGGERS = [
    ".ai/gates.yaml",        # Already has governance
    "requirements.txt",      # Has dependencies
    "package.json",          # Node.js project
    "pyproject.toml",        # Python project
    "docker-compose.yml",    # Multi-service
    "migrations/",           # Database migrations
]

# Risk factors that auto-trigger STANDARD
AUTO_STANDARD_TRIGGERS = [
    "src/",                  # Has source directory
    "tests/",                # Has tests
    ".gitignore",            # Version controlled
]

# Multi-module indicators → can parallelize → needs Loop
PARALLEL_INDICATORS = [
    "src/*/",                # Multiple source subdirectories
    "services/",             # Microservices
    "packages/",             # Monorepo packages
    "modules/",              # Modular structure
]


def analyze_project(root: Path) -> str:
    """Analyze project complexity and return recommended loop_mode."""
    score = 0

    for trigger in AUTO_FULL_TRIGGERS:
        p = root / trigger
        if p.exists():
            if trigger == ".ai/gates.yaml":
                score += 3  # Already governed
            elif trigger in ("requirements.txt", "package.json", "pyproject.toml"):
                score += 2  # Has dependencies
            elif trigger in ("docker-compose.yml", "migrations/"):
                score += 3  # Multi-service or database

    for trigger in AUTO_STANDARD_TRIGGERS:
        if (root / trigger).exists():
            score += 1

    # Parallel task detection: multiple independent source modules
    parallel_score = 0
    for indicator in PARALLEL_INDICATORS:
        p = root / indicator.rstrip("/*/")
        if p.exists() and p.is_dir():
            subdirs = [d for d in p.iterdir() if d.is_dir() and not d.name.startswith(".")]
            if len(subdirs) >= 2:
                parallel_score += 3  # Multiple independent modules → can parallelize
                break

    score += parallel_score

    if score >= 5:
        return "FULL"
    elif score >= 2:
        return "STANDARD"
    return "LIGHTWEIGHT"


def main():
    hook_input = read_stdin_json()
    root = project_root(hook_input)

    if not is_governance_project(root):
        return 0

    try:
        state = load_state(root)
    except Exception:
        return 0

    loop_mode = state.get("loop_mode", "")

    if not loop_mode:
        # Auto-activate: analyze and set loop_mode
        recommended = analyze_project(root)

        # Write to state.yaml
        state_path = root / ".ai" / "state.yaml"
        try:
            text = state_path.read_text(encoding="utf-8")
            if "loop_mode:" not in text:
                text += f"\nloop_mode: {recommended}\n"
                state_path.write_text(text, encoding="utf-8")
        except Exception:
            pass  # Can't write, but don't block session

        # Inject activation notice
        notice = (
            f"[loop-governance] ⚡ Loop 工程已自动激活 | mode={recommended} | "
            f"loop_enforcement hook 已生效——所有写入必须在批准任务范围内。"
        )
        output = {
            "hookSpecificOutput": {
                "hookEventName": "SessionStart",
                "additionalContext": notice,
            }
        }
        sys.stdout.write(json.dumps(output, ensure_ascii=False))
    else:
        # Already activated — inject enforcement reminder
        notice = (
            f"[loop-governance] Loop mode={loop_mode} | "
            f"loop_enforcement: {'ACTIVE (hard enforcement)' if loop_mode != 'LIGHTWEIGHT' else 'passive'}"
        )
        output = {
            "hookSpecificOutput": {
                "hookEventName": "SessionStart",
                "additionalContext": notice,
            }
        }
        sys.stdout.write(json.dumps(output, ensure_ascii=False))

    return 0


if __name__ == "__main__":
    sys.exit(main())
