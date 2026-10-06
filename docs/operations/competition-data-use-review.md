# Competition Data Use Review — Round 9

**Review date:** 2026-10-06
**Project:** university student, non-commercial competition project
**Route:** no applications, government outreach, login bypass, or CAPTCHA bypass

## Decisions by use context

| Use context | Decision |
| --- | --- |
| Local research and internal candidate review | Keep source links, evidence, and review dates in the local candidate ledger |
| Supervised offline competition demo using the seven reviewed records | `COMPETITION_DEMO_REVIEWED`, limited to organization facts and visible attribution/source links |
| Public website, production operation, full roster reproduction, or raw-data release | `PUBLIC_RELEASE_REVIEW_REQUIRED`; Round 9 does not authorize these uses |

This is a bounded project assessment, not a legal guarantee. Non-commercial status does not settle every use question. The absence of a separate license is also not treated as an automatic requirement to apply. No applications or contacts are planned. Sources whose relevant page terms restrict use, or whose exact site cannot be tied to the eye evidence, remain outside the demo.

## Separate assessment questions

1. **Can the objective fact be used in this demo?** The local artifact uses a small number of organization names, districts, addresses, categories, eye-service evidence labels, and source links. It does not reproduce page prose or table layout. Each sample has a source trail and an explicitly named site.
2. **Is protected expression or a compilation copied?** No paragraph, image, logo, screenshot, raw workbook, or complete directory is included. Copyright rules distinguish factual news from original expression and can protect an original selection or arrangement of a compilation; this does not create a blanket right to reuse a full list or database. The demo is a small independently selected subset and links to the source.
3. **Are there explicit access or use restrictions?** Pages were checked through ordinary public access only. No login, CAPTCHA, hidden endpoint, or bulk download was used. The Wuhan Puri legal statement restricts unauthorized copying/modification/distribution/use of site content and automated access. Its provider page is therefore not used as demo evidence/content. The row stays in the research pool and is excluded from the local demo pending a source basis that avoids those restrictions.
4. **Does the data include personal information?** The demo contains organization-level facts only. It omits individual names, personal phone numbers, identity data, patient data, and staff rosters. Information about an identifiable person still requires a purpose and lawful basis even if publicly accessible; this dataset does not need those fields.
5. **What display scope is being assessed?** Only supervised, offline defense/list-detail display. Public deployment, broader dissemination, and persistent map markers need a separate review of source-specific terms, scope, attribution, update obligations, and coordinate rights.

## Source-level decision record

| Source / sample | Public facts and verification used | Restrictions / uncertainty | Round 9 decision |
| --- | --- | --- | --- |
| Wuhan Municipal Health Commission roster | Named institution, district, address, category/grade; used only for selected rows | Public HTML; no explicit reuse license located. The 185-row roster is not copied or redistributed | Four selected Wuhan facts may appear in the supervised offline demo only when supported by the institution page and with attribution. No full-list reuse |
| Shanghai government medical directory | Shanghai EuroEyes name, address, ophthalmic-clinic classification | Public directory; no explicit data license located | One selected organization fact record for offline demo with attribution/link |
| Wuxi WJW 2026 validation notice | Confirms current existence/validation of Wuxi Huaxia and New Vision entries | Validation notice is not itself proof of address or service detail; Huaxia provider page supplies its exact facts; New Vision provider page was not retrievable | Huaxia selected for offline demo using the provider’s single-hospital detail page; New Vision remains research-only |
| Institution pages for the seven eligible records | Exact named site, address, and eye service where the page supports those facts | Use only the facts needed for the demo; no photos, logos, page copy, people data, or embedded assets | Offline demo with source link and attribution |
| Wuhan Puri provider website | Site address and eye-service material were reviewed | Its legal statement restricts copying/use of site content and automated access | Excluded from demo; retain candidate and source trail only |
| Sichuan Provincial People’s Hospital pages | Hospital has multiple clinical sites; a general eye department page exists | Reviewed evidence does not bind the eye service to the selected Qingyang address | Excluded until a public official page explicitly joins department and site; no inference or outreach |
| Zhengzhou Puri / Wuhan Aige / Wuxi New Vision | Candidate and government evidence exists | Direct provider-page verification failed or timed out under normal access | Excluded from local demo; no bypass or retry escalation |
| Local candidate ledger and source files | Candidate identity and prior provenance | Quarantined research materials | Remain outside Git and outside demo except for the seven checked fact records |

## Minimal-field controls

The demo artifact includes only institution name, region, exact reviewed address, institution/ophthalmology evidence category, official source URL, institution website URL, verification date, and `coordinates: null`. It excludes all unrelated individual and operational fields. It does not contain the source roster or workbook.

## Coordinates

No exact coordinate with a clear persistence and display basis was found for the seven eligible sites. No geocoder, third-party POI lookup, inferred coordinate, or manual pin placement was used. Coordinates remain null. This review approves a list/detail defense demo only.

## Offline presentation conditions

- Keep the official source link visible beside each record.
- Cite the government directory for facts drawn from it and the institution page for its specific site/service details.
- Show the 2026-10-06 review date and site/campus label.
- State that the selection is illustrative and incomplete; do not imply endorsement, availability, or nearest-provider ranking.
- Do not distribute source files, screenshots, or the local JSON artifact.
- Do not publish this dataset or add map markers without a new, source-specific assessment.

## Legal references

- [Copyright Law of the People’s Republic of China, National Copyright Administration](https://www.ncac.gov.cn/xxfb/flfg/flfg_532/202103/t20210309_50530.html), including Articles 5 and 15.
- [Personal Information Protection Law, CAC](https://www.cac.gov.cn/2021-08/20/c_1631050028355286.htm), including Articles 4–7, 10, 13, and 27.
- [Wuhan Puri Eye Hospital legal statement](https://www.pr027.com/p/Legal-Statement), reviewed for site-content and automated-access restrictions.
