"""Auto-generated conversation titles for the chat list (short, word-aware)."""

import re

# Fits typical sidebars; full text stays in legal_situation on the model.
_DEFAULT_MAX_TOTAL = 60
_DOMAIN_MAX = 24
_SEP = " · "


def _collapse_ws(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip())


def _truncate_at_word(text: str, max_len: int) -> str:
    if not text:
        return ""
    if len(text) <= max_len:
        return text
    if max_len <= 1:
        return "…"
    cut = text[: max_len - 1]
    last_space = cut.rfind(" ")
    if last_space > 0:
        return cut[:last_space].rstrip() + "…"
    return cut.rstrip() + "…"


def format_auto_chat_name(
    legal_domain: str | None,
    legal_situation: str,
    *,
    max_total: int = _DEFAULT_MAX_TOTAL,
) -> str:
    """
    Build a compact label: short domain + short situation snippet.
    Stays within max_total for display; still under 255 for CharField.
    """
    situation = _collapse_ws(legal_situation)
    domain_raw = _collapse_ws(legal_domain or "") or "Legal"
    domain = _truncate_at_word(domain_raw, _DOMAIN_MAX)

    if not situation:
        out = domain
    else:
        budget = max(8, max_total - len(domain) - len(_SEP))
        snippet = _truncate_at_word(situation, budget)
        out = f"{domain}{_SEP}{snippet}"

    if len(out) > 255:
        return out[:252] + "…"
    return out
