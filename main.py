"""Run a vendor due-diligence check: python main.py "Company name" [--kvk 12345678]"""
import argparse

from dotenv import load_dotenv

load_dotenv()

from agent.graph import build_graph


def main():
    parser = argparse.ArgumentParser(description="Vendor due-diligence agent")
    parser.add_argument("company_name")
    parser.add_argument("--kvk", default=None, help="KvK number (optional)")
    parser.add_argument("--label", default=None, help="Name for this run, e.g. presentation (optional)")
    args = parser.parse_args()

    print(f"Checking {args.company_name!r} ...")
    result = build_graph().invoke({
        "company_name": args.company_name,
        "kvk_number": args.kvk,
        "errors": [],
        "trace": [],
        "check_attempts": 0,
    }, config={"run_name": args.label or "vendor-dd", "tags": [args.label] if args.label else []})

    print("Path:", " -> ".join(result["trace"]))
    if not result.get("valid", True):
        print("Stopped:", "; ".join(result.get("errors", [])))
        return

    print(f"Risk rating: {result.get('risk_rating')} | Recommendation: {result.get('recommendation')}")
    print(f"Sanctions hits: {len(result.get('sanctions_hits', []))} | "
          f"Adverse media findings: {len(result.get('news', []))} | "
          f"Red flags: {len(result.get('red_flags', []))} | "
          f"Data limitations: {len(result.get('errors', []))}")
    status = "passed" if result.get("report_ok") else f"FAILED ({'; '.join(result.get('check_problems', []))})"
    print(f"Quality check: {status} after {result.get('check_attempts')} attempt(s)")
    print(f"Report saved: {result.get('report_path')}")
    if args.label and result.get("report_path"):
        import shutil
        from pathlib import Path
        copy = Path("reports") / f"{args.label}_{Path(result['report_path']).name}"
        shutil.copy(result["report_path"], copy)
        print(f"Labelled copy: {copy}")


if __name__ == "__main__":
    main()
