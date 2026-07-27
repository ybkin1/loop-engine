"""
Phase constants and exit codes used across the Codex Loop project.

Adapted from zcode loop-engine v3.0.0 src/loop_engine/constants.py for Codex.
"""

# Governance phases (12-stage loop)
PHASE_S0_INIT = "S0-init"
PHASE_S1_REQUIREMENTS = "S1-requirements"
PHASE_S2_ARCHITECTURE = "S2-architecture"
PHASE_S3_INTERFACE = "S3-interface"
PHASE_S4_IMPLEMENTATION = "S4-implementation"
PHASE_S5_QUALITY = "S5-quality"
PHASE_S6_DELIVERY = "S6-delivery"
PHASE_S7_INTEGRATION = "S7-integration"
PHASE_S8_FUNCTIONAL_TEST = "S8-functional-test"
PHASE_S9_FIX_OPTIMIZE = "S9-fix-optimize"
PHASE_S10_PERFORMANCE = "S10-performance"
PHASE_S11_MAINTENANCE = "S11-maintenance"

PHASES = [
    PHASE_S0_INIT, PHASE_S1_REQUIREMENTS, PHASE_S2_ARCHITECTURE,
    PHASE_S3_INTERFACE, PHASE_S4_IMPLEMENTATION, PHASE_S5_QUALITY,
    PHASE_S6_DELIVERY, PHASE_S7_INTEGRATION, PHASE_S8_FUNCTIONAL_TEST,
    PHASE_S9_FIX_OPTIMIZE, PHASE_S10_PERFORMANCE, PHASE_S11_MAINTENANCE,
]

# Task status
TASK_PENDING = "pending"
TASK_ACTIVE = "active"
TASK_IN_PROGRESS = "in_progress"
TASK_COMPLETED = "completed"
TASK_BLOCKED = "blocked"
TASK_REJECTED = "rejected"

# Gate status
GATE_PENDING = "pending"
GATE_APPROVED = "approved"
GATE_REJECTED = "rejected"

# Hook exit codes
EXIT_PASS = 0
EXIT_BLOCK = 2

# Hook events
EVENT_SESSION_START = "SessionStart"
EVENT_PRE_TOOL_USE = "PreToolUse"

# Path guard modes
PATH_GUARD_ASK = "ask"
PATH_GUARD_DENY = "deny"

# Gate guard fail modes
FAIL_CLOSED = "closed"
FAIL_OPEN = "open"

# Schema versions
STATE_SCHEMA_VERSION = 1
GATES_SCHEMA_VERSION = 1
TASK_GRAPH_SCHEMA_VERSION = 1

# Governance file paths (relative to project root)
AI_DIR = ".ai"
STATE_FILE = ".ai/state.yaml"
GATES_FILE = ".ai/gates.yaml"
TASK_GRAPH_FILE = ".ai/task_graph.yaml"
HANDOFF_FILE = ".ai/HANDOFF.md"
PROGRESS_FILE = ".ai/PROGRESS.md"

