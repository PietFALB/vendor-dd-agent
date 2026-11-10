"""Run a vendor due-diligence check: python main.py "Company name" [--kvk 12345678]"""
import argparse

from dotenv import load_dotenv

load_dotenv()

from agent.graph import build_graph


def main():
    parser = argparse.ArgumentParser(description="Vendor due-diligence agent")
    parser.add_argument("company_name")
    parser.add_argument("--kvk", default=None, help="KvK number (optional)")
    args = parser.parse_args()

    result = build_graph().invoke({
        "company_name": args.company_name,
        "kvk_number": args.kvk,
        "errors": [],
        "trace": [],
        "check_attempts": 0,
    })

    print("\nPath:", " -> ".join(result["trace"]))

    entity = result.get("entity")
    if entity:
        print("\nEntity:", entity["legal_name"], "| LEI:", entity["lei"], "| Country:", entity["country"])
        print("KvK:", entity["kvk_number"], "| Parent:", (entity.get("ultimate_parent") or {}).get("legal_name"))

    hits = result.get("sanctions_hits", [])
    print(f"\nSanctions hits: {len(hits)} (screening complete: {result.get('screening_complete')})")
    for h in hits:
        print(f"  - {h['name']} (score {h['score']}) {h['programs']}")
        print(f"      matched via: {'; '.join(h['matched_via'])}")

    if result.get("errors"):
        print("\nData limitations:")
        for e in result["errors"]:
            print("  -", e)


if __name__ == "__main__":
    main()
