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
    print("\nAgent searches:")
    for s in result.get("agent_steps", []):
        print(f"  - {s['tool']}: {s['args']}")

    print("\nAdverse media findings:")
    for f in result.get("news", []):
        ref = f" | guidance: {f['guidance_source']} p.{f['guidance_page']}" if f.get("guidance_source") else ""
        print(f"  - [{f['risk_type']}] {f['title']} ({f.get('date') or 'no date'}){ref}")
        print(f"      {f['url']}")
    print("\nReview summary:", result.get("review_summary"))
    
    print(f"\nRISK RATING: {result.get('risk_rating')}  |  RECOMMENDATION: {result.get('recommendation')}")
    if result.get("rating_floor_reason"):
        print("Code rule:", result["rating_floor_reason"])
    print("Rationale:", result.get("risk_rationale"))
    print("\nRed flags:")
    for f in result.get("red_flags", []):
        ref = f" | {f['guidance_ref']}" if f.get("guidance_ref") else ""
        print(f"  - [{f['severity']}] {f['flag']} ({f['category']}){ref}")
        print(f"      {f['evidence']}  <- {f['evidence_source']}")

    if result.get("errors"):
        print("\nData limitations:")
        for e in result["errors"]:
            print("  -", e)


if __name__ == "__main__":
    main()
