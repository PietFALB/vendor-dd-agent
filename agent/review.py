"""Adverse media review in two phases:
1. Research: a ReAct agent searches news and guidance (tools, budget, step limit).
2. Synthesis: one LLM call without tools turns what was found into a structured result.
Code checks then drop findings with unverified URLs or that don't name the company."""
import json
import os
import re
from typing import Literal

from langchain.agents import create_agent
from langchain_core.messages import AIMessage, ToolMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langgraph.errors import GraphRecursionError
from pydantic import BaseModel, Field

from rag.retrieve import retrieve
from tools.amounts import unverified_amounts
from tools.news import search_news
from tools.sanctions import normalize

MAX_STEPS = 20     # hard safety net for the research loop
MAX_SEARCHES = 6   # tool budget per review
_calls = {"n": 0}

BUDGET_MSG = json.dumps({"error": "Search budget used up. Do not call any tool again. Reply with the single word DONE."})


# ---------------------------------------------------------------- tools the agent can use

@tool
def news_search(company_name: str, focus: str | None = None) -> str:
    """Search recent news about a company. Without focus it looks for negative coverage
    (fraud, sanctions, investigations, lawsuits, fines, corruption, money laundering).
    Use focus to follow up on a lead, e.g. focus='subsidiary sale' or focus='EU sanctions 2026'.
    Returns JSON: a list of articles with title, url, date and snippet."""
    if _calls["n"] >= MAX_SEARCHES:
        return BUDGET_MSG
    _calls["n"] += 1
    r = search_news(company_name, focus=focus)
    return json.dumps(r.data["articles"] if r.ok else {"error": r.error})


@tool
def guidance_search(question: str) -> str:
    """Search AML and sanctions guidance (FATF, European Commission, DNB) for the rule or red flag
    that applies to a finding, e.g. 'ownership by a listed person' or 'circumvention via third countries'.
    Returns JSON: passages with source document and page."""
    if _calls["n"] >= MAX_SEARCHES:
        return BUDGET_MSG
    _calls["n"] += 1
    hits = retrieve(question, k=3)
    return json.dumps([{"text": h["text"][:800], "source": h["source"], "page": h["page"]} for h in hits])


# ---------------------------------------------------------------- output format

class Finding(BaseModel):
    title: str
    url: str = Field(description="Exact URL from the articles provided")
    date: str | None = None
    summary: str = Field(description="What happened to THIS company, 1-2 sentences, only from the article")
    risk_type: Literal[
        "sanctions", "ownership or control", "circumvention", "fraud", "corruption",
        "money laundering", "regulatory fine", "litigation", "other",
    ] = Field(description="Pick exactly one of the listed values; use 'other' if none fits")
    guidance_source: str | None = Field(None, description="Guidance file name from the passages provided")
    guidance_page: int | None = None


class ReviewResult(BaseModel):
    findings: list[Finding]
    no_adverse_media: bool = Field(description="True if no credible negative coverage was found")
    summary: str = Field(description="2-3 sentence conclusion that uses ONLY the findings listed")


# ---------------------------------------------------------------- prompts

SYSTEM = """You are an adverse media researcher supporting a compliance officer's vendor due diligence.
Your only job is to gather evidence with the tools. Someone else writes the conclusion.

Rules:
- Use news_search to find credible negative coverage about the company.
- Use guidance_search to find the rule that applies to what you found. Ask a real question,
  e.g. 'what are red flags when a counterparty paid an AML settlement'.
- Call one tool at a time. Never repeat a search. You have 6 searches in total.
- When you have enough evidence, or the budget is used up, reply with the single word DONE."""

STANDARD_BRIEF = """Company: {name}
Country: {country}
No sanctions hits were found. Look for credible negative news: fraud, corruption, money laundering,
regulatory fines, litigation. Then find the guidance that applies."""

ENHANCED_BRIEF = """Company: {name}
Country: {country}
SANCTIONS SCREENING MATCHED THESE ENTRIES:
{hits}

This is an enhanced review. Run one news_search per angle:
1. Recent enforcement and sanctions news (focus: 'sanctions enforcement').
2. Ownership and control by listed parties (focus: 'ownership shareholders').
3. Circumvention signals: renamed entities, asset transfers, subsidiaries sold (focus: 'subsidiary sale asset transfer').
Then find the guidance that applies."""

SYNTHESIS = """You write the adverse media section of a vendor due-diligence file for: {name}.

Below are ALL articles and guidance passages the research found. Use nothing else.

Rules:
- A finding must be about THIS company itself, or name it as a party. Skip articles about other firms.
- Skip articles that are not negative (share price, product news).
- Copy URLs exactly from the articles. Never invent articles, dates or facts.
- Never add up, convert or calculate amounts. Only use amounts exactly as they appear in the articles.
- Link each finding to the most relevant guidance passage (file name and page), if one applies.
- The summary may only use facts from your findings.
- If nothing credible remains, set no_adverse_media to true and return an empty findings list.

ARTICLES:
{articles}

GUIDANCE PASSAGES:
{guidance}"""


# ---------------------------------------------------------------- code-level checks

def _mentions_company(text: str, names: list[str]) -> bool:
    """True if the text names the company: a full name variant, or its first word as a whole word."""
    text = normalize(text)
    for n in names:
        n = normalize(n)
        if not n:
            continue
        first = n.split()[0]
        if n in text or (len(first) >= 3 and re.search(rf"\b{re.escape(first)}\b", text)):
            return True
    return False


def _collect(messages) -> tuple[dict, dict, list]:
    """What the tools actually returned: articles by URL, guidance by (source, page), and the calls made."""
    articles, guidance, steps, seen = {}, {}, [], set()
    for msg in messages:
        if isinstance(msg, AIMessage):
            for call in msg.tool_calls or []:
                key = (call["name"], json.dumps(call["args"], sort_keys=True))
                if key not in seen:
                    seen.add(key)
                    steps.append({"tool": call["name"], "args": call["args"]})
        if isinstance(msg, ToolMessage):
            try:
                payload = json.loads(msg.content)
            except (TypeError, json.JSONDecodeError):
                continue
            if not isinstance(payload, list):
                continue
            if msg.name == "news_search":
                for a in payload:
                    if a.get("url"):
                        articles[a["url"]] = a
            elif msg.name == "guidance_search":
                for g in payload:
                    guidance[(g["source"], g["page"])] = g
    return articles, guidance, steps


# ---------------------------------------------------------------- run

def run_review(company: str, entity: dict | None, hits: list[dict] | None = None) -> dict:
    entity = entity or {}
    _calls["n"] = 0  # fresh search budget for each review
    errors = []

    if hits:
        hit_lines = "\n".join(f"- {h['name']} ({h['programs']})" for h in hits[:5])
        brief = ENHANCED_BRIEF.format(name=company, country=entity.get("country") or "unknown", hits=hit_lines)
    else:
        brief = STANDARD_BRIEF.format(name=company, country=entity.get("country") or "unknown")

    # TODO (Day 4): evaluate a stronger model, see "Model choice" in the build guide
    model = os.environ.get("REVIEW_MODEL") or os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
    llm = ChatOpenAI(model=model, temperature=0)

    # ---- Phase 1: research. Keep the latest state, so a stuck agent still leaves its evidence.
    agent = create_agent(llm, tools=[news_search, guidance_search], system_prompt=SYSTEM)
    last_state = {"messages": []}
    try:
        for state in agent.stream({"messages": [("user", brief)]},
                                  config={"recursion_limit": MAX_STEPS}, stream_mode="values"):
            last_state = state
    except GraphRecursionError:
        errors.append(f"Review: research agent hit the step limit ({MAX_STEPS}); using the evidence found so far.")
    except Exception as e:
        errors.append(f"Review: research agent failed ({e}); using the evidence found so far.")

    articles, guidance, steps = _collect(last_state["messages"])

    # ---- Phase 2: synthesis. One call, no tools, only the evidence that was actually found.
    review = None
    if articles:
        try:
            prompt = SYNTHESIS.format(
                name=company,
                articles=json.dumps(list(articles.values()), ensure_ascii=False, indent=1),
                guidance=json.dumps([{"source": g["source"], "page": g["page"], "text": g["text"][:500]}
                                     for g in guidance.values()], ensure_ascii=False, indent=1),
            )
            review = llm.with_structured_output(ReviewResult).invoke(prompt)
        except Exception as e:
            errors.append(f"Review: synthesis failed ({e}).")
    elif not errors:
        errors.append("Review: news search returned no articles.")

    # ---- Code checks: the URL must come from the news tool, and the article must name the company.
    names = [company, entity.get("legal_name") or "", *entity.get("other_names", [])]
    evidence_texts = [f"{a.get('title', '')} {a.get('snippet', '')}" for a in articles.values()]
    findings = []
    for f in (review.findings if review else []):
        source = articles.get(f.url)
        if source is None:
            errors.append(f"Review: dropped finding with unverified URL: {f.title!r}")
        elif not _mentions_company(f"{source.get('title', '')} {source.get('snippet', '')}", names):
            errors.append(f"Review: dropped finding not about this company: {f.title!r}")
        else:
            item = f.model_dump()
            bad = unverified_amounts(f.summary, evidence_texts)
            if bad:
                errors.append(f"Review: amount(s) {bad} not in source; summary of {f.title!r} replaced by source excerpt")
                item["summary"] = (source.get("snippet") or "")[:300]
            findings.append(item)

    summary = review.summary if review else None
    if summary and unverified_amounts(summary, evidence_texts):
        errors.append("Review: summary contained amounts not in the sources; summary removed")
        summary = None

    return {
        "news": findings,
        "guidance": list(guidance.values()),
        "review_summary": summary,
        "agent_steps": steps,
        "evidence_texts": evidence_texts,
        "errors": errors,
    }
