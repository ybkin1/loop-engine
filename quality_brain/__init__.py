"""Quality Brain — 确定性质量验证引擎（Kimi Code Loop 工程核心创新）。

不靠 LLM 评审 LLM，靠确定性 Python 代码验证 AI 产出。
"""

from .core import Violation, Severity, Blocker, High, Medium, Low
from .contract_verifier import ContractVerifier, verify_contract
from .import_checker import ImportChecker, check_imports
from .architecture_scanner import ArchitectureScanner, scan_architecture
from .evidence_verifier import EvidenceVerifier, verify_evidence
from .gate_aggregator import GateAggregator, GateDecision, evaluate_gate
from .static_analyzer import StaticAnalyzer, load_all_rules

__all__ = [
    "Violation", "Severity", "Blocker", "High", "Medium", "Low",
    "ContractVerifier", "verify_contract",
    "ImportChecker", "check_imports",
    "ArchitectureScanner", "scan_architecture",
    "EvidenceVerifier", "verify_evidence",
    "GateAggregator", "GateDecision", "evaluate_gate",
    "StaticAnalyzer", "load_all_rules",
]
