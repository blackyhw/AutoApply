from __future__ import annotations

import re
import unicodedata

BEGIN = "<<<UNTRUSTED_THIRD_PARTY_DATA>>>"
END = "<<<END_UNTRUSTED_THIRD_PARTY_DATA>>>"

_INVISIBLE_CATEGORIES = {"Cf", "Cc"}
_ALLOWED_CONTROL = {"\n", "\t"}

# Patterns that commonly appear in prompt-injection payloads (EN + ES).
_INJECTION_PATTERNS: tuple[re.Pattern[str], ...] = tuple(
    re.compile(p, re.IGNORECASE)
    for p in (
        r"ignore (all |any |the )?(previous|prior|above) instructions",
        r"disregard (your|the) (system )?prompt",
        r"you are now",
        r"act as (a |an )?(system|developer|root)",
        r"reveal (your )?(system )?prompt",
        r"new instructions?:",
        r"</?system>",
        r"ignora(r)? (todas )?las instrucciones (anteriores|previas)",
        r"olvid(a|á|ate) (tu |el )?prompt",
        r"ahora sos",
        r"ahora eres",
        r"revel(a|á|ame) el (system )?prompt",
        r"instrucciones del sistema",
    )
)


def strip_invisible(text: str) -> str:
    chars: list[str] = []
    for ch in text:
        if ch in _ALLOWED_CONTROL:
            chars.append(ch)
            continue
        if unicodedata.category(ch) in _INVISIBLE_CATEGORIES:
            continue
        if ord(ch) in {0x200B, 0x200C, 0x200D, 0x2060, 0xFEFF, 0x202A, 0x202B, 0x202C, 0x202D, 0x202E}:
            continue
        chars.append(ch)
    return "".join(chars)


def redact_injection_phrases(text: str) -> str:
    redacted = text
    for pattern in _INJECTION_PATTERNS:
        redacted = pattern.sub("[redacted-untrusted-instruction]", redacted)
    return redacted


def sanitize_untrusted_text(text: str) -> str:
    cleaned = strip_invisible(text)
    cleaned = cleaned.replace(BEGIN, "").replace(END, "")
    cleaned = redact_injection_phrases(cleaned)
    return cleaned.strip()
