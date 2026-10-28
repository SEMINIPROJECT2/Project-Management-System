# Iteration 2 demonstration guide

Status: script prepared; recordings NOT COMPLETE. No recording file or verified recording link is available. Use only fictional project and account data. Do not display personal names, student identifiers, real account details or secrets.

## Recording A — Estimates and time logging

1. Start the application with migrations applied, then sign in using fictional demo accounts with Owner, Manager and Member roles.
2. As Owner or Manager, create a task estimated at 2.5 hours. Show that 0 and 9999.5 are accepted, while -0.5, 0.25, NaN, Infinity and 10000 receive validation errors through the API. Show a Member cannot change the estimate.
3. As Member, log 1.25 hours dated 2026-10-20 with the note “Initial work”; log another 0.75. Show actual hours total 2.00 on the task detail and dashboard.
4. Through the time-entry API, PUT the first entry with hours 2.5, date 2026-10-21 and note “Revised work”. Read task detail again: the stored date/note changed and actual hours are 3.25. Explain that the board currently has no edit/date picker UI.
5. Attempt invalid quarter-hour inputs, malformed dates and non-text notes. Show HTTP 400 and unchanged stored values. As another user, attempt edit/delete and show HTTP 403. Delete as creator and show actual hours fall to 0.75.

## Recording B — Capacity, restart and rollback evidence

1. Run `python manage.py test tests.test_iteration2_effort_reliability --verbosity=2`.
2. Explain the capacity fixture: exactly 500 tasks, 20 members and 2000 activity events; test compares every returned ID, including events beyond the former 100-event cutoff.
3. Explain restart test: writer process migrates a temporary SQLite file, commits task create/edit and a time log, exits; reader process starts separately and checks title, version, estimate, time entry date/note, actual totals and audit actions.
4. Explain rollback test: failures are injected after audit/notification inserts in actual API operations; snapshots prove task/time entry, audit and notification rows are unchanged afterward.
5. Show the full test report and execution logs. Read the actual passed/skipped counts, and identify browser or other unexecuted checks explicitly. Do not claim all checks passed if skips exist.

## Completion checklist

- [x] Scoped walkthrough script prepared.
- [x] Final project report prepared.
- [ ] Recording A produced and reviewed.
- [ ] Recording B produced and reviewed.
- [ ] Required sprint recordings uploaded and working URLs linked here.

These unchecked items remain open under #41. No names or SRNs are required in the demo.
