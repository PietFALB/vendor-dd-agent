"""Graph nodes for the vendor due-diligence agent."""
import re

from agent import report as rpt
from agent.assess import assess
from agent.review import run_review
from agent.state import DDState
from tools.gleif import search_gleif
from tools.kvk import get_kvk_profile
from tools.sanctions import screen_sanctions


# ---------------------------------------------------------------- 1. validate

def validate_input(state: DDState) -> dict:
    name = (state.get("company_name") or "").strip()
    kvk = (state.get("kvk_number") or "").strip() or None
    problems = []
    if len(name) < 2:
        problems.append("Company name is empty or too short.")
    if kvk and not re.fullmatch(r"\d{8}", kvk):
        problems.append(f"KvK number {kvk!r} must be 8 digits.")
    return {
        "company_name": name,
        "kvk_number": kvk,
        "valid": not problems,
        "errors": [f"Input: {p}" for p in problems],
        "trace": ["validate_input"],
    }


# ---------------------------------------------------------------- 2. resolve

def resolve_entity(state: DDState) -> dict:
    name = state["company_name"]
    errors, sources = [], []

    gleif = search_gleif(name)
    sources.append(gleif.source)
    match = gleif.data.get("match") if gleif.ok else None
    if not gleif.ok:
        errors.append(gleif.error)
    elif match is None:
        errors.append(f"GLEIF: no LEI record found for {name!r}; using the name as given.")
    elif match.get("match_score", 100) < 85:
        errors.append(
            f"GLEIF: best match {match['legal_name']!r} (similarity {match['match_score']}) "
            f"may not be the company searched for. Verify identity manually."
        )

    if match and not match.get("direct_parent") and not match.get("ultimate_parent"):
        errors.append("Ownership: no parent reported to GLEIF; ownership and ultimate beneficial owners "
                      "(UBOs) are not verified. Obtain a UBO declaration.")

    kvk_number = state.get("kvk_number")
    if not kvk_number and match and match.get("jurisdiction") == "NL":
        kvk_number = match.get("registered_as")

    kvk_profile = None
    if kvk_number:
        kvk = get_kvk_profile(kvk_number)
        sources.append(kvk.source)
        if not kvk.ok:
            errors.append(kvk.error)
        elif not kvk.data.get("found"):
            note = " (test environment only holds fictitious companies)" if "/test/" in kvk.source else ""
            errors.append(f"KvK: {kvk_number} not found{note}.")
        else:
            kvk_profile = kvk.data

    entity = {
        "name_as_given": name,
        "legal_name": match["legal_name"] if match else name,
        "lei": match["lei"] if match else None,
        "match_score": match.get("match_score") if match else None,
        "other_names": match["other_names"] if match else [],
        "entity_status": match["entity_status"] if match else None,
        "registration_status": match["registration_status"] if match else None,
        "country": match["country"] if match else None,
        "address": match["address"] if match else None,
        "direct_parent": match["direct_parent"] if match else None,
        "ultimate_parent": match["ultimate_parent"] if match else None,
        "kvk_number": kvk_number,
        "kvk_profile": kvk_profile,
        "other_candidates": gleif.data.get("candidates", []) if gleif.ok else [],
        "sources": sources,
    }
    return {"entity": entity, "errors": errors, "trace": ["resolve_entity"]}


# ---------------------------------------------------------------- 3. screen

def screen_sanctions_node(state: DDState) -> dict:
    entity = state.get("entity") or {}

    # The name as given is always screened, so a wrong GLEIF match can never produce a false "clean"
    targets = [(entity.get("legal_name") or state["company_name"], "company")]
    targets.append((state["company_name"], "name as given"))
    targets += [(n, "former or other name") for n in entity.get("other_names", [])]
    for key, role in [("direct_parent", "direct parent"), ("ultimate_parent", "ultimate parent")]:
        parent = entity.get(key)
        if parent and parent.get("legal_name"):
            targets.append((parent["legal_name"], role))

    hits, errors, seen, screened, complete = [], [], set(), [], True
    for name, role in targets:
        if name.lower() in seen:
            continue
        seen.add(name.lower())
        screened.append(f"{name} [{role}]")
        result = screen_sanctions(name)
        if not result.ok:
            errors.append(result.error)
            complete = False
            continue
        for hit in result.data["hits"]:
            hits.append({"screened": name, "role": role, **hit})

    # One entry per sanctioned entity, listing every name that matched it
    merged = {}
    for h in hits:
        entry = merged.setdefault(h["id"], {**h, "matched_via": [], "score": 0})
        entry["matched_via"].append(f"{h['screened']} [{h['role']}]")
        entry["score"] = max(entry["score"], h["score"])
    hits = sorted(merged.values(), key=lambda h: h["score"], reverse=True)

    # Second step of screening: clear fuzzy hits with a secondary identifier (country)
    company_country = (entity.get("country") or "").lower()
    for h in hits:
        hit_countries = {c for c in h.get("countries", "").lower().split(";") if c}
        h["country_mismatch"] = bool(company_country and hit_countries and company_country not in hit_countries)
        h["likely_false_positive"] = bool(h["country_mismatch"] and h["score"] < 95 and entity.get("lei"))

    return {
        "sanctions_hits": hits,
        "screened_names": screened,
        "screening_complete": complete,
        "errors": errors,
        "trace": ["screen_sanctions"],
    }


# ---------------------------------------------------------------- 4. review

def enhanced_review(state: DDState) -> dict:
    out = run_review(state["company_name"], state.get("entity"), hits=state.get("sanctions_hits"))
    return {**out, "trace": ["enhanced_review"]}


def standard_review(state: DDState) -> dict:
    out = run_review(state["company_name"], state.get("entity"), hits=None)
    return {**out, "trace": ["standard_review"]}


# ---------------------------------------------------------------- 5. assess

def assess_risk(state: DDState) -> dict:
    return {**assess(state), "trace": ["assess_risk"]}


# ---------------------------------------------------------------- 6. report

def write_report(state: DDState) -> dict:
    return {"report": rpt.build_report(state), "trace": ["write_report"]}


def check_report(state: DDState) -> dict:
    problems = rpt.check_report(state)
    return {
        "report_ok": not problems,
        "check_problems": problems,
        "check_attempts": state.get("check_attempts", 0) + 1,
        "trace": ["check_report"],
    }


def save_report(state: DDState) -> dict:
    path = rpt.save_report(state, ok=state.get("report_ok", False))
    return {"report_path": path, "trace": ["save_report"]}


# ---------------------------------------------------------------- routers

def route_after_validate(state: DDState) -> str:
    return "continue" if state.get("valid") else "stop"


def route_after_screening(state: DDState) -> str:
    real = [h for h in state.get("sanctions_hits", []) if not h.get("likely_false_positive")]
    return "enhanced" if real else "standard"


def route_after_check(state: DDState) -> str:
    if state.get("report_ok") or state.get("check_attempts", 0) >= 2:
        return "save"
    return "rewrite"
