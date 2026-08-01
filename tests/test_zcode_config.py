"""
T-0091 AC-02 — ZCode host model-configuration resolution tests.

Every test is fully fixture-driven:
- the ZCode config is written under tmp_path — the real
  ~/.zcode/v2/config.json is NEVER read: an autouse fixture monkeypatches
  zcode_config.default_config_path() to a tmp_path location, so even a
  forgotten explicit path cannot reach the real file (proven by
  test_default_config_path_is_isolated);
- keys are fake test-only values ("sk-test-...") and base URLs use the
  reserved .invalid TLD — never resolvable, never a real endpoint;
- env vars are injected via `env=` / monkeypatch.setenv and cleared by the
  autouse fixture (no dependence on the real process environment).

AC mapping:
  AC-02a test_resolve_zcode_provider_*   fixture parse + field correctness
  AC-02b test_select_provider_*          selection (preferred / kind priority)
  AC-02c test_env_* / test_file_*        env priority chain, file fallback,
                                         all-missing -> KEY_MISSING
  AC-02d test_*_redacts_* / error text   redaction (no raw keys anywhere)
  AC-02e test_corrupt_*                  broken file -> env fallback / error
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from loop_core.llm import zcode_config
from loop_core.llm.errors import ErrorCode, LLMError, LLMKeyError
from loop_core.llm.zcode_config import (
    ENV_TIERS,
    ResolvedModelConfig,
    ZCodeProvider,
    resolve_model_config,
    resolve_zcode_provider,
    select_provider,
)

FAKE_KEY = "sk-test-0123456789abcdef"  # fake test-only key (never a real secret)
FAKE_KEY2 = "sk-test-abcdef0123456789"
BASE = "https://llm.test.invalid/v1"   # .invalid TLD — never resolvable
BASE2 = "https://api.example.invalid/v1"

MODEL_ACME = ("m-alpha", "m-beta")
MODEL_NEBULA = ("gpt-test",)


# ── fixtures ────────────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def isolate_zcode_config(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    """Point the default ZCode config path at tmp_path and clear every env
    var this module consults — no test can touch the real ~/.zcode/v2/config.json
    or be influenced by the real process environment."""
    isolated = tmp_path / "zcode" / "v2" / "config.json"
    monkeypatch.setattr(zcode_config, "default_config_path", lambda: isolated)
    for key_var, base_url_var, _protocol in ENV_TIERS:
        monkeypatch.delenv(key_var, raising=False)
        monkeypatch.delenv(base_url_var, raising=False)
    monkeypatch.delenv("LLM_REDACT_SECRETS", raising=False)
    return isolated


def _write_config(tmp_path: Path, providers: dict[str, object]) -> Path:
    """Write a fixture ZCode v2 config at the isolated tmp_path location."""
    path = tmp_path / "zcode" / "v2" / "config.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"provider": providers}, ensure_ascii=False), encoding="utf-8")
    return path


def _write_corrupt_config(tmp_path: Path) -> Path:
    path = tmp_path / "zcode" / "v2" / "config.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text('{"provider": {"acme": {"options": {"apiKey": ', encoding="utf-8")
    return path


def _fixture_providers() -> dict[str, object]:
    """A representative provider mix: enabled anthropic, enabled openai,
    disabled anthropic (never auto-selected), keyless anthropic (never
    auto-selected)."""
    return {
        "acme": {
            "name": "Acme Anthropic",
            "kind": "anthropic",
            "source": "custom",
            "enabled": True,
            "options": {"apiKey": FAKE_KEY, "baseURL": BASE},
            "models": {"m-alpha": {"display_name": "Alpha"}, "m-beta": {}},
        },
        "nebula": {
            "name": "Nebula OpenAI",
            "kind": "openai",
            "enabled": True,
            "options": {"apiKey": FAKE_KEY2, "baseURL": BASE2},
            "models": MODEL_NEBULA,
        },
        "zephyr": {
            "name": "Zephyr",
            "kind": "anthropic",
            "enabled": False,
            "options": {"apiKey": "sk-test-disabled-000000", "baseURL": BASE},
        },
        "ghost": {
            "name": "Ghost",
            "kind": "anthropic",
            "enabled": True,
            "options": {},
        },
    }


# ══════════════════════════════════════════════════════════════════════════
# AC-02a — fixture parse (provider list fields; enabled/apiKey filtering
#          happens at selection time, both verified here)
# ══════════════════════════════════════════════════════════════════════════


def test_resolve_zcode_provider_parses_fixture_fields(
    tmp_path: Path, isolate_zcode_config: Path
) -> None:
    _write_config(tmp_path, _fixture_providers())
    providers = resolve_zcode_provider()

    assert [p.provider_id for p in providers] == ["acme", "nebula", "zephyr", "ghost"]

    acme = providers[0]
    assert acme.name == "Acme Anthropic"
    assert acme.kind == "anthropic"
    assert acme.source == "custom"
    assert acme.enabled is True
    assert acme.api_key == FAKE_KEY
    assert acme.base_url == BASE
    assert acme.models == MODEL_ACME  # dict -> key list, insertion order

    nebula = providers[1]
    assert nebula.kind == "openai"
    assert nebula.api_key == FAKE_KEY2
    assert nebula.models == MODEL_NEBULA  # list form accepted too
    assert nebula.source == "custom"      # default when absent

    zephyr = providers[2]
    assert zephyr.enabled is False
    assert zephyr.api_key  # parsed but not auto-selected (enabled=False)

    ghost = providers[3]
    assert ghost.api_key == ""  # parsed but not auto-selected (no key)
    assert ghost.models == ()


def test_resolve_zcode_provider_missing_file_returns_empty(
    tmp_path: Path, isolate_zcode_config: Path
) -> None:
    assert resolve_zcode_provider() == []
    assert resolve_zcode_provider(isolate_zcode_config) == []  # not created yet
    assert resolve_zcode_provider(tmp_path / "nope" / "config.json") == []


def test_resolve_zcode_provider_default_path_is_fixture_path(
    tmp_path: Path, isolate_zcode_config: Path
) -> None:
    _write_config(tmp_path, _fixture_providers())
    # no config_path argument -> monkeypatched default (isolated tmp path)
    assert resolve_zcode_provider() == resolve_zcode_provider(isolate_zcode_config)


def test_explicit_config_path_parameter_wins(
    tmp_path: Path, isolate_zcode_config: Path
) -> None:
    # a config OUTSIDE the default location, passed explicitly
    path = tmp_path / "elsewhere" / "config.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"provider": {"acme": _fixture_providers()["acme"]}}), encoding="utf-8"
    )
    providers = resolve_zcode_provider(config_path=path)
    assert [p.provider_id for p in providers] == ["acme"]
    # default (isolated) location has no file at all
    assert resolve_zcode_provider() == []


def test_default_config_path_is_isolated(isolate_zcode_config: Path) -> None:
    """Proof the autouse fixture redirects the default path away from the
    real ~/.zcode/v2/config.json for every test in this module."""
    assert zcode_config.default_config_path() == isolate_zcode_config
    assert isolate_zcode_config != Path.home() / ".zcode" / "v2" / "config.json"


# ══════════════════════════════════════════════════════════════════════════
# AC-02b — selection logic (preferred wins; default prefers anthropic;
#          enabled/apiKey/kind filtering)
# ══════════════════════════════════════════════════════════════════════════


def test_select_provider_default_prefers_anthropic_kind() -> None:
    # openai listed first in the file, anthropic second — kind priority wins
    providers = [
        ZCodeProvider("nebula", kind="openai", api_key=FAKE_KEY2),
        ZCodeProvider("acme", kind="anthropic", api_key=FAKE_KEY),
    ]
    chosen = select_provider(providers)
    assert chosen is not None
    assert chosen.provider_id == "acme"
    assert chosen.kind == "anthropic"


def test_select_provider_preferred_wins_over_kind_priority() -> None:
    providers = [
        ZCodeProvider("acme", kind="anthropic", api_key=FAKE_KEY),
        ZCodeProvider("nebula", kind="openai", api_key=FAKE_KEY2),
    ]
    chosen = select_provider(providers, preferred="nebula")
    assert chosen is not None
    assert chosen.provider_id == "nebula"
    assert chosen.kind == "openai"


def test_select_provider_skips_disabled_and_keyless() -> None:
    providers = [
        ZCodeProvider("zephyr", kind="anthropic", api_key=FAKE_KEY, enabled=False),
        ZCodeProvider("ghost", kind="anthropic", api_key="", enabled=True),
        ZCodeProvider("acme", kind="anthropic", api_key=FAKE_KEY, enabled=True),
    ]
    chosen = select_provider(providers)
    assert chosen is not None
    assert chosen.provider_id == "acme"


def test_select_provider_accepts_openai_compatible_kind() -> None:
    providers = [
        ZCodeProvider("acme", kind="anthropic", api_key="", enabled=True),
        ZCodeProvider("proxy", kind="openai-compatible", api_key=FAKE_KEY, enabled=True),
    ]
    chosen = select_provider(providers)
    assert chosen is not None
    assert chosen.provider_id == "proxy"


def test_select_provider_none_when_no_eligible() -> None:
    assert select_provider([]) is None
    assert select_provider([ZCodeProvider("g", kind="anthropic", api_key="", enabled=True)]) is None
    assert (
        select_provider([ZCodeProvider("z", kind="anthropic", api_key=FAKE_KEY, enabled=False)])
        is None
    )
    # unknown kind is never auto-selected
    assert (
        select_provider([ZCodeProvider("x", kind="azure", api_key=FAKE_KEY, enabled=True)])
        is None
    )


def test_select_provider_preferred_unknown_raises_configuration_error() -> None:
    providers = [ZCodeProvider("acme", kind="anthropic", api_key=FAKE_KEY)]
    with pytest.raises(LLMError) as excinfo:
        select_provider(providers, preferred="nope")
    assert excinfo.value.code is ErrorCode.CONFIGURATION_ERROR
    message = str(excinfo.value)
    assert "nope" in message and "acme" in message  # ids are not secrets
    assert FAKE_KEY not in message


def test_select_provider_preferred_keyless_raises_key_missing() -> None:
    providers = [ZCodeProvider("ghost", kind="anthropic", api_key="")]
    with pytest.raises(LLMKeyError) as excinfo:
        select_provider(providers, preferred="ghost")
    assert excinfo.value.code is ErrorCode.KEY_MISSING
    assert excinfo.value.retryable is False
    assert "ghost" in str(excinfo.value)
    assert FAKE_KEY not in str(excinfo.value)


# ══════════════════════════════════════════════════════════════════════════
# AC-02c — env priority chain (env > file; LLM > ANTHROPIC > OPENAI > ZCODE;
#          all missing -> KEY_MISSING)
# ══════════════════════════════════════════════════════════════════════════


def test_env_llm_tier_wins(
    tmp_path: Path, isolate_zcode_config: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_config(tmp_path, _fixture_providers())  # file exists, env must win
    monkeypatch.setenv("LLM_API_KEY", FAKE_KEY)
    monkeypatch.setenv("LLM_BASE_URL", BASE)
    monkeypatch.setenv("ANTHROPIC_API_KEY", FAKE_KEY2)
    monkeypatch.setenv("ZCODE_API_KEY", FAKE_KEY2)

    cfg = resolve_model_config()
    assert isinstance(cfg, ResolvedModelConfig)
    assert cfg.api_key == FAKE_KEY
    assert cfg.base_url == BASE
    assert cfg.protocol == "openai"
    assert cfg.source == "env:LLM_API_KEY"
    assert cfg.provider_id == ""  # env-only: no provider from the file
    assert cfg.is_env_only is True


def test_env_anthropic_tier_second(
    monkeypatch: pytest.MonkeyPatch, isolate_zcode_config: Path
) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", FAKE_KEY)
    monkeypatch.setenv("ANTHROPIC_BASE_URL", BASE)
    cfg = resolve_model_config()
    assert cfg.api_key == FAKE_KEY
    assert cfg.base_url == BASE
    assert cfg.protocol == "anthropic"
    assert cfg.source == "env:ANTHROPIC_API_KEY"


def test_env_openai_tier_third(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", FAKE_KEY)
    monkeypatch.setenv("OPENAI_BASE_URL", BASE)
    cfg = resolve_model_config()
    assert cfg.api_key == FAKE_KEY
    assert cfg.base_url == BASE
    assert cfg.protocol == "openai"
    assert cfg.source == "env:OPENAI_API_KEY"


def test_env_zcode_tier_fourth(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ZCODE_API_KEY", FAKE_KEY)
    monkeypatch.setenv("ZCODE_BASE_URL", BASE)
    cfg = resolve_model_config()
    assert cfg.api_key == FAKE_KEY
    assert cfg.base_url == BASE
    assert cfg.protocol == "openai"
    assert cfg.source == "env:ZCODE_API_KEY"


def test_env_whitespace_key_skipped(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_API_KEY", "   ")
    monkeypatch.setenv("OPENAI_API_KEY", FAKE_KEY)
    cfg = resolve_model_config()
    assert cfg.api_key == FAKE_KEY
    assert cfg.source == "env:OPENAI_API_KEY"


def test_env_mapping_injection_without_process_env(isolate_zcode_config: Path) -> None:
    cfg = resolve_model_config(env={"ZCODE_API_KEY": FAKE_KEY, "ZCODE_BASE_URL": BASE})
    assert cfg.api_key == FAKE_KEY
    assert cfg.base_url == BASE
    assert cfg.source == "env:ZCODE_API_KEY"


def test_env_priority_order_llm_over_anthropic_over_openai(
    monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-openai-000001")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test-anthropic-000002")
    monkeypatch.setenv("LLM_API_KEY", "sk-test-llm-000003")
    cfg = resolve_model_config()
    assert cfg.api_key == "sk-test-llm-000003"
    assert cfg.source == "env:LLM_API_KEY"


def test_file_fallback_when_env_missing(
    tmp_path: Path, isolate_zcode_config: Path
) -> None:
    _write_config(tmp_path, _fixture_providers())
    cfg = resolve_model_config()
    assert cfg.provider_id == "acme"          # anthropic preferred
    assert cfg.api_key == FAKE_KEY
    assert cfg.base_url == BASE
    assert cfg.protocol == "anthropic"
    assert cfg.source == "file:acme"
    assert cfg.is_env_only is False
    assert cfg.model == MODEL_ACME[0]         # default = first provider model


def test_file_model_default_and_preferred_model(
    tmp_path: Path, isolate_zcode_config: Path
) -> None:
    _write_config(tmp_path, _fixture_providers())
    assert resolve_model_config().model == "m-alpha"
    assert resolve_model_config(preferred_model="m-beta").model == "m-beta"
    assert resolve_model_config(preferred_model="  ").model == "m-alpha"  # blank -> default


def test_file_preferred_provider_and_model(
    tmp_path: Path, isolate_zcode_config: Path
) -> None:
    _write_config(tmp_path, _fixture_providers())
    cfg = resolve_model_config(preferred_provider="nebula", preferred_model="gpt-test")
    assert cfg.provider_id == "nebula"
    assert cfg.model == "gpt-test"
    assert cfg.api_key == FAKE_KEY2
    assert cfg.protocol == "openai"
    assert cfg.source == "file:nebula"


def test_file_preferred_provider_skips_kind_priority(
    tmp_path: Path, isolate_zcode_config: Path
) -> None:
    _write_config(tmp_path, _fixture_providers())
    cfg = resolve_model_config(preferred_provider="nebula")  # openai kind, explicit
    assert cfg.provider_id == "nebula"
    assert cfg.model == "gpt-test"


def test_file_without_usable_provider_raises_key_missing(
    tmp_path: Path, isolate_zcode_config: Path
) -> None:
    _write_config(
        tmp_path,
        {
            "zephyr": {"kind": "anthropic", "enabled": False,
                       "options": {"apiKey": "sk-test-disabled-000000"}},
            "ghost": {"kind": "anthropic", "enabled": True, "options": {}},
        },
    )
    with pytest.raises(LLMKeyError) as excinfo:
        resolve_model_config()
    assert excinfo.value.code is ErrorCode.KEY_MISSING


def test_file_preferred_provider_unknown_raises_configuration_error(
    tmp_path: Path, isolate_zcode_config: Path
) -> None:
    _write_config(tmp_path, _fixture_providers())
    with pytest.raises(LLMError) as excinfo:
        resolve_model_config(preferred_provider="nope")
    assert excinfo.value.code is ErrorCode.CONFIGURATION_ERROR


def test_all_missing_raises_key_missing(isolate_zcode_config: Path) -> None:
    with pytest.raises(LLMKeyError) as excinfo:
        resolve_model_config()
    err = excinfo.value
    assert err.code is ErrorCode.KEY_MISSING
    assert err.retryable is False
    message = str(err)
    # env var NAMES and the config path are named — values never are
    for var in ("LLM_API_KEY", "ANTHROPIC_API_KEY", "OPENAI_API_KEY", "ZCODE_API_KEY"):
        assert var in message
    assert "config.json" in message
    assert "sk-" not in message
    assert FAKE_KEY not in message
    assert FAKE_KEY2 not in message


# ══════════════════════════════════════════════════════════════════════════
# AC-02d — redaction (to_dict masks keys; no raw key in any error message)
# ══════════════════════════════════════════════════════════════════════════


def test_resolved_config_to_dict_redacts_key(
    tmp_path: Path, isolate_zcode_config: Path
) -> None:
    _write_config(tmp_path, _fixture_providers())
    cfg = resolve_model_config()
    d = cfg.to_dict()
    assert d["api_key"] == "<REDACTED>"
    assert FAKE_KEY not in json.dumps(d)


def test_provider_to_dict_redacts_key(
    tmp_path: Path, isolate_zcode_config: Path
) -> None:
    _write_config(tmp_path, _fixture_providers())
    providers = resolve_zcode_provider()
    acme = providers[0].to_dict()
    assert acme["api_key"] == "<REDACTED>"
    assert FAKE_KEY not in json.dumps(acme)
    ghost = providers[3].to_dict()
    assert ghost["api_key"] == ""  # honest: keyless stays empty, no fake marker


def test_key_missing_error_message_never_contains_key(
    tmp_path: Path, isolate_zcode_config: Path
) -> None:
    _write_config(tmp_path, _fixture_providers())
    with pytest.raises(LLMKeyError) as excinfo:
        resolve_model_config(preferred_provider="ghost")  # keyless provider
    message = str(excinfo.value)
    assert FAKE_KEY not in message
    assert FAKE_KEY2 not in message
    assert "sk-" not in message


def test_configuration_error_message_never_contains_key(
    tmp_path: Path, isolate_zcode_config: Path
) -> None:
    _write_config(tmp_path, _fixture_providers())
    with pytest.raises(LLMError) as excinfo:
        resolve_model_config(preferred_provider="nope")
    message = str(excinfo.value)
    assert FAKE_KEY not in message
    assert FAKE_KEY2 not in message


def test_corrupt_file_error_message_never_contains_key(
    tmp_path: Path, isolate_zcode_config: Path
) -> None:
    _write_corrupt_config(tmp_path)
    with pytest.raises(LLMError) as excinfo:
        resolve_zcode_provider()
    message = str(excinfo.value)
    assert FAKE_KEY not in message
    assert FAKE_KEY2 not in message
    assert "sk-" not in message


# ══════════════════════════════════════════════════════════════════════════
# AC-02e — broken config file (fall back to env; explicit error otherwise)
# ══════════════════════════════════════════════════════════════════════════


def test_corrupt_file_raises_configuration_error(
    tmp_path: Path, isolate_zcode_config: Path
) -> None:
    _write_corrupt_config(tmp_path)
    with pytest.raises(LLMError) as excinfo:
        resolve_zcode_provider()
    assert excinfo.value.code is ErrorCode.CONFIGURATION_ERROR
    assert "config.json" in str(excinfo.value)


def test_corrupt_file_with_env_key_still_resolves_from_env(
    tmp_path: Path, isolate_zcode_config: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_corrupt_config(tmp_path)
    monkeypatch.setenv("LLM_API_KEY", FAKE_KEY)
    cfg = resolve_model_config()
    assert cfg.api_key == FAKE_KEY  # broken file never blocks a working env


def test_corrupt_file_without_env_raises_explicit_error(
    tmp_path: Path, isolate_zcode_config: Path
) -> None:
    _write_corrupt_config(tmp_path)
    with pytest.raises(LLMError) as excinfo:
        resolve_model_config()
    assert excinfo.value.code is ErrorCode.CONFIGURATION_ERROR
    assert excinfo.value.retryable is False


def test_config_without_provider_section_raises_configuration_error(
    tmp_path: Path, isolate_zcode_config: Path
) -> None:
    path = tmp_path / "zcode" / "v2" / "config.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text('{"theme": "dark"}', encoding="utf-8")
    with pytest.raises(LLMError) as excinfo:
        resolve_zcode_provider()
    assert excinfo.value.code is ErrorCode.CONFIGURATION_ERROR


def test_config_with_empty_provider_object_returns_empty_list(
    tmp_path: Path, isolate_zcode_config: Path
) -> None:
    path = tmp_path / "zcode" / "v2" / "config.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text('{"provider": {}}', encoding="utf-8")
    assert resolve_zcode_provider() == []
    # and resolution fails explicitly (no env, no provider)
    with pytest.raises(LLMKeyError) as excinfo:
        resolve_model_config()
    assert excinfo.value.code is ErrorCode.KEY_MISSING
