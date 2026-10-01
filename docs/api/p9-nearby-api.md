# P9 Nearby Facilities API

## Endpoint

`GET /api/nearby?lat=<latitude>&lng=<longitude>&radius=<meters>&category=<category>&limit=<count>`

`lat` and `lng` are required WGS84 coordinates. `radius` defaults to `10000` meters and accepts values from `500` through `50000`. `limit` defaults to `50` and accepts integers from `1` through `100`. `category` is optional and must match an existing public facility category. Invalid or missing values return `400 INVALID_ARGUMENT`; validation runs before the repository query.

The repository asks PostGIS for `limit + 1` rows. It returns at most `limit`, ordered by `distanceMeters` ascending and then facility `id` ascending. `meta` contains the result count, requested radius, and `truncated` flag. A truncated result means more matching facilities exist inside the radius.

Each item contains the existing `PublicFacility` fields plus `distanceMeters`. The response does not contain the requesting user's coordinates, request accuracy, source payload, review data, or internal identifiers.

## Database query and permissions

Migration `012_nearby_api.sql` adds `public.query_published_facilities_nearby`. It constructs the request point as `ST_SetSRID(ST_MakePoint(lng, lat), 4326)::geography`, filters with `ST_DWithin(location.geog_wgs84, user_point, radius_meters)`, and reports distance with `ST_Distance`. The geography predicate is applied directly to the existing indexed column `app_private.facility_locations.geog_wgs84`; `ST_DWithin` is PostGIS's index-aware predicate for radius searches ([PostGIS documentation](https://postgis.net/docs/ST_DWithin.html)).

The function joins `public.published_facility_api`, which only exposes verified, published facilities with approved source evidence. `PUBLIC` has no execute privilege; `eye_public_api` receives execute on this function and retains only its existing P7 public API permissions. It gains no direct access to private facility, location, evidence, or source-record tables and cannot write them.

## Privacy and caching

The browser sends coordinates only after the user clicks the location control. The nearby request uses `Cache-Control: no-store`; successful, invalid-argument, and internal-error nearby responses also use `no-store`. The repository performs a parameterized `SELECT` and does not write or log coordinates. The API never echoes user coordinates in its payload or error messages.

No location table, history, analytics event, cookie, or browser storage entry is created. Deployment operators must ensure their hosting access-log configuration does not retain query-string values for this endpoint, because the specified GET contract carries coordinates in its query string.

## Failure behavior

Malformed coordinates, invalid radius or limit, and unsupported categories return `400 INVALID_ARGUMENT`. Unexpected failures return a generic `500 INTERNAL_ERROR` without SQL details or coordinates. Empty results return `200` with an empty array and `truncated: false`.
