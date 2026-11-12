"""HTTP API around the vendor due-diligence agent, for n8n and other tools.
Run: uvicorn api:app --port 8000"""
import os

from dotenv import load_dotenv
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel

load_dotenv()

from agent.graph import build_graph

app = FastAPI(title="Vendor Due-Diligence Agent API")
graph = build_graph()
API_TOKEN = os.environ.get("API_TOKEN")  # optional: protects the endpoint


class CheckRequest(BaseModel):
    company_name: str
    kvk_number: str | None = None


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/check")
def check(req: CheckRequest, x_api_key: str | None = Header(default=None)):
    if API_TOKEN and x_api_key != API_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid or missing X-API-Key header")

    result = graph.invoke(
        {"company_name": req.company_name, "kvk_number": req.kvk_number or None,
         "errors": [], "trace": [], "check_attempts": 0},
        config={"run_name": "n8n", "tags": ["n8n"]},
    )
    if not result.get("valid", True):
        raise HTTPException(status_code=422, detail=" ".join(result.get("errors", [])))

    return {
        "company_name": req.company_name,
        "legal_name": (result.get("entity") or {}).get("legal_name"),
        "risk_rating": result.get("risk_rating"),
        "recommendation": result.get("recommendation"),
        "minimum_rule": result.get("rating_floor_reason"),
        "sanctions_hits": len(result.get("sanctions_hits", [])),
        "adverse_media_findings": len(result.get("news", [])),
        "red_flags": len(result.get("red_flags", [])),
        "data_limitations": result.get("errors", []),
        "report_markdown": result.get("report"),
        "report_path": result.get("report_path"),
    }
