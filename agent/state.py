import operator
from typing import Annotated, TypedDict


class DDState(TypedDict, total=False):
    # Input
    company_name: str
    kvk_number: str | None
    valid: bool                  # set by validate_input; False stops the run
    screening_complete: bool     # False if any sanctions check failed

    # Collected facts (from tools)
    entity: dict | None          # GLEIF + KvK identity, parents
    sanctions_hits: list[dict]   # hits on company and parents
    news: list[dict]             # adverse media articles
    guidance: list[dict]         # retrieved RAG chunks with source + page
    evidence_texts: list[str]    # raw article titles + snippets, for the number check
    review_summary: str | None   # the review agent's overall conclusion
    agent_steps: list[dict]      # which searches the agent chose (audit trail)

    # Judgement (from LLM)
    red_flags: list[dict]
    risk_rating: str | None      # Low / Medium / High
    recommendation: str | None   # Onboard / Onboard with conditions / Escalate
    risk_rationale: str | None
    rating_floor_reason: str | None  # code rule that set a minimum rating, if any

    # Output
    report: str | None
    report_path: str | None
    check_attempts: int
    report_ok: bool              # set by check_report
    check_problems: list[str]    # what check_report found missing (fed back on rewrite)
    screened_names: list[str]    # every name screened, with its role

    # Audit trail: lists that every node appends to
    errors: Annotated[list[str], operator.add]
    trace: Annotated[list[str], operator.add]
