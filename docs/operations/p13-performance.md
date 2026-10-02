# P13 Synthetic Performance Notes

Date: 2026-10-03. Runtime-generated fixture: 5,000 published facilities, five synthetic regions and two categories. The complete fixture and benchmark transaction rolls back. These are local reference observations, not a production SLA or national traffic claim.

## Structural checks

| Query | Required structure | Observed plan | Result |
|---|---|---|---|
| Viewport | Geography `ST_Intersects` on the stored geography with the GiST index | `Index Scan using facility_locations_geog_wgs84_idx`; 1,000 synthetic points in the test viewport | PASS |
| Nearby | `ST_DWithin` on stored geography with the GiST index | `Bitmap Heap Scan` backed by `facility_locations_geog_wgs84_idx`; 1,000 synthetic points within the test radius | PASS |
| Prefix search | Indexed normalized-name prefix path | `Index Scan using facilities_normalized_name_idx`; 21-row page | PASS |
| Bounds | Hard page sizes and public-state checks remain inside API query | DB repository tests verified viewport limits, nearby radius/limit, and published-only search | PASS |

The initial benchmark exposed repeated expensive expansion of the source-rights and attribution views: viewport took approximately 209 seconds and nearby approximately 2.6 seconds. Migration `015_public_query_performance.sql` now materializes the spatial candidate set, the eligible published set, and the bounded API projection before returning results. This preserves the existing publication eligibility view while avoiding repeated expansion for each candidate. The search repository uses a security-definer search function: name filtering starts from the normalized-name index, then each candidate must join the protected published-facility view before output.

## Reference requests

The disposable SQL harness ran 52 sequential requests total (13 per query family) after warming the 5,000-row fixture. Times are in milliseconds.

| Query family | Requests | Median | p95 | Max | Error rate |
|---|---:|---:|---:|---:|---:|
| Viewport facilities | 13 | 707.62 | 867.99 | 898.34 | 0% |
| Nearby | 13 | 356.74 | 440.79 | 515.07 | 0% |
| Search | 13 | 553.74 | 639.17 | 722.07 | 0% |
| Detail | 13 | 0.21 | 2.08 | 2.25 | 0% |

This harness times PostgreSQL functions/views directly, not deployed HTTP, TLS, CDN, or browser rendering. The Web database integration suite separately exercises the actual repository methods and least-privilege database roles. No request was sent to a production API.

## Limits

- Query plans are visible for the underlying spatial and prefix predicates; `EXPLAIN` around security-definer SQL functions shows a function scan and does not expose the function's internal nested plan. The plan evidence therefore pairs function execution observations with direct index-capability plans and integration behavior.
- The 5,000 rows are synthetic and tightly clustered by design. They validate index paths and bounded work at the fixture scale only.
- A browser pan/zoom/filter stress test around 500 visible facilities, route-level HTTP latency distribution, memory profile, and deployment-scale load test remain unmeasured.
