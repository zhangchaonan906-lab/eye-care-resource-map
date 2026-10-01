# P5 Pilot Source Gate

P5-A source reviews are stored separately for each region. A source is eligible only after a reviewer has documented the owner, jurisdiction, exact permitted fields, access method, robots policy, terms, automation, storage, redistribution, attribution, and rate limits. If any essential right is unclear, decision stays `UNKNOWN` and P2 keeps the catalog row pending.

An `APPROVED` document alone does not change database state. A separately reviewed catalog change must set `status=approved`, `access_policy=automated_access_allowed`, non-empty use basis and permitted fields. The existing P2 `SourcePolicy` remains the runtime authorization gate. A provider review is separate; coordinates cannot be persisted unless its database policy explicitly allows persistent storage.

Current gate result:

- Beijing: `UNKNOWN`; no automated collection or storage authority established.
- Guangdong: `UNKNOWN`; no automated collection or storage authority established.
- AMap geocoder: blocked for persistent coordinate storage until specific written authorization is obtained.
- P5-B: not started. No adapter is enabled and no real-source fixture has been captured.

The P4 quota and pacing guard is per pipeline process/run. Before enabling any real geocoder across concurrent workers, serialize executions or add shared quota reservation and rate limiting; independent processes can otherwise exceed an account-wide provider policy in aggregate.

The CLI accepts only pilot region codes `110000` and `440000`, requires `--limit`, and checks `PILOT_REAL_DATA=true`. These are additional safety checks; they do not approve a source. Until the review gate and a source adapter are approved, the command fails closed before database access or network activity. Use the existing `run --source fixture` command only for synthetic pipeline development; fixture output must not be included in production pilot reports.

## Approval evidence needed to unblock

Obtain a written owner response or applicable license that explicitly covers automated access, permitted fields, persistent storage, external display/redistribution, attribution and request limits. Record the proof and reviewer/date in the regional review. Separately qualify coordinate system and persistence rights for any real geocoder. Then implement and fixture-test one adapter per approved source, retain raw snapshots and source URLs, and only then schedule a bounded `--limit` run.
