[x] LangGraph chosen and justified in stack_decision.md
[ ] One command runs trigger → report with no babysitting
[ ] 4 tools wired, each with validation and clear failure
[ ] RAG over AML and sanctions guidance, cited in reports
[ ] 2+ sample reports, including one that triggers the sanctions branch
[ ] gtm_future_sprints.md with 3 sprints
[ ] README with setup, run, file map, diagram
[ ] 5–7 minute demo rehearsed

API
OpenSanctions: free API keys don’t cover coursework. The guide has you download their bulk data, which is free for non-commercial use, and match names locally instead.
KvK: the test environment is free with a public test key, but it only returns fictitious companies. Real lookups cost €6.40 a month plus €0.02 per query.

Create accounts and keys. Put each key in a .env file, never in code.
    ◦ LLM: Anthropic or OpenAI API key
    ◦ Pinecone (free starter tier)
    ◦ Tavily or another news/search API (free tier)
    ◦ LangSmith (optional, for tracing runs; useful in the demo)
    ◦ GitHub repo, public