# P14-B Production Coordinate Provider Decision

**Decision: no provider selected; no geocoder calls made. Gate: `PRODUCTION_COORDINATE_PROVIDER=PENDING`.**

**Persistent production coordinates written: NO.**

**Reviewed:** 2026-10-02 UTC. This is a preliminary official-document review, not legal approval or a provider contract.

## Candidate comparison

| Candidate | Geocoding capability | Result storage / redisplay / public use | Coordinate system / accuracy | Quota / price / deletion | Disposition |
|---|---|---|---|---|---|
| AMap Web Service | Official Web Service APIs include geocoding; API-specific documentation and product access must be reviewed for the chosen account. | Current platform agreement restricts direct storage/cache and use of returned content unless an explicit written license applies. No documented approval to persist geocoded coordinates in this app's database and redisplay them publicly is on file. The Web Service API additional terms also say that while using it, the developer and affiliates will use only AMap map-service products; this may conflict with a separate map provider and requires explicit resolution before combining providers. | China coordinate-system behavior, conversion requirements, accuracy and error bounds must be established from the exact API docs and tested on real QA addresses. | Account, exact API quota/pricing, retention and withdrawal/deletion terms for stored results are not recorded. | Do not call or persist results until written permission expressly covers each use; separately resolve the map-provider exclusivity clause. |
| Tencent Location Services WebService | Official product documentation describes location APIs; a project-specific forward-geocoding product/permission is not confirmed in this review. | Search/API availability does not establish rights to store results or display them on another basemap. Obtain the applicable product terms and written scope. | Exact returned coordinate system and accuracy must be verified from the selected API docs. | Key, quotas, pricing, deletion/withdrawal, and applicable retention terms unverified. | Candidate only; no calls. |
| Tianditu / provincial nodes | Official portals list Web Service API and developer resources; exact geocoding API entitlement for this application is not confirmed. | Public endpoint visibility is not permission for persistent storage, redistribution, or display on an unrelated map. Terms/authorization must expressly cover these acts. | Exact service coordinate system and accuracy must be verified for selected node and API. | Registration, quotas, price, data retention, deletion and audit conditions unverified. | Candidate only; no calls. |
| MapTiler Geocoding | Official Cloud terms describe geocoding/search results and allow certain results outside the service under the terms; actual plan, region coverage, quality, and China mainland operations need confirmation. | Terms state geocoding results may be used outside the service and require database attribution for created databases. Confirm that the exact commercial plan permits this project’s storage and public redisplay and that source-attribution obligations can be met. | Coordinate system, accuracy, China suitability, and regional coverage need verification against the selected API/documentation. | Pricing/limits vary by plan; retention/deletion, withdrawal and audit conditions need confirmation. | Candidate for full terms/coverage review; no API key or call. |

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
