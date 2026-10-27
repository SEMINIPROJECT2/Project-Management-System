from datetime import timedelta
from decimal import Decimal

from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import User
from projects.models import Membership, Project
from tasks.models import Task, TimeEntry


class ProgressDashboardTests(TestCase):
    """Focused acceptance tests for SRS FR-11 progress dashboard."""

    def setUp(self):
        self.owner = User.objects.create_user(
            email="dashboard-owner@example.com",
            password="StrongPassword123!",
        )
        self.member = User.objects.create_user(
            email="dashboard-member@example.com",
            password="StrongPassword123!",
        )
        self.outsider = User.objects.create_user(
            email="dashboard-outsider@example.com",
            password="StrongPassword123!",
        )

        self.project = Project.objects.create(
            name="Dashboard Test Project",
            owner=self.owner,
        )

        Membership.objects.create(
            project=self.project,
            user=self.owner,
            role=Membership.ROLE_OWNER,
        )
        Membership.objects.create(
            project=self.project,
            user=self.member,
            role=Membership.ROLE_MEMBER,
        )

        self.client_owner = Client()
        self.client_owner.force_login(self.owner)

        self.client_member = Client()
        self.client_member.force_login(self.member)

        self.client_outsider = Client()
        self.client_outsider.force_login(self.outsider)

        self.dashboard_url = reverse(
            "tasks:project_dashboard",
            kwargs={"project_id": self.project.id},
        )

    def test_dashboard_reports_status_counts_and_hour_totals(self):
        today = timezone.now().date()
        yesterday = today - timedelta(days=1)
        tomorrow = today + timedelta(days=1)

        backlog = Task.objects.create(
            project=self.project,
            title="Overdue backlog task",
            status=Task.STATUS_BACKLOG,
            due_date=yesterday,
            estimate_hours=Decimal("3.00"),
        )
        todo = Task.objects.create(
            project=self.project,
            title="Task due today",
            status=Task.STATUS_TODO,
            due_date=today,
            estimate_hours=Decimal("2.00"),
        )
        in_progress = Task.objects.create(
            project=self.project,
            title="Overdue active task",
            status=Task.STATUS_IN_PROGRESS,
            due_date=yesterday,
            estimate_hours=Decimal("4.50"),
        )
        review = Task.objects.create(
            project=self.project,
            title="Future review task",
            status=Task.STATUS_REVIEW,
            due_date=tomorrow,
            estimate_hours=Decimal("1.50"),
        )
        done = Task.objects.create(
            project=self.project,
            title="Completed overdue-date task",
            status=Task.STATUS_DONE,
            due_date=yesterday,
            estimate_hours=Decimal("5.00"),
        )

        TimeEntry.objects.create(
            task=backlog,
            user=self.member,
            hours=Decimal("1.25"),
            date=today,
            note="Backlog work",
        )
        TimeEntry.objects.create(
            task=todo,
            user=self.member,
            hours=Decimal("0.75"),
            date=today,
            note="To Do work",
        )
        TimeEntry.objects.create(
            task=done,
            user=self.member,
            hours=Decimal("2.00"),
            date=today,
            note="Completed work",
        )

        response = self.client_member.get(
            self.dashboard_url,
            HTTP_ACCEPT="application/json",
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertEqual(
            data["status_counts"],
            {
                Task.STATUS_BACKLOG: 1,
                Task.STATUS_TODO: 1,
                Task.STATUS_IN_PROGRESS: 1,
                Task.STATUS_REVIEW: 1,
                Task.STATUS_DONE: 1,
            },
        )
        self.assertEqual(data["total_tasks"], 5)
        self.assertEqual(data["overdue_count"], 2)
        self.assertEqual(data["estimated_hours"], "16.00")
        self.assertEqual(data["actual_hours"], "4.00")

    def test_empty_project_returns_zero_metrics(self):
        response = self.client_owner.get(
            self.dashboard_url,
            HTTP_ACCEPT="application/json",
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertEqual(
            data["status_counts"],
            {
                Task.STATUS_BACKLOG: 0,
                Task.STATUS_TODO: 0,
                Task.STATUS_IN_PROGRESS: 0,
                Task.STATUS_REVIEW: 0,
                Task.STATUS_DONE: 0,
            },
        )
        self.assertEqual(data["total_tasks"], 0)
        self.assertEqual(data["overdue_count"], 0)
        self.assertEqual(data["estimated_hours"], "0.00")
        self.assertEqual(data["actual_hours"], "0.00")

    def test_dashboard_totals_exclude_other_projects(self):
        today = timezone.now().date()

        Task.objects.create(
            project=self.project,
            title="Current project task",
            estimate_hours=Decimal("2.00"),
        )

        other_project = Project.objects.create(
            name="Separate Project",
            owner=self.owner,
        )
        other_task = Task.objects.create(
            project=other_project,
            title="Other project task",
            estimate_hours=Decimal("100.00"),
        )

        TimeEntry.objects.create(
            task=other_task,
            user=self.member,
            hours=Decimal("99.00"),
            date=today,
            note="Must not affect current dashboard",
        )

        current_task = Task.objects.get(
            project=self.project,
            title="Current project task",
        )
        TimeEntry.objects.create(
            task=current_task,
            user=self.member,
            hours=Decimal("1.50"),
            date=today,
            note="Current project work",
        )

        response = self.client_member.get(
            self.dashboard_url,
            HTTP_ACCEPT="application/json",
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertEqual(data["total_tasks"], 1)
        self.assertEqual(data["estimated_hours"], "2.00")
        self.assertEqual(data["actual_hours"], "1.50")

    def test_dashboard_requires_project_membership_and_get_method(self):
        owner_response = self.client_owner.get(
            self.dashboard_url,
            HTTP_ACCEPT="application/json",
        )
        member_response = self.client_member.get(
            self.dashboard_url,
            HTTP_ACCEPT="application/json",
        )
        outsider_response = self.client_outsider.get(
            self.dashboard_url,
            HTTP_ACCEPT="application/json",
        )
        anonymous_response = self.client.get(
            self.dashboard_url,
            HTTP_ACCEPT="application/json",
        )
        post_response = self.client_member.post(
            self.dashboard_url,
            data="{}",
            content_type="application/json",
            HTTP_ACCEPT="application/json",
        )

        self.assertEqual(owner_response.status_code, 200)
        self.assertEqual(member_response.status_code, 200)
        self.assertEqual(outsider_response.status_code, 404)
        self.assertEqual(anonymous_response.status_code, 401)
        self.assertEqual(post_response.status_code, 405)
