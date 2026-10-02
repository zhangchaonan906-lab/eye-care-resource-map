# P13 Coverage and Real-Data Status

Date: 2026-10-03.

## Evidence stages

The project distinguishes discovery, file inspection, import, candidate processing, and publication. Counts at one stage do not imply completion of a later stage.

| Stage | Current evidence | What it means |
|---|---|---|
| Source discovery | P6-N1 first-pass review covered 31/31 mainland provincial planning units and listed official leads | Discovery only; not proof of exhaustive source coverage |
| File inspected | Tianjin municipal registration file: 36 rows, 7 exact fields, 4 rows with explicit eye evidence | Source-scope unknown; not proven complete Tianjin coverage |
| Separate district lead | Xiqing registration dataset appears in 2023 public-data plan | `district_only`; current detail page/file/schema unverified; no inherited Tianjin municipal row count or evidence |
| Historical real imports | P5 pilot reports Beijing 50 and Shenzhen 27 source rows; historical ETL report has 74 source records and 72 candidates | Historical processing evidence only; not a current published sample |
| Current production database | No production database credentials/configuration were present in this task environment | Current source/candidate/published counts cannot be queried safely from this checkout |
| Current published real sample | Not available for P13 review | No real accuracy rate is calculated; P0 thresholds remain open |

## Real-data gates

| Gate | Required sample | P13 evidence | Status |
|---|---:|---|---|
| Published ophthalmology evidence precision | At least 100 published real facilities; precision ≥98%; severe misclassification 0 | No current published real sample available | PENDING |
| Duplicate review / automatic matching | At least 50 groups each; zero erroneous automatic merges; no cross-campus merge | Synthetic and historical integration checks are not a real-world sample | PENDING |
| Coordinate locality | At least 50 real verified coordinates per tested region; zero wrong-city/district; no ambiguous publication | Only fixture coordinates used in P13 | PENDING |
| National source coverage | Verified coverage by source and region | 31/31 first-pass discovery is not national data coverage | PENDING |

Historical P5 files and candidates are not current public facilities and cannot be used to satisfy P13 accuracy thresholds. P13 performed no real-data import, approval change, geocoder call, coordinate persistence, or facility publication.
