from datetime import timedelta

from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import User
from projects.models import Membership, Project
from tasks.models import Comment, Task


class TaskCommentAcceptanceTests(TestCase):
    """Acceptance tests for SRS FR-12 task comments."""

    def setUp(self):
        self.owner = User.objects.create_user(
            email="comments-owner@example.com",
            password="StrongPassword123!",
        )
        self.member = User.objects.create_user(
            email="comments-member@example.com",
            password="StrongPassword123!",
        )
        self.outsider = User.objects.create_user(
            email="comments-outsider@example.com",
            password="StrongPassword123!",
        )

        self.project = Project.objects.create(
            name="Comment Test Project",
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

        self.task = Task.objects.create(
            project=self.project,
            title="Task for comment tests",
        )

        self.client_owner = Client()
        self.client_owner.force_login(self.owner)

        self.client_member = Client()
        self.client_member.force_login(self.member)

        self.client_outsider = Client()
        self.client_outsider.force_login(self.outsider)

        self.comment_url = reverse(
            "tasks:task_comment_create",
            kwargs={
                "project_id": self.project.id,
                "task_id": self.task.id,
            },
        )
        self.task_detail_url = reverse(
            "tasks:task_detail",
            kwargs={
                "project_id": self.project.id,
                "task_id": self.task.id,
            },
        )

    def test_member_can_add_comment_and_response_contains_required_fields(self):
        response = self.client_member.post(
            self.comment_url,
            '{"text": "  This task is ready for review.  "}',
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 201)
        data = response.json()

        self.assertIn("id", data)
        self.assertEqual(data["author"], self.member.email)
        self.assertEqual(data["text"], "This task is ready for review.")
        self.assertTrue(data["created_at"])
        self.assertTrue(data["message"])

        comment = Comment.objects.get(pk=data["id"])
        self.assertEqual(comment.task, self.task)
        self.assertEqual(comment.author, self.member)
        self.assertEqual(comment.text, "This task is ready for review.")

        detail_response = self.client_member.get(
            self.task_detail_url,
            HTTP_ACCEPT="application/json",
        )

        self.assertEqual(detail_response.status_code, 200)
        comments = detail_response.json()["comments"]

        self.assertEqual(len(comments), 1)
        self.assertEqual(comments[0]["id"], comment.id)
        self.assertEqual(comments[0]["author"], self.member.email)
        self.assertEqual(comments[0]["text"], "This task is ready for review.")
        self.assertEqual(comments[0]["created_at"], data["created_at"])

    def test_empty_and_whitespace_comments_are_rejected(self):
        for text in ("", "   ", "\n\t  "):
            with self.subTest(text=repr(text)):
                response = self.client_member.post(
                    self.comment_url,
                    __import__("json").dumps({"text": text}),
                    content_type="application/json",
                )

                self.assertEqual(response.status_code, 400)
                self.assertEqual(
                    response.json()["error"]["code"],
                    "BAD_REQUEST",
                )

        self.assertEqual(
            Comment.objects.filter(task=self.task).count(),
            0,
        )

    def test_task_detail_displays_comments_in_chronological_order(self):
        older = Comment.objects.create(
            task=self.task,
            author=self.member,
            text="First comment",
        )
        newer = Comment.objects.create(
            task=self.task,
            author=self.owner,
            text="Second comment",
        )

        base_time = timezone.now() - timedelta(minutes=5)
        Comment.objects.filter(pk=older.pk).update(
            created_at=base_time,
        )
        Comment.objects.filter(pk=newer.pk).update(
            created_at=base_time + timedelta(minutes=1),
        )

        response = self.client_member.get(
            self.task_detail_url,
            HTTP_ACCEPT="application/json",
        )

        self.assertEqual(response.status_code, 200)
        comments = response.json()["comments"]

        self.assertEqual(
            [comment["id"] for comment in comments],
            [older.id, newer.id],
        )
        self.assertEqual(
            [comment["text"] for comment in comments],
            ["First comment", "Second comment"],
        )
        self.assertEqual(
            [comment["author"] for comment in comments],
            [self.member.email, self.owner.email],
        )
        self.assertLess(
            comments[0]["created_at"],
            comments[1]["created_at"],
        )

    def test_outsider_cannot_read_or_add_project_comments(self):
        read_response = self.client_outsider.get(
            self.task_detail_url,
            HTTP_ACCEPT="application/json",
        )
        create_response = self.client_outsider.post(
            self.comment_url,
            '{"text": "Unauthorized comment"}',
            content_type="application/json",
            HTTP_ACCEPT="application/json",
        )

        self.assertEqual(read_response.status_code, 404)
        self.assertEqual(create_response.status_code, 404)
        self.assertEqual(
            Comment.objects.filter(task=self.task).count(),
            0,
        )
