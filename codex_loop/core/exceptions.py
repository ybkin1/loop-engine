"""
Governance-specific exceptions for the Codex Loop project.

Adapted from zcode loop-engine v3.0.0 src/loop_engine/exceptions.py for Codex.
"""


class LoopEngineError(Exception):
    """Base exception for all Loop Engine errors."""
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(f"{code}: {message}")


class GovernanceError(LoopEngineError):
    """Raised when a governance invariant is violated."""
    pass


class StateError(GovernanceError):
    """Raised when .ai/state.yaml is missing, invalid, or contradictory."""
    pass


class GateError(GovernanceError):
    """Raised when gate operations fail (missing gate, wrong status, etc.)."""
    pass


class ContinuityError(GovernanceError):
    """Raised when ProjectContinuity checks fail."""
    pass


class HookError(LoopEngineError):
    """Raised when a hook script encounters a non-recoverable error."""
    pass


class ConfigError(LoopEngineError):
    """Raised when config.yaml is missing or invalid."""
    pass

