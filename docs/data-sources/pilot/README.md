# P5 Pilot Source Gate and Status

> **Status note (2026-10-02):** this file replaces an outdated pre-import status summary. The earlier statements that no official files/imports existed were superseded by the completed local P5 pilot documented in [`../../operations/p5-real-pilot-final-report.md`](../../operations/p5-real-pilot-final-report.md). The final report is historical pilot evidence; it does not mean records are present in the current P11 application database or published.

## Current P5 facts

- The final P5 report records 50 Beijing source rows and all 27 Shenzhen Bao'an rows imported into a separate local pilot database; P3 ETL created 72 candidates and 8 duplicate-review cases.
- The P5 pilot database recorded 0 facilities and 0 facility locations. No geocoder was called and no production coordinate was stored.
- The current local P11 application database is separate. The P14-B read-only check found 0 source snapshots, 0 candidates, and 0 published facilities there.
- Source rows remain subject to each source's own fields, region, attribution, retention, withdrawal, and transfer restrictions. A historical local pilot is not authorization to move records into another database or public application.

## Catalog and use policy

An `APPROVED` source review is distinct from runtime access. These P5 sources remain `manual_only`; no automated collection or P12 schedule is authorized by this document. Source approval must be based on the exact dataset, operator, fields, allowed operations, terms, retention, attribution, and withdrawal conditions.

- Beijing “医院”: catalog review is approved for name-only fields; its catalog source-update date is 2024-11-20 and must be refreshed before production consideration.
- Beijing “定点医疗机构信息”: catalog review is approved for the bounded manual-file pilot and records rights metadata. The broad platform-use interpretation and cross-environment transfer for production still require a current rights review.
- Shenzhen Bao'an “医院基本信息”: catalog review is approved for the bounded manual-file pilot; raw transfer/redistribution is restricted and withdrawal requires deletion. The prior 27-row dataset is Bao'an-only and is not current P11 application data.

See the [P14-B source-readiness review](../../operations/p14-production-readiness.md#4-real-data) before any new use. Do not change source state or activate a source based on this README.
