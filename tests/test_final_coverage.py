"""T-0066: Final minimal coverage — import verification."""
import sys, unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

class TestRouter(unittest.TestCase):
    def test_imports(self):
        from loop_core.router import LoopMode, RiskLevel, ProjectProfile, RouteResult
        self.assertTrue(True)

class TestStateMachine(unittest.TestCase):
    def test_phase_import(self):
        from loop_core.state_machine import Phase
        self.assertIsNotNone(Phase.S0_INIT)
        self.assertIsNotNone(Phase.S6_DELIVERY)

    def test_status_imports(self):
        from loop_core.state_machine import GateStatus, TaskStatus, ProjectStatus
        self.assertTrue(True)

    def test_structures_import(self):
        from loop_core.state_machine import PhaseConstraint, GateCondition
        from loop_core.state_machine import StateValidationResult, RoleIsolationCheck
        self.assertTrue(True)

class TestStaticAnalyzer(unittest.TestCase):
    def test_imports(self):
        from loop_core.static_analyzer import Finding, AnalysisReport
        self.assertTrue(True)

if __name__ == "__main__":
    unittest.main()
