"""Adverse media search via Tavily."""
import os

from tavily import TavilyClient

import time

from tools.base import ToolResult

TERMS = "fraud OR sanctions OR investigation OR lawsuit OR fine OR corruption OR money laundering"


def _search_with_retry(client, query: str, max_results: int, attempts: int = 3) -> dict:
    """Retry temporary failures; never retry an authentication error."""
    for attempt in range(1, attempts + 1):
        try:
            return client.search(query, topic="news", max_results=max_results)
        except Exception as e:
            msg = str(e).lower()
            if attempt == attempts or any(w in msg for w in ("401", "unauthorized", "api key", "invalid")):
                raise
            time.sleep(attempt)


def search_news(name: str, focus: str | None = None, max_results: int = 5) -> ToolResult:
    query = f'"{name}" {focus}' if focus else f'"{name}" {TERMS}'
    try:
        client = TavilyClient(api_key=os.environ["TAVILY_API_KEY"])
        res = _search_with_retry(client, query, max_results)
        articles = [
            {
                "title": r.get("title"),
                "url": r.get("url"),
                "date": r.get("published_date"),
                "snippet": (r.get("content") or "")[:400],
            }
            for r in res.get("results", [])
        ]
        return ToolResult(ok=True, data={"query": query, "articles": articles}, source="Tavily news search")
    except Exception as e:
        return ToolResult(ok=False, error=f"News search failed: {e}", source="Tavily news search")
