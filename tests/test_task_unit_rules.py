from datetime import date, timedelta
from decimal import Decimal
import json

from django.test import SimpleTestCase, TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import User
from audit.models import ActivityEvent
from projects.models import Project, Membership
from tasks.models import Task, TimeEntry
from tasks.views import parse_decimal, parse_optional_date


class TaskInputHelperUnitTests(SimpleTestCase):
    """Focused tests for task input parsing helpers."""

    def test_parse_decimal_accepts_numeric_values(self):
        self.assertEqual(parse_decimal("2.5"), Decimal("2.5"))
        self.assertEqual(parse_decimal(0), Decimal("0"))
        self.assertEqual(parse_decimal(1.25), Decimal("1.25"))

    def test_parse_decimal_rejects_invalid_values(self):
        for value in (None, "", "not-a-number"):
            with self.subTest(value=value):
                self.assertIsNone(parse_decimal(value))

    def test_parse_optional_date_handles_blank_and_valid_dates(self):
        expected = date(2026, 10, 26)

        self.assertIsNone(parse_optional_date(None))
        self.assertIsNone(parse_optional_date(""))
        self.assertEqual(parse_optional_date(expected), expected)
        self.assertEqual(parse_optional_date("2026-10-26"), expected)

    def test_parse_optional_date_rejects_invalid_dates(self):
        for value in ("not-a-date", "2026-13-40", "26/10/2026"):
            with self.subTest(value=value):
                self.assertIs(parse_optional_date(value), False)


class TaskCalculationUnitTests(TestCase):
    """Focused tests for task time totals and overdue calculation."""

    def setUp(self):
        self.user = User.objects.create_user(
            email="unit-owner@example.com",
            password="StrongPassword123!",
        )
        self.project = Project.objects.create(
            name="Unit Test Project",
            owner=self.user,
        )
        self.task = Task.objects.create(
            project=self.project,
            title="Time Calculation Task",
        )

    def test_actual_hours_updates_when_entries_are_added_and_deleted(self):
        self.assertEqual(self.task.actual_hours, Decimal("0.00"))

        first = TimeEntry.objects.create(
            task=self.task,
            user=self.user,
            hours=Decimal("1.25"),
        )
        TimeEntry.objects.create(
            task=self.task,
            user=self.user,
            hours=Decimal("0.75"),
        )

        self.assertEqual(self.task.actual_hours, Decimal("2.00"))

        first.delete()
        self.assertEqual(self.task.actual_hours, Decimal("0.75"))

    def test_overdue_calculation_respects_due_date_and_done_status(self):
        today = timezone.now().date()

        past_task = Task.objects.create(
            project=self.project,
            title="Past Due",
            status=Task.STATUS_TODO,
            due_date=today - timedelta(days=1),
        )
        today_task = Task.objects.create(
            project=self.project,
            title="Due Today",
            status=Task.STATUS_TODO,
            due_date=today,
        )
        future_task = Task.objects.create(
            project=self.project,
            title="Future Due",
            status=Task.STATUS_TODO,
            due_date=today + timedelta(days=1),
        )
        completed_task = Task.objects.create(
            project=self.project,
            title="Completed Past Due",
            status=Task.STATUS_DONE,
            due_date=today - timedelta(days=1),
        )

        self.assertTrue(past_task.is_overdue)
        self.assertFalse(today_task.is_overdue)
        self.assertFalse(future_task.is_overdue)
        self.assertFalse(completed_task.is_overdue)
        self.assertFalse(self.task.is_overdue)


class TaskValidationAndWorkflowUnitTests(TestCase):
    """Boundary and failure-path tests for task creation and transitions."""

    def setUp(self):
        self.user = User.objects.create_user(
            email="workflow-owner@example.com",
            password="StrongPassword123!",
        )
        self.project = Project.objects.create(
            name="Workflow Unit Test Project",
            owner=self.user,
        )
        Membership.objects.create(
            project=self.project,
            user=self.user,
            role=Membership.ROLE_OWNER,
        )

        self.client.force_login(self.user)
        self.create_url = reverse(
            "tasks:task_list_create",
            kwargs={"project_id": self.project.id},
        )

        self.task = Task.objects.create(
            project=self.project,
            title="Workflow Boundary Task",
            status=Task.STATUS_BACKLOG,
            version=1,
        )
        self.status_url = reverse(
            "tasks:task_status_transition",
            kwargs={
                "project_id": self.project.id,
                "task_id": self.task.id,
            },
        )

    def test_estimate_accepts_half_hour_steps_and_rejects_other_values(self):
        for value in ("0", "0.5", "1.0", "2.5"):
            with self.subTest(valid_estimate=value):
                response = self.client.post(
                    self.create_url,
                    json.dumps({
                        "title": f"Valid Estimate {value}",
                        "estimate_hours": value,
                    }),
                    content_type="application/json",
                )
                self.assertEqual(response.status_code, 201)

        for value in ("0.25", "0.75", "-0.5", "abc"):
            with self.subTest(invalid_estimate=value):
                response = self.client.post(
                    self.create_url,
                    json.dumps({
                        "title": f"Invalid Estimate {value}",
                        "estimate_hours": value,
                    }),
                    content_type="application/json",
                )
                self.assertEqual(response.status_code, 400)
                self.assertEqual(
                    response.json()["error"]["code"],
                    "INVALID_ESTIMATE",
                )

    def test_invalid_status_does_not_change_task_or_create_audit_event(self):
        response = self.client.patch(
            self.status_url,
            json.dumps({
                "status": "Blocked",
                "expected_version": 1,
            }),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"]["code"], "INVALID_STATUS")

        self.task.refresh_from_db()
        self.assertEqual(self.task.status, Task.STATUS_BACKLOG)
        self.assertEqual(self.task.version, 1)
        self.assertFalse(
            ActivityEvent.objects.filter(
                project=self.project,
                action="TASK_MOVED",
            ).exists()
        )

    def test_stale_version_returns_conflict_without_changing_task(self):
        response = self.client.patch(
            self.status_url,
            json.dumps({
                "status": Task.STATUS_IN_PROGRESS,
                "expected_version": 99,
            }),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["error"]["code"], "CONFLICT")

        self.task.refresh_from_db()
        self.assertEqual(self.task.status, Task.STATUS_BACKLOG)
        self.assertEqual(self.task.version, 1)
        self.assertFalse(
            ActivityEvent.objects.filter(
                project=self.project,
                action="TASK_MOVED",
            ).exists()
        )

    def test_non_integer_expected_version_is_rejected(self):
        response = self.client.patch(
            self.status_url,
            json.dumps({
                "status": Task.STATUS_IN_PROGRESS,
                "expected_version": "not-an-integer",
            }),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"]["code"], "BAD_REQUEST")

        self.task.refresh_from_db()
        self.assertEqual(self.task.status, Task.STATUS_BACKLOG)
        self.assertEqual(self.task.version, 1)
