# -*- coding: utf-8 -*-
"""
test_mutation_scan.py — T-0128 M1 确定性检出测试。

覆盖：detector 规则库 6/6 检出、确定性（可复算）、干净代码零误报、
scan 报告结构与阈值语义。
"""

import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tests" / "seeded_defects"))

from detector import detect_all  # noqa: E402

SAMPLE = ROOT / "tests" / "seeded_defects" / "sample_code" / "user_service.py"
REGISTRY = ROOT / "tests" / "seeded_defects" / "defect_registry.json"

CLEAN_SOURCE = '''
class FakeDB:
    def execute(self, query, params=None):
        return []

class UserService:
    def __init__(self, db):
        self.db = db

    def search_users(self, keyword: str) -> list:
        query = "SELECT * FROM users WHERE name LIKE ?"
        return self.db.execute(query, [f"%{keyword}%"])

    def create_user(self, username: str, password: str, email: str):
        if not username or not password or not email:
            raise ValueError("all fields required")
        import hashlib
        hashed = hashlib.sha256(password.encode()).hexdigest()
        self.db.execute("INSERT INTO users (username, password, email) VALUES (?, ?, ?)",
                        [username, hashed, email])

    def get_average_age(self, user_ids: list[int]) -> float:
        if not user_ids:
            return 0.0
        total = sum(self.db.get_user(uid)["age"] for uid in user_ids)
        return total / len(user_ids)

    def get_users(self) -> list:
        return self.db.execute("SELECT * FROM users")
'''


class DetectorRulesTest(unittest.TestCase):
    def test_detect_all_six(self):
        """M1: 6 个种子缺陷全部被确定性检出（AC-02 >=5/6）。"""
        source = SAMPLE.read_text(encoding="utf-8")
        results = detect_all(source)
        self.assertEqual(len(results), 6)
        undetected = [sd for sd, r in results.items() if not r["detected"]]
        self.assertEqual(undetected, [], f"undetected: {undetected}")

    def test_detection_is_deterministic(self):
        """M1: 同源码两次检出结果一致（可复算）。"""
        source = SAMPLE.read_text(encoding="utf-8")
        self.assertEqual(detect_all(source), detect_all(source))

    def test_clean_code_zero_false_positives(self):
        """M1 负例：干净实现（参数化查询/校验/hash/空守卫/无循环查询）零误报。"""
        results = detect_all(CLEAN_SOURCE)
        false_pos = [sd for sd, r in results.items() if r["detected"]]
        self.assertEqual(false_pos, [], f"false positives: {false_pos}")

    def test_each_rule_reports_evidence(self):
        """每条检出规则必须带证据文本（D-02 M5 思想：verdict 引用证据）。"""
        source = SAMPLE.read_text(encoding="utf-8")
        results = detect_all(source)
        for sd, r in results.items():
            self.assertTrue(r["detected"], f"{sd} should detect")
            self.assertGreater(len(r["evidence"]), 0, f"{sd} evidence empty")


class MutationScanCliTest(unittest.TestCase):
    def test_scan_cli_report_structure(self):
        """scan 子命令：报告结构与阈值语义（PASS 6/6）。"""
        proc = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "mutation_tester.py"),
             "scan", "--sample", str(SAMPLE), "--registry", str(REGISTRY)],
            capture_output=True, text=True, encoding="utf-8",
            cwd=str(ROOT),
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        report = json.loads(proc.stdout[proc.stdout.index("{"):proc.stdout.rindex("}") + 1])
        self.assertEqual(report["report_type"], "mutation-scan-m1")
        self.assertEqual(report["detected"], 6)
        self.assertEqual(report["verdict"], "PASS")
        self.assertEqual(len(report["per_defect"]), 6)


if __name__ == "__main__":
    unittest.main()
