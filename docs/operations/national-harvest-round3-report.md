# National Harvest Round 3 Report

Round 3 expanded official-source discovery to every mainland provincial unit and a selected set of cities, with additional attention to explicit ophthalmology evidence. This report records the Round 3 results available at closeout; it does not authorize source approval, production import, or publication.

## Recorded results

| Measure | Round 3 | Rounds 2–3 cumulative |
|---|---:|---:|
| Mainland provincial units searched | 31 | 31 |
| Selected city/municipality follow-ups | 79 | — |
| Official source lead entries | 15 | — |
| Official XLSX datasets acquired | 10 | 18 |
| Source rows | 7,299 | 14,734 |
| Fresh rows under the harvest freshness convention | — | 8,253 |
| Stale rows | — | 6,481 |
| Explicit eye-evidence records | 98 | Not fully cross-round deduplicated |

Round 3's 98 structured eye-evidence rows came from explicit diagnostic-subject fields in two Guangzhou XLSX files. One additional historical official Nanjing Drum Tower licensing page explicitly listed ophthalmology; it is treated as dated page evidence, not as a current bulk record. The names from those rows were not merged into canonical facility entities.

The Round 3 acquisition records classify newly acquired sources as `UNKNOWN` / rights pending. Files were intended to remain in the user-local quarantine store. Production database writes, geocoder calls, and facility publication were zero.

## Search and checkpoint record

The completed pass covered 31 mainland provincial units and 79 selected city or municipality follow-ups. The recorded Round 3 summary contains 15 official lead entries and 10 acquired XLSX datasets. A five-unit checkpoint was recorded at 2026-10-03 11:57. Separate snapshots for the later 10/15/20/25/30-unit checkpoints were not retained; the final aggregate is available, but the original per-search transcript and a complete list of zero-result domains are not available in this closeout workspace.

On resuming this task, the Round 3 worktree had been removed and the configured external Round 2/Round 3 Harvest Store paths were absent. The figures above are preserved from the contemporaneous task record, but the original files and acquisition ledger could not be re-hashed or independently re-inspected during closeout. No source-specific filename, hash, or row-level data is recreated here.

## Provenance and coverage limits

- The 7,299 Round 3 rows are source rows, not unique hospitals or national coverage.
- The 14,734 cumulative source rows include overlap across sources; cross-round entity-level deduplication was not completed at Round 3 closeout.
- The 8,253 fresh and 6,481 stale cumulative figures use the documented convention that records dated on or after 2025-10-03 are fresh. The 2022 Hainan dataset accounts for the stale block.
- Guangzhou licensing sources are issuing-authority subsets, not a complete citywide facility census.
- Explicit eye evidence is not a measure of total ophthalmology coverage. Absence of evidence is not evidence that a facility lacks ophthalmology.
- No raw XLSX, raw HTML dump, or local Harvest Store file is included in Git.

## Code and regression coverage

The region-identity helper requires a six-digit administrative code and rejects recognized label/code conflicts. It covers the collision between `海南州` (Qinghai) and `海南省` (Hainan), preventing province assignment from relying on a shared text prefix alone. It does not infer missing administrative codes.

## Closeout limitations

Because the quarantine files and complete per-source ledger are unavailable in the current workspace, this closeout can preserve only the aggregate values above. Reacquiring those original files is required before any later row-level review or rights triage that depends on the missing acquisition artifacts. Round 4 may continue with fresh official searches and independently acquired files.
