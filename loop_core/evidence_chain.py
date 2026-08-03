"""
Evidence Chain — causal chain management for evidence integrity.

Provides EvidenceEnvelope (wrapper around evidence content with TTL and
causal linking) and EvidenceChain (manager for verifying chain integrity,
detecting broken links, and marking expired evidence).

The causal chain is a singly-linked list where each EvidenceEnvelope's
causal_parent_hash points to the content_hash of its predecessor. This
creates a verifiable, tamper-evident lineage across sessions.
"""
from __future__ import annotations

import hashlib
import json
import os
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

import yaml


# ──────────────────────────────────────────────────────────────────────────────
# EvidenceEnvelope
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class EvidenceEnvelope:
    """证据信封——包裹证据内容的完整性容器。

    Each envelope wraps a piece of evidence with:
    - A unique envelope ID (EE-{uuid12})
    - A content hash (SHA-256) for integrity verification
    - ISO 8601 creation timestamp
    - TTL-based expiration
    - A causal link to the parent evidence (via content_hash)

    The causal chain allows verification that evidence was produced in
    the correct order and that no intermediate evidence has been removed
    or tampered with.
    """

    envelope_id: str                # EE-{uuid12}
    content_hash: str               # 证据内容 SHA256
    created_at: str                 # ISO 8601
    ttl_days: int = 90
    causal_parent_hash: Optional[str] = None   # 因果链：上一个证据 content_hash
    evidence_path: Optional[str] = None        # 证据文件路径
    content_type: str = "application/json"

    # ── Freshness ────────────────────────────────────────────────────────

    def _expiration_datetime(self) -> datetime:
        """Compute the absolute expiration datetime."""
        created = datetime.fromisoformat(self.created_at)
        # created_at may or may not include timezone info; if naive,
        # treat as UTC for safety.
        if created.tzinfo is None:
            created = created.replace(tzinfo=timezone.utc)
        return created + timedelta(days=self.ttl_days)

    def is_fresh(self) -> bool:
        """检查证据是否未过期。

        Returns True if the evidence has NOT passed its TTL expiration.
        """
        now = datetime.now(timezone.utc)
        return now < self._expiration_datetime()

    def is_expired(self) -> bool:
        """检查证据是否已过期。

        Returns True if the evidence has passed its TTL expiration.
        """
        return not self.is_fresh()

    # ── Static Factory ───────────────────────────────────────────────────

    @staticmethod
    def wrap(
        content: str,
        evidence_path: Optional[str] = None,
        parent_envelope: Optional[EvidenceEnvelope] = None,
        ttl_days: int = 90,
        content_type: str = "application/json",
    ) -> EvidenceEnvelope:
        """创建证据信封，自动计算 hash + 因果链。

        Args:
            content: The evidence content string to be hashed.
            evidence_path: Optional filesystem path where the evidence is stored.
            parent_envelope: Optional parent envelope for causal chain linking.
            ttl_days: Time-to-live in days (default 90).
            content_type: MIME-style content type identifier.

        Returns:
            A new EvidenceEnvelope with computed content_hash and causal link.
        """
        content_hash = "sha256:" + hashlib.sha256(
            content.encode("utf-8")
        ).hexdigest()

        # Build causal parent hash from parent's content_hash if provided
        causal_parent_hash: Optional[str] = None
        if parent_envelope is not None:
            causal_parent_hash = parent_envelope.content_hash

        return EvidenceEnvelope(
            envelope_id=f"EE-{uuid.uuid4().hex[:12]}",
            content_hash=content_hash,
            created_at=datetime.now(timezone.utc).isoformat(),
            ttl_days=ttl_days,
            causal_parent_hash=causal_parent_hash,
            evidence_path=evidence_path,
            content_type=content_type,
        )


# ──────────────────────────────────────────────────────────────────────────────
# EvidenceChain
# ──────────────────────────────────────────────────────────────────────────────

class EvidenceChain:
    """证据链管理器——验证因果链完整性、检测断裂、过期标记。

    Maintains a chain_index.json file in the evidence directory that
    persists all envelope records. Provides methods to add evidence,
    verify chain integrity, detect broken links, find expired evidence,
    trace causal chains, and export reports.
    """

    INDEX_FILENAME = "chain_index.json"

    def __init__(self, evidence_dir: Path) -> None:
        """Initialize the evidence chain manager.

        Args:
            evidence_dir: Path to the directory where evidence files and
                          chain_index.json are stored.

        If chain_index.json exists, it is loaded. Otherwise, an empty
        chain is initialized.
        """
        self.evidence_dir = Path(evidence_dir)
        self.evidence_dir.mkdir(parents=True, exist_ok=True)
        self._index_path = self.evidence_dir / self.INDEX_FILENAME
        self._envelopes: dict[str, EvidenceEnvelope] = {}
        self._chain_head: Optional[str] = None   # envelope_id of latest
        self._load()

    # ── Persistence ──────────────────────────────────────────────────────

    def _load(self) -> None:
        """Load chain state from chain_index.json."""
        if not self._index_path.exists():
            return

        try:
            data = json.loads(self._index_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return

        raw_envelopes: dict[str, dict] = data.get("envelopes", {})
        self._envelopes = {}
        for eid, raw in raw_envelopes.items():
            self._envelopes[eid] = EvidenceEnvelope(
                envelope_id=raw["envelope_id"],
                content_hash=raw["content_hash"],
                created_at=raw["created_at"],
                ttl_days=raw.get("ttl_days", 90),
                causal_parent_hash=raw.get("causal_parent_hash"),
                evidence_path=raw.get("evidence_path"),
                content_type=raw.get("content_type", "application/json"),
            )
        self._chain_head = data.get("chain_head")

    def _save(self) -> None:
        """Persist chain state to chain_index.json."""
        raw_envelopes: dict[str, dict] = {}
        for eid, env in self._envelopes.items():
            d = asdict(env)
            raw_envelopes[eid] = d

        data: dict = {
            "envelopes": raw_envelopes,
            "chain_head": self._chain_head,
        }
        self._index_path.write_text(
            json.dumps(data, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    # ── Mutation ─────────────────────────────────────────────────────────

    def add_evidence(
        self,
        content: str,
        evidence_path: Optional[str] = None,
        parent_id: Optional[str] = None,
        ttl_days: int = 90,
        content_type: str = "application/json",
    ) -> EvidenceEnvelope:
        """添加新证据，自动链接到父证据。

        Args:
            content: The evidence content to wrap.
            evidence_path: Optional path to the evidence file.
            parent_id: Optional envelope_id of the parent evidence.
                       If None, defaults to the current chain_head.
            ttl_days: TTL in days.
            content_type: Content type identifier.

        Returns:
            The newly created EvidenceEnvelope, now part of the chain.

        If parent_id is not provided, the chain_head (latest envelope)
        is used as the parent, creating a linear causal chain.
        """
        # Resolve parent
        parent_envelope: Optional[EvidenceEnvelope] = None
        if parent_id is not None:
            parent_envelope = self._envelopes.get(parent_id)
        elif self._chain_head is not None:
            parent_envelope = self._envelopes.get(self._chain_head)

        envelope = EvidenceEnvelope.wrap(
            content=content,
            evidence_path=evidence_path,
            parent_envelope=parent_envelope,
            ttl_days=ttl_days,
            content_type=content_type,
        )

        self._envelopes[envelope.envelope_id] = envelope
        self._chain_head = envelope.envelope_id
        self._save()
        return envelope

    # ── Query ────────────────────────────────────────────────────────────

    def get_envelope(self, envelope_id: str) -> Optional[EvidenceEnvelope]:
        """Retrieve a single envelope by ID."""
        return self._envelopes.get(envelope_id)

    def list_all(self) -> list[EvidenceEnvelope]:
        """Return all envelopes in insertion order."""
        return list(self._envelopes.values())

    def get_chain(self, envelope_id: str) -> list[EvidenceEnvelope]:
        """从指定证据回溯完整因果链。

        Starting from the given envelope, follows causal_parent_hash
        backward through the chain until reaching an envelope with no
        parent (the root).

        Returns envelopes in order from the specified envelope back to
        the root (most recent first).

        Args:
            envelope_id: The envelope ID to start tracing from.

        Returns:
            List of EvidenceEnvelope in reverse causal order (most recent first).
        """
        chain: list[EvidenceEnvelope] = []
        visited: set[str] = set()

        current = self._envelopes.get(envelope_id)
        while current is not None:
            if current.envelope_id in visited:
                break  # Cycle detected
            visited.add(current.envelope_id)
            chain.append(current)

            # Follow parent hash
            parent_hash = current.causal_parent_hash
            if parent_hash is None:
                break

            # Find the envelope whose content_hash matches this parent_hash
            current = self._find_by_content_hash(parent_hash)

        return chain

    # ── Integrity ────────────────────────────────────────────────────────

    def _find_by_content_hash(self, content_hash: str) -> Optional[EvidenceEnvelope]:
        """Find an envelope by its content_hash."""
        for env in self._envelopes.values():
            if env.content_hash == content_hash:
                return env
        return None

    def _content_hash_exists(self, content_hash: str) -> bool:
        """Check whether any envelope has the given content_hash."""
        return self._find_by_content_hash(content_hash) is not None

    def verify_chain(self) -> tuple[bool, list[str]]:
        """验证因果链完整性。

        Checks:
        1. Every non-root envelope's causal_parent_hash points to an
           existing content_hash in the chain (no broken links).
        2. No envelope is expired (optional warning — expired evidence
           is reported but does not by itself make the chain invalid).

        Returns:
            (is_valid, issues) where is_valid is True only if zero
            integrity violations exist, and issues is a human-readable
            list of problems found.
        """
        issues: list[str] = []
        has_integrity_issue = False

        # Collect all known content_hashes
        known_hashes: set[str] = {env.content_hash for env in self._envelopes.values()}

        for env in self._envelopes.values():
            # Check causal parent link
            if env.causal_parent_hash is not None:
                if env.causal_parent_hash not in known_hashes:
                    has_integrity_issue = True
                    issues.append(
                        f"[BROKEN] {env.envelope_id}: causal_parent_hash "
                        f"({env.causal_parent_hash[:20]}...) points to an "
                        f"unknown evidence record"
                    )

            # Check expiration (warning only, does not break integrity)
            if env.is_expired():
                issues.append(
                    f"[EXPIRED] {env.envelope_id}: created {env.created_at}, "
                    f"TTL={env.ttl_days}d, evidence is stale"
                )

        is_valid = not has_integrity_issue
        return is_valid, issues

    def find_expired(self) -> list[EvidenceEnvelope]:
        """找出所有过期证据。

        Returns:
            List of EvidenceEnvelope that have passed their TTL.
        """
        return [env for env in self._envelopes.values() if env.is_expired()]

    def find_broken_links(self) -> list[str]:
        """找出因果链中所有断裂点（parent_hash 指向不存在的证据）。

        A broken link means an envelope's causal_parent_hash does not
        match any content_hash currently in the chain.

        Returns:
            List of envelope_id strings that have broken parent links.
        """
        broken: list[str] = []
        known_hashes: set[str] = {env.content_hash for env in self._envelopes.values()}

        for env in self._envelopes.values():
            if env.causal_parent_hash is not None:
                if env.causal_parent_hash not in known_hashes:
                    broken.append(env.envelope_id)

        return broken

    # ── Reporting ────────────────────────────────────────────────────────

    def export_chain_report(self) -> str:
        """导出证据链完整性报告（Markdown 格式）。

        Produces a human-readable Markdown report covering:
        - Total envelope count
        - Chain head
        - Expired evidence
        - Broken causal links
        - Per-envelope details table

        Returns:
            Markdown-formatted report string.
        """
        total = len(self._envelopes)
        expired = self.find_expired()
        broken = self.find_broken_links()
        is_valid, issues = self.verify_chain()

        lines: list[str] = []
        lines.append("# Evidence Chain Report")
        lines.append("")
        lines.append(f"**Evidence Directory:** `{self.evidence_dir}`")
        lines.append(f"**Report Generated:** {datetime.now(timezone.utc).isoformat()}")
        lines.append("")

        lines.append("## Summary")
        lines.append("")
        lines.append(f"- **Total Envelopes:** {total}")
        lines.append(f"- **Chain Head:** {self._chain_head or 'N/A'}")
        lines.append(f"- **Chain Integrity:** {'VALID' if is_valid else 'INVALID'}")
        lines.append(f"- **Expired Evidence:** {len(expired)}")
        lines.append(f"- **Broken Links:** {len(broken)}")
        lines.append("")

        if issues:
            lines.append("## Issues")
            lines.append("")
            for issue in issues:
                lines.append(f"- {issue}")
            lines.append("")

        if expired:
            lines.append("## Expired Evidence")
            lines.append("")
            lines.append("| Envelope ID | Created At | TTL (days) | Evidence Path |")
            lines.append("|-------------|------------|------------|---------------|")
            for env in expired:
                path_display = env.evidence_path or "N/A"
                lines.append(
                    f"| {env.envelope_id} | {env.created_at} | "
                    f"{env.ttl_days} | {path_display} |"
                )
            lines.append("")

        if broken:
            lines.append("## Broken Links")
            lines.append("")
            lines.append("The following envelopes have causal parent hashes "
                         "that point to missing evidence:")
            lines.append("")
            for bid in broken:
                env = self._envelopes.get(bid)
                if env and env.causal_parent_hash:
                    lines.append(
                        f"- **{bid}** → parent_hash `{env.causal_parent_hash[:20]}...` "
                        f"(not found)"
                    )
            lines.append("")

        if self._envelopes:
            lines.append("## All Envelopes")
            lines.append("")
            lines.append(
                "| Envelope ID | Content Hash | Created At | TTL | "
                "Parent Hash | Fresh? |"
            )
            lines.append(
                "|-------------|--------------|------------|-----|"
                "-------------|--------|"
            )
            for env in self._envelopes.values():
                parent_short = (
                    env.causal_parent_hash[:20] + "..."
                    if env.causal_parent_hash
                    else "N/A (root)"
                )
                fresh = "Yes" if env.is_fresh() else "NO"
                lines.append(
                    f"| {env.envelope_id} | {env.content_hash[:20]}... | "
                    f"{env.created_at} | {env.ttl_days}d | "
                    f"{parent_short} | {fresh} |"
                )
            lines.append("")

        return "\n".join(lines)


# ──────────────────────────────────────────────────────────────────────────────
# T-0109 F5: 证据链三处收敛（chain.yaml 校验/冻结 → loop_core 单一实现）
# ──────────────────────────────────────────────────────────────────────────────
# 原实现散落三处：loop_core.evidence_chain（chain_index.json 信封链，本模块
# 上部）、tools/tool_evidence_chain.py（subprocess 壳 → scripts/evidence_chain.py
# 的 chain.yaml 校验）。T-0109 将 chain.yaml 校验/冻结逻辑收敛至此模块
# （verify_chain_yaml / freeze_file_yaml），tools/tool_evidence_chain.py 与
# scripts/evidence_chain.py 改为 in-process / 遗留 CLI 引用本实现。
# 宿主无关（DR-002）：宿主特定安装副本路径（.zcode 前缀）不硬编码于
# loop_core，由调用方经 host_candidates 参数或环境变量
# LOOP_GOVERNANCE_CHAIN_YAML_HOST 显式注入；注入候选优先于仓库源回退
# （T-0105 安装副本优先语义保持），仓库源候选为纯相对路径。输出 dict
# 结构逐字段等价（整体/问题/节点），供行为等价测试对照。

CHAIN_YAML_CANDIDATES = (
    "skills/loop-governance/chain.yaml",
)

# 宿主注入通道：环境变量值为相对 project_root 的 chain.yaml 路径
# （宿主部署时显式配置其安装副本，如 .zcode 安装副本），注入候选优先
# 于仓库源回退。loop_core 自身不含任何宿主路径字面量。
ENV_CHAIN_YAML_HOST_CANDIDATE = "LOOP_GOVERNANCE_CHAIN_YAML_HOST"


def load_chain_yaml(
    project_root: str | Path,
    host_candidates: tuple[str, ...] = (),
) -> dict | None:
    """Load chain.yaml（宿主注入副本优先，仓库源回退）。缺失/不可解析 → None。

    宿主特定路径由调用方显式传入（host_candidates）或经环境变量
    LOOP_GOVERNANCE_CHAIN_YAML_HOST 配置注入；loop_core 不含宿主路径
    字面量（DR-002 宿主无关原则）。
    """
    root = Path(project_root).resolve()
    env_host = os.environ.get(ENV_CHAIN_YAML_HOST_CANDIDATE)
    injected = (*host_candidates, *((env_host,) if env_host else ()))
    for rel in (*injected, *CHAIN_YAML_CANDIDATES):
        candidate = root / rel
        if candidate.exists():
            try:
                return yaml.safe_load(candidate.read_text(encoding="utf-8"))
            except Exception:
                return None
    return None


def verify_chain_yaml(
    project_root: str | Path,
    strict: bool = False,
    host_candidates: tuple[str, ...] = (),
) -> dict:
    """按 chain.yaml 校验证据节点与上游哈希（收敛自 scripts/evidence_chain.py
    verify_chain，行为等价：overall/issues/nodes 结构逐字段一致）。

    strict 参数与配置 verify.strict_mode 取或（原语义）；required 节点缺失
    且 strict → MISSING/BLOCKED（fail-closed 语义不变）。host_candidates
    为宿主特定安装副本路径（可选注入，优先于仓库源回退）。
    """
    config = load_chain_yaml(project_root, host_candidates=host_candidates)
    if not config:
        return {"overall": "BLOCKED", "issues": ["chain.yaml not found"]}

    chain = config.get("chain", [])
    verify_config = config.get("verify", {})
    strict = strict or bool(verify_config.get("strict_mode", False))

    nodes_status: list[dict] = []
    issues: list[str] = []

    for node in chain:
        node_file = Path(project_root).resolve() / node["file"]
        name = node["name"]
        required = node.get("required", False)

        if not node_file.exists():
            if required and strict:
                issues.append(f"MISSING required node: {name} ({node['file']})")
                nodes_status.append({"name": name, "status": "MISSING"})
            else:
                nodes_status.append({"name": name, "status": "SKIPPED"})
            continue

        try:
            file_hash = hashlib.sha256(node_file.read_bytes()).hexdigest()
        except OSError as exc:
            # 不可读节点（目录/权限）→ 显式 ERROR + BLOCKED（fail-closed：
            # 不静默跳过，等价于原 subprocess 路径崩溃 → rc!=0 → BLOCKED）。
            issues.append(f"[ERROR] {name}: cannot read {node['file']}: {exc}")
            nodes_status.append({"name": name, "status": "HASH_MISMATCH"})
            continue

        # 上游依赖是否已断裂（与 scripts/evidence_chain.py 同语义）
        upstream = node.get("upstream", [])
        stale = False
        for up_name in upstream:
            up_node = next((n for n in nodes_status if n["name"] == up_name), None)
            if up_node and up_node.get("status") == "HASH_MISMATCH":
                stale = True
                break

        nodes_status.append({
            "name": name,
            "status": "PASS",
            "sha256": file_hash,
        })

        if not stale:
            issues.append(f"[ok] {name}: sha256={file_hash[:16]}...")

    overall = "BLOCKED" if any(
        n["status"] in ("MISSING", "HASH_MISMATCH") for n in nodes_status
    ) else "PASS"

    return {"overall": overall, "issues": issues, "nodes": nodes_status}


def freeze_file_yaml(project_root: str | Path, rel_path: str) -> dict:
    """冻结文件：计算并写入 SHA256 冻结记录（收敛自
    scripts/evidence_chain.py freeze_file，行为等价）。

    写入 .ai/evidence/frozen/<name>.freeze.json（幂等覆盖；记录含
    path/sha256/frozen_at/size）。目标文件缺失 → 失败 dict（不静默成功）。
    """
    target = Path(project_root).resolve() / rel_path
    if not target.exists():
        return {"success": False, "message": f"File not found: {rel_path}"}

    sha = hashlib.sha256(target.read_bytes()).hexdigest()
    frozen_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    freeze_dir = Path(project_root).resolve() / ".ai" / "evidence" / "frozen"
    freeze_dir.mkdir(parents=True, exist_ok=True)
    record_path = freeze_dir / f"{Path(rel_path).name}.freeze.json"
    record_path.write_text(json.dumps({
        "path": rel_path,
        "sha256": sha,
        "frozen_at": frozen_at,
        "size": target.stat().st_size,
    }, indent=2, ensure_ascii=False), encoding="utf-8")

    return {"success": True, "message": f"Frozen {rel_path} → sha256:{sha[:16]}..."}
