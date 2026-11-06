# Unit Test Report

Execution: 2026-11-06T17:46:12.589413+00:00 (GitHub Actions). Python 3.12.16, Django 5.2.19, SQLite. Source revision: `de496554513c8ce0ba146965949f9c16eb6a01ed`.

Platform: Linux-7.0.0-1019-azure-x86_64-with-glibc2.43. The Part 3 test settings create and destroy a separate on-disk database; development data is not used.

## Scope and outcome

The focused unit group contains the existing task parsing, task calculations,
validation/workflow rule and environment configuration suites. Some focused
rule tests exercise the database/API; this group is not described as entirely
isolated pure-function testing. The wider integration and browser suites are
reported separately.

23 methods: 23 passed, 0 non-pass outcomes.

Sprint updates add NaN/sNaN/infinity/boolean rejection and impossible calendar
dates to the earlier parser cases. API boundary and date-edit regressions from
Iteration 2 remain in the full run.

| Test method | Result | Seconds |
| --- | --- | --- |
| test_actual_hours_updates_when_entries_are_added_and_deleted | passed | 0.183 |
| test_overdue_calculation_respects_due_date_and_done_status | passed | 0.173 |
| test_estimate_accepts_half_hour_steps_and_rejects_other_values | passed | 0.209 |
| test_invalid_status_does_not_change_task_or_create_audit_event | passed | 0.191 |
| test_non_integer_expected_version_is_rejected | passed | 0.193 |
| test_stale_version_returns_conflict_without_changing_task | passed | 0.191 |
| test_allowed_hosts_are_required_when_debug_is_disabled | passed | 0.000 |
| test_allowed_hosts_are_split_and_trimmed | passed | 0.000 |
| test_allowed_hosts_reject_empty_value | passed | 0.000 |
| test_allowed_hosts_use_local_defaults_only_in_debug | passed | 0.000 |
| test_boolean_setting_accepts_common_true_and_false_values | passed | 0.000 |
| test_boolean_setting_rejects_invalid_values | passed | 0.000 |
| test_boolean_setting_uses_default_when_unset | passed | 0.000 |
| test_secret_key_has_local_only_fallback_in_debug | passed | 0.000 |
| test_secret_key_is_required_when_debug_is_disabled | passed | 0.000 |
| test_secret_key_rejects_example_placeholder | passed | 0.000 |
| test_secret_key_requires_minimum_length_in_production | passed | 0.000 |
| test_secret_key_uses_configured_value | passed | 0.000 |
| test_wildcard_hosts_are_rejected_when_debug_is_disabled | passed | 0.000 |
| test_parse_decimal_accepts_numeric_values | passed | 0.000 |
| test_parse_decimal_rejects_invalid_values | passed | 0.000 |
| test_parse_optional_date_handles_blank_and_valid_dates | passed | 0.000 |
| test_parse_optional_date_rejects_invalid_dates | passed | 0.000 |

## Evidence and limits

135 unique test methods verified across functional/coverage and separate untraced performance runs: 135 passed, 0 unexecuted/skipped, 0 failures and 0 errors. Combined runner time: 75.307 seconds. [Functional/coverage log](evidence/full_test_run.txt), [untraced performance log](evidence/performance_run.txt), [named outcomes](evidence/test_results.json), [environment/commands](evidence/environment.json). The functional run deliberately skips the two opt-in performance methods, which are then executed separately; these placeholders are replaced by their measured outcomes, not counted as additional unique tests.
Subtests exercise multiple inputs; they are not inflated into additional test
method counts. Passing tests do not establish exhaustive input correctness.
