# Test results and traceability — Iteration 2

Execution date: 28 October 2026 (Asia/Calcutta).
Scope: #9, #10, #19, #20, #40 and #41, assigned to SaquinSauron.
Base main: `5e45107c2b84f8208d64e39a3f17dd67d3cfca91`.
Environment: Windows, Python 3.13.14, Django 5.2.18, SQLite; isolated virtual environment installed from requirements.txt.

## Executed commands and observed results

### Demo-delivery re-verification — 29 October 2026

Merged build `4c853b9` was re-tested on Linux, Python 3.12, Django 5.2.18,
SQLite: **133 discovered, 130 passed, 3 skipped, 0 failures/errors in 81.196 s**.
The three skips are the optional performance test and Chrome/Firefox workflows.
[Fresh full output](test-evidence/demo-delivery-tests.txt).
The previous Windows execution and separate performance measurement below are
retained as historical evidence; their environment/timings do not describe
this new run. Fresh demo API results and independently repeated restart and
failure-injection checks are included in [the demo artifacts](ITERATION_2_DEMO_GUIDE.md).

Local test configuration: `DJANGO_DEBUG=True`, `ALLOWED_HOSTS=testserver,localhost,127.0.0.1`; no production secret is needed in this local configuration.

| Command | Observed result | Evidence |
| --- | --- | --- |
| `python manage.py test --verbosity=2` | 133 discovered; 130 passed; 3 skipped; 0 failures/errors; 397.531 s | [Full execution log](test-evidence/iteration2-full-tests.txt) |
| `RUN_PERFORMANCE_TESTS=1 python manage.py test tests.test_board_performance --verbosity=2` | 1 test passed in 10.165 s | [Performance log](test-evidence/iteration2-performance-tests.txt) |
| `python manage.py check` | No issues, 0 silenced | Local execution |
| `python manage.py makemigrations --check --dry-run` | No changes detected; no schema migration required | Local execution |
| `git diff --check` | Passed | Local execution |

The initial targeted run discovered 9 new tests: 8 passed and 1 errored because the test attempted to set the read-only `Project.is_archived` property. The test setup was corrected to set `archived_at`. This was a test fixture defect, not an application failure; the final full-run evidence supersedes that exploratory run.

## Scoped requirement-to-test matrix

All test names below are in [test_iteration2_effort_reliability.py](../tests/test_iteration2_effort_reliability.py).

| Issue / requirement | Test method | Expected behavior and actual result |
| --- | --- | --- |
| #9 / FR-09 / TC-09 | `test_estimate_rejects_invalid_create_and_edit_without_writes` | NaN/sNaN/infinities, negative, wrong-step, storage overflow, huge/tiny exponents and malformed inputs return 400; no task, version or audit changes. PASS. |
| #9 / FR-09 | `test_estimate_boundaries_and_authorized_roles` | Owner/Manager create and edit at 0, 0.5 and 9999.5; stored values match; Member denied 403, outsider 404. PASS. |
| #10 / FR-10 / TC-10 | `test_time_invalid_hours_dates_notes_create_and_edit` | Invalid quarter-hour, storage, non-finite, date and note inputs reject create/edit with 400; original entry and audit counts unchanged. PASS. |
| #10 / FR-10 | `test_time_lifecycle_date_changes_notes_and_totals` | Log 1.25 + 0.75 = 2; edit to 2.5 with changed date/note gives 3.25; omitted date/note retained; max 999.75 works; delete leaves 0.75 in task/detail/dashboard. PASS. |
| #10 / FR-10 | `test_time_ownership_scope_archival_and_forged_owner` | Caller owns newly created entry despite forged user ID; other Owner/Manager cannot edit/delete; outsiders and wrong-task routes denied; archived writes rejected. PASS. |
| #10 / FR-10 | `test_time_json_shape_errors` | Malformed JSON and non-object time-log requests return 400. PASS. |
| #19 / NFR-02 / TC-16 | `test_capacity_returns_all_tasks_members_events_and_isolates_projects` | Exactly 500 tasks and 20 memberships; every expected task/member ID returned; all 2000 event IDs returned without duplicates/truncation, stable ordering, other project's event excluded, outsider denied. PASS. |
| #20 / NFR-03 / TC-17 | `test_endpoint_failure_rolls_back_tasks_entries_audit_and_notifications` | Inject failure after actual audit insertion in create/edit/time create/update/delete and after notification insertion during task create. Compare complete task/entry/audit/notification snapshots; all unchanged after failure. PASS. |
| #20 / NFR-03 | `RestartPersistenceTests.test_committed_api_updates_survive_new_application_process` | Writer process migrates temporary SQLite, commits API create/edit/time log, exits; reader starts independently and checks task title/version/estimate, actual total, date/note and audit actions. PASS. |
| #40 / DOC-02 | This report, matrix and raw logs | Executed results separated from skipped and missing evidence. Prepared. |
| #41 / DOC-03 | [Final report](FINAL_PROJECT_REPORT.md), [demonstration evidence and guide](ITERATION_2_DEMO_GUIDE.md) | Report, walkthrough, actual API source evidence and renderer included. Video binaries excluded at the user's request; video submission remains outside this change. |

## Performance observation

The separate opt-in test used 500 tasks, 20 members and 2000 activity events, 5 warmups and 40 samples per endpoint. Board HTML p95/max: 5.7/6.6 ms. Task-list p95/max: 206.5/209.1 ms. Both p95 values were below the existing 2000 ms threshold. These are local Django client timings, not network/browser or production load timings. The fixture's storage counts do not alone prove event retrievability; the new capacity test separately checks every event ID through the activity API.

## Skipped or unexecuted checks

- The default full run skips the opt-in performance method because `RUN_PERFORMANCE_TESTS` is unset. It was then run explicitly and passed, as recorded above.
- Chrome Stable and Firefox browser compatibility methods are opt-in (`RUN_BROWSER_TESTS=1` and Playwright). They were not executed in this environment. Rendered-template/accessibility tests do not substitute for those real browser workflows.
- Video files are not included in this change. The renderer and source evidence cover API execution and test output, not browser screen recordings or historical sprint captures. Browser criteria remain outside their evidence scope.
- PostgreSQL, production deployment/load, power-loss recovery, full HTTP server restart and manual keyboard/browser evaluation were not executed. The persistence test specifically verifies fresh Django processes and an on-disk SQLite database.
- Inherited TC-16 tests include smaller fixtures or database count checks; inherited TC-17 refresh/atomic tests do not demonstrate application restart. The new tests above supply the stronger evidence required here.

## Defects fixed in this iteration

| Defect | Fix | Regression evidence |
| --- | --- | --- |
| Non-finite decimal arithmetic could raise server exceptions | Reject non-finite values before comparisons/remainder | Invalid estimate/time input tests |
| Numeric inputs could exceed DecimalField storage bounds | Check 6,2 estimate and 5,2 time bounds before arithmetic/write | Boundary/overflow/extreme exponent cases |
| Time-entry edit silently ignored supplied date | Validate and persist date; return saved date and note | Lifecycle/date-change test |
| Non-text notes could raise errors or be stored unexpectedly | Reject non-text notes and consistently trim text | Invalid-note tests |
| Activity API silently returned only newest 100 events | Remove implicit cutoff and add ID tie-break ordering | All 2000 returned IDs compared |
| Historical reports claimed complete/100% verification despite gaps | Replace unsupported counts and distinguish scripts, recordings, skipped checks and actual tests | This report and raw evidence |

Existing transaction blocks passed the failure-injection checks, so no transaction behavior was changed. Existing teammate tests and application features were retained. Earlier historical all-requirements completion claims in other documents are not evidence for checks skipped or missing in this run.
