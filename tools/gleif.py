"""GLEIF: legal identity, KvK number and parent companies. Free, no key."""
from rapidfuzz import fuzz

from tools.base import ToolResult
from tools.http import get_with_retry
from tools.sanctions import normalize

BASE = "https://api.gleif.org/api/v1/lei-records"
LEGAL_FORMS = ["", " N.V.", " B.V.", " Limited", " Ltd", " PLC", " AG", " SA", " GmbH", " Inc."]
STRONG = 95  # below this, also try exact legal-name searches


def _summary(record: dict) -> dict:
    a = record["attributes"]
    e = a["entity"]
    return {
        "lei": a["lei"],
        "legal_name": e["legalName"]["name"],
        "other_names": [n["name"] for n in e.get("otherNames", [])],
        "entity_status": e.get("status"),
        "registration_status": a["registration"].get("status"),
        "jurisdiction": e.get("jurisdiction"),
        "category": e.get("category"),  # GENERAL, BRANCH, FUND, ...
        "registered_as": e.get("registeredAs"),  # KvK number for Dutch entities
        "address": ", ".join(e["legalAddress"].get("addressLines", []) + [e["legalAddress"].get("city") or ""]),
        "country": e["legalAddress"].get("country"),
    }


def _parent(lei: str, kind: str) -> dict | None:
    """kind = 'direct-parent' or 'ultimate-parent'. None if not reported."""
    r = get_with_retry(f"{BASE}/{lei}/{kind}")
    if r.status_code == 404:
        return None
    r.raise_for_status()
    data = r.json().get("data")
    return _summary(data) if data else None


GENERIC_PREFIXES = ("koninklijke ", "royal ")  # 'Koninklijke Ahold Delhaize' = 'Ahold Delhaize'


def _clean(name: str) -> str:
    """normalize() plus GLEIF-only stripping of generic prefixes (not used for sanctions)."""
    s = normalize(name).strip()
    for prefix in GENERIC_PREFIXES:
        if s.startswith(prefix):
            s = s[len(prefix):]
    return s


def _similarity(query: str, rec: dict) -> float:
    """Best name similarity between the query and the record's legal or other names."""
    q = _clean(query)
    return max(fuzz.token_sort_ratio(q, _clean(n)) for n in [rec["legal_name"], *rec["other_names"]])


def _tiebreak(query: str, rec: dict) -> float:
    """Raw closeness of the full name, so 'Heineken N.V.' beats 'Heineken Holding N.V.' on a tie."""
    return fuzz.ratio(query.lower(), rec["legal_name"].lower())


def _rank(name: str, rec: dict) -> float:
    """Similarity, with a penalty for inactive (merged, dissolved) entities."""
    penalty = (0 if rec["entity_status"] == "ACTIVE" else 15) + (10 if rec.get("category") == "BRANCH" else 0)
    return _similarity(name, rec) - penalty


def _search(params: dict) -> list[dict]:
    r = get_with_retry(BASE, params=params)
    r.raise_for_status()
    return [_summary(rec) for rec in r.json().get("data", [])]


def search_gleif(name: str) -> ToolResult:
    try:
        # 1. Full-text search: broad, but noisy for short or common names
        records = {rec["lei"]: rec for rec in _search({"filter[fulltext]": name, "page[size]": 25})}

        # 2. If nothing matches strongly, try the exact legal name with common legal forms
        # Use the ranking (with branch/inactive penalties), so a branch never counts as 'found'
        if not records or max(_rank(name, r) for r in records.values()) < STRONG:
            for form in LEGAL_FORMS:
                for rec in _search({"filter[entity.legalName]": name + form, "page[size]": 50}):
                    records.setdefault(rec["lei"], rec)

        if not records:
            return ToolResult(ok=True, data={"match": None, "candidates": []}, source=BASE)

        scored = sorted(records.values(), key=lambda rec: (_rank(name, rec), _tiebreak(name, rec)), reverse=True)
        best = scored[0]
        best["match_score"] = round(_similarity(name, best), 1)
        best["direct_parent"] = _parent(best["lei"], "direct-parent")
        best["ultimate_parent"] = _parent(best["lei"], "ultimate-parent")
        candidates = [
            {"legal_name": rec["legal_name"], "country": rec["country"], "score": round(_similarity(name, rec), 1)}
            for rec in scored[1:6]
        ]
        return ToolResult(ok=True, data={"match": best, "candidates": candidates}, source=f"{BASE}/{best['lei']}")
    except Exception as e:
        return ToolResult(ok=False, error=f"GLEIF failed: {e}", source=BASE)
