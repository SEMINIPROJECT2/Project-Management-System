# Browser Compatibility Verification — NFR-06

**Verification date:** 26 October 2026

## Objective

Verify core project-management workflows in Chrome and Firefox through
headless Playwright browser automation.

## Locally tested browsers

- Google Chrome: 155.0.8059.86
- Playwright-managed Firefox: 157.0

These are the versions observed locally. The local Chrome installation was
not upgraded during this verification, so version 155 is not claimed to be
the latest Chrome Stable release.

## Workflow coverage

The automated tests cover:

1. Signing in through the browser login form.
2. Creating a project through the user interface.
3. Creating a task on the Kanban board.
4. Verifying that the dashboard task count updates.
5. Searching for tasks, including a search with no results.
6. Opening task details and moving a task to In Progress.
7. Verifying the final task status in the database.
8. Checking for uncaught JavaScript page exceptions.

## Local verification results

Command: `python manage.py test --verbosity=2`

- Full regression suite: 21 tests passed.
- Django system check: passed.
- `git diff --check`: no whitespace errors.

Dedicated browser command:
`python manage.py test tests.test_browser_compatibility --verbosity=2`

- Chrome workflow: passed.
- Firefox workflow: passed.
- Total: 2 browser tests passed.

## Continuous integration

The workflow at `.github/workflows/browser-compatibility.yml` is configured
to install Chrome and Firefox and run the browser tests for pull requests
targeting main.

GitHub Actions results must be checked after the pull request is opened.
A successful CI run has not yet been verified.

## Scope and limitations

This is headless desktop-browser workflow testing. It does not establish
compatibility across every operating system, browser version, device, or
assistive technology. The local Chrome version is recorded explicitly so
that the results remain reproducible and accurately described.
