import json
from decimal import Decimal
from django.db import transaction
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from accounts.models import User
from audit.models import ActivityEvent
from projects.models import Project, Membership
from tasks.models import Task, TimeEntry, Comment

class ProjectsAndRolesTests(TestCase):
    """
    Verification of TC-03, TC-04, TC-13, TC-16, TC-17.
    SRS FR-03, FR-04, FR-15, FR-16, SR-01, NFR-01, NFR-02, NFR-03.
    """
    def setUp(self):
        self.owner = User.objects.create_user(email='owner@example.com', password='Password123!')
        self.manager = User.objects.create_user(email='manager@example.com', password='Password123!')
        self.member = User.objects.create_user(email='member@example.com', password='Password123!')
        self.outsider = User.objects.create_user(email='outsider@example.com', password='Password123!')

        self.client_owner = Client()
        self.client_owner.force_login(self.owner)

        self.client_member = Client()
        self.client_member.force_login(self.member)

        self.client_outsider = Client()
        self.client_outsider.force_login(self.outsider)

    def test_tc03_create_project(self):
        """TC-03: Submit complete project form -> Project created; creator Owner."""
        resp = self.client_owner.post(reverse('projects:project_list'), {
            'name': 'Alpha Project',
            'description': 'Description for Alpha',
            'start_date': str(timezone.now().date())
        })
        self.assertEqual(resp.status_code, 302)
        project = Project.objects.get(name='Alpha Project')
        self.assertEqual(project.owner, self.owner)

        membership = Membership.objects.get(project=project, user=self.owner)
        self.assertEqual(membership.role, Membership.ROLE_OWNER)

    def test_tc04_membership_and_role_control(self):
        """TC-04: Owner invites; Member tries role change -> Member denied (403)."""
        project = Project.objects.create(name='Beta Project', owner=self.owner)
        Membership.objects.create(project=project, user=self.owner, role=Membership.ROLE_OWNER)
        Membership.objects.create(project=project, user=self.member, role=Membership.ROLE_MEMBER)

        # Owner invites manager
        resp_invite = self.client_owner.post(
            reverse('projects:project_members', kwargs={'project_id': project.id}),
            json.dumps({'email': self.manager.email, 'role': Membership.ROLE_MANAGER}),
            content_type='application/json'
        )
        self.assertEqual(resp_invite.status_code, 201)
        self.assertTrue(Membership.objects.filter(project=project, user=self.manager, role=Membership.ROLE_MANAGER).exists())

        # Member tries to change own role to Owner (SR-01 / TC-04)
        resp_member_change = self.client_member.post(
            reverse('projects:project_member_role_update', kwargs={'project_id': project.id, 'member_user_id': self.member.id}),
            json.dumps({'role': Membership.ROLE_OWNER}),
            content_type='application/json'
        )
        self.assertEqual(resp_member_change.status_code, 403)

        # The canonical project owner cannot accidentally remove the last stable
        # Owner identity while Project.owner still points at that account.
        resp_owner_demote = self.client_owner.post(
            reverse('projects:project_member_role_update', kwargs={'project_id': project.id, 'member_user_id': self.owner.id}),
            json.dumps({'role': Membership.ROLE_MEMBER}),
            content_type='application/json'
        )
        self.assertEqual(resp_owner_demote.status_code, 400)
        self.assertEqual(resp_owner_demote.json()['error']['code'], 'OWNER_ROLE_REQUIRED')

    def test_tc13_csv_export_and_archive(self):
        """TC-13 / FR-16: Owner archives project; non-owners denied; read access retained; edits denied."""
        project = Project.objects.create(name='Gamma Project', owner=self.owner)
        Membership.objects.create(project=project, user=self.owner, role=Membership.ROLE_OWNER)
        Membership.objects.create(project=project, user=self.member, role=Membership.ROLE_MEMBER)
        task = Task.objects.create(project=project, title='Exportable Task', estimate_hours=Decimal('4.0'))

        # CSV Export before archival
        csv_resp = self.client_owner.get(reverse('tasks:project_tasks_csv', kwargs={'project_id': project.id}))
        self.assertEqual(csv_resp.status_code, 200)
        self.assertEqual(csv_resp['Content-Type'], 'text/csv')
        self.assertIn('Exportable Task', csv_resp.content.decode('utf-8'))

        # Non-owner (Member) attempts to archive -> 403 Forbidden
        member_archive_resp = self.client_member.post(
            reverse('projects:project_archive', kwargs={'project_id': project.id}),
            content_type='application/json'
        )
        self.assertEqual(member_archive_resp.status_code, 403)
        project.refresh_from_db()
        self.assertFalse(project.is_archived)

        # Outsider attempts to archive -> 404 Not Found
        outsider_archive_resp = self.client_outsider.post(
            reverse('projects:project_archive', kwargs={'project_id': project.id}),
            content_type='application/json'
        )
        self.assertEqual(outsider_archive_resp.status_code, 404)

        # Owner archives project (FR-16)
        archive_resp = self.client_owner.post(reverse('projects:project_archive', kwargs={'project_id': project.id}))
        self.assertEqual(archive_resp.status_code, 302)
        project.refresh_from_db()
        self.assertTrue(project.is_archived)
        self.assertIsNotNone(project.archived_at)

        # Attempt to archive an already archived project -> 409 Conflict
        rearchive_resp = self.client_owner.post(
            reverse('projects:project_archive', kwargs={'project_id': project.id}),
            content_type='application/json'
        )
        self.assertEqual(rearchive_resp.status_code, 409)
        self.assertEqual(rearchive_resp.json()['error']['code'], 'PROJECT_ALREADY_ARCHIVED')

        # Retain read access for Owner and Member
        detail_resp = self.client_member.get(reverse('projects:project_detail', kwargs={'project_id': project.id}))
        self.assertEqual(detail_resp.status_code, 200)
        self.assertContains(detail_resp, 'Archived')

        tasks_resp = self.client_member.get(reverse('tasks:task_list_create', kwargs={'project_id': project.id}))
        self.assertEqual(tasks_resp.status_code, 200)
        self.assertEqual(len(tasks_resp.json()['tasks']), 1)

        task_detail_resp = self.client_member.get(
            reverse('tasks:task_detail', kwargs={'project_id': project.id, 'task_id': task.id})
        )
        self.assertEqual(task_detail_resp.status_code, 200)

        dashboard_resp = self.client_member.get(reverse('tasks:project_dashboard', kwargs={'project_id': project.id}))
        self.assertEqual(dashboard_resp.status_code, 200)

        # Owner retains CSV export read access; Member is forbidden per FR-15
        csv_read_resp = self.client_owner.get(reverse('tasks:project_tasks_csv', kwargs={'project_id': project.id}))
        self.assertEqual(csv_read_resp.status_code, 200)
        self.assertEqual(self.client_member.get(reverse('tasks:project_tasks_csv', kwargs={'project_id': project.id})).status_code, 403)

        members_resp = self.client_member.get(reverse('projects:project_members', kwargs={'project_id': project.id}))
        self.assertEqual(members_resp.status_code, 200)

        # Attempt to create new task in archived project (Must return 409 Conflict)
        create_resp = self.client_owner.post(
            reverse('tasks:task_list_create', kwargs={'project_id': project.id}),
            json.dumps({'title': 'Task In Archived Project'}),
            content_type='application/json'
        )
        self.assertEqual(create_resp.status_code, 409)

    def test_archived_project_rejects_all_mutations(self):
        """FR-16: Prevent all modifications to archived project across tasks, time logs, comments, and members."""
        project = Project.objects.create(name='Archived Fortress', owner=self.owner, archived_at=timezone.now())
        Membership.objects.create(project=project, user=self.owner, role=Membership.ROLE_OWNER)
        Membership.objects.create(project=project, user=self.member, role=Membership.ROLE_MEMBER)

        task = Task.objects.create(project=project, title='Fortress Task', assignee=self.member)
        entry = TimeEntry.objects.create(task=task, user=self.owner, hours=Decimal('1.0'), date=timezone.now().date())

        candidate_user = User.objects.create_user(email='candidate@example.com', password='Password123!')

        # 1. Task Creation -> 409
        r_create = self.client_owner.post(
            reverse('tasks:task_list_create', kwargs={'project_id': project.id}),
            json.dumps({'title': 'Blocked Task'}),
            content_type='application/json'
        )
        self.assertEqual(r_create.status_code, 409)
        self.assertEqual(r_create.json()['error']['code'], 'PROJECT_ARCHIVED')

        # 2. Task Edit -> 409
        r_edit = self.client_owner.patch(
            reverse('tasks:task_detail', kwargs={'project_id': project.id, 'task_id': task.id}),
            json.dumps({'title': 'Attempted Update'}),
            content_type='application/json'
        )
        self.assertEqual(r_edit.status_code, 409)
        self.assertEqual(r_edit.json()['error']['code'], 'PROJECT_ARCHIVED')

        # 3. Task Status Move -> 409
        r_move = self.client_owner.patch(
            reverse('tasks:task_status_transition', kwargs={'project_id': project.id, 'task_id': task.id}),
            json.dumps({'status': Task.STATUS_IN_PROGRESS, 'expected_version': 1}),
            content_type='application/json'
        )
        self.assertEqual(r_move.status_code, 409)
        self.assertEqual(r_move.json()['error']['code'], 'PROJECT_ARCHIVED')

        # 4. Log Time -> 409
        r_time = self.client_owner.post(
            reverse('tasks:task_time_log', kwargs={'project_id': project.id, 'task_id': task.id}),
            json.dumps({'hours': 1.0}),
            content_type='application/json'
        )
        self.assertEqual(r_time.status_code, 409)
        self.assertEqual(r_time.json()['error']['code'], 'PROJECT_ARCHIVED')

        # 5. Edit Time Entry -> 409
        r_time_edit = self.client_owner.put(
            reverse('tasks:time_entry_detail', kwargs={'project_id': project.id, 'task_id': task.id, 'entry_id': entry.id}),
            json.dumps({'hours': 2.0}),
            content_type='application/json'
        )
        self.assertEqual(r_time_edit.status_code, 409)
        self.assertEqual(r_time_edit.json()['error']['code'], 'PROJECT_ARCHIVED')

        # 6. Delete Time Entry -> 409
        r_time_delete = self.client_owner.delete(
            reverse('tasks:time_entry_detail', kwargs={'project_id': project.id, 'task_id': task.id, 'entry_id': entry.id}),
            content_type='application/json'
        )
        self.assertEqual(r_time_delete.status_code, 409)
        self.assertEqual(r_time_delete.json()['error']['code'], 'PROJECT_ARCHIVED')

        # 7. Post Comment -> 409
        r_comment = self.client_owner.post(
            reverse('tasks:task_comment_create', kwargs={'project_id': project.id, 'task_id': task.id}),
            json.dumps({'text': 'Blocked Comment'}),
            content_type='application/json'
        )
        self.assertEqual(r_comment.status_code, 409)
        self.assertEqual(r_comment.json()['error']['code'], 'PROJECT_ARCHIVED')

        # 8. Member Invite -> 409
        r_invite = self.client_owner.post(
            reverse('projects:project_members', kwargs={'project_id': project.id}),
            json.dumps({'email': candidate_user.email, 'role': Membership.ROLE_MEMBER}),
            content_type='application/json'
        )
        self.assertEqual(r_invite.status_code, 409)
        self.assertEqual(r_invite.json()['error']['code'], 'PROJECT_ARCHIVED')

        # 9. Role Update -> 409
        r_role = self.client_owner.post(
            reverse('projects:project_member_role_update', kwargs={'project_id': project.id, 'member_user_id': self.member.id}),
            json.dumps({'role': Membership.ROLE_MANAGER}),
            content_type='application/json'
        )
        self.assertEqual(r_role.status_code, 409)
        self.assertEqual(r_role.json()['error']['code'], 'PROJECT_ARCHIVED')

        # 10. Re-Archival -> 409
        r_archive = self.client_owner.post(
            reverse('projects:project_archive', kwargs={'project_id': project.id}),
            content_type='application/json'
        )
        self.assertEqual(r_archive.status_code, 409)
        self.assertEqual(r_archive.json()['error']['code'], 'PROJECT_ALREADY_ARCHIVED')

    def test_tc16_capacity_limits(self):
        """TC-16: Support 500 tasks, 20 members, and 2,000 audit events."""
        project = Project.objects.create(name='Capacity Project', owner=self.owner)
        Membership.objects.create(project=project, user=self.owner, role=Membership.ROLE_OWNER)

        users = [User(email=f'capacity-{i}@example.com') for i in range(19)]
        User.objects.bulk_create(users)
        Membership.objects.bulk_create([
            Membership(project=project, user=user, role=Membership.ROLE_MEMBER)
            for user in User.objects.filter(email__startswith='capacity-')
        ])

        # Batch create 500 tasks (NFR-02 capacity verification)
        bulk_tasks = [
            Task(project=project, title=f"Task #{i}", status=Task.STATUS_BACKLOG, estimate_hours=Decimal('1.0'))
            for i in range(500)
        ]
        Task.objects.bulk_create(bulk_tasks)

        ActivityEvent.objects.bulk_create([
            ActivityEvent(
                project=project,
                actor=self.owner,
                action='CAPACITY_TEST',
                entity_type='Task',
                entity_id=str(i),
                details=f'Capacity event #{i}',
            )
            for i in range(2000)
        ])

        self.assertEqual(Membership.objects.filter(project=project).count(), 20)
        self.assertEqual(Task.objects.filter(project=project).count(), 500)
        self.assertEqual(ActivityEvent.objects.filter(project=project).count(), 2000)

        # Verify board request completes cleanly
        resp = self.client_owner.get(reverse('tasks:task_list_create', kwargs={'project_id': project.id}))
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(len(data['tasks']), 500)

    def test_tc17_transaction_commit_and_rollback(self):
        """TC-17: Committed data survives refresh; aborted transactions leave no partial rows."""
        project = Project.objects.create(name='Reliability Project', owner=self.owner)
        Membership.objects.create(project=project, user=self.owner, role=Membership.ROLE_OWNER)

        with transaction.atomic():
            committed = Task.objects.create(project=project, title='Committed Task')
        committed.refresh_from_db()
        self.assertEqual(committed.title, 'Committed Task')

        with self.assertRaises(RuntimeError):
            with transaction.atomic():
                Task.objects.create(project=project, title='Rolled Back Task')
                ActivityEvent.objects.create(
                    project=project,
                    actor=self.owner,
                    action='ROLLBACK_TEST',
                    entity_type='Task',
                    details='This row must be rolled back with the task.',
                )
                raise RuntimeError('force transaction rollback')

        self.assertFalse(Task.objects.filter(project=project, title='Rolled Back Task').exists())
        self.assertFalse(ActivityEvent.objects.filter(project=project, action='ROLLBACK_TEST').exists())
