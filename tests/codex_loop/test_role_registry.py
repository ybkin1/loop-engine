import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from codex_loop.core.contracts import RoleRegistry
from codex_loop.quality.checks import check_role_prompts
REGISTRY = ROOT / "codex_loop" / "roles" / "registry.json"


class RoleRegistryTests(unittest.TestCase):
    def test_all_stable_roles_and_project_specialist_load(self):
        registry = RoleRegistry.load(REGISTRY)
        self.assertEqual(len(registry.roles), 12)
        self.assertEqual(len([r for r in registry.roles if r.data["category"] == "stable"]), 11)
        self.assertIn("controller", registry.ids())
        self.assertIn("research-engineer", registry.ids())

    def test_contracts_are_bounded_and_isolated(self):
        registry = RoleRegistry.load(REGISTRY)
        self.assertEqual(registry.validate_isolation(), [])
        self.assertEqual(check_role_prompts(registry).status, "PASS")
        for role in registry.roles:
            self.assertLessEqual(len(role.prompt_text()), 12000)
            self.assertGreater(role.context_budget_tokens, 0)
        reviewer = registry.get("independent-reviewer")
        self.assertTrue(reviewer.is_independent_reviewer)
        self.assertFalse(reviewer.data["can_write_state"])

    def test_unknown_role_is_rejected(self):
        registry = RoleRegistry.load(REGISTRY)
        with self.assertRaises(ValueError):
            registry.get("not-a-role")


if __name__ == "__main__":
    unittest.main()
