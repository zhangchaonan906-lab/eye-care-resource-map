# P14-B Production Coordinate Provider Decision

**Decision: no provider selected; no geocoder calls made. Gate: `PRODUCTION_COORDINATE_PROVIDER=PENDING`.**

**Persistent production coordinates written: NO.**

**Reviewed:** 2026-10-05 UTC. This is a preliminary official-document review, not legal approval or a provider contract.

## Candidate comparison

| Candidate | Geocoding capability | Result storage / redisplay / public use | Coordinate system / accuracy | Quota / price / deletion | Disposition |
|---|---|---|---|---|---|
| AMap Web Service | Official Web Service APIs include geocoding. | Terms require technical-service license for organization commercial use and prohibit direct storage/cache absent a clear separate license; using its Web Service together with a different map provider has a documented restriction. | Exact coordinate output and accuracy still require service-specific evidence. | No configured account, plan, budget, deletion terms, or storage permission. | Not compatible with planned persistent coordinates + independent MapLibre basemap under currently documented terms. No calls. |
| Baidu Maps Geocoding V3 | Official docs accept structured mainland-China addresses and allow `ret_coordtype=gcj02ll`; default response is `bd09ll`. This is a documented coordinate-system choice, not proof that downstream conversion/storage is permitted. | The reviewed API docs establish capability only. They do not establish this app's rights to persist returned coordinates, keep backups, or redisplay them on a different MapLibre map. | Mainland support is explicit; result quality still needs a controlled representative QA sample. | Current plan pricing/quota, persistence/deletion, withdrawal and third-party map terms have not been confirmed. | Strong technical candidate for further document review; no calls or coordinate writes. |
| Tencent Location Services WebService | Official product documentation describes location APIs; a project-specific forward-geocoding product/permission is not confirmed in this review. | Search/API availability does not establish rights to store results or display them on another basemap. Obtain the applicable product terms and written scope. | Exact returned coordinate system and accuracy must be verified from the selected API docs. | Key, quotas, pricing, deletion/withdrawal, and applicable retention terms unverified. | Candidate only; no calls. |
| Tianditu / provincial nodes | Official portals list Web Service API and developer resources; exact geocoding API entitlement for this application is not confirmed. | Public endpoint visibility is not permission for persistent storage, redistribution, or display on an unrelated map. Terms/authorization must expressly cover these acts. | Exact service coordinate system and accuracy must be verified for selected node and API. | Registration, quotas, price, data retention, deletion and audit conditions unverified. | Candidate only; no calls. |
| MapTiler Geocoding | Official Cloud terms permit documented geocoding results to be used outside the service; bulk downloads are specifically permitted only for its Geocoding API under its terms. | The terms require attribution for a database created from search services. Exact plan, backups, public redisplay, and any third-party data rights still need to be verified for this app. | Mainland address quality, coordinate system, coverage, and accuracy are not demonstrated by the pricing/terms pages. | Current public pricing lists a $30/month Flex plan with metered overage; production volume/budget and deletion obligations need review. | Most promising documented storage candidate, but China suitability and full retention/redisplay case remain unproven. No account or API calls. |

## Mandatory approval checklist

For one named provider and plan, retain dated documentary evidence for every item below. A blank or ambiguous item keeps the gate PENDING:

1. Geocoding is permitted for the intended hospital address inputs.
2. Results may be persisted after the API response expires.
3. Results may be stored in the project database and backups.
4. Results may be redisplayed to end users on the selected public map.
5. Public and commercial application use is included, if applicable.
6. Coordinate system, any permitted conversion, expected accuracy, and suitable QA method are explicit.
7. Quotas, pricing, overage, domain/API-key restrictions, and service limits are recorded.
8. Retention, withdrawal, deletion, backup deletion, and audit requirements are implementable.

Until all eight items are approved, geocoder calls remain 0 and production coordinates remain unstored. Do not infer persistent storage permission from map-provider selection or from a successful API response.

## Official references reviewed

- [AMap Open Platform Agreement](https://lbs.amap.com/pages/terms/), [AMap Web Service API terms](https://lbs.amap.com/pages/law-web-service/summary) (including its restriction on combining the Web Service API with third-party map services), and [Technical Service License](https://lbs.amap.com/pages/authorization/).
- [Tencent Location Services official product page](https://cloud.tencent.cn/solution/lbs) and [Tencent Maps API documentation](https://cloud.tencent.com/document/product/1301/68448). These describe product capabilities/API-key setup, not storage rights for this project.
- [Tianditu Tianjin official platform](https://tianjin.tianditu.gov.cn/) and [Tianditu Guangdong service clause](https://guangdong.tianditu.gov.cn/index/page/serviceClause.html).
- [MapTiler Cloud Terms](https://www.maptiler.com/terms/cloud/), [General Terms](https://www.maptiler.com/terms/), and [pricing](https://www.maptiler.com/cloud/pricing/).
- [Baidu Geocoding V3](https://lbs.baidu.com/docs/webapi?title=geocoding%2Fguide%2Fwebservice-geocoding-base) documents address geocoding and `ret_coordtype=gcj02ll` (default `bd09ll`); its API page does not resolve persistent-storage rights for this application.
