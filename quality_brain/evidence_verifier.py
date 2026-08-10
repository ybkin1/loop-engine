"""证据验证器 — 检查证据文件的完整性和真实性。

不做内容判断（那需要人类），只做结构性验证：
- 文件存在
- JSON 可解析
- 必填字段完整
- 无伪造标记
- 评审独立性
- 证据新鲜度（与源码 SHA256 对比）
"""

import hashlib
import json
from pathlib import Path
from typing import Optional

from .core import Violation, Severity, Blocker, High, Medium, Low


class EvidenceVerifier:
    """证据验证器。"""

    def verify(self, evidence_dir: str, expected_evidence: list[dict] = None,
               source_root: str = None) -> list[Violation]:
        """
        验证证据目录中的所有证据文件。

        expected_evidence 格式:
        [{"path": "quality_report.json", "required_fields": [...],
          "check_independence": False, "check_freshness": False,
          "source_file": "src/main.py"}]
        """
        violations = []
        ev_dir = Path(evidence_dir)

        if not ev_dir.exists():
            violations.append(Blocker(
                f"证据目录不存在: {evidence_dir}",
                rule_id="EVIDENCE-MISSING-DIR"))
            return violations

        if expected_evidence:
            for expected in expected_evidence:
                violations.extend(self._verify_single(ev_dir, expected, source_root))
        else:
            # 遍历所有 JSON 文件
            for json_file in ev_dir.rglob('*.json'):
                violations.extend(self._verify_file(json_file))

        return violations

    def _verify_single(self, ev_dir: Path, expected: dict,
                       source_root: str = None) -> list[Violation]:
        """验证单个预期的证据文件。"""
        violations = []
        path = ev_dir / expected['path']

        # 检查 1：文件存在
        if not path.exists():
            violations.append(Blocker(
                f"证据缺失: {expected['path']}",
                rule_id="EVIDENCE-MISSING-FILE",
                file_path=str(path)))
            return violations

        # 基本验证
        violations.extend(self._verify_file(path))

        # 读取内容
        try:
            data = json.loads(path.read_text(encoding='utf-8'))
        except (json.JSONDecodeError, UnicodeDecodeError):
            return violations  # _verify_file 已经添加了错误

        # 检查 2：必填字段
        for field in expected.get('required_fields', []):
            if field not in data:
                violations.append(High(
                    f"证据不完整: '{expected['path']}' 缺少字段 '{field}'",
                    rule_id="EVIDENCE-MISSING-FIELD",
                    file_path=str(path)))

        # 检查 3：独立性（reviewer != developer）
        if expected.get('check_independence'):
            dev_id = data.get('developer_session_id', '')
            rev_id = data.get('reviewer_session_id', '')
            if dev_id and rev_id and dev_id == rev_id:
                violations.append(Blocker(
                    f"非独立评审: developer_session_id == reviewer_session_id",
                    rule_id="EVIDENCE-SELF-REVIEW",
                    file_path=str(path)))

        # 检查 4：新鲜度
        if expected.get('check_freshness') and source_root:
            source_file = Path(source_root) / expected.get('source_file', '')
            if source_file.exists():
                evidence_hash = data.get('content_sha256', '')
                current_hash = self._sha256(source_file)
                if evidence_hash and evidence_hash != current_hash:
                    violations.append(High(
                        f"证据过期: '{expected['path']}' — 源码已变更",
                        rule_id="EVIDENCE-STALE",
                        file_path=str(path)))

        return violations

    def _verify_file(self, path: Path) -> list[Violation]:
        """验证单个证据文件的基本完整性。"""
        violations = []
        fpath = str(path)

        if not path.exists():
            return [Blocker(f"证据文件不存在: {fpath}")]

        # 可解析性
        try:
            data = json.loads(path.read_text(encoding='utf-8'))
        except json.JSONDecodeError:
            violations.append(Blocker(
                f"证据损坏: {fpath} 无法解析为 JSON",
                rule_id="EVIDENCE-CORRUPT"))
            return violations
        except UnicodeDecodeError:
            violations.append(Blocker(
                f"证据损坏: {fpath} 编码错误",
                rule_id="EVIDENCE-ENCODING"))
            return violations

        # 反伪造检查
        content_str = json.dumps(data).lower()
        if 'simulated output' in content_str or 'simulated_output' in content_str:
            violations.append(Blocker(
                f"疑似伪造证据: {fpath} 包含 'Simulated output' 标记",
                rule_id="EVIDENCE-FORGED"))

        # 空结果标记
        summary = data.get('summary', '')
        verdict = data.get('verdict', '')
        findings = data.get('findings', [])
        if verdict in ('PASS', 'GO', 'APPROVED') and len(findings) == 0:
            if not summary or summary.strip() in ('', 'No issues found', 'All checks passed'):
                violations.append(Medium(
                    f"可疑证据: {fpath} — verdict=PASS 但无 findings",
                    rule_id="EVIDENCE-EMPTY",
                    file_path=fpath))

        return violations

    def _sha256(self, filepath: Path) -> str:
        """计算文件的 SHA256 哈希。"""
        h = hashlib.sha256()
        with open(filepath, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                h.update(chunk)
        return h.hexdigest()

    def summary(self, violations: list[Violation]) -> dict:
        """生成证据验证摘要。"""
        missing = sum(1 for v in violations if v.rule_id == 'EVIDENCE-MISSING-FILE')
        forged = sum(1 for v in violations if v.rule_id == 'EVIDENCE-FORGED')
        stale = sum(1 for v in violations if v.rule_id == 'EVIDENCE-STALE')
        corrupt = sum(1 for v in violations if v.rule_id in ('EVIDENCE-CORRUPT', 'EVIDENCE-ENCODING'))
        return {
            'total': len(violations),
            'missing': missing,
            'forged': forged,
            'stale': stale,
            'corrupt': corrupt,
            'has_blockers': any(v.is_blocker() for v in violations),
        }


def verify_evidence(evidence_dir: str, expected: list[dict] = None,
                    source_root: str = None) -> list[Violation]:
    """便捷函数。"""
    verifier = EvidenceVerifier()
    return verifier.verify(evidence_dir, expected, source_root)
