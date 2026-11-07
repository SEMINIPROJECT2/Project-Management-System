# System Validation Report

Execution: 2026-11-06T17:46:12.589413+00:00 (GitHub Actions). Python 3.12.16, Django 5.2.19, SQLite. Source revision: `de496554513c8ce0ba146965949f9c16eb6a01ed`.

Platform: Linux-7.0.0-1019-azure-x86_64-with-glibc2.43. The Part 3 test settings create and destroy a separate on-disk database; development data is not used.

## Executed test-plan validation

135 unique test methods verified across functional/coverage and separate untraced performance runs: 135 passed, 0 unexecuted/skipped, 0 failures and 0 errors. Combined runner time: 75.307 seconds.

| Case | Requirements | Scenario | Actual outcome |
| --- | --- | --- | --- |
| TC-01 | FR-01 | Registration | PASS |
| TC-02 | FR-02 | Authentication | PASS |
| TC-03 | FR-03 | Project creation | PASS |
| TC-04 | FR-04, SR-01 | Membership and roles | PASS |
| TC-05 | FR-05 | Task creation | PASS |
| TC-06 | FR-06, SR-01 | Task edit permissions | PASS |
| TC-07 | FR-07, FR-13 | Kanban workflow | PASS |
| TC-08 | FR-08 | Combined filters | PASS |
| TC-09 | FR-09 | Effort estimates | PASS |
| TC-10 | FR-10, FR-11 | Time lifecycle | PASS |
| TC-11 | FR-11 | Dashboard | PASS |
| TC-12 | FR-12, FR-14 | Comments and search | PASS |
| TC-13 | FR-15, FR-16 | CSV and archive | PASS |
| TC-14 | FR-17 | Notifications | PASS |
| TC-15 | SR-02, SR-03, SR-04, SR-05 | Security | PASS |
| TC-16 | NFR-01, NFR-02 | Capacity and load | PASS |
| TC-17 | NFR-03 | Persistence and rollback | PASS |
| TC-18 | NFR-04, NFR-05, NFR-06 | Browser and usability | PASS |

## Browser and keyboard execution

| Browser | Version | Viewport | Project actions | Task actions |
| --- | --- | --- | --- | --- |
| Chrome | 157.0.8103.38 | 1280x720 | 4 | 3 |
| Firefox | 157.0 | 1280x720 | 4 | 3 |

Actions are counted after sign-in/navigation: open a dialog, fill a field and
submit each count once. Project creation includes an optional description
field (4 actions); minimal task creation uses 3. Keyboard checks activate a
card with Enter, change status using arrows and Tab, and close using Escape.
Font-CDN requests are aborted so external font availability does not control
the local workflow. Other application content is unchanged.

## Required concurrent HTTP load

| Endpoint | HTTP samples | p95 seconds | Maximum seconds |
| --- | --- | --- | --- |
| board | 50 | 0.2234 | 0.2481 |
| tasks | 50 | 1.2108 | 1.2311 |

The fixture contains 500 tasks, 20 members and 2000 events. Twenty authenticated
workers each send five requests through a live threaded HTTP server, for 100
requests total. The test server's TCP connection backlog is explicitly 64,
so the burst is admitted without the development server's default 10-slot
backlog causing SYN retries. This is not the earlier sequential Django-client benchmark.
The task response retains all 500 tasks; exact activity ID equality is checked
by the separate capacity regression. Timings are local/CI qualification results,
not a production SLA or distributed-user measurement.

## Acceptance and limits

Executed test-plan gate: **PASS**.
The original plan spans FR-01..17, NFR-01..06 and SR-01..05. The matrix records
functional case outcomes; statement/branch coverage is reported independently.
No unexecuted browser is treated as passed. No assertion here establishes
power-loss durability, production load capacity, PostgreSQL behavior or formal
WCAG conformance. The restart check starts fresh Django application processes,
not an operating-system reboot.

[Functional/coverage log](evidence/full_test_run.txt), [untraced performance log](evidence/performance_run.txt), [named outcomes](evidence/test_results.json), [environment/commands](evidence/environment.json). The functional run deliberately skips the two opt-in performance methods, which are then executed separately; these placeholders are replaced by their measured outcomes, not counted as additional unique tests.


## Additional execution environment and historical results

The complete qualification above is the hosted run at
https://github.com/SaquinSauron/Project-Management-System/actions/runs/42264295208
for source `de496554513c8ce0ba146965949f9c16eb6a01ed`.

A separate local sandbox run passed its functional checks but could not launch
Chrome because the operating system denied its process-singleton socket.
Firefox passed locally. Its untraced 20-user workload measured task-list p95
2.4134 seconds, above the 2-second criterion; board p95 was 0.4811 seconds.
This local timing failure is retained in [local evidence](evidence/local_run/),
not counted as a hosted pass or suppressed. The hosted workload passed with
board p95 0.2234 seconds and task-list p95 1.2108 seconds. Performance acceptance
is therefore established for the recorded hosted qualification environment,
not every machine. Both environments used the same application changes.
