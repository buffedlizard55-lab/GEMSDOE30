# GEMS Official Rules — complete review notes (2026-10-03)

**Source reviewed:** [Geologic Enhanced Mapping System (GEMS) Prize Official Rules, September 2026](https://docs.nlr.gov/docs/fy26osti/96647.pdf), hosted on the National Laboratory of the Rockies’ official `docs.nlr.gov` domain. All seven parsed chunks (0–6 of 7) were retrieved and reviewed. The source is authoritative for the written rules but should be rechecked before any entry because the organizer may update dates or terms. This is a project compliance summary, not legal advice or an eligibility determination.

## Requirements that affect this repository

| Topic | Rules section | Verified requirement / project consequence |
| --- | --- | --- |
| Prize phases | §1.1, §3.6 | Phase 1 is a $50,000 pool split equally among five top entries on a private withheld subset. Phase 2 is a separate $250,000 pool, scored on the expert-revised label set ($100k / $70k / $40k / $25k / $15k for places 1–5). The rules say all Phase 1 entries remain eligible for Phase 2 and are automatically reconsidered. A public score is not a private or final score. |
| Eligibility | §1.3, Appendix A.1–A.3 | Individual competitors must meet the stated U.S. citizenship/permanent-residency rules; entities must satisfy U.S. establishment requirements. The rules exclude several federal, FFRDC, DOE-support, foreign-interference, age, and other categories. The authorized competitor must certify eligibility and truthfulness under penalty of perjury. The repository cannot determine or certify the entrant’s status. |
| Data and target | §2, §3.3 | Features include GeoDAWN and USGS 1 m DEM; the rules describe INGENIOUS Great Basin compilation labels and expert-labelled new-fault test data, alongside the USGS Quaternary Fault and Fold Database. The organizers’ expert-new test labels are not locally available here. Owner mirrors remain owner-supplied, not organizer-authenticated. |
| GeoTIFF format | §3.2–§3.3 | The rules call for one single-layer GeoTIFF at 100 m covering the complete GeoDAWN study area, in the competition’s prescribed format, with the official example/template supplied on the competition site. The exact portal acceptance of this repository’s finite-zero outside-mask fallback is **not verified**; the official sample uses NaN outside the footprint. Local format checks are not organizer acceptance. |
| Feedback and final selection | §3.2, §3.4–§3.6 | The rules allow up to three automated platform submissions per week (subject to the website’s current terms). Only one final submission may be selected for both prize rounds, and selection must be made without knowledge of private-set scores. This project does not upload, spend slots, or choose the entrant’s final submission. |
| AI use | §3.2 | Generative AI is allowed, but the competitor must disclose in the narrative the extent of its use and how it was used, outside the word count. The competitor is responsible for accuracy, authenticity, and authorship representations. Keep [`../ai-disclosure-draft.md`](../ai-disclosure-draft.md) factual and entrant-approved before an entry. |
| Reproducibility | §3.2, §3.5 | Finalists must provide complete code assets and documentation describing required resources and sufficient to reproduce results and generate new predictions. The repository’s experiment manifests, hashes, source register, tests, and run instructions support this requirement but do not by themselves establish a winning result. |
| Rights and public materials | Appendix A.4–A.5, A.10 | Public-designated submission materials may become public and grant DOE/NLR the stated broad government-use license. The competitor warrants original work and must have necessary rights to third-party content and to authorize its use as the rules require. Confidential information requires precise marking and may still be subject to FOIA/legal limits. Verify licenses and attribution for every external dataset; do not include credentials or sensitive materials. |
| Deadline | §1.2 and Appendix A.1 | Appendix A.1 states submission by **5:00 p.m. ET** on the deadline date. The competition homepage read on 2026-10-03 states **11:59 p.m. UTC** on 2026-12-03. On that December date, 5:00 p.m. Eastern Standard Time is 22:00 UTC, so the displayed clock times differ by 1 hour 59 minutes. Obtain organizer clarification; do not assume which controls. See IR-30-008. |
| Decision authority | §3.2, §3.6, Appendix A.12–A.17 | DOE is the final decision-maker; the rules reserve the ability to cancel/modify the prize and to award some, none, or all awards. A leaderboard rank is not a guarantee of an award. |

## Source and access boundaries

- Official rules PDF: <https://docs.nlr.gov/docs/fy26osti/96647.pdf>
- Competition problem and format: <https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/>
- Competition overview: <https://www.drivendata.org/competitions/306/competition-doe-gems/page/968/>
- Competition data tab: <https://www.drivendata.org/competitions/306/competition-doe-gems/data/> — unauthenticated access redirected to login; no competition archive was obtained and no login bypass was attempted.
- DrivenData Terms of Use: <https://www.drivendata.org/termsofuse/> — the prohibited-uses clause bars robot/spider/automatic website access for monitoring or copying; no automated leaderboard monitoring is implemented.

## Decision and unresolved items

No experiment in this repository is a competition submission or score. The official public leaderboard snapshot read on 2026-10-03 displayed DARD at **0.3195** and `wbg1` at **0.2600**; neither row identifies a TIFF hash. The owner page describes the named D2.8 file as unscored/not slot-approved, so its claimed 0.2600 attribution remains unresolved. No candidate is holdout-promoted, and no weekly slot has been used.

Before any eventual entry, the authorized human competitor must independently verify eligibility, current deadline, current data-use terms, the source/license status of every external layer, the exact portal file convention, the AI-use narrative, and the final selected artifact. None of those checks is delegated to an automated upload or monitoring workflow here.
