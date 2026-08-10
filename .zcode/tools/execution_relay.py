#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
execution_relay.py — ZCode 接力执行编排（P1-1，补"ZCode 执行浅"）

宿主限制：子代理不能拉子孙代理（无法构建执行树）。本工具把"多层执行"
展开为**主会话序列接力**：每个阶段一个子代理，主会话按计划依次派发，
后一阶段的输入 = 前一阶段的产物（上下文打包传递）。质量门：每阶段
expected_output 校验（存在性 + 哈希记录），重量阶段强制 quality_pair。

用法：
    python .zcode/tools/execution_relay.py plan --task T-XXXX
        生成接力计划（relay/plan.json + 各阶段 prompt 文件 + state.json）
    python .zcode/tools/execution_relay.py status --task T-XXXX
        查看阶段进度
    python .zcode/tools/execution_relay.py stage --task T-XXXX --n 1
        输出阶段 1 执行指令（给主会话：角色 + prompt 文件 + 期望产物）
    python .zcode/tools/execution_relay.py verify --task T-XXXX --n 1
        校验阶段 1 产物（存在性 + 哈希记录 + 标记 completed）

主会话执行流（文档见 docs/designs/T-0168 附录）：
    plan → 依次 {stage 输出指令 → 调 Agent(角色, prompt, 输入) → 产物落盘 → verify}
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

sys.dont_write_bytecode = True

PLAN_SCHEMA = "execution-relay/v1"

# 通用接力链（P1 版：侦察 → 实现 → 验证）
STAGE_TEMPLATES = [
    {
        "name": "scout",
        "role": "scout",
        "expected_output": "context-summary.md",
        "quality_pair": False,
        "prompt_tail": (
            "你是侦察子代理（接力第 1 阶段）。任务卡与 AC 见下方。"
            "产出：<项目根>/relay/artifacts/context-summary.md —— 相关代码/契约/"
            "依赖的结构化摘要（供下一阶段实现者使用，他们看不到你的原始侦察过程）。"
        ),
    },
    {
        "name": "implement",
        "role": "developer",
        "expected_output": "implementation.md",
        "quality_pair": True,
        "prompt_tail": (
            "你是实现子代理（接力第 2 阶段）。上阶段侦察摘要见 relay/artifacts/context-summary.md"
            "（先读它）。按任务卡 AC 逐条实现，产出文件清单与变更说明写入"
            "<项目根>/relay/artifacts/implementation.md。本阶段为重量动作："
            "完成后必须配质量校验（quality_pair）。"
        ),
    },
    {
        "name": "verify",
        "role": "quality-engineer",
        "expected_output": "verification-report.md",
        "quality_pair": False,
        "prompt_tail": (
            "你是验证子代理（接力第 3 阶段）。上阶段实现说明见 "
            "relay/artifacts/implementation.md（先读它）。独立验证：读实际代码/运行测试，"
            "逐 AC 给出 PASS/FAIL + 证据，写入 <项目根>/relay/artifacts/verification-report.md。"
            "反幻觉要求：必须实际调用工具验证，禁止凭印象判定。"
        ),
    },
]


def relay_dir(root: Path, task: str) -> Path:
    return root / ".ai" / "evidence" / task / "relay"


def load_state(root: Path, task: str) -> dict:
    p = relay_dir(root, task) / "state.json"
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {"schema": "relay-state/v1", "task_id": task, "stages": {}}


def save_state(root: Path, task: str, state: dict) -> None:
    p = relay_dir(root, task) / "state.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")


def read_task_card(root: Path, task: str) -> str:
    p = root / ".ai" / "tasks" / f"{task}.md"
    if not p.exists():
        print(f"[error] 任务卡不存在: {p}", file=sys.stderr)
        raise SystemExit(2)
    return p.read_text(encoding="utf-8")


def stage_prompt_file(rdir: Path, idx: int, name: str) -> Path:
    return rdir / "prompts" / f"stage-{idx + 1}-{name}.md"


def cmd_plan(args) -> int:
    root = Path(args.zcode_root).resolve()
    task = args.task.upper()
    card_text = read_task_card(root, task)
    rdir = relay_dir(root, task)
    rdir.mkdir(parents=True, exist_ok=True)
    artifacts = rdir / "artifacts"
    artifacts.mkdir(parents=True, exist_ok=True)
    (rdir / "prompts").mkdir(parents=True, exist_ok=True)

    # 从任务卡提取 AC 摘要（供 prompt 注入）
    ac_lines = []
    m = re.search(r"^##\s+可验证验收标准\s*$([\s\S]*?)(?=^##\s|\Z)", card_text, re.M)
    if m:
        for line in m.group(1).splitlines():
            am = re.search(r"\[\s*AC-\d+\s*\]\s*(.+)", line.strip())
            if am:
                ac_lines.append(f"- {am.group(1).strip().lstrip('* ').strip()}")

    stages = []
    for idx, tmpl in enumerate(STAGE_TEMPLATES):
        stage = {
            "index": idx + 1,
            "name": tmpl["name"],
            "role": tmpl["role"],
            "expected_output": f"relay/artifacts/{tmpl['expected_output']}",
            "quality_pair": tmpl["quality_pair"],
            "depends_on": f"relay/artifacts/{STAGE_TEMPLATES[idx - 1]['expected_output']}" if idx > 0 else None,
        }
        stages.append(stage)
        # 生成阶段 prompt 文件
        prompt = [
            f"# 接力阶段 {idx + 1}: {tmpl['name']}（角色: {tmpl['role']}）",
            "",
            f"## 任务: {task}",
            "## 任务卡（摘要）",
            card_text[:3000],
            "",
            "## 验收标准（AC）",
            "\n".join(ac_lines) if ac_lines else "（任务卡无 AC 节）",
            "",
            "## 阶段指令",
            tmpl["prompt_tail"],
            "",
            "## 产物路径约定",
            f"- 本阶段产物: <项目根>/.ai/evidence/{task}/relay/artifacts/{tmpl['expected_output']}",
            "- 只读输入: 见 depends_on（上阶段产物，若存在）",
        ]
        stage_prompt_file(rdir, idx, tmpl["name"]).write_text("\n".join(prompt), encoding="utf-8")

    plan = {
        "schema": PLAN_SCHEMA,
        "task_id": task,
        "stages": stages,
        "created_at": __import__("datetime").datetime.now().isoformat(),
    }
    (rdir / "plan.json").write_text(json.dumps(plan, indent=2, ensure_ascii=False), encoding="utf-8")
    save_state(root, task, load_state(root, task))
    print(f"[ok] 接力计划生成: {rdir}")
    for s in stages:
        print(f"  stage-{s['index']} {s['name']}（{s['role']}）→ {s['expected_output']}"
              f"{' [quality_pair 强制]' if s['quality_pair'] else ''}")
    return 0


def cmd_status(args) -> int:
    root = Path(args.zcode_root).resolve()
    task = args.task.upper()
    state = load_state(root, task)
    plan_path = relay_dir(root, task) / "plan.json"
    if not plan_path.exists():
        print("[info] 无接力计划——先运行 plan")
        return 0
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    for s in plan["stages"]:
        st = state.get("stages", {}).get(str(s["index"]), {"status": "pending"})
        mark = {"pending": "⏳", "launched": "🚀", "completed": "✅"}.get(st.get("status"), "⏳")
        print(f"  {mark} stage-{s['index']} {s['name']} [{st.get('status')}]"
              f"{'  sha256=' + st['sha256'][:12] if st.get('sha256') else ''}")
    return 0


def cmd_stage(args) -> int:
    root = Path(args.zcode_root).resolve()
    task = args.task.upper()
    n = args.n
    plan_path = relay_dir(root, task) / "plan.json"
    if not plan_path.exists():
        print("[error] 无接力计划——先运行 plan", file=sys.stderr)
        return 2
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    if n < 1 or n > len(plan["stages"]):
        print(f"[error] 阶段号超出范围（1~{len(plan['stages'])}）", file=sys.stderr)
        return 2
    s = plan["stages"][n - 1]
    rdir = relay_dir(root, task)
    print("=" * 60)
    print(f"接力阶段 {n}: {s['name']}（角色 {s['role']}）")
    print("=" * 60)
    print(f"执行指令（主会话）：")
    print(f"  1. 调 Agent 工具：subagent_id/角色 = {s['role']}")
    print(f"  2. prompt 文件：{stage_prompt_file(rdir, n - 1, s['name'])}")
    if s.get("depends_on"):
        dep = rdir.parent / s["depends_on"]
        print(f"  3. 输入（上阶段产物）：{dep}（{'已存在' if dep.exists() else '缺失——先完成上阶段'}）")
    print(f"  4. 产物落盘到：{rdir / s['expected_output'].split('/', 1)[-1]}")
    print(f"  5. 完成后运行：execution_relay.py verify --task {task} --n {n}")
    if s.get("quality_pair"):
        print("  ⚠️ 重量阶段：必须配 quality_pair 质量校验（独立审查）")
    # 标记 launched
    state = load_state(root, task)
    state.setdefault("stages", {})[str(n)] = {"status": "launched", "at": __import__("datetime").datetime.now().isoformat()}
    save_state(root, task, state)
    return 0


def cmd_verify(args) -> int:
    root = Path(args.zcode_root).resolve()
    task = args.task.upper()
    n = args.n
    plan_path = relay_dir(root, task) / "plan.json"
    if not plan_path.exists():
        print("[error] 无接力计划——先运行 plan", file=sys.stderr)
        return 2
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    if n < 1 or n > len(plan["stages"]):
        print(f"[error] 阶段号超出范围（1~{len(plan['stages'])}）", file=sys.stderr)
        return 2
    s = plan["stages"][n - 1]
    rdir = relay_dir(root, task)
    artifact = rdir / s["expected_output"].split("/", 1)[-1]
    if not artifact.exists():
        print(f"[error] 阶段产物缺失: {artifact}", file=sys.stderr)
        return 2
    data = artifact.read_bytes()
    if len(data) == 0:
        print(f"[error] 阶段产物为空: {artifact}", file=sys.stderr)
        return 2
    sha = hashlib.sha256(data).hexdigest()
    state = load_state(root, task)
    state.setdefault("stages", {})[str(n)] = {
        "status": "completed",
        "sha256": sha,
        "size": len(data),
        "at": __import__("datetime").datetime.now().isoformat(),
    }
    save_state(root, task, state)
    print(f"[ok] 阶段 {n}（{s['name']}）产物校验通过: {artifact.name} "
          f"({len(data)} bytes, sha256 {sha[:16]}…)")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="ZCode 接力执行编排")
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("plan", "status", "stage", "verify"):
        p = sub.add_parser(name)
        p.add_argument("--task", required=True)
        p.add_argument("--zcode-root", default=".")
        if name in ("stage", "verify"):
            p.add_argument("--n", type=int, required=True)
    args = ap.parse_args()
    return {"plan": cmd_plan, "status": cmd_status, "stage": cmd_stage, "verify": cmd_verify}[args.cmd](args)


if __name__ == "__main__":
    raise SystemExit(main())
