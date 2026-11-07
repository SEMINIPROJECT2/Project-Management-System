# Branch Coverage Report

Execution: 2026-11-06T17:46:12.589413+00:00 (GitHub Actions). Python 3.12.16, Django 5.2.19, SQLite. Source revision: `de496554513c8ce0ba146965949f9c16eb6a01ed`.

Platform: Linux-7.0.0-1019-azure-x86_64-with-glibc2.43. The Part 3 test settings create and destroy a separate on-disk database; development data is not used.

Branch-outcome coverage: **76.49%**
(231 / 302 measured Python branch outcomes).
Partially exercised branch locations: 53.

## Measurement scope

Coverage includes Python application modules in accounts, projects, tasks, audit, notifications and config. Only generated migration modules are excluded. Tests, vendored Django/Playwright, JavaScript, CSS and templates are outside the Python coverage denominator. Browser execution is measured by functional assertions rather than Python line coverage. Subprocess tracing is enabled and the child data is combined. Latency tests run separately without tracing so coverage overhead does not distort application timing. No missing branch is excluded merely to increase the percentage.

| Module | Covered outcomes | All outcomes | Branch coverage | Partial locations | Missing arcs |
| --- | --- | --- | --- | --- | --- |
| accounts/__init__.py | 0 | 0 | N/A | 0 | - |
| accounts/admin.py | 0 | 0 | N/A | 0 | - |
| accounts/apps.py | 0 | 0 | N/A | 0 | - |
| accounts/models.py | 8 | 18 | 44.44% | 6 | 9->10; 25->26; 25->27; 27->28; 27->30; 73->74; 96->97; 107->108; 117->119; 123->-121 |
| accounts/urls.py | 0 | 0 | N/A | 0 | - |
| accounts/views.py | 34 | 46 | 73.91% | 8 | 12->13; 24->25; 27->28; 31->32; 44->45; 46->47; 46->48; 51->52; 53->54; 53->55; 61->62; 70->71 |
| audit/__init__.py | 0 | 0 | N/A | 0 | - |
| audit/admin.py | 0 | 0 | N/A | 0 | - |
| audit/apps.py | 0 | 0 | N/A | 0 | - |
| audit/models.py | 0 | 0 | N/A | 0 | - |
| audit/services.py | 0 | 0 | N/A | 0 | - |
| audit/urls.py | 0 | 0 | N/A | 0 | - |
| audit/views.py | 0 | 0 | N/A | 0 | - |
| config/__init__.py | 0 | 0 | N/A | 0 | - |
| config/asgi.py | 0 | 0 | N/A | 0 | - |
| config/settings.py | 22 | 22 | 100.00% | 0 | - |
| config/urls.py | 0 | 0 | N/A | 0 | - |
| config/wsgi.py | 0 | 0 | N/A | 0 | - |
| notifications/__init__.py | 0 | 0 | N/A | 0 | - |
| notifications/admin.py | 0 | 0 | N/A | 0 | - |
| notifications/apps.py | 0 | 0 | N/A | 0 | - |
| notifications/context_processors.py | 2 | 2 | 100.00% | 0 | - |
| notifications/models.py | 0 | 0 | N/A | 0 | - |
| notifications/services.py | 1 | 2 | 50.00% | 1 | 8->15 |
| notifications/urls.py | 0 | 0 | N/A | 0 | - |
| notifications/views.py | 3 | 6 | 50.00% | 3 | 10->23; 31->33; 39->41 |
| projects/__init__.py | 0 | 0 | N/A | 0 | - |
| projects/admin.py | 0 | 0 | N/A | 0 | - |
| projects/apps.py | 0 | 0 | N/A | 0 | - |
| projects/models.py | 0 | 0 | N/A | 0 | - |
| projects/permissions.py | 16 | 20 | 80.00% | 4 | 13->14; 46->48; 52->54; 67->69 |
| projects/urls.py | 0 | 0 | N/A | 0 | - |
| projects/views.py | 34 | 50 | 68.00% | 12 | 40->41; 41->42; 41->43; 93->94; 139->141; 156->157; 185->187; 201->202; 208->210; 215->217; 279->281; 283->290; 292->293; 300->308; 321->322; 321->328 |
| tasks/__init__.py | 0 | 0 | N/A | 0 | - |
| tasks/admin.py | 0 | 0 | N/A | 0 | - |
| tasks/apps.py | 0 | 0 | N/A | 0 | - |
| tasks/models.py | 4 | 4 | 100.00% | 0 | - |
| tasks/urls.py | 0 | 0 | N/A | 0 | - |
| tasks/views.py | 107 | 132 | 81.06% | 19 | 65->67; 92->94; 99->101; 105->106; 112->114; 120->122; 133->134; 133->135; 192->193; 204->205; 219->220; 303->309; 315->316; 331->332; 335->336; 341->342; 343->344; 343->345; 355->370; 360->372; 419->431; 469->471; 556->557; 556->558; 559->560 |

## Reading the results

Each `start->end` pair is a missing control-flow arc; a negative endpoint can
represent function exit in coverage.py. A module without measurable branches
is N/A, not 100%. Negative/positive validation, role rejection, archived writes,
conflict, invalid dates, extreme decimals and rollback paths are exercised by
the regression suite. Remaining arcs above are the next targeted-test backlog.
This is Python branch coverage, not JavaScript coverage, MC/DC, path coverage
or proof of every possible input combination.

[Machine-readable arcs](evidence/coverage.json) and [HTML inspection](coverage_html/index.html).
