"""KvK Handelsregister basisprofiel. Uses the free test environment by default."""
import os
import re

import requests

from tools.base import ToolResult
from tools.http import get_with_retry

BASE = os.environ.get("KVK_BASE_URL", "https://api.kvk.nl/test/api/v1")


def get_kvk_profile(kvk_number: str) -> ToolResult:
    url = f"{BASE}/basisprofielen/{kvk_number}"
    if not re.fullmatch(r"\d{8}", str(kvk_number or "")):
        return ToolResult(ok=False, error=f"Invalid KvK number: {kvk_number!r} (must be 8 digits)", source=url)
    try:
        r = get_with_retry(url, headers={"apikey": os.environ.get("KVK_API_KEY", "")}, timeout=15)
        if r.status_code == 401:
            return ToolResult(ok=False, error="KvK rejected the API key (401)", source=url)
        if r.status_code == 404:
            return ToolResult(ok=True, data={"found": False}, source=url)
        r.raise_for_status()
        d = r.json()
        emb = d.get("_embedded", {})
        hoofd = emb.get("hoofdvestiging", {})
        adres = (hoofd.get("adressen") or [{}])[0]
        return ToolResult(
            ok=True,
            data={
                "found": True,
                "kvk_number": d.get("kvkNummer"),
                "name": d.get("naam"),
                "legal_form": emb.get("eigenaar", {}).get("rechtsvorm"),
                "registration_date": d.get("formeleRegistratiedatum"),
                "trade_names": [h.get("naam") for h in d.get("handelsnamen", [])],
                "activities": [s.get("sbiOmschrijving") for s in d.get("sbiActiviteiten", [])],
                "address": adres.get("volledigAdres"),
                "test_environment": "/test/" in BASE,
            },
            source=url,
        )
    except Exception as e:
        return ToolResult(ok=False, error=f"KvK failed: {e}", source=url)
