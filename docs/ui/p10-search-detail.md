# P10: Stable Search and Shareable Facility Details

## Scope

P10 adds paginated facility-name search, public detail pages at `/hospitals/{id}`, and a map deep link using `?facility={id}`. It does not change the existing `/api/search` or `/api/facilities/{id}` contracts.

## Search behavior

- Search keeps the API cursor and requests at most 20 records per page.
- The first page replaces results. “加载更多搜索结果” appends results by facility ID and ignores IDs already present.
- Changing the query, category, or region clears the cursor and aborts the pending page request. Stale first-page responses are ignored as well.
- A failed later page keeps earlier results visible and offers a retry.
- Result rows include the public name, category, region, and address. The result button selects the facility on the map; the separate “详情” link opens its shareable page.

## Public facility detail

`/hospitals/{id}` reads through `getPublicFacilityRepository().getById()`, which selects only from `public.published_facility_api`. Invalid UUIDs and IDs absent from that published-only projection use the same not-found page. Direct page loads and refreshes are handled by the App Router server page.

The page displays public name, category, address, region, optional hospital level and grade, verified ophthalmology status, last verification date, and source attribution. It omits internal IDs, raw source payloads, evidence counts, and private fields. Attribution links are clickable only for HTTPS URLs and open with `noopener noreferrer`. Missing source attribution or dates are shown as “公开来源信息暂缺”.

The page metadata uses the same published lookup and only available public fields. Missing or invalid facilities receive no facility-specific metadata. No canonical host is configured. The page includes the approved information disclaimer and a “在地图中查看” link.

## Map deep link

The map validates the `facility` query value as a UUID before making a request. For a published facility, it loads the normal detail endpoint, selects the facility, opens the detail panel, adds the public point to the map layer, and flies to its coordinates. Invalid or unavailable IDs produce a non-blocking status message and leave search and map browsing available. User coordinates are never placed in the URL or browser storage.

## Search query and index

Search continues to use keyset pagination ordered by `(normalized_name, id)`. Migration `003_published_view.sql` provides the `facilities_normalized_name_idx` B-tree index. The current prefix predicate uses `left(normalized_name, char_length($1)) = $1`; P10 does not claim that this expression uses the B-tree index, and does not add a speculative index migration without representative production-scale data and an `EXPLAIN` comparison. Recheck the query plan when a representative non-production dataset is available. The cursor remains the existing opaque API cursor and is passed through unchanged.

## Verification

The web unit suite covers search paging, ID de-duplication, cursor resets, stale request cancellation, preservation after a later-page error, detail metadata and not-found behavior, safe attribution, map deep links, and P8/P9 UI behavior. Run `npm test`, `npm run test:db`, `npm run lint`, `npm run typecheck`, and `npm run build` from `apps/web`. The repository CI also runs `scripts/test-db.sh` and `git diff --check`.
