# Code Coverage Report

Execution: 2026-11-06T17:46:12.589413+00:00 (GitHub Actions). Python 3.12.16, Django 5.2.19, SQLite. Source revision: `de496554513c8ce0ba146965949f9c16eb6a01ed`.

Platform: Linux-7.0.0-1019-azure-x86_64-with-glibc2.43. The Part 3 test settings create and destroy a separate on-disk database; development data is not used.

Statement coverage: **87.39%**
(970 / 1110 executable Python statements).
This is the statement-only calculation, not coverage.py's blended line/branch percentage.

## Measurement scope

Coverage includes Python application modules in accounts, projects, tasks, audit, notifications and config. Only generated migration modules are excluded. Tests, vendored Django/Playwright, JavaScript, CSS and templates are outside the Python coverage denominator. Browser execution is measured by functional assertions rather than Python line coverage. Subprocess tracing is enabled and the child data is combined. Latency tests run separately without tracing so coverage overhead does not distort application timing. No missing branch is excluded merely to increase the percentage.

| Module | Covered | Statements | Statement coverage | Missing lines |
| --- | --- | --- | --- | --- |
| accounts/__init__.py | 0 | 0 | N/A | - |
| accounts/admin.py | 16 | 16 | 100.00% | - |
| accounts/apps.py | 4 | 4 | 100.00% | - |
| accounts/models.py | 69 | 83 | 83.13% | 10, 21, 22, 23, 25, 26, 27, 28, 30, 45, 74, 97, 108, 119 |
| accounts/urls.py | 4 | 4 | 100.00% | - |
| accounts/views.py | 90 | 114 | 78.95% | 13, 25, 28, 32, 33, 34, 35, 36, 37, 38, 45, 46, 47, 48, 49, 52, 53, 54, 55, 56, 62, 71, 99, 100 |
| audit/__init__.py | 0 | 0 | N/A | - |
| audit/admin.py | 8 | 8 | 100.00% | - |
| audit/apps.py | 4 | 4 | 100.00% | - |
| audit/models.py | 15 | 17 | 88.24% | 26, 27 |
| audit/services.py | 3 | 3 | 100.00% | - |
| audit/urls.py | 4 | 4 | 100.00% | - |
| audit/views.py | 9 | 9 | 100.00% | - |
| config/__init__.py | 0 | 0 | N/A | - |
| config/asgi.py | 0 | 4 | 0.00% | 1, 2, 4, 5 |
| config/settings.py | 73 | 73 | 100.00% | - |
| config/urls.py | 4 | 4 | 100.00% | - |
| config/wsgi.py | 0 | 4 | 0.00% | 1, 2, 4, 5 |
| notifications/__init__.py | 0 | 0 | N/A | - |
| notifications/admin.py | 7 | 7 | 100.00% | - |
| notifications/apps.py | 4 | 4 | 100.00% | - |
| notifications/context_processors.py | 6 | 6 | 100.00% | - |
| notifications/models.py | 12 | 13 | 92.31% | 20 |
| notifications/services.py | 4 | 5 | 80.00% | 15 |
| notifications/urls.py | 4 | 4 | 100.00% | - |
| notifications/views.py | 25 | 28 | 89.29% | 23, 33, 41 |
| projects/__init__.py | 0 | 0 | N/A | - |
| projects/admin.py | 16 | 16 | 100.00% | - |
| projects/apps.py | 4 | 4 | 100.00% | - |
| projects/models.py | 30 | 32 | 93.75% | 27, 55 |
| projects/permissions.py | 38 | 42 | 90.48% | 14, 48, 54, 69 |
| projects/urls.py | 4 | 4 | 100.00% | - |
| projects/views.py | 125 | 158 | 79.11% | 28, 29, 41, 42, 43, 44, 94, 141, 142, 157, 187, 188, 193, 194, 202, 210, 211, 217, 218, 281, 286, 287, 290, 293, 308, 309, 310, 311, 312, 321, 322, 328, 329 |
| tasks/__init__.py | 0 | 0 | N/A | - |
| tasks/admin.py | 23 | 23 | 100.00% | - |
| tasks/apps.py | 4 | 4 | 100.00% | - |
| tasks/models.py | 61 | 64 | 95.31% | 72, 91, 107 |
| tasks/urls.py | 4 | 4 | 100.00% | - |
| tasks/views.py | 296 | 341 | 86.80% | 34, 35, 67, 68, 94, 95, 101, 102, 106, 114, 115, 122, 123, 131, 132, 133, 134, 135, 136, 193, 205, 220, 306, 307, 309, 316, 332, 336, 342, 343, 344, 345, 367, 368, 370, 409, 410, 471, 555, 556, 557, 558, 560, 608, 609 |

## Reproduction and interpretation

Run `python scripts/run_part3_tests.py` after installing `requirements-test.txt`
and browser dependencies. The same run exports [coverage JSON](evidence/coverage.json),
[XML](evidence/coverage.xml), [text summary](evidence/coverage_summary.txt) and
[interactive HTML](coverage_html/index.html). Coverage below 100% is retained
honestly; executed coverage does not prove absence of defects or assertion quality.
