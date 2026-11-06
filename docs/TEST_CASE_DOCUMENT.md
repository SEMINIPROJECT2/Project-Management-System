# Test Case Document - Version 1.1

Updated for Part 3 on 6 November 2026. Supersedes the execution procedures in the original STP v1.0 case table; the original PDF is retained as the historical plan.

Execution: 2026-11-06T17:46:12.589413+00:00 (GitHub Actions). Python 3.12.16, Django 5.2.19, SQLite. Source revision: `de496554513c8ce0ba146965949f9c16eb6a01ed`.

Platform: Linux-7.0.0-1019-azure-x86_64-with-glibc2.43. The Part 3 test settings create and destroy a separate on-disk database; development data is not used.

Use isolated Owner, Manager, Member and outsider accounts. Each automated case resets its fixture. No production credentials/data are used.

## TC-01: Registration

Requirements: FR-01.

Procedure/data: Fresh email, repeated email and malformed registration fields.

Expected: One valid account/session; duplicate rejected without another row.

Actual: **PASS** in the named methods below. Detailed assertions, HTTP statuses and fixtures are in the linked source; actual method outcomes are in `part3/evidence/test_results.json`.

- `tests.test_auth_and_security.AuthAndSecurityTests.test_tc01_registration_valid_and_duplicate`: passed.
- `tests.test_system_acceptance.SystemAcceptanceSuiteTests.test_tc01_user_registration`: passed.

## TC-02: Authentication

Requirements: FR-02.

Procedure/data: Valid and invalid credentials, logout and session policy.

Expected: Correct login authenticates; invalid credentials and expired/logout sessions deny access.

Actual: **PASS** in the named methods below. Detailed assertions, HTTP statuses and fixtures are in the linked source; actual method outcomes are in `part3/evidence/test_results.json`.

- `tests.test_auth_and_security.AuthAndSecurityTests.test_tc02_sign_in_and_sign_out`: passed.
- `tests.test_system_acceptance.SystemAcceptanceSuiteTests.test_tc02_authentication_and_sessions`: passed.

## TC-03: Project creation

Requirements: FR-03.

Procedure/data: Create a project as an authenticated new user.

Expected: Project persists and creator receives Owner membership.

Actual: **PASS** in the named methods below. Detailed assertions, HTTP statuses and fixtures are in the linked source; actual method outcomes are in `part3/evidence/test_results.json`.

- `tests.test_projects_and_roles.ProjectsAndRolesTests.test_tc03_create_project`: passed.
- `tests.test_system_acceptance.SystemAcceptanceSuiteTests.test_tc03_project_creation`: passed.

## TC-04: Membership and roles

Requirements: FR-04, SR-01.

Procedure/data: Owner invites; Member attempts role elevation; check owner invariant.

Expected: Authorized invitation succeeds; unauthorized membership/role changes fail.

Actual: **PASS** in the named methods below. Detailed assertions, HTTP statuses and fixtures are in the linked source; actual method outcomes are in `part3/evidence/test_results.json`.

- `tests.test_projects_and_roles.ProjectsAndRolesTests.test_tc04_membership_and_role_control`: passed.
- `tests.test_system_acceptance.SystemAcceptanceSuiteTests.test_tc04_membership_and_role_escalation`: passed.

## TC-05: Task creation

Requirements: FR-05.

Procedure/data: Create a complete task; blank/overlong titles and invalid fields.

Expected: Valid task starts in Backlog; invalid input does not create a task.

Actual: **PASS** in the named methods below. Detailed assertions, HTTP statuses and fixtures are in the linked source; actual method outcomes are in `part3/evidence/test_results.json`.

- `tests.test_system_acceptance.SystemAcceptanceSuiteTests.test_tc05_task_creation_and_title_validation`: passed.
- `tests.test_tasks_and_workflow.TasksAndWorkflowTests.test_tc05_task_creation_validation`: passed.

## TC-06: Task edit permissions

Requirements: FR-06, SR-01.

Procedure/data: Assigned Member edits allowed fields; attempts estimate/assignee changes; outsider access.

Expected: Allowed edit persists; forbidden changes return 403/404 and retain state.

Actual: **PASS** in the named methods below. Detailed assertions, HTTP statuses and fixtures are in the linked source; actual method outcomes are in `part3/evidence/test_results.json`.

- `tests.test_system_acceptance.SystemAcceptanceSuiteTests.test_tc06_task_editing_permissions`: passed.
- `tests.test_tasks_and_workflow.TasksAndWorkflowTests.test_tc06_task_edit_permissions`: passed.

## TC-07: Kanban workflow

Requirements: FR-07, FR-13.

Procedure/data: Move status; repeat with stale expected_version; inspect audit.

Expected: New status/version and audit persist; stale update returns 409 without overwriting.

Actual: **PASS** in the named methods below. Detailed assertions, HTTP statuses and fixtures are in the linked source; actual method outcomes are in `part3/evidence/test_results.json`.

- `tests.test_system_acceptance.SystemAcceptanceSuiteTests.test_tc07_kanban_transition_and_audit`: passed.
- `tests.test_tasks_and_workflow.TasksAndWorkflowTests.test_tc07_kanban_movement_and_audit`: passed.

## TC-08: Combined filters

Requirements: FR-08.

Procedure/data: Combine assignee, priority and due filters.

Expected: Only the intersection is returned within the selected project.

Actual: **PASS** in the named methods below. Detailed assertions, HTTP statuses and fixtures are in the linked source; actual method outcomes are in `part3/evidence/test_results.json`.

- `tests.test_system_acceptance.SystemAcceptanceSuiteTests.test_tc08_board_filters_intersection`: passed.
- `tests.test_tasks_and_workflow.TasksAndWorkflowTests.test_tc08_combined_board_filters`: passed.

## TC-09: Effort estimates

Requirements: FR-09.

Procedure/data: Create/edit at 0, 0.5, 9999.5; negative, off-step, nonfinite and extreme exponents.

Expected: Authorized half-hour values persist; invalid values return 400 without writes.

Actual: **PASS** in the named methods below. Detailed assertions, HTTP statuses and fixtures are in the linked source; actual method outcomes are in `part3/evidence/test_results.json`.

- `tests.test_system_acceptance.SystemAcceptanceSuiteTests.test_tc09_effort_estimation_bounds`: passed.
- `tests.test_tasks_and_workflow.TasksAndWorkflowTests.test_tc09_estimate_bounds`: passed.
- `tests.test_iteration2_effort_reliability.Iteration2EffortTests.test_estimate_boundaries_and_authorized_roles`: passed.
- `tests.test_iteration2_effort_reliability.Iteration2EffortTests.test_estimate_rejects_invalid_create_and_edit_without_writes`: passed.

## TC-10: Time lifecycle

Requirements: FR-10, FR-11.

Procedure/data: Log 1.25 + 0.75; revise first to 2.5 with new date/note; reject malformed edits; delete.

Expected: Totals are 2.00 then 3.25 then 0.75; creator-only editing and atomic rejection hold.

Actual: **PASS** in the named methods below. Detailed assertions, HTTP statuses and fixtures are in the linked source; actual method outcomes are in `part3/evidence/test_results.json`.

- `tests.test_system_acceptance.SystemAcceptanceSuiteTests.test_tc10_time_logging_and_recalculation`: passed.
- `tests.test_tasks_and_workflow.TasksAndWorkflowTests.test_tc10_time_log_calculation`: passed.
- `tests.test_iteration2_effort_reliability.Iteration2EffortTests.test_time_invalid_hours_dates_notes_create_and_edit`: passed.
- `tests.test_iteration2_effort_reliability.Iteration2EffortTests.test_time_json_shape_errors`: passed.
- `tests.test_iteration2_effort_reliability.Iteration2EffortTests.test_time_lifecycle_date_changes_notes_and_totals`: passed.
- `tests.test_iteration2_effort_reliability.Iteration2EffortTests.test_time_ownership_scope_archival_and_forged_owner`: passed.

## TC-11: Dashboard

Requirements: FR-11.

Procedure/data: Seed known task statuses, due dates, estimates and retained entries.

Expected: Counts and estimated/actual totals match stored data.

Actual: **PASS** in the named methods below. Detailed assertions, HTTP statuses and fixtures are in the linked source; actual method outcomes are in `part3/evidence/test_results.json`.

- `tests.test_system_acceptance.SystemAcceptanceSuiteTests.test_tc11_progress_dashboard_metrics`: passed.
- `tests.test_tasks_and_workflow.TasksAndWorkflowTests.test_tc11_dashboard_totals`: passed.

## TC-12: Comments and search

Requirements: FR-12, FR-14.

Procedure/data: Comment and search across two isolated projects; exercise output encoding.

Expected: Comments ordered; searches scoped; text is safely encoded.

Actual: **PASS** in the named methods below. Detailed assertions, HTTP statuses and fixtures are in the linked source; actual method outcomes are in `part3/evidence/test_results.json`.

- `tests.test_system_acceptance.SystemAcceptanceSuiteTests.test_tc12_comments_and_scoped_search`: passed.
- `tests.test_tasks_and_workflow.TasksAndWorkflowTests.test_tc12_comments_and_search_scope`: passed.

## TC-13: CSV and archive

Requirements: FR-15, FR-16.

Procedure/data: Export with estimates/actuals; archive; attempt all mutation routes.

Expected: CSV values match; archived writes fail while authorized reads remain available.

Actual: **PASS** in the named methods below. Detailed assertions, HTTP statuses and fixtures are in the linked source; actual method outcomes are in `part3/evidence/test_results.json`.

- `tests.test_projects_and_roles.ProjectsAndRolesTests.test_tc13_csv_export_and_archive`: passed.
- `tests.test_system_acceptance.SystemAcceptanceSuiteTests.test_tc13_csv_export_and_project_archival`: passed.

## TC-14: Notifications

Requirements: FR-17.

Procedure/data: Invite and assign, then read notifications as recipient/outsider.

Expected: Exactly the expected recipient records are created; unauthorized actions denied.

Actual: **PASS** in the named methods below. Detailed assertions, HTTP statuses and fixtures are in the linked source; actual method outcomes are in `part3/evidence/test_results.json`.

- `tests.test_system_acceptance.SystemAcceptanceSuiteTests.test_tc14_notification_dispatch`: passed.
- `tests.test_tasks_and_workflow.TasksAndWorkflowTests.test_tc14_notification_delivery`: passed.

## TC-15: Security

Requirements: SR-02, SR-03, SR-04, SR-05.

Procedure/data: Hash inspection; CSRF omission/token; script payload; five bad logins and sixth attempt.

Expected: Salted adaptive hashes, CSRF rejection, inert output and temporary lockout hold.

Actual: **PASS** in the named methods below. Detailed assertions, HTTP statuses and fixtures are in the linked source; actual method outcomes are in `part3/evidence/test_results.json`.

- `tests.test_auth_and_security.AuthAndSecurityTests.test_tc15_security_handling`: passed.
- `tests.test_system_acceptance.SystemAcceptanceSuiteTests.test_tc15_security_hash_csrf_and_lockout`: passed.

## TC-16: Capacity and load

Requirements: NFR-01, NFR-02.

Procedure/data: 500 tasks, 20 members, 2000 events; 20 concurrent authenticated users issue 100 HTTP requests.

Expected: All expected IDs present; per-endpoint p95 at most 2 seconds and no HTTP errors.

Actual: **PASS** in the named methods below. Detailed assertions, HTTP statuses and fixtures are in the linked source; actual method outcomes are in `part3/evidence/test_results.json`.

- `tests.test_projects_and_roles.ProjectsAndRolesTests.test_tc16_capacity_limits`: passed.
- `tests.test_system_acceptance.SystemAcceptanceSuiteTests.test_tc16_high_volume_capacity_scaling`: passed.
- `tests.test_concurrent_performance.ConcurrentPerformanceTests.test_twenty_users_and_one_hundred_http_requests`: passed.

## TC-17: Persistence and rollback

Requirements: NFR-03.

Procedure/data: Independent writer/reader application processes; injected API/audit/notification failures.

Expected: Committed changes survive; failed operations leave no partial database rows.

Actual: **PASS** in the named methods below. Detailed assertions, HTTP statuses and fixtures are in the linked source; actual method outcomes are in `part3/evidence/test_results.json`.

- `tests.test_projects_and_roles.ProjectsAndRolesTests.test_tc17_transaction_commit_and_rollback`: passed.
- `tests.test_system_acceptance.SystemAcceptanceSuiteTests.test_tc17_transaction_atomic_rollback`: passed.
- `tests.test_iteration2_effort_reliability.RestartPersistenceTests.test_committed_api_updates_survive_new_application_process`: passed.
- `tests.test_iteration2_effort_reliability.Iteration2EffortTests.test_endpoint_failure_rolls_back_tasks_entries_audit_and_notifications`: passed.

## TC-18: Browser and usability

Requirements: NFR-04, NFR-05, NFR-06.

Procedure/data: Chrome Stable and Firefox at 1280x720; count creation actions; Enter/arrows/Tab/Escape.

Expected: Each creation flow uses at most 10 actions; keyboard and browser flows complete without JS exceptions.

Actual: **PASS** in the named methods below. Detailed assertions, HTTP statuses and fixtures are in the linked source; actual method outcomes are in `part3/evidence/test_results.json`.

- `tests.test_system_acceptance.SystemAcceptanceSuiteTests.test_tc18_ui_action_count_and_accessibility`: passed.
- `tests.test_tasks_and_workflow.TasksAndWorkflowTests.test_tc18_usability_and_keyboard_controls`: passed.
- `tests.test_browser_compatibility.BrowserCompatibilityTests.test_chrome_stable_core_workflows`: passed.
- `tests.test_browser_compatibility.BrowserCompatibilityTests.test_firefox_core_workflows`: passed.

## Sprint changes reflected in this revision

- TC-09/10: non-finite and storage boundaries, invalid JSON shapes, date/note edits, ownership and retained totals.
- TC-16: exact ID retrieval plus the specified concurrent 20-user/100-request HTTP run; bounded query regression replaces an unmeasured scalability assumption.
- TC-17: independent processes and injected endpoint failures, beyond simple ORM refresh.
- TC-18: real browser action counts and keyboard steps at 1280x720, beyond static HTML inspection.
