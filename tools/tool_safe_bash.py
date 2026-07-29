"""
tool_safe_bash.py — MCP tool: safe Bash execution with command-level parsing.

Unlike bash_content_guard (regex-based PreToolUse hook), this tool:
1. Uses shlex to properly parse command structure
2. Extracts target file paths from redirects and cp/mv arguments
3. Validates against task allowed_paths
4. Only executes safe commands

Registered as MCP tool: safe_bash
"""

import json
import logging
import os
import shlex
import subprocess
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

# Patterns that indicate file writes
WRITE_REDIRECTS = {">", ">>", "1>", "2>", "&>"}
DANGEROUS_COMMANDS = {"rm", "rmdir", "dd", "mkfs", "shred", "chmod", "chown", "wget", "curl", "nc", "telnet", "find", "xargs"}
FILE_WRITE_COMMANDS = {"cp", "mv", "tee", "touch", "mkdir", "dd", "curl", "wget"}


def _parse_command(command: str) -> dict:
    """Parse a shell command and extract structure using shlex."""
    try:
        tokens = shlex.split(command)
    except ValueError:
        return {"error": "Cannot parse command", "tokens": []}

    if not tokens:
        return {"tokens": [], "main_command": "", "redirects": [], "target_files": []}

    main_cmd = tokens[0]
    redirects = []
    target_files = []
    args = []

    i = 1
    while i < len(tokens):
        token = tokens[i]
        if token in WRITE_REDIRECTS:
            if i + 1 < len(tokens):
                redirects.append({"op": token, "target": tokens[i + 1]})
                target_files.append(tokens[i + 1])
                i += 2
                continue
        elif token == "|":
            break  # Don't parse beyond pipe
        args.append(token)
        i += 1

    # Extract targets from file-write commands
    if main_cmd in FILE_WRITE_COMMANDS:
        for arg in args:
            if not arg.startswith("-"):
                target_files.append(arg)

    return {
        "tokens": tokens,
        "main_command": main_cmd,
        "args": args,
        "redirects": redirects,
        "target_files": target_files,
    }


def _is_safe(parsed: dict, project_root: str, allowed_paths: list[str]) -> tuple[bool, str]:
    """Check if the parsed command is safe to execute.

    Returns (is_safe, reason).
    """
    main_cmd = parsed.get("main_command", "")

    # Block dangerous commands
    if main_cmd in DANGEROUS_COMMANDS:
        return False, f"Command '{main_cmd}' is blocked by safe_bash policy."

    # Check target files
    proj = Path(project_root).resolve()
    for tf in parsed.get("target_files", []):
        target_path = Path(tf)
        if not target_path.is_absolute():
            target_path = (proj / tf).resolve()
        else:
            target_path = target_path.resolve()

        # Must be within project
        try:
            target_path.relative_to(proj)
        except ValueError:
            return False, f"Target '{tf}' is outside project root."

        # Check allowed_paths
        if allowed_paths:
            rel = str(target_path.relative_to(proj)).replace("\\", "/")
            allowed = False
            for ap in allowed_paths:
                ap_norm = ap.rstrip("/").replace("\\", "/")
                if rel.startswith(ap_norm) or rel == ap_norm:
                    allowed = True
                    break
            if not allowed:
                return False, f"Target '{rel}' is not in allowed_paths."

    return True, "OK"


def run(command: str, project_root: str = "", allowed_paths: list[str] | None = None, timeout: int = 30) -> dict:
    """Execute a safe Bash command.

    Args:
        command: The shell command to execute
        project_root: Project root for path validation
        allowed_paths: List of allowed relative paths
        timeout: Command timeout in seconds

    Returns:
        {"status": "ok"|"blocked", "stdout": "...", "stderr": "..."}
    """
    parsed = _parse_command(command)
    if "error" in parsed:
        return {"status": "blocked", "reason": parsed["error"], "stdout": "", "stderr": ""}

    safe, reason = _is_safe(parsed, project_root, allowed_paths or [])
    if not safe:
        return {"status": "blocked", "reason": reason, "stdout": "", "stderr": ""}

    try:
        result = subprocess.run(
            command, shell=True, capture_output=True, text=True,
            timeout=timeout, cwd=project_root or None,
        )
        return {
            "status": "ok",
            "exit_code": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
        }
    except subprocess.TimeoutExpired:
        return {"status": "error", "reason": f"Command timed out after {timeout}s"}
    except Exception as e:
        return {"status": "error", "reason": str(e)}


# MCP tool entry point
def handle(params: dict) -> dict:
    """MCP tool handler for safe_bash."""
    command = params.get("command", "")
    if not command:
        return {"status": "error", "reason": "No command provided"}

    project_root = params.get("project_root", os.getcwd())
    allowed_paths = params.get("allowed_paths", [])
    timeout = params.get("timeout", 30)

    return run(command, str(project_root), allowed_paths, timeout)


# MCP schema
SCHEMA = {
    "name": "safe_bash",
    "description": "Execute safe shell commands with path validation. Blocks file writes outside allowed_paths.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "command": {"type": "string", "description": "Shell command to execute"},
            "project_root": {"type": "string", "description": "Project root directory"},
            "allowed_paths": {"type": "array", "items": {"type": "string"}},
            "timeout": {"type": "integer", "default": 30},
        },
        "required": ["command"],
    },
}
