"""Regression test for entity resolution: run after every change to tools/gleif.py."""
from tools.gleif import search_gleif

EXPECTED = {
    "Philips": "Koninklijke Philips N.V.",
    "Heineken": "Heineken N.V.",
    "Ahold Delhaize": "Koninklijke Ahold Delhaize N.V.",
    "ING Bank": "ING BANK N.V.",
    "Shell": "Shell plc",
    "ASML": "ASML Holding N.V.",
    "Sberbank": 'Публичное акционерное общество "Сбербанк России"',
}

f = getattr(search_gleif, "invoke", search_gleif)
failed = 0
for name, expected in EXPECTED.items():
    m = f(name).data["match"]
    ok = m["legal_name"].lower() == expected.lower()
    failed += not ok
    print(f"{'OK  ' if ok else 'FAIL'} {name:15} -> {m['legal_name']} | {m['country']} | {m['match_score']} | {m['registered_as']}")
print(f"\n{len(EXPECTED) - failed}/{len(EXPECTED)} correct")
