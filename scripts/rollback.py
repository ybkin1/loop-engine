#!/usr/bin/env python3
"""
Loop Engine 回滚器 — 回滚治理状态到之前的备份。

用法: python scripts/rollback.py <project_root> [--to-backup <backup_dir>]

操作:
1. 列出可用备份（.ai/backups/ 下）
2. 如果指定 --to-backup，使用指定备份
3. 否则使用最新备份
4. 将当前 .ai/ 备份（安全措施）
5. 将备份恢复到 .ai/
6. 验证恢复后状态（validate_state.py）
7. 如果不一致 → 恢复到回滚前的状态
8. 输出回滚摘要
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# ── Path setup ──────────────────────────────────────────────────────────
_SOURCE_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_SOURCE_ROOT / ".zcode" / "tools"))

from governor_lib import ai_dir, load_yaml  # noqa: E402


# ── Public API ──────────────────────────────────────────────────────────

def list_backups(project_root: Path) -> list[Path]:
    """列出所有可用备份，按时间降序排列。

    Args:
        project_root: 项目根目录。

    Returns:
        备份目录 Path 列表，最新的在前。
    """
    ai = ai_dir(project_root)
    backups_root = ai / "backups"
    if not backups_root.is_dir():
        return []

    result = []
    for item in backups_root.iterdir():
        if item.is_dir():
            result.append(item)
    result.sort(reverse=True)
    return result


def rollback(project_root: Path, backup_dir: str | None = None,
             *, dry_run: bool = False) -> int:
    """回滚项目治理状态。

    Args:
        project_root: 项目根目录。
        backup_dir: 指定备份目录名（如 "2026-07-23-150000"）或 None 使用最新。
        dry_run: 如果 True，仅模拟执行不实际修改。

    Returns:
        0 成功，非 0 失败。
    """
    project_root = project_root.resolve()
    ai = ai_dir(project_root)

    if not ai.is_dir():
        print(f"[rollback] 错误: .ai/ 目录不存在: {ai}")
        return 1

    backups = list_backups(project_root)

    if not backups:
        print("[rollback] 错误: 没有可用的备份。")
        return 1

    # 选择备份
    if backup_dir:
        backup_name = Path(backup_dir).name
        target_backup = ai / "backups" / backup_name
        if not target_backup.is_dir():
            print(f"[rollback] 错误: 指定的备份不存在: {target_backup}")
            print("[rollback] 可用备份:")
            for b in backups:
                print(f"  - {b.name}")
            return 1
    else:
        target_backup = backups[0]
        print(f"[rollback] 使用最新备份: {target_backup.name}")

    if dry_run:
        print(f"[rollback] [DRY RUN] 将从备份恢复: {target_backup.name}")
        state_in_backup = target_backup / "state.yaml"
        if state_in_backup.exists():
            try:
                state = load_yaml(state_in_backup)
                phase = state.get("current_phase", "unknown")
                task_id = state.get("current_task_id", "none")
                print(f"[rollback] [DRY RUN] 备份状态: phase={phase}, task={task_id}")
            except Exception:
                pass
        print("[rollback] [DRY RUN] 完成（无实际修改）。")
        return 0

    # 1. 备份当前状态（安全措施）
    timestamp = datetime.now().strftime("%Y-%m-%d-%H%M%S")
    pre_rollback_backup = ai / "backups" / f"pre-rollback-{timestamp}"
    _copy_ai_contents(ai, pre_rollback_backup)
    print(f"[rollback] 当前状态已备份到: {pre_rollback_backup.name}")

    # 2. 执行回滚
    try:
        _restore_from_backup(ai, target_backup)
        print(f"[rollback] 已从备份恢复: {target_backup.name}")

        # 3. 验证
        print("[rollback] 验证回滚后状态...")
        if not _verify_state(project_root):
            print("[rollback] 验证失败，回滚到回滚前状态...")
            _restore_from_backup(ai, pre_rollback_backup)
            return 1

        # 4. 输出摘要
        print(f"\n[rollback] 回滚成功。")
        if target_backup / "state.yaml":
            try:
                state = load_yaml(target_backup / "state.yaml")
                print(f"[rollback] 恢复后 phase: {state.get('current_phase', 'unknown')}")
                print(f"[rollback] 恢复后 task: {state.get('current_task_id', 'none')}")
            except Exception:
                pass
        print(f"[rollback] 回滚前状态备份: {pre_rollback_backup.name}")

    except Exception as exc:
        print(f"[rollback] 回滚过程中发生错误: {exc}")
        print("[rollback] 尝试恢复到回滚前状态...")
        try:
            _restore_from_backup(ai, pre_rollback_backup)
        except Exception as exc2:
            print(f"[rollback] 恢复失败: {exc2}")
            print(f"[rollback] 手动恢复请使用: {pre_rollback_backup}")
        return 1

    return 0


# ── Internal helpers ────────────────────────────────────────────────────

def _copy_ai_contents(ai: Path, dest: Path) -> None:
    """复制 .ai/ 所有内容到 dest（排除 backups/）。"""
    dest.mkdir(parents=True, exist_ok=True)
    for item in ai.iterdir():
        if item.name == "backups":
            continue
        dst = dest / item.name
        if item.is_dir():
            shutil.copytree(item, dst, symlinks=False)
        else:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(item, dst)


def _restore_from_backup(ai: Path, backup_dir: Path) -> None:
    """从备份目录恢复 .ai/ 内容。"""
    if not backup_dir.is_dir():
        raise FileNotFoundError(f"备份目录不存在: {backup_dir}")

    # 删除当前 .ai/ 内容（排除 backups/ 和 backup_dir 自身）
    for item in list(ai.iterdir()):
        if item.name == "backups":
            continue
        if item.is_dir():
            shutil.rmtree(item, ignore_errors=True)
        else:
            item.unlink(missing_ok=True)

    # 复制备份内容
    for item in backup_dir.iterdir():
        dest = ai / item.name
        if item.is_dir():
            if dest.exists():
                shutil.rmtree(dest, ignore_errors=True)
            shutil.copytree(item, dest, symlinks=False)
        else:
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(item, dest)


def _verify_state(project_root: Path) -> bool:
    """运行 validate_state.py 验证状态一致性。"""
    validate_script = _SOURCE_ROOT / ".zcode" / "tools" / "validate_state.py"

    if not validate_script.exists():
        print("[rollback] 警告: validate_state.py 未找到，跳过验证。")
        return True

    try:
        result = subprocess.run(
            [sys.executable, str(validate_script), str(project_root)],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode == 0:
            print("[rollback] validate_state.py 通过。")
            return True
        else:
            print(f"[rollback] validate_state.py 失败 (exit {result.returncode}):")
            print(result.stdout[-500:] if len(result.stdout) > 500 else result.stdout)
            if result.stderr:
                print(result.stderr[-500:] if len(result.stderr) > 500 else result.stderr)
            return False
    except subprocess.TimeoutExpired:
        print("[rollback] validate_state.py 超时。")
        return False
    except Exception as exc:
        print(f"[rollback] 无法运行 validate_state.py: {exc}")
        return True  # 无法运行时不阻塞回滚


# ── CLI entry point ─────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Loop Engine 回滚器 — 回滚治理状态到之前的备份"
    )
    parser.add_argument(
        "project_root",
        help="项目根目录（包含 .ai/ 的目录）",
    )
    parser.add_argument(
        "--to-backup",
        default=None,
        help="指定备份目录名（如 2026-07-23-150000），不指定则使用最新",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="仅列出可用备份",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="模拟执行，不实际修改任何文件",
    )
    args = parser.parse_args()

    root = Path(args.project_root)

    if args.list:
        backups = list_backups(root)
        if not backups:
            print("没有可用的备份。")
            return 0
        print("可用备份:")
        for b in backups:
            state_in_backup = b / "state.yaml"
            extra = ""
            if state_in_backup.exists():
                try:
                    s = load_yaml(state_in_backup)
                    extra = f"  phase={s.get('current_phase', '?')}  task={s.get('current_task_id', 'none')}"
                except Exception:
                    pass
            print(f"  - {b.name}{extra}")
        return 0

    return rollback(root, args.to_backup, dry_run=args.dry_run)


if __name__ == "__main__":
    raise SystemExit(main())
