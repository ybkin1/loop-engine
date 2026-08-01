"""
Sensitive-information redaction — api keys / tokens never appear in logs or
error messages.

T-0090 D1: mirrors the StaffDeck `_safe_fragment` discipline.  Every error
message and log line built by the LLM layer passes through a Redactor seeded
with the resolved api key (plus optional extra secrets from
LLM_REDACT_SECRETS, comma-separated).  A defensive guard also masks
credentials in URLs / header maps before they reach any message.
"""
from __future__ import annotations

import os
import re
from collections.abc import Iterable, Mapping

__version__ = "1.0.0"

_REDACTED = "<REDACTED>"

# Header names whose values are credentials (matched case-insensitively).
_SECRET_HEADER_NAMES = frozenset(
    {
        "authorization",
        "proxy-authorization",
        "x-api-key",
        "api-key",
        "apikey",
        "cookie",
        "set-cookie",
    }
)

# Query parameter names whose values are credentials.
_SECRET_QUERY_NAMES = frozenset(
    {
        "key",
        "api_key",
        "apikey",
        "token",
        "access_token",
        "auth",
        "sig",
        "signature",
        "password",
        "secret",
    }
)

_MIN_SECRET_LEN = 6  # ignore trivially short values to avoid over-redaction


def _env_extra_secrets() -> tuple[str, ...]:
    raw = os.environ.get("LLM_REDACT_SECRETS", "")
    return tuple(s.strip() for s in raw.split(",") if len(s.strip()) >= _MIN_SECRET_LEN)


class Redactor:
    """Replaces known secret values with a fixed marker in arbitrary text."""

    def __init__(self, secrets: Iterable[str] = ()) -> None:
        self._secrets: tuple[str, ...] = tuple(
            sorted({s for s in secrets if s and len(s) >= _MIN_SECRET_LEN}, key=len, reverse=True)
        )
        # Longest-first so overlapping secrets redact deterministically.

    @property
    def secret_count(self) -> int:
        return len(self._secrets)

    def redact(self, text: str) -> str:
        """Replace every occurrence of any known secret with <REDACTED>."""
        if not self._secrets or not text:
            return text
        out = text
        for secret in self._secrets:
            if secret in out:
                out = out.replace(secret, _REDACTED)
        return out

    def redact_url(self, url: str) -> str:
        """Strip credentials from a URL string (userinfo + secret query params)."""
        if not url:
            return url
        # userinfo: https://user:pass@host -> https://<REDACTED>@host
        url = re.sub(r"//[^/@\s]+@", "//" + _REDACTED + "@", url)
        if "?" in url:
            base, _, query = url.partition("?")
            cleaned = []
            for part in query.split("&"):
                name, _, _ = part.partition("=")
                if name.lower() in _SECRET_QUERY_NAMES:
                    cleaned.append(name + "=" + _REDACTED)
                else:
                    cleaned.append(part)
            url = base + "?" + "&".join(cleaned)
        return url

    def redact_headers(self, headers: Mapping[str, str]) -> dict[str, str]:
        """Mask credential header values (names preserved for debuggability)."""
        return {
            name: (_REDACTED if name.lower() in _SECRET_HEADER_NAMES else value)
            for name, value in headers.items()
        }

    def safe_fragment(self, payload: object, max_len: int = 300) -> str:
        """Short, printable, redacted fragment of an arbitrary payload.

        StaffDeck `_safe_fragment` style: stringify, strip control chars,
        truncate with an ellipsis, redact secrets.  Safe for error messages
        and logs.
        """
        if isinstance(payload, bytes):
            raw = payload.decode("utf-8", errors="replace")
        elif isinstance(payload, str):
            raw = payload
        else:
            raw = str(payload)
        raw = "".join(ch if ch.isprintable() or ch in "\n\t" else "?" for ch in raw)
        raw = re.sub(r"\s+", " ", raw).strip()
        if len(raw) > max_len:
            raw = raw[: max_len - 1] + "…"
        return self.redact(raw)


def make_redactor(api_key: str | None = None) -> Redactor:
    """Redactor seeded with the resolved key + LLM_REDACT_SECRETS env extras."""
    secrets = [s for s in (api_key, *list(_env_extra_secrets())) if s]
    return Redactor(secrets)
