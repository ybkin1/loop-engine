#!/usr/bin/env python3
"""
gov_delegation.py — T-0134 P4 委托链管理工具（授权模型 v2）。

委托链 = 用户一次批准覆盖链内任务（含未来登记任务）的自治执行授权；
规则层（AGENTS.md / forbidden 语义 / EVIDENCE_ONLY_BOUNDARY）不因委托豁免。

用法：
    python gov_delegation.py <root> register --chain C-001 --tasks T-A,T-B [--note ...]
    python gov_delegation.py <root> revoke --chain C-001
    python gov_delegation.py <root> status [--chain C-001]
    python gov_delegation.py <root> check --task T-A      # 0=链内active / 2=非链内或已revoke

delegations 记录于 .ai/gates.yaml 顶层 delegations 列表（append-only，revoke
不删除记录只改 status）。
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path


def _load_gates(root: Path) -> dict:
    import yaml
    return yaml.safe_load((root / ".ai" / "gates.yaml").read_text(encoding="utf-8")) or {}


def _save_gates(root: Path, doc: dict) -> None:
    import yaml
    (root / ".ai" / "gates.yaml").write_text(
        yaml.safe_dump(doc, allow_unicode=True, sort_keys=False), encoding="utf-8")


def active_delegations(root: Path) -> list[dict]:
    """返回 status=active 的委托链列表。"""
    doc = _load_gates(root)
    return [d for d in doc.get("delegations", []) if d.get("status") == "active"]


def task_in_active_delegation(root: Path, task_id: str) -> bool:
    """任务是否在任一 active 委托链内。"""
    for d in active_delegations(root):
        if task_id in d.get("task_ids", []):
            return True
    return False


def register(root: Path, chain_id: str, task_ids: list[str], note: str = "") -> None:
    doc = _load_gates(root)
    delegations = doc.setdefault("delegations", [])
    if any(d.get("chain_id") == chain_id for d in delegations):
        print(f"[delegation] chain {chain_id} already exists (use revoke/register)")
        sys.exit(2)
    delegations.append({
        "chain_id": chain_id,
        "task_ids": task_ids,
        "status": "active",
        "approved_by": "user",
        "approved_at": datetime.now(timezone.utc).isoformat(),
        "note": note,
    })
    _save_gates(root, doc)
    print(f"[delegation] registered {chain_id}: tasks={task_ids} (active)")


def revoke(root: Path, chain_id: str) -> None:
    doc = _load_gates(root)
    delegations = doc.setdefault("delegations", [])
    for d in delegations:
        if d.get("chain_id") == chain_id:
            d["status"] = "revoked"
            d["revoked_at"] = datetime.now(timezone.utc).isoformat()
            _save_gates(root, doc)
            print(f"[delegation] revoked {chain_id}")
            return
    print(f"[delegation] chain {chain_id} not found")
    sys.exit(2)


def status(root: Path, chain_id: str | None = None) -> None:
    doc = _load_gates(root)
    delegations = doc.get("delegations", [])
    for d in delegations:
        if chain_id and d.get("chain_id") != chain_id:
            continue
        print(f"{d['chain_id']}: {d['status']} tasks={d.get('task_ids')} "
              f"approved_at={d.get('approved_at', '')[:19]}")
    if not delegations:
        print("[delegation] no delegations registered")


def main() -> int:
    parser = argparse.ArgumentParser(description="T-0134 delegation chain tool")
    parser.add_argument("root")
    sub = parser.add_subparsers(dest="command", required=True)

    p_reg = sub.add_parser("register")
    p_reg.add_argument("--chain", required=True)
    p_reg.add_argument("--tasks", required=True, help="comma-separated task ids")
    p_reg.add_argument("--note", default="")

    p_rev = sub.add_parser("revoke")
    p_rev.add_argument("--chain", required=True)

    p_st = sub.add_parser("status")
    p_st.add_argument("--chain", default=None)

    p_chk = sub.add_parser("check")
    p_chk.add_argument("--task", required=True)

    args = parser.parse_args()
    root = Path(args.root).resolve()
    if args.command == "register":
        register(root, args.chain, [t.strip() for t in args.tasks.split(",") if t.strip()],
                 args.note)
    elif args.command == "revoke":
        revoke(root, args.chain)
    elif args.command == "status":
        status(root, args.chain)
    elif args.command == "check":
        if task_in_active_delegation(root, args.task):
            print(f"[delegation] task {args.task} is in an active delegation")
            return 0
        print(f"[delegation] task {args.task} NOT in an active delegation (fail-closed)")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
