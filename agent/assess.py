"""Risk assessment: the LLM judges the evidence in a fixed format; code enforces a rating floor
and checks that every red flag cites evidence that was actually gathered."""
import json
import os
import re
from typing import Literal

from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from rag.retrieve import retrieve
from tools.amounts import unverified_amounts
from tools.dates import age_years, event_year

RATINGS = ["Low", "Medium", "High"]
RECOMMENDATIONS = ["Onboard", "Onboard with conditions", "Escalate", "Do not onboard"]
STRONG_HIT = 95  # sanctions score from which a hit sets the floor to High


class RedFlag(BaseModel):
    flag: str = Field(description="Short name of the red flag, e.g. 'Listed on EU sanctions list'")
    category: Literal["sanctions", "ownership or control", "circumvention", "adverse media",
                      "investigation", "identity", "data gap", "other"]
    severity: Literal["Low", "Medium", "High"]
    evidence: str = Field(description="One sentence: what the evidence shows")
    evidence_source: str = Field(description="Exact URL or source name from the EVIDENCE SOURCES list")
    guidance_ref: str | None = Field(None, description="Exact reference from the GUIDANCE REFERENCES list, or null")
    event_year: int | None = Field(None, description="Year the underlying event happened, from the evidence")


class RiskAssessment(BaseModel):
    rating: Literal["Low", "Medium", "High"]
    recommendation: Literal["Onboard", "Onboard with conditions", "Escalate", "Do not onboard"]
    red_flags: list[RedFlag]
    rationale: str = Field(description="2-4 sentences explaining the rating, using only the evidence")


PROMPT = """You are a senior compliance officer assessing a new vendor before onboarding.

Judge ONLY the evidence below. Rules:
- No evidence, no flag. Every red flag must cite an exact source from EVIDENCE SOURCES.
- Never add up, convert or calculate amounts. Use amounts exactly as they appear in the evidence.
- Give each red flag the year of the underlying event (event_year), if the evidence shows it.
- An unresolved, ongoing investigation or prosecution is its own red flag, category 'investigation'.
  Do not merge it into an older, settled case.
- Events older than 5 years (age_years > 5) weigh less: on their own they support at most a Medium
  rating, and they are past events, never 'current' or 'ongoing'.
- Use guidance_ref only with an exact entry from GUIDANCE REFERENCES, otherwise null.
- Sanctions hits are shown in the evidence, but do NOT create sanctions red flags yourself:
  code adds one per hit. Add the OTHER flags (circumvention, ownership or control, adverse media, identity).
- One red flag per event. Several articles about the same event (e.g. one settlement reported by
  two outlets) go into ONE flag; pick the most authoritative article as the source.
- Recommendation: 'Escalate' for High. For Medium, choose 'Onboard with conditions' (e.g. enhanced
  monitoring) unless there is an unresolved, current investigation. 'Onboard' only for Low.
  'Do not onboard' is set by code for entities listed under EU or UK sanctions.
- Count adverse media only if it is about this company itself, not if it is merely mentioned.
- Data gaps (listed under LIMITATIONS) are not red flags about the company, but an incomplete check
  must lower your confidence: never recommend 'Onboard' when sanctions screening was incomplete.
- Rating guide: High = sanctions exposure or serious recent financial crime; Medium = past enforcement,
  unresolved investigations, or material data gaps; Low = no relevant findings and complete checks.

EVIDENCE:
{evidence}

EVIDENCE SOURCES (use exactly):
{sources}

GUIDANCE REFERENCES (use exactly):
{refs}"""


def _freeze_guidance() -> str | None:
    """Reference to the guidance passage on asset freezes, for code-made sanctions flags."""
    try:
        hits = retrieve("prohibition on making funds or economic resources available to a listed person or entity, asset freeze", k=4)
    except Exception:
        return None
    preferred = [h for h in hits if h["source"].startswith("ec_faq")] or hits
    return f"{preferred[0]['source']} p.{preferred[0]['page']}" if preferred else None


def _floor(state: dict) -> tuple[str, str, str | None]:
    """Minimum rating and recommendation enforced by code: the strictest of ALL rules that apply."""
    rules = []
    for h in state.get("sanctions_hits", []):
        roles = " ".join(h.get("matched_via", []))
        if h["score"] >= STRONG_HIT and ("[company]" in roles or "[name as given]" in roles):
            if re.search(r"\b(EU|GB)-", h.get("programs", "")):
                rules.append(("High", "Do not onboard",
                              f"Strong match on an EU/UK-listed entity ({h['name']}, score {h['score']}); "
                              "making funds or economic resources available to it is prohibited."))
            else:
                rules.append(("High", "Escalate",
                              f"Strong sanctions match on the company itself ({h['name']}, score {h['score']})."))
    real_hits = [h for h in state.get("sanctions_hits", []) if not h.get("likely_false_positive")]
    if real_hits and not rules:
        rules.append(("Medium", "Escalate", "Possible sanctions match that needs manual review before onboarding."))
    if not state.get("screening_complete", True):
        rules.append(("Medium", "Escalate", "Sanctions screening was incomplete; complete it before onboarding."))
    entity = state.get("entity") or {}
    if not entity.get("lei") and not entity.get("kvk_profile"):
        rules.append(("Medium", "Escalate", "Identity not verified: no LEI record and no company register profile found."))
    if not state.get("media_complete", True):
        rules.append(("Medium", "Onboard with conditions", "Adverse media check incomplete: the news search failed."))

    if not rules:
        return "Low", "Onboard", None
    rating = max((r[0] for r in rules), key=RATINGS.index)
    recommendation = max((r[1] for r in rules), key=RECOMMENDATIONS.index)
    return rating, recommendation, " ".join(r[2] for r in rules)


def assess(state: dict) -> dict:
    entity = state.get("entity") or {}
    hits = state.get("sanctions_hits", [])
    news = state.get("news", [])
    guidance = state.get("guidance", [])

    evidence = {
        "company": {
            "name_as_given": state.get("company_name"),
            "legal_name": entity.get("legal_name"),
            "country": entity.get("country"),
            "entity_status": entity.get("entity_status"),
            "lei": entity.get("lei"),
            "ultimate_parent": (entity.get("ultimate_parent") or {}).get("legal_name"),
        },
        "sanctions_screening_complete": state.get("screening_complete", True),
        "sanctions_hits": [{"name": h["name"], "score": h["score"], "programs": h["programs"],
                            "matched_via": h.get("matched_via"), "source": h["url"]} for h in hits],
        "adverse_media": [{"title": n["title"], "date": n.get("date"), "summary": n["summary"],
                           "risk_type": n["risk_type"], "year": event_year(n.get("date")),
                           "age_years": age_years(n.get("date")), "source": n["url"]} for n in news],
        "review_summary": state.get("review_summary"),
        "article_excerpts": [t[:400] for t in state.get("evidence_texts", [])],
        "guidance": [{"ref": f"{g['source']} p.{g['page']}", "text": g["text"][:400]} for g in guidance],
        "limitations": state.get("errors", []),
    }
    sources = sorted({h["url"] for h in hits} | {n["url"] for n in news}
                     | {"GLEIF", "KvK", "OpenSanctions"})
    refs = sorted({f"{g['source']} p.{g['page']}" for g in guidance})

    model = os.environ.get("ASSESS_MODEL") or os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
    llm = ChatOpenAI(model=model, temperature=0).with_structured_output(RiskAssessment)

    errors = []
    try:
        result: RiskAssessment = llm.invoke(PROMPT.format(
            evidence=json.dumps(evidence, ensure_ascii=False, indent=1),
            sources="\n".join(sources),
            refs="\n".join(refs) or "(none)",
        ))
    except Exception as e:
        result = None
        errors.append(f"Assessment: LLM failed ({e}); rating set by code rules only.")

    # Check every red flag against the evidence that was actually gathered
    flags = []
    for f in (result.red_flags if result else []):
        if f.evidence_source not in sources:
            errors.append(f"Assessment: dropped red flag with unknown source: {f.flag!r}")
            continue
        if f.guidance_ref and f.guidance_ref not in refs:
            errors.append(f"Assessment: removed unverified guidance reference from {f.flag!r}")
            f.guidance_ref = None
        bad = unverified_amounts(f.evidence, state.get("evidence_texts", []))
        if bad:
            errors.append(f"Assessment: amount(s) {bad} not in the evidence; evidence text of {f.flag!r} cleared")
            f.evidence = "See source."
        flags.append(f.model_dump())

    # Sanctions red flags are made by code, one per hit; any LLM sanctions flags are replaced
    flags = [f for f in flags if f["category"] != "sanctions"]
    hits_for_flags = state.get("sanctions_hits", [])
    freeze_ref = _freeze_guidance() if hits_for_flags else None
    code_flags = []
    for h in hits_for_flags:
        via = "; ".join(h.get("matched_via", []))
        strong = h["score"] >= STRONG_HIT and ("[company]" in via or "[name as given]" in via)
        code_flags.append({
            "flag": f"Listed under sanctions programs: {h['programs']}" if strong
                    else f"Name similar to a sanctioned entity in another country, likely false positive: {h['name']}"
                    if h.get("likely_false_positive")
                    else f"Possible sanctions match, verify: {h['name']}",
            "category": "sanctions",
            "severity": "High" if strong else "Low" if h.get("likely_false_positive") else "Medium",
            "evidence": f"{h['name']} ({h.get('countries') or 'country unknown'}) matched at score {h['score']} via {via}.",
            "evidence_source": h["url"],
            "guidance_ref": freeze_ref,
            "event_year": None,
        })
    ent = state.get("entity") or {}
    if not ent.get("lei") and not ent.get("kvk_profile"):
        flags = [f for f in flags if f["category"] != "identity"]
        code_flags.append({
            "flag": "Company identity could not be verified",
            "category": "identity",
            "severity": "Medium",
            "evidence": "No LEI record in GLEIF and no company register (KvK) profile found for the name as given.",
            "evidence_source": "GLEIF",
            "guidance_ref": None,
            "event_year": None,
        })
    flags = code_flags + flags

    # A settled case is not an open investigation: relabel before merging
    settled_words = ("settle", "settled", "fined", "agreed to pay", "paid a fine", "penalty")
    for f in flags:
        text = f"{f['flag']} {f['evidence']}".lower()
        if f["category"] == "investigation" and any(w in text for w in settled_words):
            f["category"] = "adverse media"
            errors.append(f"Assessment: {f['flag']!r} relabelled from investigation to adverse media (case was settled)")

    # Merge red flags about the same event (same category and year), keeping all sources
    merged = {}
    for f in flags:
        if f["category"] == "sanctions" or not f.get("event_year"):
            key = (f["category"], f["flag"].lower())        # sanctions: one flag per listed entity
        elif f["category"] == "investigation":
            key = ("investigation", f["event_year"])      # open cases stay apart from settled ones
        else:
            key = ("event", f["event_year"])              # same year = same event, whatever the category
        if key in merged:
            m = merged[key]
            m["other_sources"].append(f["evidence_source"])
            if RATINGS.index(f["severity"]) > RATINGS.index(m["severity"]):
                m["severity"] = f["severity"]
            m["guidance_ref"] = m.get("guidance_ref") or f.get("guidance_ref")
            errors.append(f"Assessment: merged red flag {f['flag']!r} into {m['flag']!r} (same event)")
        else:
            merged[key] = {**f, "other_sources": []}
    flags = list(merged.values())

    # Enforce the floor: the LLM may rate higher than the code rules, never lower
    floor_rating, floor_rec, floor_reason = _floor(state)
    llm_rating = result.rating if result else floor_rating
    llm_rec = result.recommendation if result else floor_rec
    rating = max(llm_rating, floor_rating, key=RATINGS.index)
    recommendation = max(llm_rec, floor_rec, key=RECOMMENDATIONS.index)

    overridden = result is not None and (rating != llm_rating or recommendation != llm_rec)
    if overridden:
        errors.append(f"Assessment: LLM said {llm_rating}/{llm_rec}; raised to {rating}/{recommendation} by rule: {floor_reason}")

    return {
        "risk_rating": rating,
        "recommendation": recommendation,
        "red_flags": flags,
        "risk_rationale": result.rationale if result else floor_reason,
        "rating_floor_reason": floor_reason,
        "errors": errors,
    }
