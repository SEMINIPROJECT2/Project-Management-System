import json
from datetime import timedelta
from decimal import Decimal
from pathlib import Path

from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import User
from audit.models import ActivityEvent
from projects.models import Membership, Project
from tasks.models import Task


class KanbanBoardUITests(TestCase):
    """Integration tests for SRS ENG-05 Kanban board UI."""

    def setUp(self):
        self.owner = User.objects.create_user(
            email="kanban-owner@example.com",
            password="StrongPassword123!",
        )
        self.manager = User.objects.create_user(
            email="kanban-manager@example.com",
            password="StrongPassword123!",
        )
        self.member = User.objects.create_user(
            email="kanban-member@example.com",
            password="StrongPassword123!",
        )
        self.outsider = User.objects.create_user(
            email="kanban-outsider@example.com",
            password="StrongPassword123!",
        )

        self.project = Project.objects.create(
            name="Kanban UI Test Project",
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

        self.board_url = reverse(
            "projects:project_detail",
            kwargs={"project_id": self.project.id},
        )
        self.task_list_url = reverse(
            "tasks:task_list_create",
            kwargs={"project_id": self.project.id},
        )

    def test_board_renders_five_status_columns_and_board_script(self):
        response = self.client_manager.get(self.board_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="kanban-columns-container"')

        for status in (
            Task.STATUS_BACKLOG,
            Task.STATUS_TODO,
            Task.STATUS_IN_PROGRESS,
            Task.STATUS_REVIEW,
            Task.STATUS_DONE,
        ):
            with self.subTest(status=status):
                self.assertContains(
                    response,
                    f'data-status="{status}"',
                )

        self.assertContains(response, "js/board.js")
        self.assertContains(response, 'id="modal-status-select"')

    def test_task_card_renderer_displays_status_and_estimate_safely(self):
        board_js = (
            Path(__file__).resolve().parents[1]
            / "static"
            / "js"
            / "board.js"
        ).read_text(encoding="utf-8-sig")

        self.assertIn(
            'class="task-status">Status: ${this.escapeHtml(task.status)}</span>',
            board_js,
        )
        self.assertIn(
            'class="task-estimate">Estimate: ${this.escapeHtml(String(task.estimate_hours))}h</span>',
            board_js,
        )
        self.assertIn("class=\"task-meta task-meta-secondary\"", board_js)
        self.assertIn("this.escapeHtml(task.title)", board_js)
        self.assertIn("this.escapeHtml(task.due_date)", board_js)

        self.assertIn("window.KanbanBoard = KanbanBoard", board_js)
        self.assertIn("this.renderBoard()", board_js)

    def test_task_api_supplies_fields_needed_by_board_cards(self):
        due_date = timezone.now().date() + timedelta(days=5)
        task = Task.objects.create(
            project=self.project,
            title="Display task metadata",
            status=Task.STATUS_IN_PROGRESS,
            priority=Task.PRIORITY_HIGH,
            assignee=self.member,
            estimate_hours=Decimal("2.50"),
            due_date=due_date,
        )

        response = self.client_manager.get(
            self.task_list_url,
            HTTP_ACCEPT="application/json",
        )

        self.assertEqual(response.status_code, 200)
        tasks = response.json()["tasks"]
        self.assertEqual(len(tasks), 1)

        card_data = tasks[0]
        self.assertEqual(card_data["id"], task.id)
        self.assertEqual(card_data["title"], "Display task metadata")
        self.assertEqual(card_data["status"], Task.STATUS_IN_PROGRESS)
        self.assertEqual(card_data["priority"], Task.PRIORITY_HIGH)
        self.assertEqual(card_data["estimate_hours"], "2.50")
        self.assertEqual(card_data["assignee_email"], self.member.email)
        self.assertEqual(card_data["due_date"], due_date.isoformat())
        self.assertIn("version", card_data)

    def test_manager_can_change_status_and_updated_board_data_is_returned(self):
        task = Task.objects.create(
            project=self.project,
            title="Move through Kanban",
            status=Task.STATUS_BACKLOG,
            estimate_hours=Decimal("1.50"),
            version=1,
        )
        status_url = reverse(
            "tasks:task_status_transition",
            kwargs={
                "project_id": self.project.id,
                "task_id": task.id,
            },
        )

        response = self.client_manager.patch(
            status_url,
            json.dumps({
                "status": Task.STATUS_IN_PROGRESS,
                "expected_version": 1,
            }),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], Task.STATUS_IN_PROGRESS)
        self.assertEqual(response.json()["version"], 2)

        task.refresh_from_db()
        self.assertEqual(task.status, Task.STATUS_IN_PROGRESS)
        self.assertEqual(task.version, 2)

        board_response = self.client_manager.get(
            self.task_list_url,
            HTTP_ACCEPT="application/json",
        )
        self.assertEqual(board_response.status_code, 200)

        updated_task = next(
            item for item in board_response.json()["tasks"]
            if item["id"] == task.id
        )
        self.assertEqual(updated_task["status"], Task.STATUS_IN_PROGRESS)
        self.assertEqual(updated_task["estimate_hours"], "1.50")

        self.assertTrue(
            ActivityEvent.objects.filter(
                project=self.project,
                action="TASK_MOVED",
                entity_id=str(task.id),
            ).exists()
            or ActivityEvent.objects.filter(
                project=self.project,
                action="TASK_MOVED",
                entity_id=task.id,
            ).exists()
        )

    def test_outsider_cannot_access_board_or_task_api(self):
        board_response = self.client_outsider.get(
            self.board_url,
            HTTP_ACCEPT="application/json",
        )
        task_response = self.client_outsider.get(
            self.task_list_url,
            HTTP_ACCEPT="application/json",
        )

        self.assertEqual(board_response.status_code, 404)
        self.assertEqual(task_response.status_code, 404)
