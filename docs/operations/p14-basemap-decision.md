# P14-B Production Basemap Decision

**Decision: no provider selected. Gate: `PRODUCTION_BASEMAP=PENDING`.**

**Reviewed:** 2026-10-05 UTC. This is a preliminary official-document review, not legal approval or a contract.

## Candidate comparison

| Candidate | Mainland China coverage / coordinates | Browser rendering | Usage rights and attribution | Quota, pricing, domain, retention, audit | Current disposition |
|---|---|---|---|---|---|
| AMap JavaScript API | China-oriented provider candidate; coordinate-system behavior and regional coverage must be verified for the actual product. | Web map API is documented; MapLibre interoperability is not assumed. | Current AMap platform agreement describes commercial use as requiring a technical-service license for organizations and restricts storage/caching or derivative use of returned content. Exact map display scenario and attribution still require written confirmation. | Account, key restrictions, plan/quota, pricing, domain limits, retention/logging, and audit obligations are unconfigured. | Do not select without licensed use scenario and written confirmation of required use. |
| Tencent Location Services | Official product describes map/location/search/routing capabilities; precise coverage and coordinate behavior for this app must be confirmed. | SDK/API integration options exist; specific Web/map rendering and MapLibre fit are not confirmed here. | Product-specific Open API agreement and attribution obligations have not been reviewed to a scope sufficient for public/commercial use. | Key/account, current quotas/pricing, domain restrictions, retention, and audit conditions remain unverified. | Candidate for a separate terms review only. |
| Tianditu / provincial nodes | Official national/provincial geographic-information platforms expose map/API developer resources. Nationwide consistency, regional service availability, and coordinates need verification. | Public pages list map, web-service, and data APIs; exact browser SDK integration/MapLibre compatibility remains unverified. | Portal service clauses and copyright/attribution pages exist, but applicable authorization for this public/commercial application and each content layer has not been confirmed. | Registration/key conditions, quotas, prices, domains, retention, and audit requirements need provider-specific confirmation. | Candidate for official inquiry; not yet approved. |
| MapTiler Cloud | Mainland China latency, data completeness, and service behavior have not been observed from a deployed mainland environment. | Official integration docs show MapLibre GL JS usage. | Cloud terms require visible attribution and restrict proxying/export and excessive bulk tile downloads. Exact content/style/font/icon rights still need project review. | Pricing page currently lists Flex at $30/month (USD), 25k sessions and 500k API requests included; extra traffic is metered. Custom advertises 99.9% SLA. No quota/key is configured. | Strongest documented MapLibre/commercial candidate, but mainland usability/reliability and exact data rights remain unverified. No key configured. |
| OpenStreetMap Foundation public tile servers | Coverage is not an approval basis. | Common clients can render OSM-derived tiles, but rendering capability does not grant tile-hosting rights. | Public OSM tile servers are not a production tile CDN. Attribution and OSM database licensing do not grant unlimited use of the public tile infrastructure. | No production quota, SLA, domain, support, or service contract for this use. | Explicitly not selected for production. |

## Required decision evidence

Before changing the gate to PASS, attach a provider/plan and written approval for:

- mainland China availability and coordinate system;
- MapLibre/browser compatibility and any required SDK;
- commercial/public display, data/content and style/font/icon rights;
- exact user-visible attribution;
- quota, overage pricing, SLA, domain/key restrictions;
- tile caching, logs, data retention, deletion, and audit obligations.

Do not put provider credentials in Git. Keep development placeholders separate from production configuration.

## Official references reviewed

- [AMap Open Platform Agreement](https://lbs.amap.com/pages/terms/) and [Technical Service License](https://lbs.amap.com/pages/authorization/).
- [Tencent Location Services official product page](https://cloud.tencent.cn/solution/lbs) and [Tencent Maps API documentation](https://cloud.tencent.com/document/product/1301/68448). These pages identify capabilities and API-key requirements; they are not sufficient evidence of the project-specific rights in the table.
- [Tianditu Tianjin official platform](https://tianjin.tianditu.gov.cn/) and [Tianditu Guangdong service clause](https://guangdong.tianditu.gov.cn/index/page/serviceClause.html); applicability and terms require provider/legal review.
- [MapTiler Cloud Terms](https://www.maptiler.com/terms/cloud/), [General Terms](https://www.maptiler.com/terms/), [pricing](https://www.maptiler.com/cloud/pricing/), and [MapLibre GL JS integration guide](https://docs.maptiler.com/maplibre/).
- [OpenStreetMap Tile Usage Policy](https://operations.osmfoundation.org/policies/tiles/).
