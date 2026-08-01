# -*- coding: utf-8 -*-
"""
T-0095 item 10 — HANDOFF evidence-manifest 模板引用修正。

`.ai/HANDOFF.md` 曾引用 `.ai/evidence/T-0095/evidence-manifest.v1.yaml`
（该文件当时不存在）。本任务在 `.ai/evidence/T-0095/` 下创建了真实的
EvidenceManifest/v1 清单（引用即真实路径），并锁定：
- 清单文件存在（HANDOFF 引用目标可解析）；
- 清单列出的每个证据文件真实存在且 sha256/size 与清单一致；
- 清单通过 .zcode/tools/evidence_manifest 的官方校验（字段集/排序绑定/
  语义哈希/流式指纹）。
"""

import hashlib
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
MANIFEST_REL = ".ai/evidence/T-0095/evidence-manifest.v1.yaml"
MANIFEST_PATH = ROOT / MANIFEST_REL

HANDOFF_PATH = ROOT / ".ai" / "HANDOFF.md"


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


class TestT0095EvidenceManifest:
    def test_manifest_exists_and_handoff_reference_is_real(self):
        """HANDOFF 引用的 manifest 路径必须真实存在。"""
        assert MANIFEST_PATH.is_file(), f"missing: {MANIFEST_PATH}"
        if HANDOFF_PATH.exists():
            text = HANDOFF_PATH.read_text(encoding="utf-8")
            if "Evidence manifest:" in text:
                # every manifest reference in HANDOFF must resolve to a file
                for line in text.splitlines():
                    if "evidence-manifest.v1.yaml" in line:
                        ref = line.split("Evidence manifest:", 1)[-1].strip().rstrip(".")
                        assert (ROOT / ref).is_file(), f"dangling HANDOFF ref: {ref}"

    def test_manifest_schema_and_entries(self):
        doc = yaml.safe_load(MANIFEST_PATH.read_text(encoding="utf-8"))
        assert doc["schema"] == "EvidenceManifest/v1"
        assert doc["task_id"] == "T-0095"
        assert doc["gate_id"] == "G-T-0095-REQUIREMENTS"
        files = doc["files"]
        assert isinstance(files, list) and files
        assert doc["file_count"] == len(files)
        assert doc["total_bytes"] == sum(e["size"] for e in files)

    def test_every_listed_file_exists_and_matches_fingerprint(self):
        doc = yaml.safe_load(MANIFEST_PATH.read_text(encoding="utf-8"))
        for entry in doc["files"]:
            path = ROOT / entry["path"]
            assert path.is_file(), f"listed file missing: {entry['path']}"
            data = path.read_bytes()
            assert len(data) == entry["size"], entry["path"]
            assert _sha256_bytes(data) == entry["sha256"].upper(), entry["path"]

    def test_manifest_passes_official_verifier(self):
        """用 .zcode/tools/evidence_manifest 官方校验器完整验证。"""
        sys.path.insert(0, str(ROOT / ".zcode" / "tools"))
        from evidence_manifest import verify_evidence_manifest

        result = verify_evidence_manifest(ROOT, MANIFEST_REL)
        assert result["file_count"] >= 1
        assert result["ordered_entries_sha256"]
        assert result["semantic_sha256"]
