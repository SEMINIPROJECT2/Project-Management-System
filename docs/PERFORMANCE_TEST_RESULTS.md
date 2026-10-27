# NFR-01: Board Response-Time Performance

**Issue:** #18 — 95% of board and task-list requests should complete within 2 seconds.

## Local Benchmark Results

**Date:** 26 October 2026

| Measurement | Board HTML | Task-list JSON |
|---|---:|---:|
| Warm-up requests | 5 | 5 |
| Measured requests | 40 | 40 |
| Observed p95 latency | 8.4 ms | 427.6 ms |
| Observed maximum latency | 8.5 ms | 489.7 ms |
| Threshold | 2,000 ms | 2,000 ms |
| Local result | Pass | Pass |

## Test Conditions

- 500 tasks, 20 project members, and 2,000 activity events.
- Five warm-up requests followed by 40 measured requests per endpoint.
- Latency measured using Python time.perf_counter().
- p95 calculated using the nearest-rank method.
- The board measurement covers the project detail HTML request.
- The task-list measurement covers the project-scoped JSON endpoint.
- The test verifies that all 500 tasks are returned.

## Reproduce the Benchmark

Run from the project root in PowerShell:

    $env:RUN_PERFORMANCE_TESTS = "1"
    python manage.py test tests.test_board_performance --verbosity=2
    Remove-Item Env:RUN_PERFORMANCE_TESTS

## Limitations

These results were measured locally using Django's in-process test client
and an in-memory SQLite test database. They exclude real network latency,
browser rendering, and production deployment overhead. The hardware
configuration and concurrent-user load were not recorded.

The results meet the numerical threshold for this local test run, but do
not by themselves prove production SLA compliance. Repeat testing in the
required SRS environment before making a production performance guarantee.
