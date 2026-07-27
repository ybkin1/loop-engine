import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from codex_loop.cli.main import main
from codex_loop.materials import MaterialCatalog, MaterialError


class CliAndMaterialsTests(unittest.TestCase):
    def test_material_selection_excludes_unverified_by_default(self):
        catalog = MaterialCatalog.load(ROOT / "materials" / "catalog.yaml")
        selected = catalog.select(("architecture", "software engineering", "quality"))
        self.assertTrue(selected)
        self.assertTrue(all(item.verification_status not in {"access_blocked", "not_yet_checked"} for item in selected))

    def test_catalog_requires_fields_used_by_selection_record(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "catalog.yaml"
            path.write_text("materials:\n  - material_id: X\n    category: test\n    title: Test\n    problem_solved: issue\n    when_to_use: now\n    risks: none\n    evidence_level: candidate\n", encoding="utf-8")
            with self.assertRaises(MaterialError):
                MaterialCatalog.load(path)

    def test_cli_init_demo_and_verify(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.assertEqual(main(["init", "--root", str(root), "--project-id", "demo", "--goal", "demo goal"]), 0)
            self.assertEqual(main(["demo-t0036", "--root", str(root)]), 0)
            self.assertEqual(main(["verify", "--root", str(root)]), 0)
            packet = root / ".loop" / "packets" / "functional" / "T-0036-material-library.md"
            review = root / ".loop" / "packets" / "review" / "P11-human-review.md"
            self.assertTrue(packet.exists())
            self.assertTrue(review.exists())
            self.assertIn("前端设计", packet.read_text(encoding="utf-8"))
            self.assertIn("这不是用户批准", review.read_text(encoding="utf-8"))

    def test_cli_packet_can_render_full_feature_contract(self):
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "login.md"
            self.assertEqual(main(["packet", "--demo-t0036", "--output", str(output)]), 0)
            text = output.read_text(encoding="utf-8")
            for heading in ("用户怎么使用", "前端设计", "后端设计", "安全设计", "性能设计", "可维护性与演进", "测试设计"):
                self.assertIn(heading, text)

    def test_packet_requires_input_without_demo_switch(self):
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaises(SystemExit) as context:
                main(["packet", "--output", str(Path(temp) / "packet.md")])
            self.assertIn("--input", str(context.exception))

    def test_cli_prepare_run_writes_bounded_invocation_spec(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.assertEqual(main(["init", "--root", str(root), "--project-id", "demo", "--goal", "demo goal"]), 0)
            tools = ["workspace_read", "graph_check", "schema_check", "structured_write"]
            argv = ["prepare-run", "--root", str(root), "--role", "system-architect", "--task-id", "T-1", "--phase-id", "P3", "--purpose", "design boundaries"]
            for tool in tools:
                argv.extend(["--tool", tool])
            argv.extend(["--write-target", ".loop/packets/architecture/design.json"])
            self.assertEqual(main(argv), 0)
            spec = root / ".loop/runs/run-system-architect-T-1.invocation.json"
            self.assertTrue(spec.exists())
            self.assertEqual(json.loads(spec.read_text(encoding="utf-8"))["execution_status"], "not_performed_by_candidate")


if __name__ == "__main__":
    unittest.main()
