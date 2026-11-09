# Decision                            Answer

Industry / use case                 Compliance: third-party (vendor) due diligence for Dutch regulated firms

Report buyer / user                 Compliance officer at a mid-size law firm, notary or payment company who must check a new supplier before onboarding

Primary stack                       LangGraph

Why this stack                      Due diligence branches: a sanctions hit must trigger enhanced checks, a clean result must not. LangGraph models this as explicit state and conditional edges in Python, which I can test and version. Every node writes to shared state, which gives an audit trail of what was checked and why, a core compliance need. A ReAct loop fits the open-ended part (adverse media), while the fixed steps stay deterministic.

Why not n8n (for MVP)                n8n shines at ops plumbing (triggers, email, CRMs), but branching agent logic with retries and typed state gets hard to read and test in nodes. A thin n8n webhook could trigger the agent later (GTM sprint 3), but the brains stay in Python.

