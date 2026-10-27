import json

from django.test import TestCase
from django.urls import reverse

from accounts.models import User
from notifications.models import Notification
from projects.models import Membership, Project
from tasks.models import Task


class NotificationWorkflowTests(TestCase):
    """Focused tests for SRS FR-17 in-app notification behavior."""

    def setUp(self):
        self.owner = User.objects.create_user(
            email="notify-owner@example.com",
            password="StrongPassword123!",
        )
        self.manager = User.objects.create_user(
            email="notify-manager@example.com",
            password="StrongPassword123!",
        )
        self.member = User.objects.create_user(
            email="notify-member@example.com",
            password="StrongPassword123!",
        )
        self.invitee = User.objects.create_user(
            email="notify-invitee@example.com",
            password="StrongPassword123!",
        )

        self.project = Project.objects.create(
            name="Notification Test Project",
            owner=self.owner,
        )

        Membership.objects.create(
            project=self.project,
            user=self.owner,
            role=Membership.ROLE_OWNER,
        )
        Membership.objects.create(
            project=self.project,
            user=self.manager,
            role=Membership.ROLE_MANAGER,
        )
        Membership.objects.create(
            project=self.project,
            user=self.member,
            role=Membership.ROLE_MEMBER,
        )

        self.client_owner = self.client_class()
        self.client_owner.force_login(self.owner)

        self.client_manager = self.client_class()
        self.client_manager.force_login(self.manager)

        self.client_member = self.client_class()
        self.client_member.force_login(self.member)

        self.task_create_url = reverse(
            "tasks:task_list_create",
            kwargs={"project_id": self.project.id},
        )
        self.invite_url = reverse(
            "projects:project_members",
            kwargs={"project_id": self.project.id},
        )

    def test_task_assignment_sends_one_notification_to_assignee(self):
        response = self.client_manager.post(
            self.task_create_url,
            json.dumps({
                "title": "Build notification feature",
                "assignee_id": self.member.id,
            }),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 201)
        task_id = response.json()["id"]

        notifications = Notification.objects.filter(
            recipient=self.member,
        )
        self.assertEqual(notifications.count(), 1)

        notification = notifications.get()
        self.assertEqual(
            notification.title,
            f"New Task Assigned: #{task_id}",
        )
        self.assertIn("Build notification feature", notification.message)
        self.assertIn(self.project.name, notification.message)
        self.assertEqual(
            notification.link,
            f"/projects/{self.project.id}/",
        )
        self.assertFalse(notification.is_read)
        self.assertEqual(
            Notification.objects.filter(recipient=self.owner).count(),
            0,
        )

    def test_assigning_task_to_actor_does_not_notify_actor(self):
        response = self.client_manager.post(
            self.task_create_url,
            json.dumps({
                "title": "Self-assigned task",
                "assignee_id": self.manager.id,
            }),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(
            Notification.objects.filter(recipient=self.manager).count(),
            0,
        )

    def test_owner_invitation_sends_one_notification_to_invitee(self):
        response = self.client_owner.post(
            self.invite_url,
            json.dumps({
                "email": self.invitee.email,
                "role": Membership.ROLE_MANAGER,
            }),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 201)

        membership = Membership.objects.get(
            project=self.project,
            user=self.invitee,
        )
        self.assertEqual(membership.role, Membership.ROLE_MANAGER)

        notifications = Notification.objects.filter(
            recipient=self.invitee,
        )
        self.assertEqual(notifications.count(), 1)

        notification = notifications.get()
        self.assertEqual(
            notification.title,
            f"Invited to {self.project.name}",
        )
        self.assertIn("Manager", notification.message)
        self.assertIn(self.project.name, notification.message)
        self.assertEqual(
            notification.link,
            f"/projects/{self.project.id}/",
        )
        self.assertFalse(notification.is_read)

    def test_unknown_or_duplicate_invitation_sends_no_notification(self):
        unknown_response = self.client_owner.post(
            self.invite_url,
            json.dumps({
                "email": "unknown-notify-user@example.com",
                "role": Membership.ROLE_MEMBER,
            }),
            content_type="application/json",
        )

        self.assertEqual(unknown_response.status_code, 404)
        self.assertEqual(
            unknown_response.json()["error"]["code"],
            "USER_NOT_FOUND",
        )

        duplicate_response = self.client_owner.post(
            self.invite_url,
            json.dumps({
                "email": self.member.email,
                "role": Membership.ROLE_MEMBER,
            }),
            content_type="application/json",
        )

        self.assertEqual(duplicate_response.status_code, 400)
        self.assertEqual(
            duplicate_response.json()["error"]["code"],
            "ALREADY_MEMBER",
        )
        self.assertEqual(
            Notification.objects.filter(
                recipient=self.member,
            ).count(),
            0,
        )

    def test_non_owner_cannot_invite_or_notify_user(self):
        response = self.client_member.post(
            self.invite_url,
            json.dumps({
                "email": self.invitee.email,
                "role": Membership.ROLE_MEMBER,
            }),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 403)
        self.assertFalse(
            Membership.objects.filter(
                project=self.project,
                user=self.invitee,
            ).exists()
        )
        self.assertEqual(
            Notification.objects.filter(
                recipient=self.invitee,
            ).count(),
            0,
        )

    def test_notification_list_contains_only_current_users_notifications(self):
        own_notification = Notification.objects.create(
            recipient=self.member,
            title="Your task was assigned",
            message="A task was assigned to you.",
            link=f"/projects/{self.project.id}/",
        )
        Notification.objects.create(
            recipient=self.manager,
            title="Private manager notification",
            message="This belongs to another user.",
        )

        response = self.client_member.get(
            reverse("notifications:list"),
            HTTP_ACCEPT="application/json",
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()["notifications"]
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["id"], own_notification.id)
        self.assertEqual(data[0]["title"], "Your task was assigned")
        self.assertFalse(data[0]["is_read"])

    def test_only_recipient_can_mark_notification_as_read(self):
        notification = Notification.objects.create(
            recipient=self.member,
            title="Read permission test",
            message="Only the recipient may mark this as read.",
        )
        read_url = reverse(
            "notifications:mark_read",
            kwargs={"notification_id": notification.id},
        )

        forbidden_response = self.client_manager.post(
            read_url,
            HTTP_ACCEPT="application/json",
        )

        self.assertEqual(forbidden_response.status_code, 404)
        notification.refresh_from_db()
        self.assertFalse(notification.is_read)

        owner_response = self.client_member.post(
            read_url,
            HTTP_ACCEPT="application/json",
        )

        self.assertEqual(owner_response.status_code, 200)
        self.assertTrue(owner_response.json()["success"])

        notification.refresh_from_db()
        self.assertTrue(notification.is_read)

    def test_mark_all_read_only_changes_current_users_notifications(self):
        member_unread = Notification.objects.create(
            recipient=self.member,
            title="Member unread notification",
            message="This should become read.",
        )
        member_read = Notification.objects.create(
            recipient=self.member,
            title="Member already read notification",
            message="This should remain read.",
            is_read=True,
        )
        manager_unread = Notification.objects.create(
            recipient=self.manager,
            title="Manager unread notification",
            message="This must remain unread.",
        )

        response = self.client_member.post(
            reverse("notifications:mark_all_read"),
            HTTP_ACCEPT="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["success"])

        member_unread.refresh_from_db()
        member_read.refresh_from_db()
        manager_unread.refresh_from_db()

        self.assertTrue(member_unread.is_read)
        self.assertTrue(member_read.is_read)
        self.assertFalse(manager_unread.is_read)
