# Optional Sprint 3 - testing spillovers

Date: 6 November 2026. Scope: qualification gaps found while executing Part 3.

1. A 500-task task-list request performed 504 queries because every task queried
   its own time-entry sum. The new bounded-query regression failed before the
   fix. Task-list and CSV querysets now annotate the aggregate once; the model
   retains its normal aggregation fallback for mutation/detail instances.
   Correct retained totals and a query limit are regression tested.
2. A successful status change updated the board but left the open task dialog's
   status text and active-task version stale. The UI now synchronizes that
   dialog after the successful response. Real keyboard browser checks verify
   the displayed status as well as the moved card.
3. The load harness uses a separate on-disk SQLite test database. The exploratory
   shared in-memory connection failed under threaded access; this was a harness
   artifact, not a demonstrated production database defect. No production
   database configuration was changed.

The original feature scope was retained. Development fixes and regression,
browser, load and coverage testing were completed as parallel Sprint 3 work.
See the current system report for actual outcomes and unresolved checks.
