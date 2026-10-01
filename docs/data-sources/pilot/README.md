# P5 Pilot Source Gate

P5-A source reviews are stored separately for each region. A source is eligible only after a reviewer has documented the owner, jurisdiction, exact permitted fields, access method, robots policy, terms, automation, storage, redistribution, attribution, and rate limits. If any essential right is unclear, decision stays `UNKNOWN` and P2 keeps the catalog row pending.

An `APPROVED` document alone does not change database state. A separately reviewed catalog change must set `status=approved`, `access_policy=automated_access_allowed`, non-empty use basis and permitted fields. The existing P2 `SourcePolicy` remains the runtime authorization gate. A provider review is separate; coordinates cannot be persisted unless its database policy explicitly allows persistent storage.

## First-round query-entry reviews (preserved)

- Beijing health-institution query entry: `UNKNOWN`; this finding is preserved.
- Guangdong health-institution query entry: `UNKNOWN`; this finding is preserved.

## Second-round open-data platform reviews

- Beijing `医院`: `APPROVED` for bounded, registered-user official-file import; 15,191 published rows, names only, and not selected for this pilot import.
- Beijing `定点医疗机构信息`: `APPROVED` for bounded, registered-user official-file import; 4,877 rows and six listed fields. This is the selected Beijing pilot dataset.
- Shenzhen `宝安区-医院基本信息`: `APPROVED` for a bounded registered-user file import; 27 archived records from Bao'an only. This is the selected Shenzhen sample, not Guangdong-wide coverage.
- Beijing permits free dissemination with attribution. Shenzhen prohibits all paid or unpaid transfer of platform data and requires deletion/cessation if the dataset is taken offline.
- Portal accounts are required for dataset downloads/API access. No authorized portal account or downloaded source file is available in this execution environment; therefore the approved catalog rows do not imply that data have been imported.

The dataset-specific rights, exact mappings, scope, freshness, and access requirements are documented in the individual review files in `beijing/` and `shenzhen/`.

Current execution gate:

- Both platform agreements qualify source use, but no registered-user export is available to the collector. P5 real-data import and manual QA are blocked pending official files obtained by an authorized platform user.
- AMap geocoder: blocked for persistent coordinate storage until specific written authorization is obtained.
- P5-B: file and API adapter framework is implemented. API access is not enabled for the reviewed `manual_only` sources. Real source rows and coordinates have not been imported.

The P4 quota and pacing guard is per pipeline process/run. Before enabling any real geocoder across concurrent workers, serialize executions or add shared quota reservation and rate limiting; independent processes can otherwise exceed an account-wide provider policy in aggregate.

The `run` command supports only the reviewed Beijing and Bao'an file mappings. File imports require the matching catalog source to be `approved` and `manual_only`, an exact region (`110000` for Beijing, `440306` for Bao'an), an explicit limit of at most 150, and `PILOT_REAL_DATA=true`. A database trigger caps the shared pilot group at 300 source snapshots. `manual_only` sources are rejected by the HTTP adapter policy. Use `run --source fixture` only for synthetic development; fixture output must not be presented as real pilot data.

## Approval evidence needed to unblock

Have an authorized portal user download the selected official file and provide it through a secure, non-repository path. Verify the platform terms and dataset metadata again immediately before import, run a dry-run first, then import no more than 150 Beijing rows and all 27 Bao'an rows (177 total). Perform manual QA on at least 50 Beijing rows and every available Shenzhen row. Do not commit the real source files. Before public application release, add source attribution in the UI and complete any platform application filing requirements.
