"""Find money amounts in text and check them against evidence."""
import re

_CUR = r"(?:€|\$|£|eur|usd|gbp|euros?|dollars?|pounds?)"
_NUM = r"\d{1,3}(?:[.,]\d{3})+(?:[.,]\d+)?|\d+(?:[.,]\d+)?"
_UNIT = r"(?:billion|million|thousand|bn|mln|mn|m|k|b)\b"
_WORD_UNIT = r"(?:billion|million|thousand|bn|mln)\b"
_MULT = {"billion": 1e9, "bn": 1e9, "b": 1e9, "million": 1e6, "mln": 1e6, "mn": 1e6, "m": 1e6,
         "thousand": 1e3, "k": 1e3}

PATTERN = re.compile(
    rf"{_CUR}\s?(?P<n1>{_NUM})\s?(?P<u1>{_UNIT})?"        # €775 million, $900m, EUR 1.45bn
    rf"|(?P<n2>{_NUM})\s?(?P<u2>{_WORD_UNIT})\s?{_CUR}?",  # 775 million euros, 1.45 billion
    re.IGNORECASE,
)


def _to_float(s: str) -> float:
    if re.fullmatch(r"\d{1,3}([.,]\d{3})+", s):  # 1,450,000 or 1.450.000
        return float(re.sub(r"[.,]", "", s))
    return float(s.replace(",", "."))


def extract_amounts(text: str) -> list[tuple[str, float]]:
    """Return (text as written, value) for every money amount in the text."""
    found = []
    for m in PATTERN.finditer(text or ""):
        number = m.group("n1") or m.group("n2")
        unit = (m.group("u1") or m.group("u2") or "").lower()
        try:
            found.append((m.group(0).strip(), _to_float(number) * _MULT.get(unit, 1)))
        except ValueError:
            continue
    return found


def unverified_amounts(text: str, evidence_texts: list[str]) -> list[str]:
    """Amounts in text that do not appear (within 1%) anywhere in the evidence."""
    evidence = [v for t in evidence_texts for _, v in extract_amounts(t)]
    return [raw for raw, value in extract_amounts(text)
            if not any(abs(value - e) <= 0.01 * max(value, e) for e in evidence)]
