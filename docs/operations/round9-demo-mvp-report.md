# National Data Round 9 — Competition Demo Data MVP

**Review date:** 2026-10-06
**Baseline:** Round 8 local candidate ledger
**Candidates:** 193; traceability gaps: 0
**Candidates with an address:** 38
**Use scope:** supervised, offline university competition demo; no public operation

## Result

Twelve address-bearing candidates were selected for individual verification. Seven passed identity, specific-site, address, ophthalmology-evidence, official-link, and limited-use review for an offline list/detail demo. Five remain in the candidate pool: two need better campus or source-use evidence, and three could not be fully verified through normal public pages. Only the seven eligible fact records are in the local demo JSON.

| Measure | Result |
| --- | ---: |
| Candidates in baseline | 193 |
| Address-bearing candidates in baseline | 38 |
| Pilot targets individually reviewed | 12 |
| Eligible for local competition demo | 7 |
| Eligible sample addresses verified | 7 |
| Explicit coordinates verified for persistent display | 0 |
| Targets retained in candidate pool | 5 |
| New candidates added | 0 |

## Individually reviewed targets

| Candidate / specific site | Address and eye-service evidence | Official link | Decision |
| --- | --- | --- | --- |
| Shanghai EuroEyes Eye Clinic — Jinmao clinic | Shanghai, Pudong, Jinmao Tower podium, 5F; Shanghai government directory classifies it as an ophthalmic clinic and the clinic location page identifies the Jinmao site | [Shanghai locations](https://www.euroeyes.cn/locations/) | Eligible for offline list/detail demo |
| Wuhan Aier Eye Hospital — Wuchang | Wuhan, Wuchang, 481 Zhongshan Road; Wuhan WJW roster category is “眼科医院”; Aier site identifies this site and eye services | [Wuhan Aier](https://www.eye027.com/) | Eligible; one named site |
| Wuhan Puri Eye Hospital — Qiaokou | Wuhan, Qiaokou, 179 Zhongshan Avenue; WJW roster category is “眼科医院”; provider site has eye-service material, but its legal statement restricts copying/use of site content and automated access | [Wuhan Puri legal statement](https://www.pr027.com/p/Legal-Statement) | Excluded from demo pending a source/use basis that does not rely on restricted site content; no application planned |
| Hubei Puri Eye Hospital — Guanggu | Wuhan, Hongshan, 718 Luoyu Road, Chunhe Tiandi; WJW roster category is “眼科医院”; provider page identifies the Guanggu site and eye services | [Hubei Puri](https://hbpryy.com/Corneal-Disease) | Eligible for offline list/detail demo |
| Wuhan University Zhongnan Hospital — Donghu Road site | Wuhan, Wuchang, 169 Donghu Road; the official ophthalmology page itself describes the eye department and gives this address | [Ophthalmology department](https://www.znhospital.cn/yk.html) | Eligible as this explicitly identified site; do not merge with the separate Guanggu campus |
| Wuhan Aier Eye Hospital Hanyang | Wuhan, Hanyang, 12 Luoqi North Road, Jinlong Mansion commercial building, levels 1–2; WJW roster names this distinct eye hospital and the provider page identifies the Hanyang site | [Wuhan Aier](https://www.eye027.com/) | Eligible; separate named site, not merged with Wuchang |
| Jinan Second People’s Hospital (Jinan Eye Hospital) | Jinan, Jingyi Road 148; official hospital profile identifies its ophthalmology service and eye-specialty status | [Hospital profile](https://www.sdjneye.com/yygk/yyjj.htm) | Eligible for offline list/detail demo |
| Sichuan Academy of Medical Sciences · Sichuan Provincial People’s Hospital | Official pages show several clinical sites; the reviewed general ophthalmology page does not tie the eye service to the selected Qingyang address | [Ophthalmology department](https://www.samsph.cn/eyes_intro/) | Excluded until an official page explicitly binds the eye service to a specific site |
| Zhengzhou Puri Eye Hospital | Candidate has a ledger address; the institution contact page could not be retrieved through normal public access in this review | [Institution contact page](https://www.p0371.com/contact) | Blocked; excluded from demo |
| Wuhan Aige Eye Hospital | WJW roster provides institution facts, but the listed provider website timed out on normal public retrieval | [Institution website](https://www.aige010.com/) | Blocked; excluded from demo |
| Wuxi Huaxia Eye Hospital | Wuxi, Liangxi, 100 Xingyuan Road; provider page names this hospital, gives the address, and describes ophthalmic services; Wuxi WJW 2026 validation notice independently lists the institution as qualified | [Hospital detail](https://www.huaxiaeye.com/Index/shows.html?catid=64&id=72) | Eligible for offline list/detail demo |
| Wuxi New Vision Eye Hospital | Wuxi WJW sources identify the named eye hospital and its category/address, but the institution’s public page did not complete normal retrieval in this review | [Wuxi WJW validation notice](https://wjw.wuxi.gov.cn/doc/2026/05/13/4774787.shtml) | Partial; retained in candidate pool pending direct site verification |

The Wuhan WJW roster is a Wuhan-region secondary and tertiary institution list, not a claim of complete city coverage. A roster row listing multiple addresses was not converted into a selected site. Zhongnan is tied to Donghu Road by its own ophthalmology page; other campuses remain separate. The Wuhan Aier Wuchang and Hanyang sites remain separate named institutions.

## Local demo artifact and map boundary

The seven approved fact records are stored outside Git at:

`%LOCALAPPDATA%\EyeCareResourceMap\NationalHarvest\Round9\competition-demo-candidates.json`

The JSON contains only organization name, region, address, organization/eye-evidence category, official source link, provider link, review date, and a null coordinate. It contains no staff names, personal phone numbers, patient data, raw spreadsheet, page text, images, or logos. It is limited to supervised offline list/detail display and is not approved for public deployment.

No explicit coordinates with a clear persistent-display basis were found. Coordinates remain null; this sample supports a sourced list/detail demo, not map pins or nearby-distance calculations.

## Boundaries

- Production database writes: 0
- Candidate or review database writes: 0
- Facility publication: 0
- Automatic merges: 0
- Geocoder calls: 0
- Public/unaudited display: 0
- Raw data committed to Git: NO
- Applications, government outreach, login bypass, CAPTCHA bypass: 0

## Verification

- Round 8 report-integrity unit tests: PASS
- Round 8 report-integrity validator: PASS
- PR #38 full CI: PASS before squash merge
- Round 9 ledger identity/address/traceability checks: PASS for all 12 selected targets
- Local demo JSON schema and eligibility checks: PASS for 7 records
- `git diff --check`: PASS

## Sources

- [Wuhan WJW, Wuhan-region secondary and tertiary medical institution roster (2026-01-22)](https://wjw.wuhan.gov.cn/bsfw_28/bjcx/yljgmd/202601/t20260122_2716488.shtml)
- [Shanghai government, Shanghai medical services directory](https://english.shanghai.gov.cn/en-Hospitals/)
- [Wuxi WJW, 2026 first-half medical institution validation results](https://wjw.wuxi.gov.cn/doc/2026/05/13/4774787.shtml)
- Provider pages linked in the table above.
- [Copyright Law of the People’s Republic of China, National Copyright Administration](https://www.ncac.gov.cn/xxfb/flfg/flfg_532/202103/t20210309_50530.html)
- [Personal Information Protection Law, CAC](https://www.cac.gov.cn/2021-08/20/c_1631050028355286.htm)
