"""context_packager.py — Build code context for role sub-agents."""
import json
import subprocess, sys
from pathlib import Path

ROLE_CONTEXT = {
    "developer": {"files": ["docs/02-architecture.md", "docs/03-interface-contract.md"], "git_diff": True, "max_content": 5000},
    "independent-reviewer": {"files": ["docs/02-architecture.md", ".ai/CODING_STANDARDS.md"], "git_diff": True, "max_content": 8000},
    "test-engineer": {"files": ["docs/03-interface-contract.md"], "git_diff_name_only": True, "max_content": 3000},
    "quality-engineer": {"files": [], "git_diff_name_only": True, "max_content": 2000},
    "system-architect": {"files": ["docs/02-architecture.md", "docs/01-requirements.md"], "git_diff_name_only": True, "max_content": 5000},
    "module-architect": {"files": ["docs/03-interface-contract.md"], "git_diff": True, "max_content": 4000},
    "product-manager": {"files": ["docs/01-requirements.md"], "git_diff_name_only": True, "max_content": 3000},
    "project-manager": {"files": [".ai/task_graph.yaml"], "git_diff": True, "max_content": 4000},
    "delivery-manager": {"files": ["docs/06-delivery.md", "docs/07-phase-specification.md"], "git_diff": True, "max_content": 5000},
    "release-engineer": {"files": ["docs/06-delivery.md", "pyproject.toml"], "git_diff": True, "max_content": 5000},
    "security-engineer": {"files": ["pyproject.toml"], "git_diff": True, "max_content": 6000},
}

def build_context(project_root, role_id, task_id="", extra_files=None,
                  *, include_memories: bool = False, memory_limit: int = 5,
                  memory_gate_id: str | None = None, memory_tag: str | None = None):
    """Build code context for a role sub-agent.

    T-0104 设计-5: ``include_memories=True`` 时追加"相关经验（Related
    Memories）"节（memory_service recall，top-N = memory_limit，渲染格式
    与 context_loader 一致）。默认 False 保持现状（零行为变化）。

    T-0105 B-4-1: 记忆召回透传过滤参数——``task_id``（复用位置参数）、
    ``memory_gate_id``、``memory_tag`` 按 AND 组合传给 recall，消除跨任务
    不相关记忆注入；任一过滤参数为 None/空 即不过滤，与 T-0104 现状一致
    （fail-closed：空召回 no-op、损坏抛异常不变）。
    """
    root = Path(project_root)
    spec = ROLE_CONTEXT.get(role_id, {"files": [], "git_diff_name_only": True, "max_content": 2000})
    parts = []
    total = 0
    MAX = 15000
    if task_id:
        tf = root / ".ai/tasks" / (task_id + ".md")
        if tf.exists():
            tc = tf.read_text(encoding="utf-8")[:1000]
            parts.append("## Task Context\n" + tc)
    try:
        if spec.get("git_diff"):
            r = subprocess.run(["git","diff","--stat","HEAD~1"], capture_output=True, text=True, cwd=str(root), timeout=5)
            if r.returncode == 0 and r.stdout.strip():
                parts.append("## Changed Files\n" + r.stdout.strip())
            r2 = subprocess.run(["git","diff","HEAD~1","--","*.py"], capture_output=True, text=True, cwd=str(root), timeout=10)
            if r2.returncode == 0 and r2.stdout.strip():
                dt = r2.stdout[:spec["max_content"]]
                parts.append("## Code Diff\n```diff\n" + dt + "\n```")
        elif spec.get("git_diff_name_only"):
            r = subprocess.run(["git","diff","--name-only","HEAD~1"], capture_output=True, text=True, cwd=str(root), timeout=5)
            if r.returncode == 0 and r.stdout.strip():
                parts.append("## Changed Files\n" + r.stdout.strip())
    except Exception:
        pass
    for f in spec.get("files", []):
        fp = root / f
        if fp.exists() and total < MAX:
            c = fp.read_text(encoding="utf-8")[:spec["max_content"]]
            parts.append("## " + f + "\n" + c)
    if extra_files:
        for f in extra_files[:5]:
            fp = root / f
            if fp.exists() and total < MAX:
                c = fp.read_text(encoding="utf-8")[:2000]
                parts.append("## " + f + "\n```\n" + c + "\n```")
    knowledge = root / ".ai" / "knowledge" / "cases.json"
    if knowledge.exists() and total < MAX:
        try:
            cases = json.loads(knowledge.read_text(encoding="utf-8"))
            selected = cases[:3] if isinstance(cases, list) else []
            if selected:
                parts.append("## Knowledge Cases\n" + json.dumps(selected, ensure_ascii=False, indent=2)[:3000])
        except (OSError, json.JSONDecodeError):
            pass
    if include_memories:
        # T-0104 设计-5: 记忆注入（S4+ 调用点显式开启）。空召回 = 无节 = no-op；
        # store 损坏时 fail-closed（与 context_loader 语义一致，不静默猜记忆）。
        from loop_core.memory_service import memories_to_context, recall
        if isinstance(memory_limit, int) and memory_limit > 0:
            # T-0105 B-4-1: 透传 task_id/gate_id/tag 过滤（None = 不过滤，
            # 与 context_loader._apply_memory_injection 的 recall 用法一致）。
            entries = recall(
                root,
                limit=memory_limit,
                task_id=task_id or None,
                gate_id=memory_gate_id,
                tag=memory_tag,
            )
            section = memories_to_context(entries)
            if section and total < MAX:
                parts.append(section)
    parts.append("execution_mode: SIMULATED_MAIN_SESSION\nagent_takeover: false")
    parts.append("\n---\nUse the above context to complete your role duties.")
    return "\n\n".join(parts)

if __name__ == "__main__":
    r = sys.argv[1] if len(sys.argv) > 1 else "."
    role = sys.argv[2] if len(sys.argv) > 2 else "developer"
    tid = sys.argv[3] if len(sys.argv) > 3 else ""
    print(build_context(r, role, tid))