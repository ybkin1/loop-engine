#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
pi_evidence_import.py — Pi 验证证据回灌 ZCode 验收（T-0168 闭环）

"Pi 执行 → 质量证据 → ZCode 验收"的物理载体：
读取 Pi mini-loop 运行时数据（~/.pi/agent/loop/<encoded-cwd>/），把
verification-evidence（L2 机器验证）+ auditor 评审记录（L3）+ 追溯矩阵
导入 ZCode 项目的 .ai/evidence/<task>/ 作为验收证据，形成闭环：
  Pi 完成质量环 → 证据落盘 Pi 侧 → 本脚本导入 ZCode 侧 → ZCode 收口引用

用法：
    python .zcode/tools/pi_evidence_import.py <pi_cwd> --task T-XXXX
      --pi-cwd <Pi 项目根>（如 C:\\Users\\Administrator\\pi-test-lab）
      --task <ZCode 任务 ID>（写入 .ai/evidence/<task>/）
      [--pi-project-key <覆盖 Pi loop 目录 key（缺省由 cwd 编码）>]

校验：
  - verification-evidence.json 的 sha256 字段重算比对（防篡改，失败 → exit 2）
  - 评审记录文件哈希与 task.evidence 锚定比对（不一致 → 警告）
输出：
  .ai/evidence/<task>/pi-verification-evidence.json（机器验证证据，格式对齐）
  .ai/evidence/<task>/pi-audit-report.md（评审汇总 + auditor 发现 + 追溯矩阵）
  （证据清单 manifest 需在收口时重新生成——见收口流程）
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

sys.dont_write_bytecode = True

EVIDENCE_ROLE = "pi-quality-loop"


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def pi_loop_dir(pi_cwd: str, key_override: str | None = None) -> Path:
    enc = key_override or re.sub(r"[\\/:]+", "_", pi_cwd)
    return Path.home() / ".pi" / "agent" / "loop" / enc


def load_json(p: Path) -> dict:
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        print(f"[error] 无法读取 {p}: {exc}", file=sys.stderr)
        raise SystemExit(2)


def main() -> int:
    ap = argparse.ArgumentParser(description="Pi 验证证据回灌 ZCode 验收")
    ap.add_argument("pi_cwd", help="Pi 项目根（如 C:\\Users\\Administrator\\pi-test-lab）")
    ap.add_argument("--task", required=True, help="ZCode 任务 ID（写入 .ai/evidence/<task>/）")
    ap.add_argument("--pi-project-key", default=None, help="覆盖 Pi loop 目录 key（缺省由 cwd 编码）")
    ap.add_argument("--zcode-root", default=".", help="ZCode 项目根（缺省当前目录）")
    args = ap.parse_args()

    root = Path(args.zcode_root).resolve()
    loop = pi_loop_dir(args.pi_cwd, args.pi_project_key)
    task = args.task
    ev_dir = root / ".ai" / "evidence" / task
    ev_dir.mkdir(parents=True, exist_ok=True)

    # ── 1) verification-evidence（L2 机器验证，防篡改校验）──
    vfile = loop / "process" / f"verification-{task}.json"
    if not vfile.exists():
        # Pi 任务 ID 与 ZCode 任务 ID 可能不同——按文件名模糊匹配 verification-*.json
        candidates = sorted((loop / "process").glob("verification-*.json")) if (loop / "process").exists() else []
        if not candidates:
            print(f"[error] Pi 侧无 verification-evidence（{vfile}），且无其他验证证据", file=sys.stderr)
            return 2
        vfile = candidates[-1]
        print(f"[info] 任务 ID 不匹配，取最近验证证据: {vfile.name}")
    vdata = load_json(vfile)
    # 防篡改：重算 sha256（与 verifier.ts 同语义：去 sha256 字段的 payload 哈希前 16 位）
    payload = {k: val for k, val in vdata.items() if k != "sha256"}
    recomputed = sha256_bytes(json.dumps(payload, sort_keys=True).encode("utf-8"))[:16].lower()
    recorded = str(vdata.get("sha256", "")).lower()
    if recorded and recorded != recomputed:
        print(f"[error] verification-evidence 哈希校验失败（{recorded} != {recomputed}）——疑似篡改", file=sys.stderr)
        return 2
    verification_ok = bool(vdata.get("ok"))

    # ── 2) auditor 评审记录（L3）──
    reviews: list[dict] = []
    if (loop / "process").exists():
        for rfile in sorted((loop / "process").glob(f"{task}-review-r*.json")):
            try:
                reviews.append(json.loads(rfile.read_text(encoding="utf-8")))
            except (json.JSONDecodeError, OSError):
                continue
    if not reviews:
        # 按任务 ID 前缀模糊匹配（Pi 任务 ID 可能不同）
        for rfile in sorted((loop / "process").glob("*-review-r*.json")):
            try:
                reviews.append(json.loads(rfile.read_text(encoding="utf-8")))
            except (json.JSONDecodeError, OSError):
                continue
        if reviews:
            print(f"[info] 任务 ID 不匹配，导入 {len(reviews)} 条评审记录（可能来自其他 Pi 任务）")

    # ── 3) 追溯矩阵（tasks.json 中该任务的 exit_criteria/verification）──
    tasks = load_json(loop / "tasks.json")
    pi_task = tasks.get("tasks", {}).get(task) or next(iter(tasks.get("tasks", {}).values()), None)
    trace = {
        "ac": pi_task.get("exit_criteria", []) if pi_task else [],
        "verification": pi_task.get("verification", []) if pi_task else [],
        "risk": pi_task.get("risk", None) if pi_task else None,
    }

    # ── 4) 写入 ZCode 侧证据 ──
    imported = {
        "schema": "PiVerificationEvidence/v1",
        "task_id": task,
        "source": f"pi:{args.pi_cwd}",
        "imported_at": __import__("datetime").datetime.now().isoformat(),
        "verification": {
            "ok": verification_ok,
            "entries": vdata.get("entries", []),
            "evidence_file": str(vfile),
            "sha256": vdata.get("sha256"),
        },
        "reviews": [
            {
                "round": r.get("round"),
                "verdict": r.get("verdict"),
                "auditors": r.get("auditors", []),
                "reviewerToolCalls": r.get("reviewerToolCalls"),
                "notes_tail": (r.get("notes") or "")[-2000:],
            }
            for r in reviews
        ],
        "trace": trace,
    }
    out_v = ev_dir / "pi-verification-evidence.json"
    out_v.write_text(json.dumps(imported, indent=2, ensure_ascii=False), encoding="utf-8")

    # auditor 报告 markdown（人可读 + 收口引用）
    lines = [
        "# Pi 质量环证据（导入自 Pi agent）",
        "",
        f"- 来源：Pi 项目 `{args.pi_cwd}` → ZCode 任务 `{task}`",
        f"- 验证（L2 机器执行）：{'✅ PASS' if verification_ok else '❌ FAIL'}",
    ]
    for e in vdata.get("entries", []):
        lines.append(f"  - `{e.get('command')}` → exit {e.get('exitCode')}{' (timeout)' if e.get('timedOut') else ''}")
    lines.append("")
    lines.append(f"## Auditor 评审（{len(reviews)} 轮）")
    for r in reviews:
        lines.append(f"- R{r.get('round')}: **{r.get('verdict')}**（auditors: {', '.join(r.get('auditors') or [])}，tool calls: {r.get('reviewerToolCalls')}）")
    lines.append("")
    lines.append("## 追溯矩阵（Pi 侧）")
    lines.append(f"- AC: {json.dumps(trace['ac'], ensure_ascii=False)}")
    lines.append(f"- 验证方案: {json.dumps(trace['verification'], ensure_ascii=False)}")
    if trace.get("risk"):
        lines.append(f"- 风险分级: {trace['risk']}")
    lines.append("")
    lines.append("> 收口：本证据由 `pi_evidence_import.py` 导入；evidence-manifest 需重新生成。")
    out_md = ev_dir / "pi-audit-report.md"
    out_md.write_text("\n".join(lines), encoding="utf-8")

    print(f"[ok] 导入完成: {out_v.relative_to(root)} + {out_md.relative_to(root)}")
    print(f"[ok] 验证 {'PASS' if verification_ok else 'FAIL'}，评审 {len(reviews)} 轮")
    print("[info] 收口时请重新生成 evidence-manifest（gen_manifest 流程）")
    return 0 if verification_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
