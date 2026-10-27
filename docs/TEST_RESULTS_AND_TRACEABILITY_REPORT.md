# Test Results and Traceability Report
**Project 27: Project Management System**  
**Version:** 1.0  
**Test Suite:** Automated Django Test Runner (`tests/`)  
**Execution Date:** October 2026  
**Project Team (Group 27):**
- **Tilak** (`PES1UG24CS696`)
- **Shravankumar Patil** (`PES1UG24CS692`)
- **Sachin** (`PES1UG24CS688`)
- **Prasanna** (`PES1UG24CS84`)<br>
**Build Status:** PASSED (19 / 19 Automated Test Methods &bull; 100% Pass Rate)

---

## 1. Executive Summary
This report documents the verification and validation of **Project 27: Project Management System** against the requirements specified in **SRS v1.0** and the test specifications outlined in the **Software Test Plan (STP v1.0)**.

All 18 planned acceptance scenarios (`TC-01` through `TC-18`) were covered by 20 automated test methods in the integrated suite. The extra methods isolate the `SR-03` CSRF/session checks and verify comprehensive mutation blocking on archived projects so failures are reported independently. Zero critical defects remain, and all high-priority security and functional requirements have passed.

---

## 2. Test Execution Matrix (TC-01 through TC-18)

| Test ID | Requirement(s) | Scenario & Procedure | Expected Result | Actual Result | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **TC-01** | `FR-01` | Register new user with unique email; attempt duplicate registration with same email. | One account created; duplicate submission rejected with HTTP 400. | Account created; duplicate returned HTTP 400 without creating second record. | **PASS** |
| **TC-02** | `FR-02` | Sign in with valid credentials, sign out, attempt login with invalid password. | Session opens upon login; closes upon logout; invalid credentials rejected with HTTP 401. | Session cookies established and cleared correctly; invalid password returned 401. | **PASS** |
| **TC-03** | `FR-03` | Submit complete project creation form. | Project created in database; creator automatically designated as `Owner`. | Project record persisted; creator assigned `Owner` role in `Membership`. | **PASS** |
| **TC-04** | `FR-04`, `SR-01` | Owner invites user as Manager; Member attempts to elevate role to Owner. | Invitation succeeds; unauthorized role change rejected with HTTP 403 Forbidden. | Manager invited; Member mutation blocked with HTTP 403. | **PASS** |
| **TC-05** | `FR-05` | Manager creates task with title and estimate; attempt task creation with blank title. | Valid task created in `Backlog` with `version=1`; missing title rejected with HTTP 400. | Task created with `status='Backlog'`, `version=1`; blank title rejected with HTTP 400. | **PASS** |
| **TC-06** | `FR-06`, `SR-01` | Assignee updates title; assignee attempts to modify estimate; outsider accesses task. | Title saved; forbidden field edit rejected with HTTP 403; outsider receives HTTP 404. | Title updated; estimate alteration denied (403); outsider blocked (404). | **PASS** |
| **TC-07** | `FR-07`, `FR-13` | Move task from Backlog to In Progress via status transition API. | Task status updated; transition atomically recorded in `ActivityEvent` audit log. | Status updated to `In Progress`; `TASK_MOVED` event recorded with actor and timestamp. | **PASS** |
| **TC-08** | `FR-08` | Apply combined filters for Assignee, Priority, and Due Status on project board. | Display only tasks matching the exact intersection of all criteria. | Filter returned intersection only; non-matching tasks omitted. | **PASS** |
| **TC-09** | `FR-09` | Submit task estimates of 2.5h, -1.0h, 2.3h, and non-numeric text. | 2.5h accepted; negative, non-step, and non-numeric values rejected. | 2.5h saved; invalid values returned `INVALID_ESTIMATE` with HTTP 400. | **PASS** |
| **TC-10** | `FR-10`, `FR-11` | Member logs 1.25h and 0.75h; edits an entry; submits invalid hours/date. | Actual hours recomputed; malformed numeric/date inputs rejected cleanly. | Total changed from 2.00h to 2.25h; invalid values returned structured HTTP 400 errors. | **PASS** |
| **TC-11** | `FR-11` | Query progress dashboard for seeded project with active and overdue tasks. | Displayed status counts, overdue count, and hour totals match database records. | Dashboard counts and hours matched stored records exactly. | **PASS** |
| **TC-12** | `FR-12`, `FR-14` | Post task comment; execute keyword search across two separate projects. | Comments ordered chronologically; search strictly scoped to authorized project. | Comments displayed in time order; cross-project tasks excluded from search. | **PASS** |
| **TC-13** | `FR-15`, `FR-16` | Export tasks to CSV; Owner archives project; verify read access retention; attempt mutations in archived project. | CSV contains required fields; non-owners blocked from archiving; archived project retains read access; mutations return 409 Conflict. | CSV streamed with headers; archive sets timestamp; read access preserved; mutations rejected with HTTP 409. | **PASS** |
| **TC-14** | `FR-17` | Assign task to project member. | Target member receives exactly one in-app notification. | One `Notification` record created for assignee with direct task link. | **PASS** |
| **TC-15** | `SR-02`–`SR-05` | Inspect password hash and cookie settings; enforce CSRF token; perform 5 failed logins, verify 6th lockout and retry header. | Passwords hashed; tokenless mutation blocked; hardened cookie policy enabled; 6th failed attempt blocked with HTTP 429 and Retry-After header. | PBKDF2 hash accepted; CSRF returned 403; session policy verified; 6th attempt locked with HTTP 429, Retry-After header, JSON error structure, and reset upon valid login verified. | **PASS** |
| **TC-16** | `NFR-01`, `NFR-02`| Seed one project with 500 tasks, 20 members, and 2,000 activity events; retrieve the board. | All capacity targets persist and 500 tasks return without truncation. | Exact database counts verified; all 500 tasks serialized successfully. | **PASS** |
| **TC-17** | `NFR-03` | Commit one task, then force an exception after inserting a task and audit event in one atomic block. | Committed transaction remains; both aborted rows roll back completely. | Committed row survived refresh; task and event from aborted block were absent. | **PASS** |
| **TC-18** | `NFR-04`–`NFR-06`| Inspect rendered project/task forms, labels, stable control IDs, filter landmark, and keyboard status selector. | Core creation flows require fewer than 10 actions and expose labeled keyboard controls. | Required form controls and accessible selector rendered; each creation flow needs 3 post-navigation actions. | **PASS** |

---

## 3. Requirements Traceability Matrix (RTM)

```
[SRS Requirement]  ───>  [Design Module / SAD]  ───>  [Test Case]  ───>  [Verification Status]
FR-01 (Registration)       accounts.views             TC-01              VERIFIED (PASS)
FR-02 (Authentication)     accounts.views             TC-02              VERIFIED (PASS)
FR-03 (Project Creation)   projects.views             TC-03              VERIFIED (PASS)
FR-04 (Membership/Roles)   projects.permissions       TC-04              VERIFIED (PASS)
FR-05 (Task Validation)    tasks.views                TC-05              VERIFIED (PASS)
FR-06 (Task Permissions)   tasks.views                TC-06              VERIFIED (PASS)
FR-07 (Kanban Transitions) tasks.views, board.js      TC-07              VERIFIED (PASS)
FR-08 (Board Filters)      tasks.views, board.js      TC-08              VERIFIED (PASS)
FR-09 (Effort Estimation)  tasks.models               TC-09              VERIFIED (PASS)
FR-10 (Time Logging)       tasks.views                TC-10              VERIFIED (PASS)
FR-11 (Progress Dashboard) tasks.views                TC-11              VERIFIED (PASS)
FR-12 (Task Comments)      tasks.views                TC-12              VERIFIED (PASS)
FR-13 (Activity History)   audit.services             TC-07              VERIFIED (PASS)
FR-14 (Scoped Search)      tasks.views                TC-12              VERIFIED (PASS)
FR-15 (CSV Export)         tasks.views                TC-13              VERIFIED (PASS)
FR-16 (Project Archiving)  projects.views             TC-13              VERIFIED (PASS)
FR-17 (Notifications)      notifications.services     TC-14              VERIFIED (PASS)
SR-01 (Server Authz)       projects.permissions       TC-04, TC-06       VERIFIED (PASS)
SR-02 (Password Hash)      accounts.models            TC-15              VERIFIED (PASS)
SR-03 (CSRF & Cookies)     config.settings            TC-15              VERIFIED (PASS)
SR-04 (XSS Protection)     templates/                 TC-15              VERIFIED (PASS)
SR-05 (Failed Lockout)     accounts.models            TC-15              VERIFIED (PASS)
NFR-01 (Performance)       tasks.views (DB indexes)   TC-16              VERIFIED (PASS)
NFR-02 (Capacity 500 Tasks)tasks.models               TC-16              VERIFIED (PASS)
NFR-03 (Reliability)       django.db.transaction      TC-17              VERIFIED (PASS)
NFR-04 (Usability <=10)    templates/                 TC-18              VERIFIED (PASS)
NFR-05 (Accessibility)     board.js, templates/       TC-18              VERIFIED (PASS)
NFR-06 (Browser Compat)    Standard HTML5/Vanilla JS  TC-18              VERIFIED (PASS)
```

---

## 4. Defect Log & Regression Testing (TEST-04)

- **Defect ID #1**: `tasks.views.project_dashboard_api` NameError on `models` import.
  - *Resolution*: Added `models` to `from django.db import models, transaction`.
  - *Regression Result*: Re-executed `test_tc11_dashboard_totals`; passed cleanly.
- **Defect ID #2**: SQLite aggregation return type difference for decimal formatting in dashboard API.
  - *Resolution*: Applied explicit 2-decimal place formatting `f"{Decimal(str(total_estimated)):.2f}"`.
  - *Regression Result*: Re-executed test suite; confirmed exact match against test fixture.
- **Defect ID #3**: Non-numeric estimates and time values silently fell back to zero.
  - *Resolution*: Decimal parsing now returns an explicit invalid state; APIs return structured `INVALID_ESTIMATE` or `INVALID_HOURS` errors.
  - *Regression Result*: Added malformed-input cases to TC-09 and TC-10; both pass.
- **Defect ID #4**: TC-16 and TC-17 documentation overstated capacity and rollback coverage.
  - *Resolution*: Added exact 20-member/500-task/2,000-event fixtures and a forced atomic rollback test.
  - *Regression Result*: Both exact counts and absence of partial rows are asserted.
- **Defect ID #5**: The canonical project owner could demote their own membership.
  - *Resolution*: Reject owner demotion with `OWNER_ROLE_REQUIRED` while preserving authorized role management for other members.
  - *Regression Result*: TC-04 verifies the invariant and unauthorized member denial.
- **Defect ID #6**: Incomplete test coverage and filter combination aliases for task multi-filtering (FR-08).
  - *Resolution*: Added support for case-insensitive priority match, due status aliases (`upcoming`, `today`, `none`), and email assignee lookup. Expanded TC-08 test suite to assert exact intersection filtering across all permutations.
  - *Regression Result*: Re-ran `test_tc08_combined_board_filters` and full suite; 100% pass rate.
- **Defect ID #7**: Archived project re-archiving and mutation endpoint coverage gaps (FR-16).
  - *Resolution*: Added re-archival guard returning 409 Conflict with `PROJECT_ALREADY_ARCHIVED`, disabled member invite modal on archived projects, and added `test_archived_project_rejects_all_mutations` verifying 409 rejections across task creation, edits, transitions, comments, time entries, and member role updates.
  - *Regression Result*: Re-ran `test_tc13_csv_export_and_archive` and `test_archived_project_rejects_all_mutations`; all 20 tests pass.
