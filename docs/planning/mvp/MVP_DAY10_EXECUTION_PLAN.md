# Focus Guard MVP Day 10 Execution Plan

## Day 10 Objective
Improve metrics historical usability: normalize schema/timestamp expectations and expose stable date-range query paths for dashboard analytics.

## Workstream
- **D) Metrics usability and historical access** (Week 2 required)

## Tasks
- [ ] Audit metrics/analytics timestamp semantics in tab-server logging paths (UTC contract, field naming, units).
- [ ] Add or refine date-range query endpoints used by admin dashboard services.
- [ ] Add missing indexes or query guards for week/month-scale reads.
- [ ] Update dashboard service aggregation logic to consume stable range-query contracts.
- [ ] Add/extend tests for:
  - day/week/month range queries
  - empty ranges and edge bounds
  - backward compatibility with existing local data
- [ ] Update docs (`MVP_TEST_MATRIX.md` and/or short note in Week 2 docs) with new query contract coverage.

## Implementation notes
- Keep this sprint local-first: do not require central DB migration.
- Prioritize query correctness and explainability over broad API expansion.
- If historical anomalies are discovered (e.g., clock skew artifacts), document handling strategy.

## Validation checklist
- [ ] API returns consistent data for day/week/month requests.
- [ ] Dashboard summaries align with direct API outputs for same windows.
- [ ] Query performance remains acceptable for typical local retention sizes.
- [ ] Tests cover both happy path and boundary cases.

## Files expected to change
- `focus_guard/core/browser_v2/tab_server/activity_logger.py`
- `focus_guard/core/admin_gateway/routers/activity.py`
- `focus_guard/core/admin_gateway/services/dashboard_service.py`
- Related tests for metrics/activity/dashboard
- `docs/planning/mvp/MVP_TEST_MATRIX.md` (if matrix updates are needed)

## Exit criteria
Day 10 is done when historical metrics can be queried reliably by date range and consumed by dashboard/reporting without ad-hoc interpretation.
