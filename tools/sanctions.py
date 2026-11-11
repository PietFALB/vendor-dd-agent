"""Fuzzy-match a company name against the OpenSanctions consolidated list (local CSV)."""
import re
from functools import lru_cache
from pathlib import Path

import pandas as pd
from rapidfuzz import fuzz, process

from tools.base import ToolResult

CSV = Path("data/sanctions/targets.simple.csv")
ENTITY_TYPES = {"Organization", "Company", "LegalEntity"}
LEGAL_PHRASES = [
    # Russian (long forms first, so the short ones don't cut them in half)
    "публичное акционерное общество", "открытое акционерное общество", "закрытое акционерное общество",
    "акционерное общество", "общество с ограниченной ответственностью", "пао", "оао", "зао", "ао", "ооо",
    # English long forms
    "public joint stock company", "open joint stock company", "closed joint stock company",
    "joint stock company", "limited liability company",
]
LEGAL_SUFFIXES = r"\b(b\s?v|n\s?v|n\.?v|ltd|llc|plc|inc|gmbh|ag|sa|spa|pjsc|ojsc|jsc|cjsc|ooo|ao|pao|co|corp|corporation|company|limited|group|holding|holdings)\b"


def normalize(name: str) -> str:
    name = name.lower()
    name = re.sub(r"[\"'“”«».,()&-]", " ", name)
    name = re.sub(r"\s+", " ", name)
    for phrase in LEGAL_PHRASES:
        name = re.sub(rf"\b{phrase}\b", " ", name)
    name = re.sub(LEGAL_SUFFIXES, " ", name)
    return re.sub(r"\s+", " ", name).strip()


@lru_cache(maxsize=1)
def _load():
    df = pd.read_csv(CSV, low_memory=False, dtype=str).fillna("")
    df = df[df["schema"].isin(ENTITY_TYPES)].reset_index(drop=True)
    names, owners = [], []
    for i, row in df.iterrows():
        for variant in [row["name"], *row["aliases"].split(";")]:
            if variant.strip():
                names.append(normalize(variant))
                owners.append(i)
    return df, names, owners


def screen_sanctions(name: str, threshold: int = 85) -> ToolResult:
    source = f"OpenSanctions consolidated sanctions ({CSV.name})"
    if not name or not name.strip():
        return ToolResult(ok=False, error="Empty name", source=source)
    try:
        df, names, owners = _load()
        query = normalize(name)
        cutoff = max(threshold, 95) if len(query) < 6 else threshold  # short names: near-exact only
        matches = process.extract(query, names, scorer=fuzz.token_sort_ratio, score_cutoff=cutoff, limit=20)
        hits, seen = [], set()
        for matched, score, idx in matches:
            row = df.iloc[owners[idx]]
            if row["id"] in seen:
                continue
            seen.add(row["id"])
            hits.append({
                "id": row["id"],
                "name": row["name"],
                "matched_variant": matched,
                "score": round(score, 1),
                "countries": row["countries"],
                "programs": row["program_ids"],
                "lists": row["dataset"],
                "url": f"https://www.opensanctions.org/entities/{row['id']}/",
            })
        return ToolResult(ok=True, data={"query": name, "hits": hits}, source=source)
    except Exception as e:
        return ToolResult(ok=False, error=f"Sanctions screening failed: {e}", source=source)
