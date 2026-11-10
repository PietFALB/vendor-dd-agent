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
    review_summary: str | None   # the review agent's overall conclusion
    agent_steps: list[dict]      # which searches the agent chose (audit trail)

    # Judgement (from LLM)
    red_flags: list[dict]
    risk_rating: str | None      # Low / Medium / High

    # Output
    report: str | None
    report_path: str | None
    check_attempts: int

    # Audit trail: lists that every node appends to
    errors: Annotated[list[str], operator.add]
    trace: Annotated[list[str], operator.add]
