# System and Acceptance Test Execution Report
**Project 27: Project Management System**  
**Course:** Software Engineering Mini-Project  
**Author / QA Lead:** Shravankumar Patil (`PES1UG24CS692`, `@shravanakumarpatil-123`)  
**Test Reference:** TEST-03 (Issue #37) & STP v1.0  
**Execution Environment:** Python 3.14.2 / Django 5.2.18 / SQLite In-Memory Engine  
**Execution Date:** October 2026  
**Build Status:** 100% PASSED (18 / 18 Acceptance Test Scenarios)

---

## 1. Scope & Execution Objective
This document provides formal verification records for acceptance scenarios **TC-01 through TC-18**, as mandated in the **Software Test Plan (STP v1.0)** and SRS requirements. The test suite executes automated system-level acceptance flows against database persistence, session security, multi-tenant RBAC, and responsive UI interactions.

---

## 2. Test Execution & Verification Matrix

| Test Case | Requirement | Scenario Description | Expected Result | Actual Result | Verification Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **TC-01** | `FR-01` | Account Registration with duplicate email prevention. | Unique account registered; duplicate rejected with HTTP 400. | Account created; duplicate submission rejected with HTTP 400. | **PASS** |
| **TC-02** | `FR-02` | Authentication session lifecycle and sign-out. | Authenticated session created; terminated on logout; bad credentials return 401. | Session cookies established and cleared cleanly; invalid credentials returned 401. | **PASS** |
| **TC-03** | `FR-03` | Project workspace creation and role designation. | Workspace persisted; creator automatically designated as `Owner`. | Project record created; creator assigned `Owner` role in `Membership`. | **PASS** |
| **TC-04** | `FR-04`, `SR-01` | Member invitation and privilege escalation prevention. | Owner can invite members; unauthorized role elevation blocked with 403. | Manager invited; unauthorized role escalation rejected with HTTP 403. | **PASS** |
| **TC-05** | `FR-05` | Task creation with title validation in Backlog. | Task persisted with `status=Backlog` and `version=1`; blank title rejected. | Task created in Backlog; blank title rejected with HTTP 400. | **PASS** |
| **TC-06** | `FR-06`, `SR-01` | Role-based task field editing permissions. | Title editable by assignee; estimate immutable by member; outsider rejected. | Title saved; estimate edit blocked with 403; outsider received 404/403. | **PASS** |
| **TC-07** | `FR-07`, `FR-13` | Kanban status transition and atomic audit logging. | Status updated; transition recorded atomically in `ActivityEvent`. | Task transitioned to `In Progress`; `TASK_MOVED` event logged. | **PASS** |
| **TC-08** | `FR-08` | Combined filtering by Assignee and Priority. | Only tasks matching the intersection of all criteria are displayed. | Filter strictly returned intersection; disjoint tasks excluded. | **PASS** |
| **TC-09** | `FR-09` | Task effort estimation bounds validation. | 2.5h accepted; non-step, negative, and non-numeric inputs rejected with 400. | 2.5h persisted; invalid inputs rejected with structured HTTP 400. | **PASS** |
| **TC-10** | `FR-10`, `FR-11` | Time logging entry and actual-hour recalculation. | Total actual hours updated automatically from individual time entries. | Actual hours incremented correctly; entry persistence verified. | **PASS** |
| **TC-11** | `FR-11` | Progress dashboard metrics aggregation. | Dashboard metrics report accurate status counts, overdue counts, and hours. | Dashboard aggregated values exactly matched underlying DB records. | **PASS** |
| **TC-12** | `FR-12`, `FR-14` | Chronological comments and project-scoped search. | Comments ordered chronologically; keyword search scoped strictly to project. | Comments displayed in time order; cross-project search isolated. | **PASS** |
| **TC-13** | `FR-15`, `FR-16` | CSV task export streaming and project archival read-only. | CSV streamed with headers; archived project rejects mutations with 409. | CSV generated cleanly; mutation on archived project rejected with 409. | **PASS** |
| **TC-14** | `FR-17` | In-app notification creation upon task assignment. | Assignee receives exactly one in-app notification record. | Notification created with target link and unread status. | **PASS** |
| **TC-15** | `SR-02`–`SR-05` | PBKDF2 hashing, CSRF enforcement, and 5-attempt lockout. | Salted hashes stored; tokenless POST rejected; 6th failed login locked (429). | Hashes verified; lockout triggered on 6th attempt with Retry-After header. | **PASS** |
| **TC-16** | `NFR-01`, `NFR-02`| High-volume capacity scaling test. | System retrieves large task collections without truncation. | All tasks serialized and returned without memory or timeout errors. | **PASS** |
| **TC-17** | `NFR-03` | Transactional atomicity and rollback on error. | Partial database mutations rolled back entirely upon unhandled exceptions. | Database integrity preserved; rolled back records cleanly eliminated. | **PASS** |
| **TC-18** | `NFR-04`–`NFR-06`| Accessibility controls, visible focus, and landmark structure.| Keyboard controls, landmarks, skip link, and accessible status selector rendered. | All accessibility landmarks, visible skip link, and selector rendered. | **PASS** |

---

## 3. Defect & Remediation Summary
- **Defect ID DEF-01 (Closed)**: `actual_hours` on `Task` model is a dynamic aggregation property and cannot be assigned directly. Resolved in test harnesses by creating `TimeEntry` fixtures to drive actual-hour calculations.
- **Defect ID DEF-02 (Closed)**: Unauthenticated registration assertion conflicted when test client reused authenticated session. Resolved by isolating registration flows to anonymous test clients.
- **Defect ID DEF-03 (Closed)**: HTML form submission for member invitation returned 302 redirect with user message. JSON API test invocation correctly validates HTTP 403 Forbidden payload.

All 18 acceptance test cases are fully verified and passing in automated CI execution.
