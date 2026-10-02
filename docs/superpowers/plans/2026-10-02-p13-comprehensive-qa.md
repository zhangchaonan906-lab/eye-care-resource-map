# P13 Comprehensive QA Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add repeatable synthetic system QA for the existing P1–P12 application and document real-data and production release gates without importing real data or adding product features.

**Architecture:** Reuse the repository's disposable PostGIS provisioning, runtime roles, fixture source and migration test harness. Add a small Playwright layer for direct browser routes and keyboard/a11y checks, run local-only fixtures, and preserve the existing unit/database/Collector jobs. Report unverified large-scale, real-data, and deployment properties as pending instead of simulating their evidence.

**Tech Stack:** Next.js 16, TypeScript, Vitest, Playwright, axe-core, PostgreSQL/PostGIS 17, Python pytest, GitHub Actions.

---

## File map

- Create `apps/web/playwright.config.ts` and `apps/web/e2e/` for local browser route, public-boundary and accessibility smoke coverage.
- Modify `apps/web/package.json` and lockfile for the minimal Playwright/axe test dependencies and commands.
- Modify `.github/workflows/collector.yml` to add isolated web E2E and accessibility jobs with local-only synthetic fixtures and failure-only artifacts.
- Create `docs/operations/p13-qa-matrix.md`, `p13-performance.md`, `p13-coverage-status.md`, and `p13-qa-report.md` with evidence-backed status and explicit pending production gates.
- Create this plan at `docs/superpowers/plans/2026-10-02-p13-comprehensive-qa.md`.
- Modify application code only where a failing P13 test demonstrates a concrete accessibility, privacy, public-boundary, or error-recovery defect; put a regression test first.

## Task 1: Baseline and scope ledger

- [ ] Verify clean branch base is P12 merge `fa3e2d37b999c12655ff3a1e1cd5088e898b903c`.
- [ ] Run existing Web unit, typecheck, lint and build; Collector unit, Ruff and mypy; P1–P12 disposable database test.
- [ ] Record any baseline failure before changing project code.
- [ ] Create the QA matrix with every requested area mapped to an executable test or an explicit `PENDING_REAL_DATA` / `BLOCKED` reason.

## Task 2: Browser test harness

- [ ] Add the smallest Playwright and axe dependencies and scripts to `apps/web/package.json`.
- [ ] Add deterministic Playwright configuration for Chromium, local web server startup, trace-on-first-retry, and no arbitrary sleeps.
- [ ] Add direct route smoke tests for the public map, detail, admin login and protected admin console, including invalid/unpublished detail behavior.
- [ ] Add map/list keyboard and detail-panel focus return assertions where current UI semantics support them.
- [ ] Run focused browser tests and fix only demonstrated product defects, writing a failing assertion before any behavior change.

## Task 3: Accessibility and public-boundary browser coverage

- [ ] Scan map, available detail route, admin login and authenticated/admin route states with axe-core; record exact critical/serious counts.
- [ ] Add keyboard-only route navigation, accessible-name and focus-visible checks for key map/search/list controls.
- [ ] Add browser assertions that private identifiers do not yield private facility content and only public API responses are rendered.
- [ ] Check XSS-like facility text is rendered as text and source links use HTTPS before rendering as links.

## Task 4: CI isolation and artifact hygiene

- [ ] Add separate Playwright and Accessibility CI jobs using synthetic/local data only.
- [ ] Upload traces/screenshots only on failure and run a secret-pattern scan on any produced artifact before upload.
- [ ] Keep existing Collector and database CI jobs intact; use only a single infrastructure retry if browser provisioning itself is flaky.

## Task 5: Evidence, performance and release-gate reports

- [ ] Populate the matrix with fresh local command output and browser/database evidence; use `NOT_APPLICABLE` only where the requirement truly does not apply.
- [ ] Record structural query/index observations and available local reference timings; mark 5,000-row EXPLAIN/benchmark pending if the environment or existing API prevents a trustworthy run.
- [ ] Inspect the current local database only if configured as disposable; never connect to or mutate production. Count currently published real facilities without changing data; below 100 means accuracy `PENDING_INSUFFICIENT_PUBLISHED_SAMPLE`.
- [ ] Separate discovered, inspected, imported, candidate and published coverage in the coverage document, and audit map copy for unsupported national-completeness claims.
- [ ] Report system QA, real-data QA, and release blockers independently. Keep production basemap, coordinate provider, access-log query redaction, source coverage and real data quality pending until deployment/source evidence exists.

## Task 6: Full verification and delivery

- [ ] Run Playwright, axe, Collector, P1–P12 database, Web unit/database, Ruff, mypy, TypeScript, lint, build, dependency audit and `git diff --check`.
- [ ] Inspect git diff and secret scan; confirm no real data import, source approval, geocoder, production basemap, facility publication, or P14 implementation was introduced.
- [ ] Commit the P13 work on `p13-comprehensive-qa`, push, and create PR `完成端到端、可访问性与综合质量验收（P13）` targeting `main`.
- [ ] Wait for GitHub Actions and report exact evidence; do not call the overall P13 status PASS while real-data gates remain pending.

## Known validation limits to preserve

- A browser-only mock cannot be called the requested database-backed golden E2E; label a flow accurately by the layers it actually exercises.
- P5 historical candidates are not current published accuracy samples.
- Synthetic truth-set results must never be represented as real-world precision or national coverage.
- P14 deployment and production-public-launch gates remain distinct.
