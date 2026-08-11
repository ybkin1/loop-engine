"""Tests for critical loop_core modules without prior coverage."""
import json, sys, tempfile, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

class TestRoleLoader(unittest.TestCase):
    def test_list_roles_returns_list(self):
        from loop_core.role_loader import list_roles
        roles = list_roles()
        self.assertGreater(len(roles), 0)
        self.assertIn("main-thread", roles)

    def test_load_role_prompt_returns_string(self):
        from loop_core.role_loader import load_role_prompt
        prompt = load_role_prompt("independent-reviewer", task_id="T-TEST")
        self.assertIsInstance(prompt, str)
        self.assertIn("T-TEST", prompt)

    def test_load_role_skill_returns_content(self):
        from loop_core.role_loader import load_role_skill
        skill = load_role_skill("quality-engineer")
        self.assertGreater(len(skill), 100)

    def test_unknown_role_raises(self):
        from loop_core.role_loader import load_role_prompt
        with self.assertRaises((ValueError, FileNotFoundError)):
            load_role_prompt("nonexistent-role-xyz")


class TestContextLoader(unittest.TestCase):
    def test_imports(self):
        """T-0177 P3-4：原 assertTrue(True) 假通过 → 真实断言。"""
        from loop_core.context_loader import ContextLoader
        loader = ContextLoader(str(ROOT))
        # 核心契约方法必须存在且可调用
        for method in ("load_for_role", "load_role_context", "estimate_tokens",
                       "load_document_section", "build_document_index"):
            self.assertTrue(hasattr(loader, method), f"ContextLoader 缺方法 {method}")


class TestContracts(unittest.TestCase):
    def test_imports(self):
        """T-0177 P3-4：原 assertTrue(True) 假通过 → 真实断言。"""
        from loop_core import contracts
        from loop_core.contracts import HostAdapter
        self.assertTrue(hasattr(contracts, "HostAdapter"))
        # HostAdapter 必须是抽象基类（宿主契约强制）
        self.assertTrue(getattr(HostAdapter, "__abstractmethods__", None),
                        "HostAdapter 应为 ABC（含抽象方法）")


if __name__ == "__main__":
    unittest.main()
