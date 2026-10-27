import os
import unittest

from django.contrib.staticfiles.testing import StaticLiveServerTestCase

from accounts.models import User
from tasks.models import Task

try:
    from playwright.sync_api import expect, sync_playwright
except ImportError:
    expect = None
    sync_playwright = None


BROWSER_TESTS_ENABLED = (
    os.environ.get("RUN_BROWSER_TESTS") == "1"
    and sync_playwright is not None
)


@unittest.skipUnless(
    BROWSER_TESTS_ENABLED,
    "Set RUN_BROWSER_TESTS=1 and install Playwright to run browser tests.",
)
class BrowserCompatibilityTests(StaticLiveServerTestCase):
    """NFR-06: Exercise core UI workflows in Chrome Stable and Firefox."""

    def setUp(self):
        self.email = "browser-test@example.com"
        self.password = "StrongPassword123!"
        User.objects.create_user(
            email=self.email,
            password=self.password,
            full_name="Browser Test User",
        )

    def test_chrome_stable_core_workflows(self):
        """Verify login, project/task creation, search and status changes."""
        self._run_core_workflows("Chrome")

    def test_firefox_core_workflows(self):
        """Verify the same core workflows in Playwright-managed Firefox."""
        self._run_core_workflows("Firefox")

    def _run_core_workflows(self, browser_name):
        with sync_playwright() as playwright:
            if browser_name == "Chrome":
                browser = playwright.chromium.launch(
                    channel="chrome",
                    headless=True,
                )
            else:
                browser = playwright.firefox.launch(headless=True)

            try:
                print(
                    f"\n[NFR-06] {browser_name} version: "
                    f"{browser.version}"
                )

                page = browser.new_page()
                page_errors = []

                page.on(
                    "pageerror",
                    lambda error: page_errors.append(str(error)),
                )

                # 1. Sign in through the actual browser form.
                page.goto(
                    f"{self.live_server_url}/accounts/login/",
                    wait_until="domcontentloaded",
                )
                expect(page.locator("#login-form")).to_be_visible()
                page.locator("#email").fill(self.email)
                page.locator("#password").fill(self.password)
                page.locator("#btn-submit-login").click()

                # 2. Create a project using the project creation dialog.
                expect(
                    page.locator("#btn-open-create-project")
                ).to_be_visible()

                project_name = f"{browser_name} Compatibility Project"
                page.locator("#btn-open-create-project").click()
                page.locator("#project-name").fill(project_name)
                page.locator("#project-desc").fill(
                    "Automated cross-browser compatibility test."
                )
                page.locator("#btn-submit-project").click()

                expect(
                    page.locator("h1").filter(has_text=project_name)
                ).to_be_visible()

                # 3. Create a task through the board UI.
                task_name = f"{browser_name} Browser Test Task"
                expect(page.locator("#btn-create-task")).to_be_visible()
                page.locator("#btn-create-task").click()
                page.locator("#task-title-input").fill(task_name)
                page.locator("#btn-submit-task").click()

                backlog_card = page.locator(
                    '.column-body[data-status="Backlog"] .task-card'
                ).filter(has_text=task_name)
                expect(backlog_card).to_be_visible()

                # 4. Confirm that the board dashboard loads task data.
                expect(page.locator("#dash-total-tasks")).to_have_text("1")

                # 5. Check task search and restoration of the matching result.
                search = page.locator("#task-search")
                search.fill("no-such-browser-test-task")
                expect(page.locator(".task-card")).to_have_count(0)

                search.fill(task_name)
                backlog_card = page.locator(
                    '.column-body[data-status="Backlog"] .task-card'
                ).filter(has_text=task_name)
                expect(backlog_card).to_be_visible()

                # 6. Open task details and move it to In Progress.
                backlog_card.click()
                expect(page.locator("#task-detail-modal")).to_be_visible()
                page.locator("#modal-status-select").select_option(
                    label="In Progress"
                )

                moved_card = page.locator(
                    '.column-body[data-status="In Progress"] .task-card'
                ).filter(has_text=task_name)
                expect(moved_card).to_be_visible()

                # Fail on uncaught JavaScript exceptions in the UI.
                self.assertEqual(
                    page_errors,
                    [],
                    f"{browser_name} raised JavaScript errors: {page_errors}",
                )
            finally:
                browser.close()

        # Query Django only after Playwright's event loop has closed.
        task = Task.objects.get(
            project__name=project_name,
            title=task_name,
        )
        self.assertEqual(task.status, Task.STATUS_IN_PROGRESS)
