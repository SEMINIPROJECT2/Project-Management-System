import csv
import io
from decimal import Decimal
from datetime import timedelta

from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import User
from projects.models import Membership, Project
from tasks.models import Task, TimeEntry


class TaskCSVExportTests(TestCase):
    """Acceptance tests for SRS FR-15 CSV task export."""

    def setUp(self):
        self.owner = User.objects.create_user(
            email="csv-owner@example.com",
            password="StrongPassword123!",
        )
        self.manager = User.objects.create_user(
            email="csv-manager@example.com",
            password="StrongPassword123!",
        )
        self.member = User.objects.create_user(
            email="csv-member@example.com",
            password="StrongPassword123!",
        )
        self.outsider = User.objects.create_user(
            email="csv-outsider@example.com",
            password="StrongPassword123!",
        )

        self.project = Project.objects.create(
            name="CSV Export Project",
            owner=self.owner,
        )

        for user, role in (
            (self.owner, Membership.ROLE_OWNER),
            (self.manager, Membership.ROLE_MANAGER),
            (self.member, Membership.ROLE_MEMBER),
        ):
            Membership.objects.create(
                project=self.project,
                user=user,
                role=role,
            )

        self.client_owner = Client()
        self.client_owner.force_login(self.owner)

        self.client_manager = Client()
        self.client_manager.force_login(self.manager)

        self.client_member = Client()
        self.client_member.force_login(self.member)

        self.client_outsider = Client()
        self.client_outsider.force_login(self.outsider)

        self.export_url = reverse(
            "tasks:project_tasks_csv",
            kwargs={"project_id": self.project.id},
        )

    def read_csv(self, response):
        """Parse the actual HTTP response as CSV rows."""
        return list(
            csv.reader(
                io.StringIO(response.content.decode("utf-8"), newline="")
            )
        )

    def test_csv_contains_required_columns_and_correct_task_values(self):
        due_date = timezone.now().date() + timedelta(days=5)

        task = Task.objects.create(
            project=self.project,
            title='Fix, "quoted"\nCSV export',
            status=Task.STATUS_IN_PROGRESS,
            assignee=self.member,
            estimate_hours=Decimal("2.50"),
            due_date=due_date,
        )

        TimeEntry.objects.create(
            task=task,
            user=self.member,
            hours=Decimal("1.25"),
            date=timezone.now().date(),
            note="CSV export test work",
        )

        response = self.client_owner.get(self.export_url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/csv")
        self.assertEqual(
            response["Content-Disposition"],
            'attachment; filename="CSV_Export_Project_tasks.csv"',
        )

        rows = self.read_csv(response)

        self.assertEqual(
            rows[0],
            [
                "ID",
                "Title",
                "Status",
                "Assignee",
                "Estimate (Hours)",
                "Actual Hours",
                "Due Date",
            ],
        )

        self.assertEqual(len(rows), 2)
        self.assertEqual(
            rows[1],
            [
                str(task.id),
                'Fix, "quoted"\nCSV export',
                Task.STATUS_IN_PROGRESS,
                self.member.email,
                "2.50",
                "1.25",
                due_date.isoformat(),
            ],
        )

    def test_csv_orders_tasks_and_uses_unassigned_and_missing_date_values(self):
        first_task = Task.objects.create(
            project=self.project,
            title="First task",
            estimate_hours=Decimal("1.00"),
        )
        second_task = Task.objects.create(
            project=self.project,
            title="Second task",
            assignee=self.member,
            estimate_hours=Decimal("3.50"),
        )

        response = self.client_manager.get(self.export_url)

        self.assertEqual(response.status_code, 200)
        rows = self.read_csv(response)

        self.assertEqual(len(rows), 3)
        self.assertEqual(
            [row[0] for row in rows[1:]],
            [str(first_task.id), str(second_task.id)],
        )
        self.assertEqual(rows[1][1], "First task")
        self.assertEqual(rows[1][3], "Unassigned")
        self.assertEqual(rows[1][6], "None")
        self.assertEqual(rows[2][3], self.member.email)
        self.assertEqual(rows[2][4], "3.50")
        self.assertEqual(rows[2][5], "0.00")
        self.assertEqual(rows[2][6], "None")

    def test_csv_excludes_tasks_from_other_projects(self):
        current_task = Task.objects.create(
            project=self.project,
            title="Included project task",
            estimate_hours=Decimal("2.00"),
        )

        other_project = Project.objects.create(
            name="Different Project",
            owner=self.owner,
        )
        other_task = Task.objects.create(
            project=other_project,
            title="Should never appear in this export",
            estimate_hours=Decimal("99.00"),
        )

        response = self.client_owner.get(self.export_url)

        self.assertEqual(response.status_code, 200)
        rows = self.read_csv(response)
        exported_ids = [row[0] for row in rows[1:]]
        exported_titles = [row[1] for row in rows[1:]]

        self.assertEqual(exported_ids, [str(current_task.id)])
        self.assertIn(current_task.title, exported_titles)
        self.assertNotIn(other_task.title, exported_titles)

    def test_empty_project_exports_header_without_data_rows(self):
        response = self.client_owner.get(self.export_url)

        self.assertEqual(response.status_code, 200)
        rows = self.read_csv(response)

        self.assertEqual(
            rows,
            [[
                "ID",
                "Title",
                "Status",
                "Assignee",
                "Estimate (Hours)",
                "Actual Hours",
                "Due Date",
            ]],
        )

    def test_export_permissions_authentication_and_get_only_method(self):
        owner_response = self.client_owner.get(
            self.export_url,
            HTTP_ACCEPT="application/json",
        )
        manager_response = self.client_manager.get(
            self.export_url,
            HTTP_ACCEPT="application/json",
        )
        member_response = self.client_member.get(
            self.export_url,
            HTTP_ACCEPT="application/json",
        )
        outsider_response = self.client_outsider.get(
            self.export_url,
            HTTP_ACCEPT="application/json",
        )
        anonymous_response = self.client.get(
            self.export_url,
            HTTP_ACCEPT="application/json",
        )
        post_response = self.client_owner.post(
            self.export_url,
            data="{}",
            content_type="application/json",
            HTTP_ACCEPT="application/json",
        )

        self.assertEqual(owner_response.status_code, 200)
        self.assertEqual(owner_response["Content-Type"], "text/csv")

        self.assertEqual(manager_response.status_code, 200)
        self.assertEqual(manager_response["Content-Type"], "text/csv")

        self.assertEqual(member_response.status_code, 403)
        self.assertEqual(outsider_response.status_code, 404)
        self.assertEqual(anonymous_response.status_code, 401)
        self.assertEqual(post_response.status_code, 405)
