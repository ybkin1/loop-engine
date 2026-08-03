"""
Contract-to-Test Coverage Verifier.

Reads interface contract files from .ai/evidence/{task_id}/ and verifies
that every `tests_required` entry has a corresponding test function in the
project's test files. Returns violations when required tests are missing.

This is a read-only module — it never modifies files.
"""
from __future__ import annotations

import json
import logging
import os
import re
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

# Recognized contract file names (ordered by priority)
CONTRACT_FILE_NAMES = [
    "interface-contract.yaml",
    "interface-contract.yml",
    "interface-contract.json",
]

# Default test directory relative to project root
DEFAULT_TEST_DIR = "tests"


# ── Data Structures ──────────────────────────────────────────────────────

class ContractTestDef:
    """A single contract entry with its required tests."""
    function: str
    tests_required: list[str]

    def __init__(self, function: str, tests_required: list[str]):
        self.function = function
        self.tests_required = list(tests_required)


class ContractTestResult:
    """Result of verifying a contract against test files."""

    def __init__(
        self,
        contract_path: str,
        found_tests: list[str],
        missing_tests: list[str],
    ):
        self.contract_path = contract_path
        self.found_tests = found_tests
        self.missing_tests = missing_tests

    @property
    def is_clean(self) -> bool:
        """True if no tests are missing."""
        return len(self.missing_tests) == 0


# ── Finder ───────────────────────────────────────────────────────────────

def find_contract_files(root: Path, task_id: str) -> list[Path]:
    """Find interface contract files for a given task_id.

    Searches:
      1. .ai/evidence/{task_id}/interface-contract.{yaml,yml,json}
      2. .ai/evidence/{task_id}/contracts/*.{yaml,yml,json}
      3. .ai/evidence/{task_id}/*-contract.{yaml,yml,json}

    Returns a list of matching Path objects (may be empty).
    """
    evidence_dir = root / ".ai" / "evidence" / task_id
    if not evidence_dir.is_dir():
        return []

    found: list[Path] = []

    # 1. Direct contract files at the evidence dir root
    for name in CONTRACT_FILE_NAMES:
        candidate = evidence_dir / name
        if candidate.is_file():
            found.append(candidate)

    # 2. contracts/ subdirectory
    contracts_dir = evidence_dir / "contracts"
    if contracts_dir.is_dir():
        for entry in contracts_dir.iterdir():
            if entry.is_file() and entry.suffix in (".yaml", ".yml", ".json"):
                found.append(entry)

    # 3. *-contract.{yaml,yml,json} files at root
    for entry in evidence_dir.iterdir():
        if entry.is_file() and entry.name.endswith("-contract.yaml") or \
           entry.is_file() and entry.name.endswith("-contract.yml") or \
           entry.is_file() and entry.name.endswith("-contract.json"):
            # Avoid double counting files already found via #1
            if entry not in found:
                found.append(entry)

    return found


# ── Parser ───────────────────────────────────────────────────────────────

def _parse_yaml_content(text: str) -> dict[str, Any]:
    """Parse YAML text into a dict.

    T-0107 D5-5: fallback 触发条件收窄——仅当 PyYAML 不可导入
    （ImportError）时才用位置推断重建结构；PyYAML 解析失败（语法错误等）
    不再静默降级到 pattern 解析，而是告警并返回空结构（fail-closed：
    不基于可能不完整的重建结果做覆盖判定）。fallback 产出去向标注
    （``_parsed_by`` 字段），字段完整性由契约测试覆盖。
    """
    try:
        import yaml  # type: ignore
        try:
            data = yaml.safe_load(text) or {}
            return data if isinstance(data, dict) else {}
        except Exception as exc:
            logger.warning(
                "PyYAML parse failed for contract content (%s); "
                "contract treated as empty (no pattern fallback)", exc,
            )
            return {"contracts": []}
    except ImportError:
        logger.warning(
            "PyYAML unavailable; using pattern-based fallback for contract "
            "content (fallback output may be incomplete)"
        )

    # Fallback: basic pattern-based parsing for the expected contract format.
    # Reached ONLY on ImportError (T-0107 D5-5). Output provenance annotated.
    result: dict[str, Any] = {"contracts": [], "_parsed_by": "pattern-fallback"}
    current_contract: dict[str, Any] | None = None

    for line in text.splitlines():
        stripped = line.strip()

        # Detect contract entry: "- function: <name>"
        m = re.match(r'^\s*-\s*function:\s*(.+)$', stripped)
        if m:
            if current_contract:
                result["contracts"].append(current_contract)
            current_contract = {
                "function": m.group(1).strip().strip('"').strip("'"),
                "tests_required": [],
            }
            continue

        # Detect tests_required list items: "- test_xxx"
        if current_contract:
            m = re.match(r'^\s*-\s*(test_\w+)\s*$', stripped)
            if m:
                current_contract.setdefault("tests_required", []).append(m.group(1))
                continue

    if current_contract:
        result["contracts"].append(current_contract)

    return result


def _parse_json_content(text: str) -> dict[str, Any]:
    """Parse JSON text into a dict."""
    data = json.loads(text)
    if not isinstance(data, dict):
        return {"contracts": []}
    return data


def parse_contract(file_path: Path) -> list[ContractTestDef]:
    """Parse a contract file and extract the list of ContractTestDef entries.

    Supports YAML (.yaml, .yml) and JSON (.json) formats.

    Returns an empty list if the file is missing or unparseable.
    """
    if not file_path.is_file():
        return []

    try:
        text = file_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as e:
        logger.warning("Cannot read contract file %s: %s", file_path, e)
        return []

    suffix = file_path.suffix.lower()
    try:
        if suffix in (".yaml", ".yml"):
            data = _parse_yaml_content(text)
        elif suffix == ".json":
            data = _parse_json_content(text)
        else:
            return []
    except Exception as e:
        logger.warning("Cannot parse contract file %s: %s", file_path, e)
        return []

    contracts_raw = data.get("contracts", [])
    if not isinstance(contracts_raw, list):
        return []

    result: list[ContractTestDef] = []
    for entry in contracts_raw:
        if not isinstance(entry, dict):
            continue
        func_name = entry.get("function")
        tests = entry.get("tests_required", [])
        if func_name and isinstance(tests, list):
            result.append(ContractTestDef(
                function=str(func_name),
                tests_required=[str(t) for t in tests],
            ))

    return result


# ── Test Finder ──────────────────────────────────────────────────────────

def find_test_files(root: Path, test_dir: str = DEFAULT_TEST_DIR) -> list[Path]:
    """Find all Python test files in the project's test directory.

    Returns Path objects for files matching test_*.py or *_test.py.
    """
    td = root / test_dir
    if not td.is_dir():
        return []

    test_files: list[Path] = []
    for entry in sorted(td.rglob("*.py")):
        if entry.is_file() and (
            entry.name.startswith("test_") or entry.name.endswith("_test.py")
        ):
            test_files.append(entry)
    return test_files


def _function_exists_in_file(file_path: Path, function_name: str) -> bool:
    """Check if a function with the given name is defined in a Python file.

    Uses a regex-based scan that matches 'def function_name(' at the start
    of a line or after whitespace (class methods included).
    """
    if not file_path.is_file():
        return False

    try:
        text = file_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return False

    # Match 'def function_name(' — accounts for indentation (module-level or method)
    pattern = re.compile(
        r'^\s*def\s+' + re.escape(function_name) + r'\s*\(',
        re.MULTILINE,
    )
    return bool(pattern.search(text))


def find_test_functions(
    root: Path,
    required_functions: list[str],
    test_dir: str = DEFAULT_TEST_DIR,
) -> tuple[list[str], list[str]]:
    """Check which required test functions exist in the project's test files.

    Args:
        root: Project root directory.
        required_functions: List of test function names to look for.
        test_dir: Relative path to the test directory (default: "tests").

    Returns:
        A tuple of (found_functions, missing_functions).
    """
    test_files = find_test_files(root, test_dir=test_dir)
    found: list[str] = []
    missing: list[str] = []

    for func_name in required_functions:
        func_found = False
        for tf in test_files:
            if _function_exists_in_file(tf, func_name):
                found.append(func_name)
                func_found = True
                break
        if not func_found:
            missing.append(func_name)

    return found, missing


# ── Verifier ─────────────────────────────────────────────────────────────

def verify_contract_coverage(
    root: Path,
    task_id: str,
    test_dir: str = DEFAULT_TEST_DIR,
) -> list[ContractTestResult]:
    """Verify that all interface contracts for a task have their required tests.

    Args:
        root: Project root directory.
        task_id: Task identifier (e.g., "T-0050").
        test_dir: Relative path to test directory (default: "tests").

    Returns:
        List of ContractTestResult, one per contract file found.
        Empty list if no contract files exist for the task.
    """
    contract_files = find_contract_files(root, task_id)
    if not contract_files:
        return []

    results: list[ContractTestResult] = []
    for cf in contract_files:
        entries = parse_contract(cf)
        if not entries:
            continue

        all_required: list[str] = []
        for entry in entries:
            all_required.extend(entry.tests_required)

        all_required = list(dict.fromkeys(all_required))  # deduplicate, preserve order

        if not all_required:
            continue

        found, missing = find_test_functions(root, all_required, test_dir=test_dir)
        results.append(ContractTestResult(
            contract_path=str(cf.relative_to(root)) if cf.is_relative_to(root) else str(cf),
            found_tests=found,
            missing_tests=missing,
        ))

    return results


# ── Hard Constraints Integration ─────────────────────────────────────────

def check_contract_test_coverage(
    root: Path,
    task_id: str,
) -> tuple[list[dict[str, Any]], bool]:
    """Check contract-to-test coverage and return violation dicts.

    Designed to be called from HardConstraints.check_c10_contract_test_coverage().

    Args:
        root: Project root directory.
        task_id: Task identifier.

    Returns:
        Tuple of (violations_list, has_contracts).
        - violations_list: List of violation dicts with keys: message, detail,
          remediation, missing_tests, contract_path.
        - has_contracts: True if at least one contract file was found.
          False means no contracts exist (caller should skip / not block).
    """
    results = verify_contract_coverage(root, task_id)
    if not results:
        return [], False

    violations: list[dict[str, Any]] = []
    for result in results:
        if not result.is_clean:
            violations.append({
                "contract_path": result.contract_path,
                "missing_tests": result.missing_tests,
                "found_tests": result.found_tests,
                "message": (
                    f"Contract '{result.contract_path}' is missing "
                    f"{len(result.missing_tests)} required test(s)"
                ),
                "detail": (
                    f"Missing tests: {result.missing_tests}. "
                    f"Found tests: {result.found_tests}. "
                    f"Each interface contract function must have its "
                    f"tests_required implemented before the task is complete."
                ),
                "remediation": (
                    f"Create test file(s) with the missing test functions: "
                    f"{result.missing_tests}. "
                    f"Tests should be placed in the '{DEFAULT_TEST_DIR}/' directory."
                ),
            })

    return violations, True
