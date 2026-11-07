# Part 3 submission

Required deliverables:

- [Updated Test Case Document v1.1](../TEST_CASE_DOCUMENT.md)
- [Unit Test Report](UNIT_TEST_REPORT.md)
- [System Validation Report](SYSTEM_VALIDATION_REPORT.md)
- [Code Coverage Report](CODE_COVERAGE_REPORT.md)
- [Branch Coverage Report](BRANCH_COVERAGE_REPORT.md)
- [Optional Sprint 3 spillover report](SPRINT_3_REPORT.md)
- [Coverage HTML](coverage_html/index.html) and [raw evidence](evidence/)

135 unique test methods verified across functional/coverage and separate untraced performance runs: 135 passed, 0 unexecuted/skipped, 0 failures and 0 errors. Combined runner time: 75.307 seconds.
Statement coverage: 87.39%.
Branch coverage: 76.49%.

Reproduce using `python scripts/run_part3_tests.py`. Install
`requirements-test.txt` and run `python -m playwright install --with-deps chrome firefox`
first. On a normal Chrome install no executable override is needed. An extracted
vendor Chrome can be selected with `PMS_CHROME_EXECUTABLE`.
`PART3_SKIP_CHROME=1` is only for an execution-restricted local runtime and
produces an explicit skip and incomplete gate; it is not a release pass.


Hosted qualification passed; a separate constrained local runtime had a Chrome launch restriction and a load-timing failure. See SYSTEM_VALIDATION_REPORT.md and evidence/local_run/ for both results.
