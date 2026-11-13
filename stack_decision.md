# Stack decision

**Primary stack: LangGraph.** n8n is secondary: a no-code form in front of the agent's API.

| Decision | Answer |
| --- | --- |
| Industry / use case | Compliance: third-party (vendor) due diligence for Dutch regulated firms |
| Report buyer / user | Compliance officer at a mid-size law firm, notary or payment company who must check a new supplier before onboarding |
| Primary stack | LangGraph (Python) |
| Secondary | n8n: Form Trigger → HTTP Request to the agent's FastAPI → report on the result page ([`n8n/vendor_dd_workflow.json`](n8n/vendor_dd_workflow.json)) |

## Why LangGraph fits this problem

- **Due diligence branches.** A sanctions hit must trigger an enhanced review; a clean result must not. LangGraph models this as explicit state and conditional edges in Python, which I can test and version.
- **Audit trail.** Every node writes to shared state (`trace`, `errors`, the agent's searches), so each report shows what was checked and why: a core compliance need.
- **Code decides, the LLM explains.** Entity resolution, sanctions matching and the minimum rating are deterministic code. Only the adverse-media research is a ReAct agent, with its search budget and step limit enforced in code.
- **Testable.** Failure tests (wrong keys, no data, a company that does not exist) and a regression test of 7 real companies run against the same Python code.

## Why n8n is only secondary for this MVP

- n8n is strong at plumbing: triggers, forms, email, CRMs. Branching agent logic with retries, typed state and code checks on LLM output gets hard to read and test as nodes.
- So the brains stay in Python, and n8n is used for what it does best: a form anyone can fill in without touching Python. The API key is stored as an encrypted n8n credential, not in the exported workflow.
- In GTM sprint 3, n8n becomes the integration layer: triggers from email or SharePoint, batch checks and re-screening alerts.
