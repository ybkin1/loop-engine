# Loop Engine -- Loop Engineering Software Delivery System


Codex native plugin. Turns AI coding into a deliverable system with full software engineering discipline.


## Version


**codex_loop v3.1.0** -- 2026-07-29 (adapted from zcode loop-engine v3.0.0)


## Installation


### Codex
This directory is the Codex plugin workspace. AGENTS.md Loop Governance rules auto-activate here.


### Init Target Project
python codex_loop/scripts/install.py --project-root /path/to/your/project


## Architecture


| Layer | Component | Function |
|-------|-----------|----------|
| Protocol | loop_core/ | Host-independent state machine, hard constraints (C1-C11), gate logic |
| Enforcement | RuntimeController + hooks | Write interception, gate blocking, role isolation, path protection |
| Knowledge | Skill + 11 Agents | Governance bootstrap, role collaboration, phase orchestration |
| Tools | 20 tools | Quality gates, security scan, dependency analysis, contract validation, evidence chain |
| Commands | 3 slash commands | State validation, evidence chain verify, cost report |


## vs zcode


| Dimension | zcode v3.0.0 | codex_loop v3.1.0 |
|-----------|-------------|-------------------|
| Write enforcement | Hook exit codes | RuntimeController.authorize_write() |
| Role isolation | ZCode Agent tool | spawn_agent native isolation |
| Tool invocation | JSON-RPC stdio process | call_tool() direct call |
| Enforcement level | MEDIUM (no cmd intercept) | STRONG (full intercept) |
| Plugin cache | Needs auto_sync | No cache issue |


## Quality


| Gate | Result |
|------|--------|
| Test (pytest) | 132 passed |
| Lint (ruff) | 0 errors |


## Dependencies


Python 3.10+, PyYAML >= 6.0