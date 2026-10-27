import json
from decimal import Decimal
from django.contrib.auth import get_user_model
from django.test import TestCase, Client
from django.urls import reverse
from audit.models import ActivityEvent
from notifications.models import Notification
from projects.models import Project, Membership
from tasks.models import Task, TimeEntry, Comment

User = get_user_model()


class IntegrationWorkflowsTests(TestCase):
    """
    Verification tests for TEST-02: Integration testing (Issue #36).
    Tests API-to-database operations, authentication, role-based authorization,
    persistence, and transactional activity history recording across all modules.
    """

    def setUp(self):
        self.client_owner = Client()
        self.client_manager = Client()
        self.client_member = Client()
        self.client_outsider = Client()

        self.owner = User.objects.create_user(email='owner@testcorp.com', password='Password123!', full_name='Owner User')
        self.manager = User.objects.create_user(email='manager@testcorp.com', password='Password123!', full_name='Manager User')
        self.member = User.objects.create_user(email='member@testcorp.com', password='Password123!', full_name='Member User')
        self.outsider = User.objects.create_user(email='outsider@testcorp.com', password='Password123!', full_name='Outsider User')

        self.client_owner.force_login(self.owner)
        self.client_manager.force_login(self.manager)
        self.client_member.force_login(self.member)
        self.client_outsider.force_login(self.outsider)

    def test_end_to_end_project_and_membership_flow(self):
        """Verify project workspace creation, owner assignment, member invitations, and notification dispatch."""
        # 1. Owner creates project
        create_resp = self.client_owner.post(
            reverse('projects:project_list'),
            json.dumps({'name': 'Enterprise Migration', 'description': 'Cloud migration workspace'}),
            content_type='application/json'
        )
        self.assertEqual(create_resp.status_code, 201)
        project_id = create_resp.json()['id']
        project = Project.objects.get(id=project_id)
        self.assertEqual(project.owner, self.owner)
        self.assertTrue(Membership.objects.filter(project=project, user=self.owner, role=Membership.ROLE_OWNER).exists())

        # 2. Owner invites Manager and Member
        invite_url = reverse('projects:project_members', kwargs={'project_id': project.id})
        resp_inv_mgr = self.client_owner.post(invite_url, {'email': self.manager.email, 'role': Membership.ROLE_MANAGER})
        self.assertEqual(resp_inv_mgr.status_code, 302)

        resp_inv_mem = self.client_owner.post(invite_url, {'email': self.member.email, 'role': Membership.ROLE_MEMBER})
        self.assertEqual(resp_inv_mem.status_code, 302)

        # 3. Assert memberships persisted in DB
        self.assertTrue(Membership.objects.filter(project=project, user=self.manager, role=Membership.ROLE_MANAGER).exists())
        self.assertTrue(Membership.objects.filter(project=project, user=self.member, role=Membership.ROLE_MEMBER).exists())

        # 4. Assert notifications dispatched to invited users
        notifs_mgr = Notification.objects.filter(recipient=self.manager)
        self.assertEqual(notifs_mgr.count(), 1)
        self.assertIn('Enterprise Migration', notifs_mgr.first().message)

    def test_end_to_end_task_crud_and_audit_logging(self):
        """Verify task lifecycle: creation, assignment, title mutation, and transactional audit trail."""
        project = Project.objects.create(name='Workflow Project', owner=self.owner)
        Membership.objects.create(project=project, user=self.owner, role=Membership.ROLE_OWNER)
        Membership.objects.create(project=project, user=self.manager, role=Membership.ROLE_MANAGER)
        Membership.objects.create(project=project, user=self.member, role=Membership.ROLE_MEMBER)

        # Manager creates task assigned to Member
        tasks_url = reverse('tasks:task_list_create', kwargs={'project_id': project.id})
        create_resp = self.client_manager.post(
            tasks_url,
            json.dumps({
                'title': 'Build Auth Service',
                'description': 'Implement OAuth2 endpoints',
                'priority': 'High',
                'estimate_hours': 4.5,
                'assignee_id': self.member.id
            }),
            content_type='application/json'
        )
        self.assertEqual(create_resp.status_code, 201)
        task_id = create_resp.json()['id']

        # Verify task state in database
        task = Task.objects.get(id=task_id)
        self.assertEqual(task.status, Task.STATUS_BACKLOG)
        self.assertEqual(task.version, 1)
        self.assertEqual(task.estimate_hours, Decimal('4.5'))
        self.assertEqual(task.assignee, self.member)

        # Verify audit log recorded creation
        creation_event = ActivityEvent.objects.filter(project=project, action='TASK_CREATED', entity_id=str(task.id)).first()
        self.assertIsNotNone(creation_event)
        self.assertEqual(creation_event.actor, self.manager)

        # Member updates title
        detail_url = reverse('tasks:task_detail', kwargs={'project_id': project.id, 'task_id': task.id})
        edit_resp = self.client_member.patch(
            detail_url,
            json.dumps({'title': 'Build Auth Service v2'}),
            content_type='application/json'
        )
        self.assertEqual(edit_resp.status_code, 200)

        task.refresh_from_db()
        self.assertEqual(task.title, 'Build Auth Service v2')
        self.assertEqual(task.version, 2)

        # Verify audit log recorded edit
        edit_event = ActivityEvent.objects.filter(project=project, action='TASK_EDITED', entity_id=str(task.id)).first()
        self.assertIsNotNone(edit_event)
        self.assertEqual(edit_event.actor, self.member)

    def test_role_based_mutation_authorization_boundaries(self):
        """Verify strict authorization enforcement for Member vs Manager/Owner and outsiders."""
        project = Project.objects.create(name='RBAC Project', owner=self.owner)
        Membership.objects.create(project=project, user=self.owner, role=Membership.ROLE_OWNER)
        Membership.objects.create(project=project, user=self.manager, role=Membership.ROLE_MANAGER)
        Membership.objects.create(project=project, user=self.member, role=Membership.ROLE_MEMBER)

        task = Task.objects.create(
            project=project,
            title='Boundary Test Task',
            assignee=self.member,
            estimate_hours=Decimal('3.0')
        )

        detail_url = reverse('tasks:task_detail', kwargs={'project_id': project.id, 'task_id': task.id})

        # Member attempting to alter estimate must receive 403 Forbidden
        mem_est_resp = self.client_member.patch(
            detail_url,
            json.dumps({'estimate_hours': 6.0}),
            content_type='application/json'
        )
        self.assertEqual(mem_est_resp.status_code, 403)

        # Member attempting to reassign task must receive 403 Forbidden
        mem_asg_resp = self.client_member.patch(
            detail_url,
            json.dumps({'assignee_id': self.manager.id}),
            content_type='application/json'
        )
        self.assertEqual(mem_asg_resp.status_code, 403)

        # Outsider attempting to access task must receive 403 or 404
        outsider_resp = self.client_outsider.get(detail_url)
        self.assertIn(outsider_resp.status_code, [403, 404])

    def test_time_logging_and_dashboard_recalculation_integration(self):
        """Verify time logging updates actual hours on the task and aggregates onto the progress dashboard."""
        project = Project.objects.create(name='Tracking Project', owner=self.owner)
        Membership.objects.create(project=project, user=self.owner, role=Membership.ROLE_OWNER)
        Membership.objects.create(project=project, user=self.member, role=Membership.ROLE_MEMBER)

        task = Task.objects.create(project=project, title='Logging Task', estimate_hours=Decimal('5.0'), assignee=self.member)
        time_url = reverse('tasks:task_time_log', kwargs={'project_id': project.id, 'task_id': task.id})

        # Log 1.25 hours
        resp1 = self.client_member.post(
            time_url,
            json.dumps({'hours': 1.25, 'note': 'First slice'}),
            content_type='application/json'
        )
        self.assertEqual(resp1.status_code, 201)

        # Log 2.50 hours
        resp2 = self.client_member.post(
            time_url,
            json.dumps({'hours': 2.50, 'note': 'Second slice'}),
            content_type='application/json'
        )
        self.assertEqual(resp2.status_code, 201)

        task.refresh_from_db()
        self.assertEqual(task.actual_hours, Decimal('3.75'))

        # Query dashboard API
        dash_url = reverse('tasks:project_dashboard', kwargs={'project_id': project.id})
        dash_resp = self.client_member.get(dash_url)
        self.assertEqual(dash_resp.status_code, 200)
        dash_data = dash_resp.json()
        self.assertEqual(dash_data['total_tasks'], 1)
        self.assertEqual(Decimal(str(dash_data['actual_hours'])), Decimal('3.75'))
        self.assertEqual(Decimal(str(dash_data['estimated_hours'])), Decimal('5.0'))

    def test_optimistic_concurrency_control_integration(self):
        """Verify optimistic concurrency version checking prevents overwrites and returns 409 Conflict."""
        project = Project.objects.create(name='Concurrency Project', owner=self.owner)
        Membership.objects.create(project=project, user=self.owner, role=Membership.ROLE_OWNER)
        Membership.objects.create(project=project, user=self.member, role=Membership.ROLE_MEMBER)

        task = Task.objects.create(project=project, title='Concurrent Task', status=Task.STATUS_BACKLOG, version=1)
        status_url = reverse('tasks:task_status_transition', kwargs={'project_id': project.id, 'task_id': task.id})

        # Successful transition with current version 1
        resp_ok = self.client_owner.patch(
            status_url,
            json.dumps({'status': Task.STATUS_IN_PROGRESS, 'expected_version': 1}),
            content_type='application/json'
        )
        self.assertEqual(resp_ok.status_code, 200)
        task.refresh_from_db()
        self.assertEqual(task.status, Task.STATUS_IN_PROGRESS)
        self.assertEqual(task.version, 2)

        # Conflicting transition with stale version 1
        resp_conflict = self.client_member.patch(
            status_url,
            json.dumps({'status': Task.STATUS_DONE, 'expected_version': 1}),
            content_type='application/json'
        )
        self.assertEqual(resp_conflict.status_code, 409)
        task.refresh_from_db()
        self.assertEqual(task.status, Task.STATUS_IN_PROGRESS)

    def test_project_archival_lifecycle(self):
        """Verify archiving a project locks all mutation operations with HTTP 409 Conflict."""
        project = Project.objects.create(name='Archival Project', owner=self.owner)
        Membership.objects.create(project=project, user=self.owner, role=Membership.ROLE_OWNER)
        task = Task.objects.create(project=project, title='Archived Task', status=Task.STATUS_TODO)

        # Archive project
        archive_url = reverse('projects:project_archive', kwargs={'project_id': project.id})
        arch_resp = self.client_owner.post(archive_url)
        self.assertEqual(arch_resp.status_code, 302)
        project.refresh_from_db()
        self.assertTrue(project.is_archived)

        # Status transition in archived project rejected with 409
        status_url = reverse('tasks:task_status_transition', kwargs={'project_id': project.id, 'task_id': task.id})
        resp = self.client_owner.patch(
            status_url,
            json.dumps({'status': Task.STATUS_DONE, 'expected_version': task.version}),
            content_type='application/json'
        )
        self.assertEqual(resp.status_code, 409)
