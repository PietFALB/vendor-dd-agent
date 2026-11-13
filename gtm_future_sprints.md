# GTM Future Sprints

The MVP proves the agent can produce a cited vendor due-diligence report from a company name. These three sprints take it from a working prototype to something a compliance team pays for and uses every week. Targets are proposals to validate, not results.

## Sprint 1: Design-partner pilot

| | |
| --- | --- |
| **Goal** | Prove that the report saves time and that compliance officers trust it enough to use it as a first draft |
| **Target user / buyer** | Compliance officers and compliance analysts at 3 mid-size Amsterdam law firms or notary offices: firms that must screen suppliers but have no screening tooling |
| **Channel / motion** | Founder-led: warm introductions through my own compliance network, followed by a 30-minute demo using one of their real (anonymised) vendors |
| **Key deliverable** | A 4-week pilot: each partner runs 20 vendor checks with the agent alongside their existing manual process, then gives structured feedback on every report (correct / missing / wrong) |
| **Success metric** | Time per check reduced by at least half; zero false all-clears in the pilot set; at least 2 of 3 partners say they would pay for it |

Why this first: trust is the product. A compliance officer will not rely on a report until they have compared it with their own work. The pilot also builds a labelled test set from real cases, which is exactly what the model comparison needs.

## Sprint 2: A version a regulated firm can buy

| | |
| --- | --- |
| **Goal** | Turn the pilot version into something a regulated firm is allowed to use and willing to sign a contract for |
| **Target user / buyer** | Heads of compliance at Dutch payment institutions, fintechs and trust offices: regulated firms with formal screening obligations and a budget for tooling |
| **Channel / motion** | Convert the pilot partners into paying customers; publish one anonymised case study; approach the next 10 prospects with it |
| **Key deliverable** | Production data and controls: a commercial OpenSanctions data licence (the free data is non-commercial only), the live KvK API instead of the test environment, PDF export, a full audit log per report, and documented accuracy on the pilot test set |
| **Success metric** | First paid contract signed; data costs per report known and below the price per report; accuracy on the test set documented and shared with the customer |

Why this second: the MVP runs on data that may not be used commercially and on fictitious KvK records. A buyer's compliance department will ask about data licences, accuracy and audit trail before anything else.

## Sprint 3: Fit into their workflow

| | |
| --- | --- |
| **Goal** | Make the agent part of the weekly routine instead of a tool someone remembers to open |
| **Target user / buyer** | The same customers, now including onboarding and procurement teams who request vendor checks |
| **Channel / motion** | Product-led expansion inside existing customers: integrate where requests already arrive, so new users start using it without training |
| **Key deliverable** | Batch mode (upload a vendor list), an n8n trigger from email or SharePoint, and scheduled re-screening of existing vendors with an alert when a sanctions or adverse media status changes |
| **Success metric** | Checks per customer per week; 80% of pilot users still active after a month; at least one status-change alert that a customer acted on |

Why this third: a one-off check is a project; re-screening every vendor every six months is a habit. Batch and monitoring turn the tool from "nice to have" into part of the compliance programme.

## Known risks across the sprints

- **Trust:** one false all-clear can end a pilot. The failure tests (incomplete checks never produce "Onboard") must stay in place and be shown to every prospect.
- **Data costs:** commercial sanctions data and live KvK queries cost money per check; pricing must cover them.
- **Liability:** the report supports, and does not replace, a compliance officer's judgement. This must be clear in the contract and on every report.
