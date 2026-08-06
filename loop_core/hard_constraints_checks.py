"""hard_constraints_checks.py — 约束检查外部模块（T-0124 拆分）。

从 loop_core/hard_constraints.py 拆出：`check_c8_evidence_freshness` /
`check_c9_import_validity` / `check_c10_contract_test_coverage` /
`check_c11_file_limit`（C8-C11 方法体原样提取；第一参数 `self` 在调用时
为壳 HardConstraints 实例）。壳文件方法保留同名委托。行为逐字节等价。
"""
from __future__ import annotations

import warnings
from pathlib import Path
from typing import Any

from loop_core.hard_constraints import (
    ConstraintID,
    ConstraintViolation,
    EvidenceEnvelope,
    Severity,
)

def check_c8_evidence_freshness(
    self,
    evidence_list: list[EvidenceEnvelope],
    current_hashes: dict[str, str] | None = None,
) -> list[ConstraintViolation]:
    """C8: Stale evidence -> old results invalidated.

    Evidence is stale if:
    - EvidenceEnvelope.is_fresh() returns False (past expiration)
    - The content_hash differs from the current hash of the source data

    Stale evidence must be marked STALE and regenerated.
    """
    violations: list[ConstraintViolation] = []
    current_hashes = current_hashes or {}

    for evidence in evidence_list:
        # FIX-6: Validate that each element is an EvidenceEnvelope
        if not isinstance(evidence, EvidenceEnvelope):
            violations.append(ConstraintViolation(
                constraint_id=ConstraintID.C8_STALE_EVIDENCE,
                severity=Severity.WARNING,
                message=(
                    f"Non-EvidenceEnvelope object in evidence_list: "
                    f"{type(evidence).__name__}"
                ),
                detail=(
                    f"Expected EvidenceEnvelope instance, got "
                    f"{type(evidence).__name__}: {evidence!r}. "
                    "This item will be skipped."
                ),
                remediation=(
                    "Ensure all items in evidence_list are "
                    "EvidenceEnvelope instances."
                ),
            ))
            continue

        is_stale = False
        reasons: list[str] = []

        if not evidence.is_fresh():
            is_stale = True
            reasons.append(
                f"expired at {evidence.expires_at}"
            )

        current_hash = current_hashes.get(evidence.evidence_id)
        if current_hash is not None and evidence.has_hash_changed(current_hash):
            is_stale = True
            reasons.append(
                f"content hash changed "
                f"(recorded: {evidence.content_hash[:12]}..., "
                f"current: {current_hash[:12]}...)"
            )

        if is_stale:
            phase_label = evidence.phase.value if evidence.phase else "unknown"
            violations.append(ConstraintViolation(
                constraint_id=ConstraintID.C8_STALE_EVIDENCE,
                severity=Severity.BLOCKER,
                message=f"Evidence '{evidence.evidence_id}' is stale and must be regenerated",
                detail=(
                    f"Evidence ID: {evidence.evidence_id}. "
                    f"Reasons: {'; '.join(reasons)}. "
                    f"Phase: {phase_label}. "
                    "Stale evidence no longer reflects the current state of the project."
                ),
                remediation=(
                    f"Re-run the verification or review that produced '{evidence.evidence_id}'. "
                    "Evidence must be regenerated whenever source data changes "
                    "or the evidence's validity window expires."
                ),
            ))

    return violations

# ── C9: Import Validity (Import真实性校验) ──────────────────────────────

def check_c9_import_validity(
    self,
    root: str | Path,
    scan_paths: list[str | Path] | None = None,
) -> list[ConstraintViolation]:
    """C9: Undeclared third-party imports detected.

    Scans all Python files in the specified directories and verifies
    that every ``import X`` and ``from X import Y`` statement references
    a package that is either:
    - In the Python standard library
    - A relative import (``from .module import ...``)
    - A project-local module (top-level package exists in scan_paths)
    - Declared in pyproject.toml or requirements.txt

    Any undeclared third-party import is a BLOCKER violation in S4/S5.

    Args:
        root: Project root directory (for locating dependency files and
              detecting project-local modules).
        scan_paths: List of directories to scan. If None or empty,
              defaults to ``[root]``.

    Returns:
        List of ConstraintViolation (empty if all imports are valid).
    """
    violations: list[ConstraintViolation] = []

    try:
        root_path = Path(root) if isinstance(root, str) else root
    except Exception:
        return violations

    if scan_paths is None:
        scan_paths = [root_path]
    else:
        scan_paths = [Path(p) if isinstance(p, str) else p for p in scan_paths]

    # Defer to the import_checker module for AST scanning
    try:
        from loop_core.import_checker import ImportChecker
    except ImportError:
        logger.warning(
            "import_checker module not available; "
            "C9 import validity check skipped."
        )
        return violations

    try:
        result = ImportChecker.check_directory(
            root=root_path,
            scan_paths=scan_paths,
        )
    except Exception as e:
        logger.warning(
            "C9 import validity check failed: %s", e
        )
        return violations

    for iv in result.violations:
        violations.append(ConstraintViolation(
            constraint_id=ConstraintID.C9_IMPORT_NOT_DECLARED,
            severity=Severity.BLOCKER,
            message=(
                f"Undeclared import '{iv.import_name}' "
                f"in {iv.file_path}:{iv.line_number}"
            ),
            detail=(
                f"File: {iv.file_path}, line {iv.line_number}. "
                f"Import: '{iv.import_name}' is not declared in "
                f"pyproject.toml or requirements.txt, is not a stdlib "
                f"module, and is not a project-local module."
            ),
            remediation=(
                f"Add '{iv.import_name.split('.')[0]}' to the project's "
                f"declared dependencies in pyproject.toml "
                f"([project].dependencies) or requirements.txt."
            ),
        ))

    # If dependency files are missing entirely, add a WARNING (not BLOCKER)
    if result.warnings:
        for w in result.warnings:
            violations.append(ConstraintViolation(
                constraint_id=ConstraintID.C9_IMPORT_NOT_DECLARED,
                severity=Severity.WARNING,
                message=f"Import checker warning: {w}",
                detail=(
                    "Dependency declaration files (pyproject.toml, "
                    "requirements.txt) were not found. Import validation "
                    "may produce false positives."
                ),
                remediation=(
                    "Create a pyproject.toml with [project].dependencies "
                    "or a requirements.txt listing all third-party dependencies."
                ),
            ))

    return violations

# ── C10: Contract Test Coverage ──────────────────────────────────────

def check_c10_contract_test_coverage(
    self,
    root: str | Path | None = None,
    task_id: str | None = None,
) -> list[ConstraintViolation]:
    """C10: Interface contract has required tests missing.

    Reads interface contract files from .ai/evidence/{task_id}/ and
    verifies that every `tests_required` entry has a corresponding test
    function defined in the project's test files.

    This is a SOFT constraint by default (WARNING severity) — it warns
    about missing tests but does not block operations. It can be
    configured as HARD in the task definition.

    If no contract files exist for the task, this check is skipped
    (no violation — not a blocker for projects without contracts).
    """
    violations: list[ConstraintViolation] = []

    if root is None or task_id is None:
        return violations

    try:
        root_path = Path(root) if isinstance(root, str) else root
    except Exception:
        return violations

    # Defer to the contract_verifier module for the heavy lifting
    try:
        from loop_core.contract_verifier import check_contract_test_coverage
    except ImportError:
        logger.warning(
            "contract_verifier module not available; "
            "C10 contract test coverage check skipped."
        )
        return violations

    try:
        raw_violations, has_contracts = check_contract_test_coverage(
            root_path, task_id
        )
    except Exception as e:
        logger.warning(
            "C10 contract test coverage check failed: %s", e
        )
        return violations

    if not has_contracts:
        # No contract files — skip, not a blocker
        return violations

    for rv in raw_violations:
        violations.append(ConstraintViolation(
            constraint_id=ConstraintID.C10_CONTRACT_TEST_MISSING,
            severity=Severity.WARNING,  # SOFT by default
            message=rv.get("message", "Contract test missing"),
            detail=rv.get("detail", ""),
            remediation=rv.get("remediation", ""),
        ))

    return violations

# ── C11: Task File Limit ─────────────────────────────────────────────

def check_c11_file_limit(
    self,
    root: str | Path | None = None,
    task_id: str | None = None,
    max_files: int = 10,
) -> list[ConstraintViolation]:
    """C11: Task's allowed_paths exceeds the maximum file limit.

    Counts the files listed in a task's allowed_paths configuration.
    If the count exceeds max_files, returns a violation.

    Governance files (.ai/* and host-specific governance dirs) are excluded.

    Args:
        root: Project root directory.
        task_id: Task identifier to load the contract for.
        max_files: Maximum number of files allowed (default: 10).

    Returns:
        List of ConstraintViolation (empty if within limit or no task).
    """
    from loop_core.hard_constraints import _parse_allowed_paths_from_markdown
    violations: list[ConstraintViolation] = []

    if root is None or task_id is None:
        return violations

    try:
        root_path = Path(root) if isinstance(root, str) else root
    except Exception:
        return violations

    # Load the task contract to get allowed_paths
    task_path = root_path / ".ai" / "tasks" / f"{task_id}.md"
    if not task_path.is_file():
        return violations

    try:
        text = task_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return violations

    # Parse allowed_paths from the task markdown
    allowed_paths = _parse_allowed_paths_from_markdown(text)

    # Filter out governance files (they don't count toward the limit)
    governance_prefixes = (".ai/",)  # host-specific prefixes injected by adapter
    file_paths = [
        p for p in allowed_paths
        if p and not p.strip().startswith(governance_prefixes)
    ]

    file_count = len(file_paths)
    if file_count > max_files:
        violations.append(ConstraintViolation(
            constraint_id=ConstraintID.C11_TASK_FILE_LIMIT_EXCEEDED,
            severity=Severity.WARNING,  # SOFT by default
            message=(
                f"Task '{task_id}' has {file_count} allowed paths, "
                f"exceeding the limit of {max_files}"
            ),
            detail=(
                f"Allowed paths count: {file_count} (max: {max_files}). "
                f"Paths: {file_paths}. "
                f"Consider splitting this task into smaller, more focused tasks."
            ),
            remediation=(
                f"Reduce the task scope to at most {max_files} file paths. "
                f"Split large tasks into multiple focused tasks, each with "
                f"a narrow scope."
            ),
        ))

    return violations


def _parse_allowed_paths_from_markdown(text: str) -> list[str]:
    """Extract allowed_paths from a task markdown file.

    Handles both YAML code block format and plain list format.
    """
    import re

    paths: list[str] = []
    in_yaml_block = False
    in_allowed_section = False

    for line in text.splitlines():
        stripped = line.strip()

        # Detect YAML code block start/end
        if stripped in ("```yaml", "```yml"):
            in_yaml_block = True
            continue
        if stripped == "```" and in_yaml_block:
            in_yaml_block = False
            in_allowed_section = False
            continue

        if in_yaml_block:
            if stripped.startswith("allowed_paths:"):
                in_allowed_section = True
                continue
            if in_allowed_section and stripped.startswith("- "):
                path = stripped[2:].strip().strip('"').strip("'")
                if path:
                    paths.append(path)
            elif in_allowed_section and not stripped.startswith("- ") and not stripped.startswith("#"):
                in_allowed_section = False
            continue

        # Non-YAML mode: allowed_paths: list
        if stripped.startswith("allowed_paths:") or stripped.startswith("allowed_actions:"):
            in_allowed_section = True
            continue
        if in_allowed_section and stripped.startswith("- "):
            path = stripped[2:].strip().strip('"').strip("'")
            if path:
                paths.append(path)
        elif in_allowed_section and not stripped.startswith("- "):
            in_allowed_section = False

    return paths


