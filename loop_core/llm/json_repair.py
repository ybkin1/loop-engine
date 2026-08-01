"""
JSON repair — multi-candidate strategies for dirty LLM structured output.

T-0090 D1: mirrors StaffDeck llm/client.py JSON repair.  `repair_json` tries
candidates in order (conservative first) and returns the first parseable
result together with the strategy name; when every candidate fails it raises
JSONRepairError (converted to LLMError(INVALID_RESPONSE) by the driver).

Candidates:
  1. identity            — direct parse (already valid)
  2. trim-fences         — strip ```json / ``` fences and surrounding prose
  3. extract-block       — pull the first balanced {…} or […]
  4. trailing-commas     — remove dangling commas before } ]
  5. control-chars       — escape raw control characters inside strings
  6. unescaped-quotes    — escape quotes that are clearly string content
  7. unquoted-keys       — quote bare keys (a: 1 -> "a": 1)
  8. combo               — every repair applied together on the extracted block
"""
from __future__ import annotations

import json
import re
from typing import Any

from loop_core.llm.errors import JSONRepairError

__version__ = "1.0.0"


# ── per-candidate transforms (each returns text to attempt parsing) ────────

def _trim_fences(text: str) -> str:
    """Strip markdown code fences and any prose around the JSON payload."""
    fenced = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
    if fenced:
        return fenced.group(1).strip()
    return text.strip()


def _find_balanced_block(text: str, start: int) -> tuple[str, int]:
    """Return (block_text, end_index) of the balanced {…}/[…] starting at `start`.

    Scans with a string-aware state machine so braces inside string literals
    do not count toward depth.  Returns (None, start) when unbalanced.
    """
    opener = text[start]
    closer = "}" if opener == "{" else "]"
    depth = 0
    in_string = False
    escaped = False
    i = start
    while i < len(text):
        ch = text[i]
        if in_string:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == '"':
                in_string = False
        else:
            if ch == '"':
                in_string = True
            elif ch == opener:
                depth += 1
            elif ch == closer:
                depth -= 1
                if depth == 0:
                    return text[start : i + 1], i + 1
        i += 1
    return None, start


def _extract_block(text: str) -> str:
    """First balanced {…} or […] block; fall back to a 'best effort' scan."""
    for m in re.finditer(r"[{\[]", text):
        block, _end = _find_balanced_block(text, m.start())
        if block is not None:
            return block
    # No balanced block: fall back to substring between first opener and the
    # last closer if both exist (still worth one parse attempt).
    first_open = text.find("{")
    first_bracket = text.find("[")
    if first_open < 0 and first_bracket < 0:
        return text
    start = first_open if (first_open >= 0 and (first_bracket < 0 or first_open < first_bracket)) else first_bracket
    last = max(text.rfind("}"), text.rfind("]"))
    return text[start : last + 1] if last >= start else text


def _strip_trailing_commas(text: str) -> str:
    """Remove dangling commas before closing braces/brackets (repeatedly)."""
    prev = None
    out = re.sub(r",\s*([}\]])", r"\1", text)
    while out != prev:
        prev = out
        out = re.sub(r",\s*([}\]])", r"\1", out)
    return out


_CONTROL_MAP = {
    "\n": "\\n",
    "\r": "\\r",
    "\t": "\\t",
    "\b": "\\b",
    "\f": "\\f",
}


def _escape_control_chars(text: str) -> str:
    """Escape raw control characters that appear INSIDE string literals."""
    out: list[str] = []
    in_string = False
    escaped = False
    for ch in text:
        if in_string:
            if escaped:
                out.append(ch)
                escaped = False
                continue
            if ch == "\\":
                out.append(ch)
                escaped = True
                continue
            if ch == '"':
                out.append(ch)
                in_string = False
                continue
            if ch in _CONTROL_MAP:
                out.append(_CONTROL_MAP[ch])
                continue
            if ord(ch) < 0x20:
                out.append(f"\\u{ord(ch):04x}")
                continue
            out.append(ch)
        else:
            if ch == '"':
                in_string = True
            out.append(ch)
    return "".join(out)


def _fix_unescaped_quotes(text: str) -> str:
    """Escape quotes inside strings that are clearly content, not terminators.

    Heuristic: while inside a string, an unescaped `"` whose next significant
    character is a letter/digit/quote (string obviously continues) is treated
    as content and gets a backslash; a quote followed by `,`/`}`/`]`/`:`/EOF
    stays a terminator.  This repairs LLM output like {"a": "he said "hi" ok"}.
    """
    out: list[str] = []
    in_string = False
    escaped = False
    i = 0
    n = len(text)
    while i < n:
        ch = text[i]
        if in_string:
            if escaped:
                out.append(ch)
                escaped = False
                i += 1
                continue
            if ch == "\\":
                out.append(ch)
                escaped = True
                i += 1
                continue
            if ch == '"':
                nxt = i + 1
                while nxt < n and text[nxt] in " \t":
                    nxt += 1
                nxt_ch = text[nxt] if nxt < n else ""
                if nxt_ch in ",}]:\n" or nxt_ch == "":
                    in_string = False
                    out.append(ch)
                else:
                    out.append("\\" + ch)  # content quote -> escape it
                i += 1
                continue
            out.append(ch)
            i += 1
        else:
            if ch == '"':
                in_string = True
            out.append(ch)
            i += 1
    return "".join(out)


def _quote_unquoted_keys(text: str) -> str:
    """Quote bare object keys: `{a: 1}` -> `{"a": 1}` (string-aware)."""
    out: list[str] = []
    in_string = False
    escaped = False
    i = 0
    n = len(text)
    while i < n:
        ch = text[i]
        if in_string:
            out.append(ch)
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == '"':
                in_string = False
            i += 1
            continue
        if ch == '"':
            in_string = True
            out.append(ch)
            i += 1
            continue
        # bare key pattern: start of value context `{` or `,`, then ident, then ':'
        if ch in "{,":
            m = re.match(r"([{,])(\s*)([A-Za-z_][A-Za-z0-9_]*)(\s*):", text[i:])
            if m:
                out.append(m.group(1) + m.group(2) + '"' + m.group(3) + '"' + m.group(4) + ":")
                i += m.end()
                continue
        out.append(ch)
        i += 1
    return "".join(out)


# ── candidate pipeline ─────────────────────────────────────────────────────

def _candidates(text: str) -> list[tuple[str, str]]:
    """Ordered (strategy, transformed_text) candidates — conservative first."""
    stripped = text.strip()
    block = _extract_block(stripped)
    combo_block = _quote_unquoted_keys(
        _fix_unescaped_quotes(_escape_control_chars(_strip_trailing_commas(block)))
    )
    return [
        ("identity", stripped),
        ("trim-fences", _trim_fences(stripped)),
        ("extract-block", block),
        ("trailing-commas", _strip_trailing_commas(stripped)),
        ("extract+trailing-commas", _strip_trailing_commas(block)),
        ("control-chars", _escape_control_chars(stripped)),
        ("unescaped-quotes", _fix_unescaped_quotes(stripped)),
        ("unquoted-keys", _quote_unquoted_keys(stripped)),
        ("combo", combo_block),
    ]


def repair_json(text: str, *, context: str = "") -> tuple[Any, str]:
    """Repair dirty JSON text; returns (parsed, strategy_used).

    Raises JSONRepairError when no candidate parses.  `context` names the
    caller (operation / field) for the error message.
    """
    if isinstance(text, bytes):
        text = text.decode("utf-8", errors="replace")
    if not isinstance(text, str):
        raise JSONRepairError(
            f"json repair: expected text, got {type(text).__name__}",
            strategies_tried=(),
        )
    tried: list[str] = []
    for strategy, candidate in _candidates(text):
        tried.append(strategy)
        try:
            return json.loads(candidate), strategy
        except (json.JSONDecodeError, ValueError, TypeError):
            continue
    label = f" for {context}" if context else ""
    raise JSONRepairError(
        f"invalid JSON response{label}: {len(tried)} repair strategies failed",
        fragment=text[:200],
        strategies_tried=tuple(tried),
    )
