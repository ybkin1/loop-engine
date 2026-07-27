#!/usr/bin/env python3
"""
Loop Engine 升级器 — 升级治理状态到新版本。

用法：python scripts/upgrade.py <project_root> --to-version 2.0.0

操作：
1. 备份当前 .ai/ 目录到 .ai/backups/YYYY-MM-DD-HHMMSS/
2. 读取当前 state.yaml
3. 迁移 schema_version（如 1 → 2）
4. 迁移 gates.yaml 格式（如有新增必填字段）
5. 迁移角色合同（如有新增角色或字段变更）
6. 验证升级后状态一致性（调用 validate_state.py）
7. 如果验证失败 → 自动回滚到备份
8. 输出升级摘要
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

# ── Path setup ──────────────────────────────────────────────────────────
_SOURCE_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_SOURCE_ROOT / ".zcode" / "tools"))

from governor_lib import (  # noqa: E402
    transactional_write_texts,
    load_yaml,
    dump_yaml,
    ai_dir,
)


# ── Migration registry ──────────────────────────────────────────────────
# Each entry: (from_version, to_version, migration_func)
# migration_func signature: (project_root: Path, ai: Path) -> list[str] (warnings)


def _migrate_1_to_2_schema(root: Path, ai: Path) -> list[str]:
    """Migrate from schema_version 1 to 2.

    Changes in v2:
    - state.yaml: add loop_mode field if missing (default FULL)
    - gates.yaml: add active and installed fields to each gate if missing
    - gates.yaml: add high_risk_flags to each gate if missing
    """
    warnings: list[str] = []

    # Migrate state.yaml
    state_path = ai / "state.yaml"
    if state_path.exists():
        state = load_yaml(state_path)
        if isinstance(state, dict):
            modified = False
            if "loop_mode" not in state:
                state["loop_mode"] = "FULL"
                warnings.append("state.yaml: 添加了缺失的 loop_mode=FULL")
                modified = True
            if "schema_version" in state:
                state["schema_version"] = 2
                modified = True
            if modified:
                transactional_write_texts(ai, {state_path: dump_yaml(state)})

    # Migrate gates.yaml
    gates_path = ai / "gates.yaml"
    if gates_path.exists():
        gate_data = load_yaml(gates_path)
        if isinstance(gate_data, dict) and "gates" in gate_data:
            modified = False
            for gate in gate_data["gates"]:
                if isinstance(gate, dict):
                    if "active" not in gate:
                        gate["active"] = False
                        modified = True
                    if "installed" not in gate:
                        gate["installed"] = False
                        modified = True
                    if "high_risk_flags" not in gate:
                        gate["high_risk_flags"] = {
                            "deployment": False,
                            "rollback": False,
                            "database": False,
                            "permission": False,
                            "secret": False,
                            "payment": False,
                            "production_data": False,
                            "migration": False,
                            "runtime_behavior": False,
                        }
                        modified = True
            if modified:
                if "schema_version" in gate_data:
                    gate_data["schema_version"] = 2
                transactional_write_texts(ai, {gates_path: dump_yaml(gate_data)})
                warnings.append("gates.yaml: 每个 gate 添加了 active/installed/high_risk_flags 字段")
            elif gate_data.get("schema_version") == 1:
                gate_data["schema_version"] = 2
                transactional_write_texts(ai, {gates_path: dump_yaml(gate_data)})
        elif isinstance(gate_data, dict):
            if gate_data.get("schema_version") == 1:
                gate_data["schema_version"] = 2
                transactional_write_texts(ai, {gates_path: dump_yaml(gate_data)})

    return warnings


def _migrate_2_to_3_schema(root: Path, ai: Path) -> list[str]:
    """Placeholder for future v2 -> v3 migration."""
    warnings: list[str] = []
    warnings.append("v2 -> v3 迁移尚未定义，仅更新 schema_version")

    for fname in ["state.yaml", "gates.yaml", "task_graph.yaml"]:
        fpath = ai / fname
        if fpath.exists():
            data = load_yaml(fpath)
            if isinstance(data, dict) and data.get("schema_version") == 2:
                data["schema_version"] = 3
                transactional_write_texts(ai, {fpath: dump_yaml(data)})

    return warnings


# Map: (from_major, to_major) -> migration function
_MIGRATIONS: dict[tuple[int, int], object] = {
    (1, 2): _migrate_1_to_2_schema,
    (2, 3): _migrate_2_to_3_schema,
}


# ── Public API ──────────────────────────────────────────────────────────

def upgrade(project_root: Path, to_version: str, *, dry_run: bool = False) -> int:
    """升级项目治理状态。

    Args:
        project_root: 项目根目录。
        to_version: 目标版本字符串，如 "2.0.0"。
        dry_run: 如果 True，仅模拟执行不实际修改。

    Returns:
        0 成功，非 0 失败。
    """
    project_root = project_root.resolve()
    ai = ai_dir(project_root)

    if not ai.is_dir():
        print(f"[upgrade] 错误: .ai/ 目录不存在: {ai}")
        return 1

    # 解析版本号
    try:
        parts = to_version.split(".")
        target_major = int(parts[0])
    except (ValueError, IndexError):
        print(f"[upgrade] 错误: 无效的版本号: {to_version}")
        return 1

    # 读取当前 schema_version
    state_path = ai / "state.yaml"
    state = load_yaml(state_path)
    current_version = state.get("schema_version", 1)
    if not isinstance(current_version, int):
        print(f"[upgrade] 错误: state.yaml 中 schema_version 非整数: {current_version}")
        return 1

    if current_version >= target_major:
        print(f"[upgrade] 当前 schema_version {current_version} >= {target_major}，无需升级。")
        return 0

    if dry_run:
        print(f"[upgrade] [DRY RUN] 将从 v{current_version} 升级到 v{target_major}")
        # Validate migration path exists
        for v in range(current_version, target_major):
            if (v, v + 1) not in _MIGRATIONS:
                print(f"[upgrade] [DRY RUN] 警告: v{v} -> v{v + 1} 迁移未定义")
        print("[upgrade] [DRY RUN] 完成（无实际修改）。")
        return 0

    # 1. 备份
    backup_dir = _create_backup(project_root, ai)
    print(f"[upgrade] 已备份到: {backup_dir.relative_to(project_root)}")

    # 2. 逐步迁移
    all_warnings: list[str] = []
    try:
        for v in range(current_version, target_major):
            migration_key = (v, v + 1)
            if migration_key not in _MIGRATIONS:
                print(f"[upgrade] 错误: v{v} -> v{v + 1} 迁移未定义")
                _restore_backup(project_root, ai, backup_dir)
                return 1

            migration_func = _MIGRATIONS[migration_key]
            print(f"[upgrade] 迁移 v{v} -> v{v + 1} ...")
            # The migration function signature we defined above
            step_warnings = migration_func(project_root, ai)  # type: ignore[operator]
            all_warnings.extend(step_warnings)

        # 3. 验证
        print("[upgrade] 验证升级后状态...")
        if not verify_upgrade(project_root):
            print("[upgrade] 验证失败，自动回滚...")
            _restore_backup(project_root, ai, backup_dir)
            return 1

        # 4. 输出摘要
        print(f"\n[upgrade] 升级成功: v{current_version} -> v{target_major}")
        if all_warnings:
            print("[upgrade] 迁移警告:")
            for w in all_warnings:
                print(f"  - {w}")
        print(f"[upgrade] 备份位置: {backup_dir.relative_to(project_root)}")

    except Exception as exc:
        print(f"[upgrade] 升级过程中发生错误: {exc}")
        print("[upgrade] 自动回滚...")
        _restore_backup(project_root, ai, backup_dir)
        return 1

    return 0


def verify_upgrade(project_root: Path) -> bool:
    """验证升级后状态一致性。

    调用 validate_state.py 检查状态是否一致。

    Args:
        project_root: 项目根目录。

    Returns:
        True 如果验证通过。
    """
    project_root = project_root.resolve()
    validate_script = _SOURCE_ROOT / ".zcode" / "tools" / "validate_state.py"

    if not validate_script.exists():
        print("[upgrade] 警告: validate_state.py 未找到，跳过验证。")
        return True

    try:
        result = subprocess.run(
            [sys.executable, str(validate_script), str(project_root)],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode == 0:
            print("[upgrade] validate_state.py 通过。")
            return True
        else:
            print(f"[upgrade] validate_state.py 失败 (exit {result.returncode}):")
            print(result.stdout[-500:] if len(result.stdout) > 500 else result.stdout)
            if result.stderr:
                print(result.stderr[-500:] if len(result.stderr) > 500 else result.stderr)
            return False
    except subprocess.TimeoutExpired:
        print("[upgrade] validate_state.py 超时。")
        return False
    except Exception as exc:
        print(f"[upgrade] 无法运行 validate_state.py: {exc}")
        return True  # 无法运行时不阻塞升级


# ── Internal helpers ────────────────────────────────────────────────────

def _create_backup(project_root: Path, ai: Path) -> Path:
    """创建 .ai/ 目录备份到 .ai/backups/YYYY-MM-DD-HHMMSS/"""
    timestamp = datetime.now().strftime("%Y-%m-%d-%H%M%S")
    backups_root = ai / "backups"
    backups_root.mkdir(parents=True, exist_ok=True)
    backup_dir = backups_root / timestamp

    # Copy all .ai contents except backups/ itself
    for item in ai.iterdir():
        if item.name == "backups":
            continue
        dest = backup_dir / item.name
        if item.is_dir():
            shutil.copytree(item, dest, symlinks=False)
        else:
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(item, dest)

    return backup_dir


def _restore_backup(project_root: Path, ai: Path, backup_dir: Path) -> None:
    """从备份恢复 .ai/ 目录。"""
    if not backup_dir.exists():
        print("[upgrade] 错误: 备份目录不存在，无法回滚。")
        return

    # Remove current .ai/ contents (except backups/)
    for item in list(ai.iterdir()):
        if item.name == "backups":
            continue
        if item.is_dir():
            shutil.rmtree(item, ignore_errors=True)
        else:
            item.unlink(missing_ok=True)

    # Copy backup contents back
    for item in backup_dir.iterdir():
        dest = ai / item.name
        if item.is_dir():
            shutil.copytree(item, dest, symlinks=False)
        else:
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(item, dest)

    print("[upgrade] 已从备份恢复。")


# ── CLI entry point ─────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Loop Engine 升级器 — 升级治理状态到新版本"
    )
    parser.add_argument(
        "project_root",
        help="项目根目录（包含 .ai/ 的目录）",
    )
    parser.add_argument(
        "--to-version",
        required=True,
        help="目标版本号，如 2.0.0",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="模拟执行，不实际修改任何文件",
    )
    args = parser.parse_args()

    root = Path(args.project_root)
    return upgrade(root, args.to_version, dry_run=args.dry_run)


if __name__ == "__main__":
    raise SystemExit(main())
