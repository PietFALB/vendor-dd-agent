"""GLEIF: legal identity, KvK number and parent companies. Free, no key."""
import requests
from rapidfuzz import fuzz

from tools.base import ToolResult
from tools.http import get_with_retry
from tools.sanctions import normalize

BASE = "https://api.gleif.org/api/v1/lei-records"


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
        "registered_as": e.get("registeredAs"),  # KvK number for Dutch entities
        "address": ", ".join(e["legalAddress"].get("addressLines", []) + [e["legalAddress"].get("city") or ""]),
        "country": e["legalAddress"].get("country"),
    }


def _parent(lei: str, kind: str) -> dict | None:
    """kind = 'direct-parent' or 'ultimate-parent'. None if not reported."""
    r = get_with_retry(f"{BASE}/{lei}/{kind}", timeout=15)
    if r.status_code == 404:
        return None
    r.raise_for_status()
    data = r.json().get("data")
    return _summary(data) if data else None


def _similarity(query: str, rec: dict) -> float:
    """Best name similarity between the query and the record's legal or other names."""
    names = [rec["legal_name"], *rec["other_names"]]
    q = normalize(query)
    return max(fuzz.token_sort_ratio(q, normalize(n)) for n in names)


def search_gleif(name: str) -> ToolResult:
    try:
        r = get_with_retry(BASE, params={"filter[fulltext]": name, "page[size]": 10}, timeout=15)
        r.raise_for_status()
        records = [_summary(rec) for rec in r.json().get("data", [])]
        if not records:
            return ToolResult(ok=True, data={"match": None, "candidates": []}, source=r.url)

        # Rank by name similarity; prefer active entities on a tie
        scored = sorted(
            records,
            key=lambda rec: (_similarity(name, rec), rec["entity_status"] == "ACTIVE"),
            reverse=True,
        )
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
