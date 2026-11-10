"""Print every step the review agent takes for one company."""
import sys

from dotenv import load_dotenv

load_dotenv()

from langchain.agents import create_agent
from langchain.agents.structured_output import ToolStrategy
from langchain_openai import ChatOpenAI

from agent import review as r

company = sys.argv[1] if len(sys.argv) > 1 else "ING Groep"
if hasattr(r, "_calls"):
    r._calls["n"] = 0

agent = create_agent(
    ChatOpenAI(model="gpt-4o-mini", temperature=0),
    tools=[r.news_search, r.guidance_search],
    system_prompt=r.SYSTEM,
    response_format=ToolStrategy(r.ReviewResult, handle_errors=True),
)
brief = r.STANDARD_BRIEF.format(name=company, country="NL")

n = 0
try:
    for update in agent.stream({"messages": [("user", brief)]},
                               config={"recursion_limit": 24}, stream_mode="updates"):
        for node, data in update.items():
            for m in (data or {}).get("messages", []):
                n += 1
                calls = getattr(m, "tool_calls", None)
                if calls:
                    print(f"{n:>2}. {node:<8} CALLS  {[(c['name'], c['args']) for c in calls]}")
                else:
                    print(f"{n:>2}. {node:<8} {type(m).__name__:<12} {str(m.content)[:160]!r}")
except Exception as e:
    print(f"\nSTOPPED: {type(e).__name__}: {str(e)[:200]}")
