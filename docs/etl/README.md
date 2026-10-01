# P3 ETL and candidate review foundation

P3 processes already collected, approved source snapshots into traceable
`candidate_records`. It does not publish or merge facilities. The runtime
command is:

```powershell
$env:ETL_DATABASE_URL = "postgresql://eye_etl_runtime:...@localhost:55432/eye"
py -m eye_collector.cli process --limit 100
```

`ETL_DATABASE_URL` must use the dedicated `eye_etl_runtime` login. The login
inherits the `eye_etl` role, which can read approved source snapshots and
facility targets and can write candidate/evidence/review rows. It has no write
privileges on `facilities`, `organizations`, or `source_records`.

## Transform rules

- Each candidate references exactly one immutable `source_record`; a unique
  constraint prevents a second candidate for that snapshot.
- Original source values remain in the source snapshot. Candidate parsed
  fields retain source text, while separate columns contain normalized values.
- Text normalization applies Unicode NFKC, whitespace collapsing, and common
  punctuation mapping. Address processing is text-only and does not infer
  missing administrative regions or coordinates.
- Phone normalization keeps digits from supported phone formats and removes a
  leading China country code. Unsupported text becomes null.
- Ophthalmology evidence is extracted only from explicit configured source
  fields (`ophthalmology_services`, `departments`, `department_text`, and
  `specialties`). Each mention is saved with the source field/value and rule
  version. A hospital name containing “眼科” is not evidence by itself.
- Matching uses a reliable source registration ID, or exact normalized name
  plus explicit administrative code and campus where supplied. Conflicts and
  ambiguity become `needs_review`. No fuzzy matching or automatic merge runs.
- Exact duplicate keys create pending review cases. Deferred database checks
  enforce at least two member candidates at transaction commit.
- Every snapshot is processed in its own transaction. A failed snapshot is
  logged and counted without changing its immutable source payload.

Structured JSON output reports snapshots read, candidates created, existing
candidates, skipped records, evidence, deterministic matches, review items,
duplicate cases, and errors. A successful no-op rerun reports zero pending
snapshots and leaves candidate counts unchanged.

## Access policy migration and P2 compatibility

Migration `005_etl_candidates.sql` constrains `source_catalog.access_policy`
to `automated_access_allowed`, `manual_only`, or `manual_review_required`.
Before adding the constraint, null and unrecognized legacy strings are
backfilled to `manual_review_required`; recognized P2 values keep their
meaning. New catalog rows default to the blocked review value. The P2
Collector still requires the exact `automated_access_allowed` value and its
approval gate is unchanged. The migration also adds a false-by-default
`registration_id_reliable` flag so matching only treats IDs as reliable when
the catalog explicitly attests to them.

The database runner inserts legacy null/unknown policy fixtures before
applying migration 005 and verifies their backfill, default, constraint, and
the existing P2 collector permissions. It then imports only packaged local
synthetic fixtures for P3 integration tests. No real or nationwide production
data is collected.

## Verification

Run unit, lint, and type checks from `services/collector`:

```powershell
py -m pytest tests -m "not database and not etl_database" -q
py -m ruff check src tests
py -m mypy src/eye_collector
```

Run `scripts/test-db.ps1` on Windows or `bash scripts/test-db.sh` on Linux to
apply all migrations and exercise P1/P2/P3 SQL, collector, and ETL database
checks against a temporary PostGIS database.
