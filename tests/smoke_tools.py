"""Each tool: one normal case, one not-found case, one forced error. All must return a ToolResult."""
from dotenv import load_dotenv

load_dotenv()

from tools.base import ToolResult
from tools.gleif import search_gleif
from tools.kvk import get_kvk_profile
from tools.news import search_news
from tools.sanctions import screen_sanctions

cases = [
    ("GLEIF normal", lambda: search_gleif("ING Groep")),
    ("GLEIF not found", lambda: search_gleif("Xyzzy Nonexistent Holding 98765")),
    ("KvK normal", lambda: get_kvk_profile("68750110")),
    ("KvK invalid number", lambda: get_kvk_profile("123")),
    ("KvK error case", lambda: get_kvk_profile("90004973")),
    ("Sanctions clean", lambda: screen_sanctions("ING Groep")),
    ("Sanctions hit", lambda: screen_sanctions("Sberbank")),
    ("Sanctions empty", lambda: screen_sanctions("")),
    ("News normal", lambda: search_news("ING Groep")),
]

for label, fn in cases:
    r = fn()
    assert isinstance(r, ToolResult), f"{label} did not return a ToolResult"
    if r.ok:
        d = r.data or {}
        detail = (
            d.get("match", {}).get("legal_name") if isinstance(d.get("match"), dict)
            else f"{len(d['hits'])} hits" if "hits" in d
            else f"{len(d['articles'])} articles" if "articles" in d
            else d.get("name") or d
        )
        print(f"OK    {label}: {detail}")
    else:
        print(f"FAIL  {label}: {r.error}")
