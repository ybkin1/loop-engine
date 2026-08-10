"""Quality Brain 核心类型定义。"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class Severity(Enum):
    BLOCKER = "BLOCKER"  # 必须修复，阻断 Gate
    HIGH = "HIGH"        # 强烈建议修复
    MEDIUM = "MEDIUM"    # 建议修复
    LOW = "LOW"          # 可选修复


@dataclass
class Violation:
    """质量违规记录。"""
    rule_id: str
    severity: Severity
    message: str
    file_path: str = ""
    line_number: int = 0
    code_snippet: str = ""
    remediation: str = ""

    def is_blocker(self) -> bool:
        return self.severity == Severity.BLOCKER


def Blocker(msg: str, rule_id: str = "", file_path: str = "", line: int = 0,
            snippet: str = "", remediation: str = "") -> Violation:
    return Violation(rule_id=rule_id, severity=Severity.BLOCKER,
                     message=msg, file_path=file_path, line_number=line,
                     code_snippet=snippet, remediation=remediation)


def High(msg: str, rule_id: str = "", file_path: str = "", line: int = 0,
         snippet: str = "", remediation: str = "") -> Violation:
    return Violation(rule_id=rule_id, severity=Severity.HIGH,
                     message=msg, file_path=file_path, line_number=line,
                     code_snippet=snippet, remediation=remediation)


def Medium(msg: str, rule_id: str = "", file_path: str = "", line: int = 0,
           snippet: str = "", remediation: str = "") -> Violation:
    return Violation(rule_id=rule_id, severity=Severity.MEDIUM,
                     message=msg, file_path=file_path, line_number=line,
                     code_snippet=snippet, remediation=remediation)


def Low(msg: str, rule_id: str = "", file_path: str = "", line: int = 0,
        snippet: str = "", remediation: str = "") -> Violation:
    return Violation(rule_id=rule_id, severity=Severity.LOW,
                     message=msg, file_path=file_path, line_number=line,
                     code_snippet=snippet, remediation=remediation)
