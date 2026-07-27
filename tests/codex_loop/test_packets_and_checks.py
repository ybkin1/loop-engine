import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from codex_loop.core.contracts import RoleRegistry
from codex_loop.planning.graph import TaskGraph, TaskNode
from codex_loop.quality.checks import check_phase_transition, check_role_registry, check_task_graph
from codex_loop.packets.functional import FunctionalDesignPacket, PacketError
from codex_loop.packets.human import render_human_review_packet


REGISTRY = ROOT / "codex_loop" / "roles" / "registry.json"


def valid_feature():
    return {
        "feature_id": "AUTH-001",
        "feature_name": "用户注册与登录",
        "user_goal": "用户可以安全创建账户并登录系统",
        "actors": ["external_user", "internal_user", "administrator"],
        "preconditions": ["service is available", "registration policy is active"],
        "user_guide": {"entry": "打开注册页", "steps": ["填写邮箱和密码", "完成验证", "登录"], "failure": "显示可恢复错误"},
        "frontend": {"pages": ["register", "login"], "elements": ["form", "submit", "verification"], "states": ["loading", "error", "success"]},
        "backend": {"modules": ["identity", "session"], "apis": ["POST /register", "POST /login"], "data_model": ["account", "credential"]},
        "security": {"authn_authz": ["email verification", "rate limit"], "abuse_prevention": ["captcha challenge", "login throttling"], "data_protection": ["password hash"]},
        "performance": {"budgets": ["p95 login < 500ms"], "bottlenecks": ["identity store"], "degradation": ["retryable dependency failure"]},
        "maintainability": {"module_boundaries": ["identity separated from profile"], "extension": ["new auth provider behind interface"]},
        "testing": {"unit": ["validation"], "integration": ["identity store"], "e2e": ["register then login"], "security": ["credential abuse"]},
        "decisions": ["email is primary identifier", "internal users use assigned domain"],
        "risks": ["verification provider outage", "credential stuffing"],
        "user_decisions": ["accept email-first registration", "accept phone binding as later phase"],
    }


def complete_feature(feature):
    feature["user_guide"].update({"success": "account works", "navigation": "return to login"})
    feature["frontend"].update({"validation": ["required"], "accessibility": ["labels"]})
    feature["backend"].update({"state_transitions": ["pending -> active"], "errors": ["invalid input"], "idempotency": ["request key"], "observability": ["audit event"]})
    feature["security"].update({"boundaries": ["identity boundary"], "input_protection": ["schema validation"], "audit": ["security event"]})
    feature["performance"].update({"scaling": ["store partitioning"]})
    feature["maintainability"].update({"dependencies": ["identity interface"], "runbook": ["rotate provider"]})
    feature["testing"].update({"component": ["form"], "contract": ["register API"], "performance": ["p95"], "recovery": ["provider retry"]})
    return feature


class PacketAndChecksTests(unittest.TestCase):
    def test_functional_packet_requires_all_software_engineering_sections(self):
        packet = FunctionalDesignPacket.from_dict(complete_feature(valid_feature()))
        self.assertEqual(packet.validate(), [])
        rendered = packet.render_markdown()
        for heading in ("用户怎么使用", "前端设计", "后端设计", "安全设计", "性能设计", "测试设计"):
            self.assertIn(heading, rendered)

    def test_incomplete_packet_is_rejected(self):
        with self.assertRaises(PacketError):
            FunctionalDesignPacket.from_dict({"feature_id": "X", "feature_name": "incomplete"})

    def test_checks_distinguish_internal_gate_from_user_gate(self):
        registry_result = check_role_registry(RoleRegistry.load(REGISTRY))
        graph = TaskGraph()
        graph.add(TaskNode("a", "A", "P1", "product-manager"))
        graph_result = check_task_graph(graph)
        self.assertEqual(registry_result.status, "PASS")
        self.assertEqual(graph_result.status, "PASS")
        self.assertEqual(check_phase_transition((registry_result, graph_result), None, True).status, "USER_DECISION_REQUIRED")
        self.assertEqual(check_phase_transition((registry_result, graph_result), "approve", True).status, "PASS")

    def test_nested_feature_sections_cannot_be_empty(self):
        payload = complete_feature(valid_feature())
        payload["frontend"]["elements"] = []
        with self.assertRaises(PacketError) as context:
            FunctionalDesignPacket.from_dict(payload)
        self.assertIn("frontend.elements", str(context.exception))

    def test_human_packet_does_not_write_approval(self):
        packet = render_human_review_packet("T-0036", "P3", "candidate result", ["artifact.md"], ["schema check"], ["independent review"], ["accept architecture direction"])
        self.assertIn("这不是用户批准", packet)
        self.assertIn("accept architecture direction", packet)


if __name__ == "__main__":
    unittest.main()
