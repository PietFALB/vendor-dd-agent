# Failure tests before the fix (11 Nov 2026)

Verbatim excerpts from the terminal output of the first failure-test runs. The full reports were overwritten
by later runs; only the parts shown here were preserved. Both are false all-clears, fixed the same morning.

## Test 1: wrong Tavily key, ING Groep (before the media_complete fix)

Command: `TAVILY_API_KEY=wrong python main.py "ING Groep"`

    Risk rating: Low | Recommendation: Onboard
    Sanctions hits: 0 | Adverse media findings: 0 | Red flags: 0 | Data limitations: 3
    Quality check: passed after 1 attempt(s)

Section 5 of the report:

> No credible adverse media found (1 news searches).

Section 8 of the report:

> - Ownership: no parent reported to GLEIF; ownership and ultimate beneficial owners (UBOs) are not verified. Obtain a UBO declaration.
> - KvK: 33231073 not found (test environment only holds fictitious companies).
> - Review: news search returned no articles.

**What was wrong:** the news search failed (invalid API key), but the report read as "searched and found nothing",
and rated a bank with a past EUR 775 million AML settlement as Low / Onboard.

## Test 2: company that does not exist, Xyzzy Holding BV (before the identity fix)

Command: `python main.py "Xyzzy Holding BV"`

    Risk rating: Low | Recommendation: Onboard
    Sanctions hits: 0 | Adverse media findings: 0 | Red flags: 0 | Data limitations: 1
    Quality check: passed after 1 attempt(s)

Section 1 of the report:

> **Risk rating: Low** · **Recommendation: Onboard**
>
> Xyzzy Holding BV has been assessed with a low risk rating, indicating a strong compliance status. The vendor has undergone complete sanctions screening with no hits, and there are no adverse media reports or red flags identified. Additionally, there are no unresolved investigations or significant past enforcement actions, providing a high level of confidence in their compliance.

Section 8 of the report:

> - GLEIF: no LEI record found for 'Xyzzy Holding BV'; using the name as given.

**What was wrong:** the company could not be identified at all (no LEI, no KvK profile), yet the report claimed
"strong compliance status" and "a high level of confidence", and recommended onboarding.

## After the fix (same day)

| Test | Before | After |
| --- | --- | --- |
| Wrong Tavily key (ING) | Low / Onboard | Medium / Onboard with conditions, "Adverse media check incomplete" |
| Xyzzy Holding BV | Low / Onboard | Medium / Escalate, red flag "Company identity could not be verified" |
