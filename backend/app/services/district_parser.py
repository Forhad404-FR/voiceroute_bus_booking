"""District matching and natural-language route parsing (pure Python, no I/O).

Canonical district names always come from the database; this module only matches user
text against the list it is given plus a small alias table for common alternate spellings.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

# alias (normalised) -> canonical district name stored in MySQL
ALIASES: dict[str, str] = {
    "chittagong": "Chattogram",
    "chitagong": "Chattogram",
    "ctg": "Chattogram",
    "barisal": "Barishal",
    "jessore": "Jashore",
    "comilla": "Cumilla",
    "bogra": "Bogura",
    "cox bazar": "Cox's Bazar",
    "cox bazaar": "Cox's Bazar",
    "coxs bazaar": "Cox's Bazar",
    "coxsbazar": "Cox's Bazar",
    "moulvi bazar": "Moulvibazar",
    "maulvibazar": "Moulvibazar",
    "mymensing": "Mymensingh",
    "narayangonj": "Narayanganj",
}

_STOPWORDS = {
    "i", "id", "im", "ill", "want", "need", "would", "like", "wanna", "go", "going", "travel",
    "travelling", "traveling", "find", "show", "search", "book", "get", "me", "some", "a", "an",
    "the", "any", "bus", "buses", "ticket", "tickets", "seat", "seats", "please", "hey", "hi",
    "ok", "okay", "trip", "journey", "route", "routes", "for", "my", "take", "can", "you", "let",
    "lets", "looking", "look", "available", "between", "there", "is", "are", "do", "we", "us",
    "voice", "route", "search",
}
_INTENT_RE = re.compile(
    r"\b(?:i\s+)?(?:want|need|would\s+like|wanna|like|have)\s+to\s+(?:go|travel|book|get|take|find|search|see|visit)\b"
)


def key(text: str) -> str:
    """Normalise for comparison: lower-case, curly apostrophes and punctuation removed."""
    t = (text or "").lower().replace("’", "'").replace("‘", "'")
    t = re.sub(r"[^a-z0-9\s']", " ", t)
    t = t.replace("'", "")
    return re.sub(r"\s+", " ", t).strip()


@dataclass
class Resolution:
    exact: str | None = None
    candidates: list[str] = field(default_factory=list)


def resolve(segment: str, districts: list[str]) -> Resolution:
    """Match a text segment against district names (list order = display order)."""
    k = key(segment)
    if not k:
        return Resolution()
    by_key = {key(d): d for d in districts}
    if k in by_key:
        return Resolution(exact=by_key[k], candidates=[by_key[k]])
    alias = ALIASES.get(k)
    if alias and alias in districts:
        return Resolution(exact=alias, candidates=[alias])

    found: set[str] = set()
    for name in districts:
        nk = key(name)
        if nk.startswith(k) or any(w.startswith(k) for w in nk.split()):
            found.add(name)
    for alias_key, canonical in ALIASES.items():
        if canonical in districts and alias_key.startswith(k):
            found.add(canonical)
    ordered = [d for d in districts if d in found]
    return Resolution(exact=ordered[0] if len(ordered) == 1 else None, candidates=ordered)


@dataclass
class ParsedRoute:
    origin: str | None = None
    destination: str | None = None
    origin_text: str = ""
    destination_text: str = ""
    origin_candidates: list[str] = field(default_factory=list)
    destination_candidates: list[str] = field(default_factory=list)
    understood: bool = False


def _clean(text: str) -> str:
    t = (text or "").lower().replace("’", "'").replace("‘", "'")
    t = re.sub(r"[^a-z0-9\s']", " ", t)
    t = _INTENT_RE.sub(" ", t)
    words = []
    for w in t.split():
        if w in ("to", "from"):
            words.append(w)
        elif w.strip("'") in _STOPWORDS:
            continue
        else:
            words.append(w)
    return " ".join(words)


def parse_route_text(text: str, districts: list[str]) -> ParsedRoute:
    """Parse phrases like 'Dhaka to Chittagong', 'I want to go from Dhaka to Sylhet',
    'Show me buses to Cox's Bazar' or the partial 'Dhaka to C'."""
    cleaned = _clean(text)
    result = ParsedRoute()
    if not cleaned:
        return result

    parts = re.split(r"\b(from|to)\b", cleaned)
    pre = parts[0].strip()
    origin_seg = ""
    dest_seg = ""
    markers = parts[1::2]
    segments = [s.strip() for s in parts[2::2]]
    if markers:
        if pre and markers[0] == "to":
            origin_seg = pre
        for m, seg in zip(markers, segments):
            if m == "from" and not origin_seg:
                origin_seg = seg
            elif m == "to" and not dest_seg:
                dest_seg = seg
    else:
        origin_seg = pre

    o = resolve(origin_seg, districts)
    d = resolve(dest_seg, districts)
    result.origin, result.destination = o.exact, d.exact
    result.origin_text, result.destination_text = origin_seg, dest_seg
    result.origin_candidates, result.destination_candidates = o.candidates, d.candidates
    result.understood = bool(o.candidates or d.candidates)
    if result.origin and result.destination and result.origin == result.destination:
        result.destination = None
        result.destination_candidates = []
    return result
