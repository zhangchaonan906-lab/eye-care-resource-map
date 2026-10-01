# P7 Public Facility API

P7 adds read-only App Router handlers over `public.published_facility_api`. The database view is the publication boundary: it is built from `public.published_facilities`, which already requires publication, verified facility/location/evidence, and approved sources. The `eye_public_api_runtime` login inherits a role that can select only the dedicated API view.

The API does not read candidate records, raw source snapshots, import runs, internal review state, private provenance, phone numbers, or websites. Response fields are constructed from an explicit TypeScript allowlist. The API is read-only; there are no write routes.

**Data minimization rule:** public facility APIs exclude personal representative/responsible-person names unless an explicit future product and legal requirement authorizes them. Source adapters must not map those names into the public facility model by default.

## Endpoints

All successful responses use `{ "data": ..., "meta": ..., "error": null }`. Errors use `{ "data": null, "meta": null, "error": { "code": "...", "message": "..." } }`.

### `GET /api/facilities`

Required:

- `bbox=west,south,east,north`: WGS84 longitude/latitude. Bounds must be ordered west-to-east and south-to-north and fall inside the world coordinate limits. Antimeridian-crossing boxes are not supported.

Optional:

- `category`: one of the five IDs returned by `/api/meta/categories`.
- `region`: 2, 4, or 6 digit administrative-code prefix.
- `limit`: 1–500, default 100.
- `cursor`: opaque keyset cursor returned by the previous page.

The repository calls a bounded `SECURITY DEFINER` SQL function. It applies PostGIS `ST_Intersects` / `ST_MakeEnvelope` directly to the indexed WGS84 geography before joining the published-only API projection. Results are ordered by facility UUID. It fetches at most `limit + 1` rows to determine whether another page exists. The existing GiST index is on the underlying verified location geography.

### `GET /api/facilities/{id}`

Returns a single published facility by UUID. A candidate or unpublished ID appears as `404 NOT_FOUND`.

### `GET /api/search`

Required:

- `q`: 1–100 characters after Unicode NFKC and whitespace normalization.

Optional:

- `match`: `exact` or `prefix`, default `prefix`.
- `region`: 2, 4, or 6 digit administrative-code prefix.
- `category`: public category ID.
- `limit`: 1–20, default 20.
- `cursor`: opaque keyset cursor returned by the previous page.

Search uses the stored normalized facility name and orders by normalized name, then UUID. It does not do fuzzy matching or entity matching.

### `GET /api/meta/categories`

Returns the stable category IDs and Chinese labels:

- `eye_specialty_hospital`
- `general_hospital_ophthalmology`
- `ophthalmology_center`
- `eye_clinic`
- `unknown`

## Facility response

Each item contains only:

- `id`, `name`, `category`, `address`
- `region: { adcode, name }`
- `hospitalLevel`, `hospitalGrade`
- `longitude`, `latitude` (WGS84)
- `ophthalmology: { status: "verified", evidenceCount }`
- `attribution: [{ name, url, updatedAt }]` for approved sources allowing app display
- `lastVerifiedAt`

Coordinates are not converted by P7. Only coordinates already verified and published by the publication gate can be returned. An empty database returns an empty `data` list and never triggers imports or seed generation.

## Errors and bounds

- `400 INVALID_ARGUMENT`: malformed or out-of-range input.
- `404 NOT_FOUND`: no published facility for a valid detail UUID.
- `500 INTERNAL_ERROR`: generic service error; SQL, connection, stack, and private table details are not returned.

All SQL values are parameters. Limits are hard-capped even if a client requests larger values. Cursors are base64url keyset values, not authorization tokens; changing filters between pages starts a logically new query and clients should discard the old cursor.

## Runtime configuration

Set `PUBLIC_API_DATABASE_URL` only in the server runtime. It must use the provisioned `eye_public_api_runtime` login (or an equivalent least-privilege login inheriting `eye_public_api`). Do not expose this variable with a `NEXT_PUBLIC_` prefix. The login cannot read `app_private` tables, source payloads, or the broader published view.

Migrations `011_public_api.sql` and `scripts/provision-public-api-login.sql` create the view/role and a disposable login respectively. `scripts/test-db.sh` applies the migrations and runs the synthetic PostGIS API integration suite; no real institution data is used.
