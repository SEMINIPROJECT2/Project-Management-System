# Final project report — Iteration 2

Original verification: 28 October 2026. Evidence and report re-verification:
29 October 2026 (Asia/Calcutta).
Scope: only assigned issues #9, #10, #19, #20, #40 and #41.
Base: latest main `5e45107c2b84f8208d64e39a3f17dd67d3cfca91`.

The existing Django application provides accounts, project membership, a Kanban board, comments, dashboards, export, archival, audit events and notifications. These teammate contributions are retained. This report describes the six requested issues and does not certify every requirement in the project as complete.

## Iteration outcomes

| Issue | Outcome | Evidence |
| --- | --- | --- |
| #9 / FR-09 | Estimates accept finite values from 0 to 9999.5 inclusive in 0.5-hour steps; create and edit reject invalid values before writes. Owner/Manager permissions remain enforced. | Boundary, invalid-input and role regression tests |
| #10 / FR-10 | Positive finite logs from 0.25 to 999.75 in quarter-hour steps; validate dates and textual notes; edits persist supplied date changes, retain omitted date/note, and recompute actual totals. Only the creator edits/deletes entries. | Time lifecycle, malformed inputs, ownership, scoping and archive tests |
| #19 / NFR-02 | All 500 tasks, 20 memberships and 2000 activity events are retrieved and compared by ID. Activity history no longer silently truncates at 100 rows and has deterministic newest-first ordering. | Capacity regression test and separate performance run |
| #20 / NFR-03 | Task edits and time logs survive termination and startup in another Django process using a temporary file database. Injected endpoint failures roll back task/entry, audit and notification writes. Existing transaction boundaries passed; no transaction rewrite was necessary. | Process restart and failure injection tests |
| #40 / DOC-02 | Test results, skipped checks, defects and requirement-to-test links documented. | [Test results and traceability](TEST_RESULTS_AND_TRACEABILITY_REPORT.md) |
| #41 / DOC-03 | Final report, walkthrough scripts, actual API evidence and reproducible video generator prepared. Video binaries are intentionally excluded from Git; #41 remains open for video submission. | [Evidence and reproduction guide](ITERATION_2_DEMO_GUIDE.md) |

## Validation

Full suite: 133 discovered, 130 passed, 3 skipped, 0 failures/errors in 397.531 seconds. The opt-in performance test passed separately; Chrome and Firefox browser workflows remain unexecuted. See the test report and raw execution logs for commands and limitations. SQLite on Windows and Python 3.13 are the tested environment. Tests do not establish PostgreSQL behavior, production load capacity, power-loss recovery or a real web-server process restart; the restart test starts independent Django application processes with the same SQLite file.

Demo-delivery re-verification on 29 October used Linux, Python 3.12, Django
5.2.18 and SQLite: 133 discovered, 130 passed, 3 skipped, zero failures/errors
in 81.196 seconds. The [fresh log](test-evidence/demo-delivery-tests.txt) and
[demonstration source evidence](ITERATION_2_DEMO_GUIDE.md) accompany this report. The original
Windows timing above is retained as historical evidence.

## Known limitations and future improvements

- Video binaries are excluded at the user's request. The reproduction script renders captioned actual API results and test output, not browser interactions or historical sprint captures. It does not establish browser compatibility or usability action counts.
- Browser execution is optional in the existing suite; skipped checks are recorded separately from passes.
- Time-entry date and note edits are supported through the API. The existing board offers log creation and deletion; an edit/date picker UI is future work.
- The complete activity response is appropriate to the required 2000-event fixture. Larger histories would benefit from explicit pagination with a tested full-history traversal contract.
- Validation here covers application API writes. Direct ORM writes do not automatically call Django model validation.
- Wider production deployment and additional database backends require separate validation.
