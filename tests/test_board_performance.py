import math
import os
import time
from datetime import timedelta
from decimal import Decimal
from unittest import skipUnless

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import User
from audit.models import ActivityEvent
from projects.models import Membership, Project
from tasks.models import Task


@skipUnless(
    os.getenv("RUN_PERFORMANCE_TESTS") == "1",
    "Set RUN_PERFORMANCE_TESTS=1 to run NFR-01 measurements.",
)
class BoardPerformanceTests(TestCase):
    """
    NFR-01: At least 95% of board and task-list requests complete
    within two seconds.

    Dataset: 500 tasks, 20 project members, 2,000 activity events.
    Measurement: 5 warm-ups and 40 timed requests per endpoint.
    """

    WARMUPS = 5
    SAMPLES = 40
    LIMIT_SECONDS = 2.0

    @classmethod
    def setUpTestData(cls):
        cls.owner = User.objects.create_user(
            email="nfr01-owner@example.com",
            password="PerformanceTest123!",
        )
        cls.project = Project.objects.create(
            name="NFR-01 Performance Project",
            owner=cls.owner,
        )
        Membership.objects.create(
            project=cls.project,
            user=cls.owner,
            role=Membership.ROLE_OWNER,
        )

        # Add 19 more members, making 20 project members in total.
        User.objects.bulk_create([
            User(
                email=f"nfr01-member-{i}@example.com",
                full_name=f"Performance Member {i}",
            )
            for i in range(19)
        ])
        members = list(
            User.objects.filter(email__startswith="nfr01-member-").order_by("id")
        )
        Membership.objects.bulk_create([
            Membership(
                project=cls.project,
                user=member,
                role=Membership.ROLE_MEMBER,
            )
            for member in members
        ])
        assignees = [cls.owner, *members]

        # Distribute tasks across statuses, priorities, members, and due dates.
        statuses = [status for status, _ in Task.STATUS_CHOICES]
        priorities = [priority for priority, _ in Task.PRIORITY_CHOICES]
        today = timezone.now().date()

        Task.objects.bulk_create([
            Task(
                project=cls.project,
                title=f"Performance task {i:03d}",
                description="NFR-01 repeatable performance fixture",
                status=statuses[i % len(statuses)],
                priority=priorities[i % len(priorities)],
                assignee=assignees[i % len(assignees)],
                estimate_hours=Decimal("2.00"),
                due_date=today + timedelta(days=(i % 21) - 10),
            )
            for i in range(500)
        ])

        ActivityEvent.objects.bulk_create([
            ActivityEvent(
                project=cls.project,
                actor=cls.owner,
                action="PERFORMANCE_FIXTURE",
                entity_type="Task",
                entity_id=str(i),
                details=f"NFR-01 fixture event {i}",
            )
            for i in range(2000)
        ])

    def setUp(self):
        self.client.force_login(self.owner)

    def measure_endpoint(self, url):
        # Warm-up requests are intentionally excluded from the measurements.
        for _ in range(self.WARMUPS):
            response = self.client.get(url)
            self.assertEqual(
                response.status_code,
                200,
                f"Warm-up request failed for {url}: HTTP {response.status_code}",
            )

        durations = []
        last_response = None

        for _ in range(self.SAMPLES):
            started = time.perf_counter()
            response = self.client.get(url)
            elapsed = time.perf_counter() - started

            self.assertEqual(
                response.status_code,
                200,
                f"Measured request failed for {url}: HTTP {response.status_code}",
            )
            durations.append(elapsed)
            last_response = response

        ordered = sorted(durations)
        percentile_index = math.ceil(0.95 * len(ordered)) - 1
        p95_seconds = ordered[percentile_index]

        return p95_seconds, durations, last_response

    def test_nfr01_board_and_task_list_p95_under_two_seconds(self):
        board_url = reverse(
            "projects:project_detail",
            kwargs={"project_id": self.project.id},
        )
        task_list_url = reverse(
            "tasks:task_list_create",
            kwargs={"project_id": self.project.id},
        )

        board_p95, board_times, _ = self.measure_endpoint(board_url)
        tasks_p95, task_times, task_response = self.measure_endpoint(
            task_list_url
        )

        self.assertEqual(
            len(task_response.json()["tasks"]),
            500,
            "The task-list request must return the complete 500-task fixture.",
        )

        print(
            "\n[NFR-01 Performance Results] "
            f"board_html_p95={board_p95 * 1000:.1f} ms; "
            f"board_html_max={max(board_times) * 1000:.1f} ms; "
            f"task_list_p95={tasks_p95 * 1000:.1f} ms; "
            f"task_list_max={max(task_times) * 1000:.1f} ms; "
            f"samples_per_endpoint={self.SAMPLES}; "
            f"warmups_per_endpoint={self.WARMUPS}; "
            "fixture=500 tasks, 20 members, 2000 activity events",
            flush=True,
        )

        self.assertLessEqual(
            board_p95,
            self.LIMIT_SECONDS,
            "Board HTML p95 exceeded the 2-second NFR-01 limit.",
        )
        self.assertLessEqual(
            tasks_p95,
            self.LIMIT_SECONDS,
            "Task-list JSON p95 exceeded the 2-second NFR-01 limit.",
        )
