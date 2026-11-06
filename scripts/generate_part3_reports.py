"""Generate the required reports from measured outcomes, not fixed pass counts."""
from collections import Counter
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'docs' / 'part3'
EVIDENCE = OUT / 'evidence'
results = json.loads((EVIDENCE / 'test_results.json').read_text())
coverage = json.loads((EVIDENCE / 'coverage.json').read_text())
environment = json.loads((EVIDENCE / 'environment.json').read_text())
records = results['records']
totals = coverage['totals']
counts = Counter(record['status'] for record in records)
unit = [r for r in records if r['id'].startswith(('tests.test_task_unit_rules.', 'tests.test_environment_configuration.'))]
browsers = [json.loads(p.read_text()) for p in sorted((EVIDENCE / 'browser').glob('*.json'))]
load_path = EVIDENCE / 'concurrent_load.json'
load = json.loads(load_path.read_text()) if load_path.exists() else None


def write(name, text):
    (OUT / name).write_text(text.strip() + '\n')


def percent(covered, total):
    return f'{100 * covered / total:.2f}%' if total else 'N/A'


def table(headers, rows):
    clean = lambda value: str(value).replace('|', '/').replace('\n', ' ')
    return '| ' + ' | '.join(headers) + ' |\n|' + '|'.join(' --- ' for _ in headers) + '|\n' + '\n'.join('| ' + ' | '.join(clean(value) for value in row) + ' |' for row in rows)


context = f"Execution: {environment['date']} ({environment['execution_context']}). Python {environment['python']}, Django {environment['django']}, SQLite. Source revision: `{environment['source_sha']}`.\n\nPlatform: {environment['platform']}. The Part 3 test settings create and destroy a separate on-disk database; development data is not used."
summary = f"{results['tests_run']} test methods executed: {counts['passed']} passed, {results['skipped']} skipped, {results['failures']} failures and {results['errors']} errors in {results['seconds']:.3f} seconds."
evidence_links = '[Raw execution log](evidence/full_test_run.txt), [named outcomes](evidence/test_results.json), [environment/commands](evidence/environment.json).'
unit_counts = Counter(r['status'] for r in unit)
write('UNIT_TEST_REPORT.md', f'''# Unit Test Report

{context}

## Scope and outcome

The focused unit group contains the existing task parsing, task calculations,
validation/workflow rule and environment configuration suites. Some focused
rule tests exercise the database/API; this group is not described as entirely
isolated pure-function testing. The wider integration and browser suites are
reported separately.

{len(unit)} methods: {unit_counts['passed']} passed, {sum(v for k,v in unit_counts.items() if k != 'passed')} non-pass outcomes.

Sprint updates add NaN/sNaN/infinity/boolean rejection and impossible calendar
dates to the earlier parser cases. API boundary and date-edit regressions from
Iteration 2 remain in the full run.

{table(['Test method', 'Result', 'Seconds'], [(r['id'].split('.')[-1], r['status'], f"{r['seconds']:.3f}") for r in unit])}

## Evidence and limits

{summary} {evidence_links}
Subtests exercise multiple inputs; they are not inflated into additional test
method counts. Passing tests do not establish exhaustive input correctness.
''')

case_data = [
('01','FR-01','Registration','Fresh email, repeated email and malformed registration fields.','One valid account/session; duplicate rejected without another row.'),
('02','FR-02','Authentication','Valid and invalid credentials, logout and session policy.','Correct login authenticates; invalid credentials and expired/logout sessions deny access.'),
('03','FR-03','Project creation','Create a project as an authenticated new user.','Project persists and creator receives Owner membership.'),
('04','FR-04, SR-01','Membership and roles','Owner invites; Member attempts role elevation; check owner invariant.','Authorized invitation succeeds; unauthorized membership/role changes fail.'),
('05','FR-05','Task creation','Create a complete task; blank/overlong titles and invalid fields.','Valid task starts in Backlog; invalid input does not create a task.'),
('06','FR-06, SR-01','Task edit permissions','Assigned Member edits allowed fields; attempts estimate/assignee changes; outsider access.','Allowed edit persists; forbidden changes return 403/404 and retain state.'),
('07','FR-07, FR-13','Kanban workflow','Move status; repeat with stale expected_version; inspect audit.','New status/version and audit persist; stale update returns 409 without overwriting.'),
('08','FR-08','Combined filters','Combine assignee, priority and due filters.','Only the intersection is returned within the selected project.'),
('09','FR-09','Effort estimates','Create/edit at 0, 0.5, 9999.5; negative, off-step, nonfinite and extreme exponents.','Authorized half-hour values persist; invalid values return 400 without writes.'),
('10','FR-10, FR-11','Time lifecycle','Log 1.25 + 0.75; revise first to 2.5 with new date/note; reject malformed edits; delete.','Totals are 2.00 then 3.25 then 0.75; creator-only editing and atomic rejection hold.'),
('11','FR-11','Dashboard','Seed known task statuses, due dates, estimates and retained entries.','Counts and estimated/actual totals match stored data.'),
('12','FR-12, FR-14','Comments and search','Comment and search across two isolated projects; exercise output encoding.','Comments ordered; searches scoped; text is safely encoded.'),
('13','FR-15, FR-16','CSV and archive','Export with estimates/actuals; archive; attempt all mutation routes.','CSV values match; archived writes fail while authorized reads remain available.'),
('14','FR-17','Notifications','Invite and assign, then read notifications as recipient/outsider.','Exactly the expected recipient records are created; unauthorized actions denied.'),
('15','SR-02, SR-03, SR-04, SR-05','Security','Hash inspection; CSRF omission/token; script payload; five bad logins and sixth attempt.','Salted adaptive hashes, CSRF rejection, inert output and temporary lockout hold.'),
('16','NFR-01, NFR-02','Capacity and load','500 tasks, 20 members, 2000 events; 20 concurrent authenticated users issue 100 HTTP requests.','All expected IDs present; per-endpoint p95 at most 2 seconds and no HTTP errors.'),
('17','NFR-03','Persistence and rollback','Independent writer/reader application processes; injected API/audit/notification failures.','Committed changes survive; failed operations leave no partial database rows.'),
('18','NFR-04, NFR-05, NFR-06','Browser and usability','Chrome Stable and Firefox at 1280x720; count creation actions; Enter/arrows/Tab/Escape.','Each creation flow uses at most 10 actions; keyboard and browser flows complete without JS exceptions.'),
]


def case_records(number):
    selected = [r for r in records if 'test_tc' + number in r['id']]
    extra = {'09':'tests.test_iteration2_effort_reliability.Iteration2EffortTests.test_estimate_', '10':'tests.test_iteration2_effort_reliability.Iteration2EffortTests.test_time_', '16':'tests.test_concurrent_performance.', '17':'tests.test_iteration2_effort_reliability.RestartPersistenceTests.', '18':'tests.test_browser_compatibility.'}
    if number in extra:
        selected += [r for r in records if r['id'].startswith(extra[number])]
    if number == '17':
        selected += [r for r in records if 'test_endpoint_failure_rolls_back' in r['id']]
    return list({r['id']: r for r in selected}.values())


def case_status(number):
    selected = case_records(number)
    if not selected:
        return 'NOT EXECUTED'
    if any(r['status'] not in ('passed', 'skipped') for r in selected):
        return 'FAIL'
    return 'PARTIAL' if any(r['status'] == 'skipped' for r in selected) else 'PASS'


matrix = table(['Case', 'Requirements', 'Scenario', 'Actual outcome'], [(f'TC-{n}', req, title, case_status(n)) for n,req,title,_,_ in case_data])
browser_table = table(['Browser', 'Version', 'Viewport', 'Project actions', 'Task actions'], [(b['browser'], b['version'], '1280x720', len(b['project_actions']), len(b['task_actions'])) for b in browsers])
load_table = table(['Endpoint', 'HTTP samples', 'p95 seconds', 'Maximum seconds'], [(endpoint, values['requests'], f"{values['p95_seconds']:.4f}", f"{values['maximum_seconds']:.4f}") for endpoint,values in load['summary'].items()]) if load else 'No completed concurrent-load result was produced.'
all_passed = all(case_status(n) == 'PASS' for n,*_ in case_data) and not results['errors'] and not results['failures'] and not results['skipped']
write('SYSTEM_VALIDATION_REPORT.md', f'''# System Validation Report

{context}

## Executed test-plan validation

{summary}

{matrix}

## Browser and keyboard execution

{browser_table}

Actions are counted after sign-in/navigation: open a dialog, fill a field and
submit each count once. Project creation includes an optional description
field (4 actions); minimal task creation uses 3. Keyboard checks activate a
card with Enter, change status using arrows and Tab, and close using Escape.
Font-CDN requests are aborted so external font availability does not control
the local workflow. Other application content is unchanged.

## Required concurrent HTTP load

{load_table}

The fixture contains 500 tasks, 20 members and 2000 events. Twenty authenticated
workers each send five requests through a live threaded HTTP server, for 100
requests total. The test server's TCP connection backlog is explicitly 64,
so the burst is admitted without the development server's default 10-slot
backlog causing SYN retries. This is not the earlier sequential Django-client benchmark.
The task response retains all 500 tasks; exact activity ID equality is checked
by the separate capacity regression. Timings are local/CI qualification results,
not a production SLA or distributed-user measurement.

## Acceptance and limits

Executed test-plan gate: **{'PASS' if all_passed else 'INCOMPLETE OR FAILED; see non-pass outcomes'}**.
The original plan spans FR-01..17, NFR-01..06 and SR-01..05. The matrix records
functional case outcomes; statement/branch coverage is reported independently.
No unexecuted browser is treated as passed. No assertion here establishes
power-loss durability, production load capacity, PostgreSQL behavior or formal
WCAG conformance. The restart check starts fresh Django application processes,
not an operating-system reboot.

{evidence_links}
''')
line_rows = []
branch_rows = []
for filename, data in sorted(coverage['files'].items()):
    s = data['summary']
    line_rows.append((filename, s['covered_lines'], s['num_statements'], percent(s['covered_lines'], s['num_statements']), ', '.join(map(str, data['missing_lines'])) or '-'))
    missing = '; '.join(f'{start}->{end}' for start,end in data.get('missing_branches', [])) or '-'
    branch_rows.append((filename, s.get('covered_branches',0), s.get('num_branches',0), percent(s.get('covered_branches',0), s.get('num_branches',0)), s.get('num_partial_branches',0), missing))
scope = 'Coverage includes Python application modules in accounts, projects, tasks, audit, notifications and config. Only generated migration modules are excluded. Tests, vendored Django/Playwright, JavaScript, CSS and templates are outside the Python coverage denominator. Browser execution is measured by functional assertions rather than Python line coverage. Subprocess tracing is enabled and the child data is combined; no missing branch is excluded merely to increase the percentage.'
write('CODE_COVERAGE_REPORT.md', f'''# Code Coverage Report

{context}

Statement coverage: **{percent(totals['covered_lines'], totals['num_statements'])}**
({totals['covered_lines']} / {totals['num_statements']} executable Python statements).
This is the statement-only calculation, not coverage.py's blended line/branch percentage.

## Measurement scope

{scope}

{table(['Module', 'Covered', 'Statements', 'Statement coverage', 'Missing lines'], line_rows)}

## Reproduction and interpretation

Run `python scripts/run_part3_tests.py` after installing `requirements-test.txt`
and browser dependencies. The same run exports [coverage JSON](evidence/coverage.json),
[XML](evidence/coverage.xml), [text summary](evidence/coverage_summary.txt) and
[interactive HTML](coverage_html/index.html). Coverage below 100% is retained
honestly; executed coverage does not prove absence of defects or assertion quality.
''')
write('BRANCH_COVERAGE_REPORT.md', f'''# Branch Coverage Report

{context}

Branch-outcome coverage: **{percent(totals['covered_branches'], totals['num_branches'])}**
({totals['covered_branches']} / {totals['num_branches']} measured Python branch outcomes).
Partially exercised branch locations: {totals['num_partial_branches']}.

## Measurement scope

{scope}

{table(['Module', 'Covered outcomes', 'All outcomes', 'Branch coverage', 'Partial locations', 'Missing arcs'], branch_rows)}

## Reading the results

Each `start->end` pair is a missing control-flow arc; a negative endpoint can
represent function exit in coverage.py. A module without measurable branches
is N/A, not 100%. Negative/positive validation, role rejection, archived writes,
conflict, invalid dates, extreme decimals and rollback paths are exercised by
the regression suite. Remaining arcs above are the next targeted-test backlog.
This is Python branch coverage, not JavaScript coverage, MC/DC, path coverage
or proof of every possible input combination.

[Machine-readable arcs](evidence/coverage.json) and [HTML inspection](coverage_html/index.html).
''')
case_text = '# Test Case Document - Version 1.1\n\nUpdated for Part 3 on 6 November 2026. Supersedes the execution procedures in the original STP v1.0 case table; the original PDF is retained as the historical plan.\n\n' + context + '\n\nUse isolated Owner, Manager, Member and outsider accounts. Each automated case resets its fixture. No production credentials/data are used.\n\n'
for number, req, title, procedure, expected in case_data:
    methods = case_records(number)
    case_text += f'## TC-{number}: {title}\n\nRequirements: {req}.\n\nProcedure/data: {procedure}\n\nExpected: {expected}\n\nActual: **{case_status(number)}** in the named methods below. Detailed assertions, HTTP statuses and fixtures are in the linked source; actual method outcomes are in `part3/evidence/test_results.json`.\n\n'
    case_text += '\n'.join(f"- `{r['id']}`: {r['status']}." for r in methods) + '\n\n'
case_text += '## Sprint changes reflected in this revision\n\n- TC-09/10: non-finite and storage boundaries, invalid JSON shapes, date/note edits, ownership and retained totals.\n- TC-16: exact ID retrieval plus the specified concurrent 20-user/100-request HTTP run; bounded query regression replaces an unmeasured scalability assumption.\n- TC-17: independent processes and injected endpoint failures, beyond simple ORM refresh.\n- TC-18: real browser action counts and keyboard steps at 1280x720, beyond static HTML inspection.\n'
(ROOT / 'docs' / 'TEST_CASE_DOCUMENT.md').write_text(case_text)
write('SPRINT_3_REPORT.md', '''# Optional Sprint 3 - testing spillovers

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
''')
write('README.md', f'''# Part 3 submission

Required deliverables:

- [Updated Test Case Document v1.1](../TEST_CASE_DOCUMENT.md)
- [Unit Test Report](UNIT_TEST_REPORT.md)
- [System Validation Report](SYSTEM_VALIDATION_REPORT.md)
- [Code Coverage Report](CODE_COVERAGE_REPORT.md)
- [Branch Coverage Report](BRANCH_COVERAGE_REPORT.md)
- [Optional Sprint 3 spillover report](SPRINT_3_REPORT.md)
- [Coverage HTML](coverage_html/index.html) and [raw evidence](evidence/)

{summary}
Statement coverage: {percent(totals['covered_lines'], totals['num_statements'])}.
Branch coverage: {percent(totals['covered_branches'], totals['num_branches'])}.

Reproduce using `python scripts/run_part3_tests.py`. Install
`requirements-test.txt` and run `python -m playwright install --with-deps chrome firefox`
first. On a normal Chrome install no executable override is needed. An extracted
vendor Chrome can be selected with `PMS_CHROME_EXECUTABLE`.
`PART3_SKIP_CHROME=1` is only for an execution-restricted local runtime and
produces an explicit skip and incomplete gate; it is not a release pass.
''')
print('Generated updated cases and all four Part 3 reports.')
