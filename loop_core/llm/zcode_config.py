"""
ZCode host model-configuration reuse — T-0091 AC-02.

The self-audit loop reuses the ZCode CLI's own model configuration instead of
maintaining a second credential store.  Resolution chain (highest priority
first, mirroring the ZCode CLI env-over-file discipline):

  1. env  LLM_API_KEY / LLM_BASE_URL          (canonical loop-engine key)
  2. env  ANTHROPIC_API_KEY / ANTHROPIC_BASE_URL
  3. env  OPENAI_API_KEY / OPENAI_BASE_URL
  4. env  ZCODE_API_KEY / ZCODE_BASE_URL      (ZCode CLI fallback)
  5. env  DEEPSEEK_API_KEY / DEEPSEEK_BASE_URL (legacy alias tier, last —
     T-0095: same canonical table as keys.resolve_api_key)
  6. `~/.zcode/v2/config.json` -> provider.<id>.options.{apiKey,baseURL}
     (select_provider: explicit preferred provider id first, else the first
      enabled provider with a non-empty api key — anthropic kinds before
      openai kinds, because anthropic-style hosts are the ZCode mainstream)
  7. explicit LLMKeyError(KEY_MISSING) / LLMError(CONFIGURATION_ERROR) —
     never a silently empty key.

The env tier that matches also determines `protocol` (openai for the
Chat-Completions-style driver, anthropic for the Messages-style driver);
file providers map kind anthropic -> "anthropic", everything else -> "openai".

Security invariants (enforced by tests/test_zcode_config.py):
- the resolved api key never appears in logs or error messages — messages
  name only env var NAMES and config paths; both dataclasses' to_dict()
  mask the key with <REDACTED>;
- tests never read the real ~/.zcode/v2/config.json (tmp_path fixtures and
  an autouse monkeypatch of default_config_path()).
"""
from __future__ import annotations

import json
import os
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path

from loop_core.llm.errors import ErrorCode, LLMError, LLMKeyError
from loop_core.llm.keys import KEY_TIERS

__version__ = "1.1.0"

_REDACTED_MARKER = "<REDACTED>"

# (key var, base url var, protocol) — first tier with a non-empty key wins.
# T-0095: aliases the canonical table in keys.py (single source of truth) so
# this module and keys.resolve_api_key can never drift apart.  Priority:
# LLM_* -> ANTHROPIC_* -> OPENAI_* -> ZCODE_* (+ DEEPSEEK_* legacy alias
# tier last).
ENV_TIERS: tuple[tuple[str, str, str], ...] = KEY_TIERS

# Kinds that may be auto-selected; anthropic is scanned first (ZCode
# mainstream), then openai / openai-compatible.
_ANTHROPIC_KINDS = frozenset({"anthropic"})
_ELIGIBLE_KINDS = frozenset({"anthropic", "openai", "openai-compatible"})
_SELECTION_PASSES: tuple[frozenset[str], ...] = (
    _ANTHROPIC_KINDS,
    _ELIGIBLE_KINDS - _ANTHROPIC_KINDS,
)


def default_config_path() -> Path:
    """Desktop-authoritative ZCode config location (~/.zcode/v2/config.json).

    Tests monkeypatch this function (autouse fixture) so the real file is
    never read by the suite.
    """
    return Path.home() / ".zcode" / "v2" / "config.json"


@dataclass(frozen=True)
class ZCodeProvider:
    """One provider entry parsed from the ZCode v2 config."""

    provider_id: str
    name: str = ""
    kind: str = "openai"          # anthropic | openai | openai-compatible
    api_key: str = ""
    base_url: str = ""
    enabled: bool = True
    source: str = "custom"        # builtin | custom
    models: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, object]:
        """Audit-safe view — api_key is masked, never the raw value."""
        return {
            "provider_id": self.provider_id,
            "name": self.name,
            "kind": self.kind,
            "api_key": _mask_secret(self.api_key),
            "base_url": self.base_url,
            "enabled": self.enabled,
            "source": self.source,
            "models": list(self.models),
        }


@dataclass(frozen=True)
class ResolvedModelConfig:
    """Final model configuration handed to a ProtocolDriver factory.

    `provider_id` is empty when the config came purely from the environment;
    `source` records where the key was found (e.g. "env:LLM_API_KEY" or
    "file:acme") for audit traces.  `api_key` is the raw value — keep it out
    of logs / error messages (to_dict() masks it).
    """

    api_key: str
    provider_id: str = ""
    model: str = ""
    base_url: str = ""
    protocol: str = "openai"      # anthropic | openai
    source: str = ""

    @property
    def is_env_only(self) -> bool:
        return not self.provider_id

    def to_dict(self) -> dict[str, object]:
        """Audit-safe view — api_key is masked, never the raw value."""
        return {
            "provider_id": self.provider_id,
            "model": self.model,
            "api_key": _mask_secret(self.api_key),
            "base_url": self.base_url,
            "protocol": self.protocol,
            "source": self.source,
        }


def _mask_secret(value: str) -> str:
    return _REDACTED_MARKER if value else ""


def _clean_model(model: str | None) -> str:
    return model.strip() if model and model.strip() else ""


def _protocol_for_kind(kind: str) -> str:
    return "anthropic" if kind == "anthropic" else "openai"


def _parse_provider(provider_id: str, spec: dict[str, object]) -> ZCodeProvider:
    options = spec.get("options")
    if not isinstance(options, dict):
        options = {}
    raw_models = spec.get("models")
    models: tuple[str, ...] = ()
    if isinstance(raw_models, dict):
        models = tuple(str(m) for m in raw_models if str(m).strip())
    elif isinstance(raw_models, list):
        models = tuple(str(m) for m in raw_models if str(m).strip())
    enabled = spec.get("enabled", True)
    if not isinstance(enabled, bool):
        enabled = True
    return ZCodeProvider(
        provider_id=provider_id,
        name=str(spec.get("name") or "").strip(),
        kind=str(spec.get("kind") or "openai").strip().lower(),
        api_key=str(options.get("apiKey") or "").strip(),
        base_url=str(options.get("baseURL") or "").strip(),
        enabled=enabled,
        source=str(spec.get("source") or "custom").strip(),
        models=models,
    )


def resolve_zcode_provider(config_path: str | Path | None = None) -> list[ZCodeProvider]:
    """Parse the ZCode v2 config into provider candidates.

    - config_path=None -> default_config_path() (~/.zcode/v2/config.json);
    - missing file -> [] (callers decide how to fail);
    - unreadable / invalid JSON / missing "provider" section -> explicit
      LLMError(CONFIGURATION_ERROR) — never a silent empty result.
    All providers are returned, including disabled and keyless ones;
    filtering is select_provider's job.
    """
    path = Path(config_path) if config_path else default_config_path()
    if not path.is_file():
        return []
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise LLMError(
            ErrorCode.CONFIGURATION_ERROR,
            f"ZCode config file {path} is unreadable or not valid JSON: {exc}",
        ) from exc
    providers = raw.get("provider") if isinstance(raw, dict) else None
    if not isinstance(providers, dict):
        raise LLMError(
            ErrorCode.CONFIGURATION_ERROR,
            f"ZCode config file {path} has no 'provider' object",
        )
    out: list[ZCodeProvider] = []
    for provider_id, spec in providers.items():
        if isinstance(spec, dict):
            out.append(_parse_provider(str(provider_id), spec))
    return out


def select_provider(
    providers: Sequence[ZCodeProvider],
    preferred: str | None = None,
) -> ZCodeProvider | None:
    """Pick the provider to use.

    - preferred provider id: that provider wins regardless of kind
      (explicit intent); unknown id -> CONFIGURATION_ERROR; known id with an
      empty api key -> KEY_MISSING (never a silently empty key);
    - otherwise: first provider that is enabled, has a non-empty api key and
      a known kind — anthropic kinds are scanned before openai kinds;
    - no eligible provider -> None.
    """
    if preferred:
        for provider in providers:
            if provider.provider_id == preferred:
                if not provider.api_key:
                    raise LLMKeyError(
                        f"ZCode provider '{preferred}' has no api key configured "
                        "(options.apiKey is empty)",
                    )
                return provider
        available = ", ".join(p.provider_id for p in providers) or "(none)"
        raise LLMError(
            ErrorCode.CONFIGURATION_ERROR,
            f"ZCode provider '{preferred}' not found; available providers: {available}",
        )
    for kind_pass in _SELECTION_PASSES:
        for provider in providers:
            if provider.enabled and provider.api_key and provider.kind in kind_pass:
                return provider
    return None


def resolve_model_config(
    preferred_provider: str | None = None,
    preferred_model: str | None = None,
    *,
    config_path: str | Path | None = None,
    env: Mapping[str, str] | None = None,
) -> ResolvedModelConfig:
    """Resolve the model configuration for the self-audit loop.

    Chain: LLM_* -> ANTHROPIC_* -> OPENAI_* -> ZCODE_* env tiers, then the
    ZCode v2 config file (select_provider), then an explicit KEY_MISSING /
    CONFIGURATION_ERROR.  `env` may be injected for tests (defaults to
    os.environ); `config_path` may be injected for tests (defaults to
    ~/.zcode/v2/config.json).
    """
    source = os.environ if env is None else env
    for key_var, base_url_var, protocol in ENV_TIERS:
        raw_key = source.get(key_var)
        if raw_key and raw_key.strip():
            return ResolvedModelConfig(
                api_key=raw_key.strip(),
                model=_clean_model(preferred_model),
                base_url=(source.get(base_url_var) or "").strip(),
                protocol=protocol,
                source=f"env:{key_var}",
            )
    path = Path(config_path) if config_path else default_config_path()
    provider = select_provider(resolve_zcode_provider(path), preferred=preferred_provider)
    if provider is None:
        raise LLMKeyError(
            "LLM model config missing: no API key in environment (checked: "
            + ", ".join(tier[0] for tier in ENV_TIERS)
            + ") and no enabled provider with a non-empty api key in ZCode config "
            + str(path)
            + " (set an environment variable or add options.apiKey to a provider).",
        )
    return ResolvedModelConfig(
        api_key=provider.api_key,
        provider_id=provider.provider_id,
        model=_clean_model(preferred_model) or (provider.models[0] if provider.models else ""),
        base_url=provider.base_url,
        protocol=_protocol_for_kind(provider.kind),
        source=f"file:{provider.provider_id}",
    )
