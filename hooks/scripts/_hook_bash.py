"""Bash command analysis module — re-exports from hook_common.py.

This module exists as a logical separation point for Bash-related functions.
The canonical implementation lives in hook_common.py to maintain backward
compatibility with integration tests that copy only hook_common.py.

For new code, prefer importing from this module:
    from _hook_bash import has_write_operations, is_readonly_command
"""
from hook_common import (  # noqa: F401
    shell_tokenize,
    is_write_command,
    has_write_operations,
    is_readonly_command,
)
