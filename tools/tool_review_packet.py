"""loop_review_packet — Generate human-readable gate/approval packet."""
import sys
from pathlib import Path


def run(packet_type: str, project_root: str = ".", **kwargs) -> dict:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

    if packet_type == "GATE_APPROVAL":
        phase = kwargs.get("phase", "unknown")
        task_id = kwargs.get("task_id", "")
        artifacts = kwargs.get("artifacts", [])
        return {
            "packet_type": "GATE_APPROVAL",
            "phase": phase,
            "task_id": task_id,
            "decision_required": f"批准进入 {phase} 阶段？",
            "artifacts": artifacts,
            "summary": f"阶段 {phase} 已完成，产出 {len(artifacts)} 个产物，请求用户批准进入下一阶段。",
        }

    elif packet_type == "VETO_ESCALATION":
        vetos = kwargs.get("vetos", [])
        return {
            "packet_type": "VETO_ESCALATION",
            "veto_count": len(vetos),
            "vetos": vetos,
            "decision_required": f"{len(vetos)} 个角色否决了当前阶段，需要你决定：重试 / 跳过 / 回退",
            "summary": "多个角色对当前产出提出了否决，详见 veto 列表。",
        }

    elif packet_type == "CHANGE_REQUEST":
        description = kwargs.get("description", "")
        return {
            "packet_type": "CHANGE_REQUEST",
            "description": description,
            "decision_required": "是否接受此变更请求？",
            "summary": description,
        }

    return {"error": f"Unknown packet_type: {packet_type}", "available": ["GATE_APPROVAL", "VETO_ESCALATION", "CHANGE_REQUEST"]}
