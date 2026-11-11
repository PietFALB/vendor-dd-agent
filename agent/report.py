"""Build, check and save the due-diligence report.
Facts (sections 2-6, 8) are filled by code from the state; the LLM only writes
the summary, the recommendation text and next steps."""
import os
import re
from datetime import date, datetime
from pathlib import Path

from langchain_openai import ChatOpenAI
from rapidfuzz import fuzz
from pydantic import BaseModel, Field

from tools.amounts import unverified_amounts
from tools.dates import age_text
from tools.sanctions import CSV

SECTIONS = [
    "## 1. Summary and risk rating",
    "## 2. Identity",
    "## 3. Ownership",
    "## 4. Sanctions screening",
    "## 5. Adverse media",
    "## 6. Red flags",
    "## 7. Recommendation",
    "## 8. Data limitations and disclaimer",
]
DISCLAIMER = ("This report is an automated pre-screening to support, not replace, the judgement of a "
              "compliance officer. It is not legal advice. Verify material findings at the source.")


STANDARD_STEPS = {
    "Do not onboard": [
        "Do not enter into the relationship and make no payments or other funds available to the entity.",
        "Inform the compliance officer and legal counsel, and record the sanctions hit and this report in the vendor file.",
        "If the entity is already a vendor, put pending payments on hold and obtain legal advice on any reporting obligations.",
    ],
    "Escalate": [
        "Do not proceed until the compliance officer has reviewed the findings and signed off.",
        "Ask the vendor for an explanation and supporting documents for each red flag.",
        "Record the decision and its rationale in the vendor file.",
    ],
    "Onboard with conditions": [
        "Obtain a UBO declaration and a recent extract from the company register.",
        "Ask the vendor how past findings were remediated, with supporting evidence.",
        "Apply enhanced monitoring: rescreen sanctions and adverse media every 6 months.",
    ],
    "Onboard": [
        "Record this check in the vendor file.",
        "Rescreen sanctions annually, and on any change in ownership.",
    ],
}


class ReportProse(BaseModel):
    summary: str = Field(description="3-4 sentences for a busy compliance officer: who the company is, "
                                     "the key findings and the rating")
    recommendation_text: str = Field(description="2-3 sentences explaining the recommendation")
    specific_steps: list[str] = Field(description="0-2 extra steps tied to a specific finding in this report, "
                                                  "e.g. 'Ask for the status of the Payvision investigation'. "
                                                  "No generic advice.")


PROSE_PROMPT = """You write the summary and recommendation of a vendor due-diligence report.
Use ONLY the facts below. Do not add facts, numbers or sources that are not listed.
Never add up, convert or calculate amounts. Only repeat amounts exactly as they appear below.
Each red flag below is ONE event. Describe each event once, even if several articles or amounts
belong to it (e.g. a fine plus disgorgement in one settlement is one settlement, not two fines).
Use the event year; do not call an event 'current' or 'ongoing' unless the evidence says so.
Specific steps must refer to a finding in this report. Standard onboarding steps are added separately.

Company: {name}
Risk rating: {rating}
Recommendation: {recommendation}
Rationale from the assessment: {rationale}
Red flags: {flags}
Data limitations: {limitations}
Evidence excerpts: {excerpts}
{feedback}"""


def _cell(x) -> str:
    """Safe text for a Markdown table cell."""
    return str(x if x not in (None, "", []) else "—").replace("|", "/").replace("\n", " ")


def sanctions_data_date() -> str:
    try:
        return datetime.fromtimestamp(CSV.stat().st_mtime).date().isoformat()
    except OSError:
        return "unknown"


def _prose(state: dict) -> ReportProse:
    flags = "\n".join(
        f"- [{f['severity']}] {f['flag']} (event year {f.get('event_year') or 'unknown'}, "
        f"{1 + len(f.get('other_sources', []))} source(s)): {f['evidence']}"
        for f in state.get("red_flags", [])
    ) or "none"
    problems = state.get("check_problems") or []
    feedback = ("A previous draft was rejected for: " + "; ".join(problems)) if problems else ""
    model = os.environ.get("ASSESS_MODEL") or os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
    try:
        llm = ChatOpenAI(model=model, temperature=0).with_structured_output(ReportProse)
        return llm.invoke(PROSE_PROMPT.format(
            name=(state.get("entity") or {}).get("legal_name") or state["company_name"],
            rating=state.get("risk_rating"),
            recommendation=state.get("recommendation"),
            rationale=state.get("risk_rationale"),
            flags=flags,
            limitations="; ".join(state.get("errors", [])) or "none",
            feedback=feedback,
            excerpts=" | ".join(t[:300] for t in state.get("evidence_texts", [])[:8]) or "none",
        ))
    except Exception:
        return ReportProse(
            summary=state.get("risk_rationale") or "Automated summary unavailable.",
            recommendation_text=f"Recommendation based on code rules: {state.get('recommendation')}.",
            specific_steps=[],
        )


def _latin(s: str) -> bool:
    """True if every letter is in the Latin script (incl. accents)."""
    return not any(c.isalpha() and ord(c) > 0x24F for c in (s or ""))


def _title(state: dict, entity: dict, legal_name: str) -> str:
    if _latin(legal_name):
        return legal_name
    for alt in [*entity.get("other_names", []), state["company_name"]]:
        if alt and _latin(alt):
            return f"{alt} ({legal_name})"
    return legal_name


def build_report(state: dict) -> str:
    entity = state.get("entity") or {}
    name = entity.get("legal_name") or state["company_name"]
    hits = state.get("sanctions_hits", [])
    news = state.get("news", [])
    flags = state.get("red_flags", [])
    errors = state.get("errors", [])
    route = "enhanced" if "enhanced_review" in state.get("trace", []) else "standard"
    data_date = sanctions_data_date()
    prose = _prose(state)

    kvk = entity.get("kvk_profile")
    if kvk:
        kvk_text = f"{kvk.get('name')}, {kvk.get('legal_form')}, registered {kvk.get('registration_date')}"
    else:
        kvk_text = "Not available"

    lines = [
        f"# Vendor Due-Diligence Report: {_title(state, entity, name)}",
        "",
        f"*Generated {date.today().isoformat()} · Review route: {route} · "
        f"Sources: GLEIF, KvK, OpenSanctions (sanctions data as of {data_date}), "
        f"news search, AML/sanctions guidance corpus*",
        "",
        SECTIONS[0],
        "",
        f"**Risk rating: {state.get('risk_rating')}** · **Recommendation: {state.get('recommendation')}**",
        "",
        prose.summary,
        "",
        SECTIONS[1],
        "",
        "| Field | Value |",
        "| --- | --- |",
        f"| Name as given | {_cell(state['company_name'])} |",
        f"| Legal name (GLEIF) | {_cell(entity.get('legal_name'))} |",
        f"| LEI | {_cell(entity.get('lei'))} |",
        f"| Country | {_cell(entity.get('country'))} |",
        f"| Address | {_cell(entity.get('address'))} |",
        f"| Entity status | {_cell(entity.get('entity_status'))} |",
        f"| LEI registration | {_cell(entity.get('registration_status'))} |",
        f"| KvK number | {_cell(entity.get('kvk_number'))} |",
        f"| KvK profile | {_cell(kvk_text)} |",
        f"| GLEIF name match | {_cell(entity.get('match_score'))} |",
        "",
    ]
    if entity.get("match_score") is not None and entity["match_score"] < 85 and entity.get("other_candidates"):
        others = "; ".join(f"{c['legal_name']} ({c['country']}, {c['score']})" for c in entity["other_candidates"])
        lines += [f"Other possible matches: {others}", ""]

    # 3. Ownership
    lines += [SECTIONS[2], ""]
    for key, label in [("direct_parent", "Direct parent"), ("ultimate_parent", "Ultimate parent")]:
        p = entity.get(key)
        if p:
            lines.append(f"- **{label}:** {p['legal_name']} ({p['country']}, LEI {p['lei']})")
        else:
            lines.append(f"- **{label}:** Not reported to GLEIF (top of group or reporting exception)")
    lines.append("")

    # 4. Sanctions screening
    lines += [SECTIONS[3], ""]
    if not state.get("screening_complete", True):
        lines += ["**Sanctions screening incomplete. Do not treat the absence of hits as clear.**", ""]
    screened = "; ".join(state.get("screened_names", [])) or "—"
    lines += [f"Names screened: {screened}. Match threshold: 85/100.", ""]
    if hits:
        lines += ["| Listed entity | Score | Programs | Matched via | Source |",
                  "| --- | --- | --- | --- | --- |"]
        for h in hits:
            via = "; ".join(h.get("matched_via", []))
            lines.append(f"| {_cell(h['name'])} | {h['score']} | {_cell(h['programs'])} | "
                         f"{_cell(via)} | [OpenSanctions]({h['url']}) |")
    else:
        lines.append("No matches above the threshold.")
    lines.append("")

    # 5. Adverse media
    lines += [SECTIONS[4], ""]
    searches = len([s for s in state.get("agent_steps", []) if s["tool"] == "news_search"])
    if news:
        for n in news:
            ref = f" Guidance: {n['guidance_source']} p.{n['guidance_page']}." if n.get("guidance_source") else ""
            lines.append(f"- **{n['title']}** ({age_text(n.get('date'))}, {n['risk_type']}). "
                         f"{n['summary']}{ref} [Source]({n['url']})")
    else:
        lines.append(f"No credible adverse media found ({searches} news searches).")
    lines.append("")

    # 6. Red flags
    lines += [SECTIONS[5], ""]
    if flags:
        lines += ["| Severity | Year | Red flag | Evidence | Source | Guidance |",
                  "| --- | --- | --- | --- | --- | --- |"]
        for f in flags:
            src = f["evidence_source"]
            src_cell = f"[{src}]({src})" if src.startswith("http") else src
            src_cell += "".join(f" · [source {i + 2}]({s})" for i, s in enumerate(f.get("other_sources", [])))
            lines.append(f"| {f['severity']} | {_cell(f.get('event_year'))} | {_cell(f['flag'])} | {_cell(f['evidence'])} | "
                         f"{src_cell} | {_cell(f.get('guidance_ref'))} |")
    else:
        lines.append("No red flags identified.")
    lines.append("")

    # 7. Recommendation
    lines += [SECTIONS[6], "",
              f"**{state.get('recommendation')}** (risk rating {state.get('risk_rating')})", "",
              prose.recommendation_text, ""]
    if state.get("rating_floor_reason"):
        lines += [f"*Minimum rating set by rule: {state['rating_floor_reason']}*", ""]
    lines.append("Next steps:")
    lines += [f"- {s}" for s in STANDARD_STEPS.get(state.get("recommendation"), [])]
    standard = STANDARD_STEPS.get(state.get("recommendation"), [])
    for s in prose.specific_steps:
        repeats = any(fuzz.token_set_ratio(s.lower(), t.lower()) >= 70 for t in standard)
        if not repeats and not ("ubo" in s.lower() and any("ubo" in t.lower() for t in standard)):
            lines.append(f"- {s}")
    lines.append("")

    # 8. Data limitations and disclaimer
    lines += [SECTIONS[7], ""]
    lines += [f"- {e}" for e in errors] or ["- None recorded."]
    lines += [f"- Sanctions data: OpenSanctions consolidated list, downloaded {data_date}; non-commercial licence.",
              "", DISCLAIMER, ""]
    return "\n".join(lines)


def check_report(state: dict) -> list[str]:
    """Return a list of problems; an empty list means the report passes."""
    report = state.get("report") or ""
    problems = [f"missing section '{s}'" for s in SECTIONS if s not in report]
    if "sanctions data as of" not in report:
        problems.append("missing sanctions data date")
    if not state.get("screening_complete", True) and "Sanctions screening incomplete" not in report:
        problems.append("incomplete screening not stated")
    for e in state.get("errors", []):
        if e[:60] not in report:
            problems.append(f"data limitation not reported: {e[:60]!r}")
    for f in state.get("red_flags", []):
        if f["evidence_source"] not in report:
            problems.append(f"red flag without visible source: {f['flag']!r}")
    body = report.split(SECTIONS[7])[0]  # section 8 may quote amounts in its error messages
    bad = unverified_amounts(body, state.get("evidence_texts", []))
    if bad:
        problems.append(f"amounts not found in the evidence: {bad}; do not add up or calculate amounts")
    summary = ""
    if SECTIONS[0] in report and SECTIONS[1] in report:
        summary = report.split(SECTIONS[0])[1].split(SECTIONS[1])[0]
    if len(summary.strip()) < 80:
        problems.append("summary is missing or too short")
    return problems


def save_report(state: dict, ok: bool) -> str:
    slug = re.sub(r"[^A-Za-z0-9]+", "_", state["company_name"]).strip("_") or "company"
    path = Path("reports") / f"{slug}_{date.today().isoformat()}.md"
    path.parent.mkdir(exist_ok=True)
    text = state.get("report") or ""
    if not ok:
        problems = "; ".join(state.get("check_problems", []))
        text = f"> **Warning: this report failed the automated quality check ({problems}).**\n\n" + text
    path.write_text(text, encoding="utf-8")
    return str(path)
