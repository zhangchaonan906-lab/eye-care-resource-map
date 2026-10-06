# National Harvest Round 8 Report

**Status:** candidate consolidation and competition-demo assessment complete.
**Round 8 branch:** `national-harvest-round8-verified-candidate-consolidation`
**Opening baseline:** 187 current candidates; 0 traceability gaps.
**Current local pool:** 193 distinct candidates; 6 new candidates; 0 traceability gaps.

## Work completed

1. Audited and copied the Round 7 verified candidate master into the Round 8 local Harvest Store without altering the prior ledger.
2. Rechecked SHA-256 and byte sizes for 14 locally available official files: 14 passed, 0 failed, 0 missing or ambiguous.
3. Matched source rows to existing candidates by exact normalized institution name plus region. Filled 31 empty addresses, 27 categories and 4 registration identifiers where source values were present.
4. Reviewed official pages and added six traceable candidates: 四川省医学科学院·四川省人民医院, 中国科学技术大学附属第一医院（安徽省立医院）, 杭州市第一人民医院, 济南市第二人民医院（济南市眼科医院）, 郑州普瑞眼科医院, and 武汉仲景东西湖中医医院. Their evidence is respectively hospital ophthalmology-department pages, an official hospital profile, or a current health-commission licensing notice; campus ambiguity was retained.
5. Classified 54 unique source URLs for research and display. No source passed the current competition-display terms review, so the eligible local demo export remains empty.

## Focus-area results

| City | Current candidates |
|---|---:|
| 北京市 | 2 |
| 上海市 | 5 |
| 深圳市 | 7 |
| 杭州市 | 1 |
| 成都市 | 2 |
| 武汉市 | 18 |
| 南京市 | 7 |
| 合肥市 | 1 |
| 济南市 | 2 |
| 郑州市 | 1 |


Round 8 adds candidates to Hangzhou, Chengdu, Wuhan, Hefei, Jinan and Zhengzhou. Beijing, Shanghai, Shenzhen and Nanjing were covered by the inherited candidate pool and received current official-source checks; the number of candidates is not a completeness claim.

The six additions are traceable to sources such as the [Sichuan Provincial People’s Hospital ophthalmology department](https://www.samsph.cn/eyes_intro/), [Hangzhou First People’s Hospital ophthalmology department](https://www.hz-hospital.com/service/deptment_details/id/35), [USTC First Affiliated Hospital ophthalmology page](https://www.ahslyy.com.cn/jyb/col1193/13684), [Jinan Eye Hospital official profile](https://www.sdjneye.com/yygk/yyjj.htm), [Zhengzhou health-commission approval entry](https://wjw.zhengzhou.gov.cn/tzgg/8245820.jhtml), and [Wuhan licensing notice](https://wjw.wuhan.gov.cn/zwgk_28/fdzdgknr/xkfw/spgg/202609/t20260903_2843036.shtml).

## Round 8 totals

- Current candidates: **193** (baseline 187; new 6; 250 target not met and remains non-mandatory).
- Candidates with an address: **38**.
- Candidates with verified coordinates: **0**.
- Candidates eligible for competition demo: **0**.
- Unique candidate source URLs: **54**; 6 of 7 new lead URLs confirmed via official page open/search; 1 direct page open unresolved; 47 inherited URLs not freshly checked this round.
- Regions represented: **23/31**; cities represented: **28**.
- Traceability gaps: **0**.
- Cross-source review: 4 exact corroborations, 2 probable alias cases, 1 ambiguous-campus cases, 0 conflicts. No automatic merge.

## Data boundaries

- Raw originals and detailed candidate ledgers remain outside Git in `C:\Users\72343\AppData\Local\EyeCareResourceMap\HarvestStore\round8\`.
- No personal names, personal contact data, or unrelated raw-table fields were added to tracked docs or demo output.
- Production database writes: **0**. Geocoder calls: **0**. Facilities published: **0**. Unreviewed public display: **0**. Automatic merges: **0**.
- No applications, government outreach, login bypass, or CAPTCHA bypass occurred.

## Tests and checks

- Local file fingerprint verification: **14 PASS / 0 FAIL / 0 missing or ambiguous**.
- Candidate ledger: **193 distinct keys**, all traceable; verify during final checks.
- Production database writes: **0** by workflow.
- `git diff --check`: PASS on the report and integrity-check changes.
- CI baseline before this follow-up: PASS for `collector`, `p13-e2e`, `p13-accessibility`, `p13-system-e2e`, and `p14-release-check`; the expanded CI run with the report-integrity gate is required before squash merge.
