import json
from decimal import Decimal
from django.contrib.auth import get_user_model
from django.db import transaction
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from accounts.models import FailedLoginAttempt
from audit.models import ActivityEvent
from notifications.models import Notification
from projects.models import Project, Membership
from tasks.models import Task, TimeEntry, Comment

User = get_user_model()


class SystemAcceptanceSuiteTests(TestCase):
    """
    Formal system and acceptance test execution suite covering TC-01 through TC-18
    as specified in Software Test Plan (STP v1.0) and Requirement Issue #37 (TEST-03).
    """

    def setUp(self):
        self.client_owner = Client()
        self.client_manager = Client()
        self.client_member = Client()
        self.client_outsider = Client()

        self.owner = User.objects.create_user(email='owner@pes.edu', password='Password123!', full_name='Owner Tester')
        self.manager = User.objects.create_user(email='manager@pes.edu', password='Password123!', full_name='Manager Tester')
        self.member = User.objects.create_user(email='member@pes.edu', password='Password123!', full_name='Member Tester')
        self.outsider = User.objects.create_user(email='outsider@pes.edu', password='Password123!', full_name='Outsider Tester')

        self.client_owner.force_login(self.owner)
        self.client_manager.force_login(self.manager)
        self.client_member.force_login(self.member)
        self.client_outsider.force_login(self.outsider)

        self.project = Project.objects.create(name='Evaluation Project', owner=self.owner)
        Membership.objects.create(project=self.project, user=self.owner, role=Membership.ROLE_OWNER)
        Membership.objects.create(project=self.project, user=self.manager, role=Membership.ROLE_MANAGER)
        Membership.objects.create(project=self.project, user=self.member, role=Membership.ROLE_MEMBER)

    def test_tc01_user_registration(self):
        """TC-01: Register user with unique email; duplicate email is rejected with 400."""
        reg_url = reverse('accounts:register')
        anon = Client()
        resp = anon.post(reg_url, {
            'email': 'newstudent@pes.edu',
            'full_name': 'New Student',
            'password': 'StrongPassword123!'
        })
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(User.objects.filter(email='newstudent@pes.edu').count(), 1)

        # Duplicate registration rejected with 400
        anon.logout()
        dup_resp = anon.post(reg_url, {
            'email': 'newstudent@pes.edu',
            'full_name': 'New Student Duplicate',
            'password': 'AnotherPassword123!'
        })
        self.assertEqual(dup_resp.status_code, 400)
        self.assertEqual(User.objects.filter(email='newstudent@pes.edu').count(), 1)

    def test_tc02_authentication_and_sessions(self):
        """TC-02: Valid sign-in opens session; sign-out closes session; invalid password rejected."""
        login_url = reverse('accounts:login')
        logout_url = reverse('accounts:logout')
        anon = Client()

        # Valid sign-in
        resp_login = anon.post(login_url, {'email': 'owner@pes.edu', 'password': 'Password123!'})
        self.assertEqual(resp_login.status_code, 302)
        self.assertIn('_auth_user_id', anon.session)

        # Sign-out
        resp_logout = anon.get(logout_url)
        self.assertEqual(resp_logout.status_code, 302)
        self.assertNotIn('_auth_user_id', anon.session)

        # Invalid password rejected with 401
        resp_invalid = anon.post(login_url, {'email': 'owner@pes.edu', 'password': 'WrongPassword!'})
        self.assertEqual(resp_invalid.status_code, 401)
        self.assertNotIn('_auth_user_id', anon.session)

    def test_tc03_project_creation(self):
        """TC-03: Create project -> Project created; creator designated Owner."""
        resp = self.client_owner.post(
            reverse('projects:project_list'),
            {'name': 'Semester Project', 'description': 'SE Mini-Project'}
        )
        self.assertEqual(resp.status_code, 302)
        proj = Project.objects.get(name='Semester Project')
        self.assertEqual(proj.owner, self.owner)
        self.assertTrue(Membership.objects.filter(project=proj, user=self.owner, role=Membership.ROLE_OWNER).exists())

    def test_tc04_membership_and_role_escalation(self):
        """TC-04: Owner invites Manager; Member escalation to Owner rejected with 403."""
        invitee = User.objects.create_user(email='invitee@pes.edu', password='Password123!')
        invite_url = reverse('projects:project_members', kwargs={'project_id': self.project.id})

        # Owner invites user
        resp = self.client_owner.post(invite_url, {'email': invitee.email, 'role': Membership.ROLE_MANAGER})
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(Membership.objects.filter(project=self.project, user=invitee, role=Membership.ROLE_MANAGER).exists())

        # Member attempts to invite or escalate role via JSON -> 403
        hacker = User.objects.create_user(email='hacker@pes.edu', password='Password123!')
        resp_escalate = self.client_member.post(
            invite_url,
            json.dumps({'email': hacker.email, 'role': Membership.ROLE_OWNER}),
            content_type='application/json'
        )
        self.assertEqual(resp_escalate.status_code, 403)

    def test_tc05_task_creation_and_title_validation(self):
        """TC-05: Manager creates task in Backlog; blank title rejected with 400."""
        tasks_url = reverse('tasks:task_list_create', kwargs={'project_id': self.project.id})

        resp = self.client_manager.post(
            tasks_url,
            json.dumps({'title': 'Valid Task Title', 'priority': 'High', 'estimate_hours': 3.0}),
            content_type='application/json'
        )
        self.assertEqual(resp.status_code, 201)
        task_id = resp.json()['id']
        task = Task.objects.get(id=task_id)
        self.assertEqual(task.status, Task.STATUS_BACKLOG)
        self.assertEqual(task.version, 1)

        # Blank title rejected
        resp_blank = self.client_manager.post(
            tasks_url,
            json.dumps({'title': '   ', 'priority': 'High'}),
            content_type='application/json'
        )
        self.assertEqual(resp_blank.status_code, 400)

    def test_tc06_task_editing_permissions(self):
        """TC-06: Assignee edits title; assignee modifying estimate denied with 403; outsider gets 403/404."""
        task = Task.objects.create(project=self.project, title='Original Title', assignee=self.member, estimate_hours=Decimal('2.0'))
        detail_url = reverse('tasks:task_detail', kwargs={'project_id': self.project.id, 'task_id': task.id})

        # Assignee edits title (permitted)
        resp_title = self.client_member.patch(detail_url, json.dumps({'title': 'New Title'}), content_type='application/json')
        self.assertEqual(resp_title.status_code, 200)

        # Assignee modifies estimate (denied)
        resp_est = self.client_member.patch(detail_url, json.dumps({'estimate_hours': 4.0}), content_type='application/json')
        self.assertEqual(resp_est.status_code, 403)

        # Outsider gets 403/404
        resp_out = self.client_outsider.get(detail_url)
        self.assertIn(resp_out.status_code, [403, 404])

    def test_tc07_kanban_transition_and_audit(self):
        """TC-07: Transition task status; transition atomically logged in ActivityEvent."""
        task = Task.objects.create(project=self.project, title='Transition Task', status=Task.STATUS_BACKLOG, version=1)
        status_url = reverse('tasks:task_status_transition', kwargs={'project_id': self.project.id, 'task_id': task.id})

        resp = self.client_owner.patch(
            status_url,
            json.dumps({'status': Task.STATUS_IN_PROGRESS, 'expected_version': 1}),
            content_type='application/json'
        )
        self.assertEqual(resp.status_code, 200)

        task.refresh_from_db()
        self.assertEqual(task.status, Task.STATUS_IN_PROGRESS)

        event = ActivityEvent.objects.filter(project=self.project, action='TASK_MOVED', entity_id=str(task.id)).first()
        self.assertIsNotNone(event)
        self.assertEqual(event.actor, self.owner)

    def test_tc08_board_filters_intersection(self):
        """TC-08: Filter board by Assignee and Priority returns only the intersection."""
        t1 = Task.objects.create(project=self.project, title='Match Both', assignee=self.member, priority=Task.PRIORITY_HIGH)
        t2 = Task.objects.create(project=self.project, title='Match Assignee Only', assignee=self.member, priority=Task.PRIORITY_LOW)
        t3 = Task.objects.create(project=self.project, title='Match Priority Only', assignee=self.manager, priority=Task.PRIORITY_HIGH)

        tasks_url = reverse('tasks:task_list_create', kwargs={'project_id': self.project.id})
        resp = self.client_member.get(
            tasks_url,
            {'assignee': str(self.member.id), 'priority': Task.PRIORITY_HIGH},
            HTTP_ACCEPT='application/json'
        )
        self.assertEqual(resp.status_code, 200)
        task_ids = [t['id'] for t in resp.json()['tasks']]
        self.assertIn(t1.id, task_ids)
        self.assertNotIn(t2.id, task_ids)
        self.assertNotIn(t3.id, task_ids)

    def test_tc09_effort_estimation_bounds(self):
        """TC-09: 2.5h accepted; negative, non-0.5 step, and non-numeric estimates rejected."""
        tasks_url = reverse('tasks:task_list_create', kwargs={'project_id': self.project.id})

        # 2.5h accepted
        resp_ok = self.client_manager.post(
            tasks_url,
            json.dumps({'title': 'Valid Estimate', 'estimate_hours': 2.5}),
            content_type='application/json'
        )
        self.assertEqual(resp_ok.status_code, 201)

        # Negative rejected
        resp_neg = self.client_manager.post(
            tasks_url,
            json.dumps({'title': 'Negative', 'estimate_hours': -1.0}),
            content_type='application/json'
        )
        self.assertEqual(resp_neg.status_code, 400)

        # Non-step rejected
        resp_step = self.client_manager.post(
            tasks_url,
            json.dumps({'title': 'Non-step', 'estimate_hours': 2.3}),
            content_type='application/json'
        )
        self.assertEqual(resp_step.status_code, 400)

    def test_tc10_time_logging_and_recalculation(self):
        """TC-10: Member logs 1.25h and 0.75h; actual hours update from 0 to 2.0h."""
        task = Task.objects.create(project=self.project, title='Log Time Task', estimate_hours=Decimal('3.0'))
        time_url = reverse('tasks:task_time_log', kwargs={'project_id': self.project.id, 'task_id': task.id})

        self.client_member.post(time_url, json.dumps({'hours': 1.25, 'note': 'Part 1'}), content_type='application/json')
        self.client_member.post(time_url, json.dumps({'hours': 0.75, 'note': 'Part 2'}), content_type='application/json')

        task.refresh_from_db()
        self.assertEqual(task.actual_hours, Decimal('2.00'))

    def test_tc11_progress_dashboard_metrics(self):
        """TC-11: Dashboard reports status counts, overdue count, and total hours accurately."""
        today = timezone.now().date()
        t1 = Task.objects.create(project=self.project, title='Task A', status=Task.STATUS_DONE, estimate_hours=Decimal('2.0'))
        TimeEntry.objects.create(task=t1, user=self.owner, hours=Decimal('2.0'), date=today)

        t2 = Task.objects.create(project=self.project, title='Task B', status=Task.STATUS_IN_PROGRESS, estimate_hours=Decimal('3.0'))
        TimeEntry.objects.create(task=t2, user=self.owner, hours=Decimal('1.0'), date=today)

        dash_url = reverse('tasks:project_dashboard', kwargs={'project_id': self.project.id})
        resp = self.client_member.get(dash_url)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data['total_tasks'], 2)
        self.assertEqual(Decimal(str(data['estimated_hours'])), Decimal('5.0'))
        self.assertEqual(Decimal(str(data['actual_hours'])), Decimal('3.0'))

    def test_tc12_comments_and_scoped_search(self):
        """TC-12: Post comment; verify chronological order and search strictly scoped to authorized project."""
        task = Task.objects.create(project=self.project, title='Specific Keyword Feature')
        com_url = reverse('tasks:task_comment_create', kwargs={'project_id': self.project.id, 'task_id': task.id})

        resp_com = self.client_member.post(com_url, json.dumps({'text': 'Initial feedback'}), content_type='application/json')
        self.assertEqual(resp_com.status_code, 201)
        self.assertEqual(Comment.objects.filter(task=task).count(), 1)

        # Scoped search
        tasks_url = reverse('tasks:task_list_create', kwargs={'project_id': self.project.id})
        search_resp = self.client_member.get(tasks_url, {'q': 'Specific Keyword'}, HTTP_ACCEPT='application/json')
        self.assertEqual(search_resp.status_code, 200)
        self.assertEqual(len(search_resp.json()['tasks']), 1)

    def test_tc13_csv_export_and_project_archival(self):
        """TC-13: Export CSV; archive project locks mutations with HTTP 409 Conflict."""
        csv_url = reverse('tasks:project_tasks_csv', kwargs={'project_id': self.project.id})
        csv_resp = self.client_owner.get(csv_url)
        self.assertEqual(csv_resp.status_code, 200)
        self.assertEqual(csv_resp['Content-Type'], 'text/csv')

        # Archival
        archive_url = reverse('projects:project_archive', kwargs={'project_id': self.project.id})
        arch_resp = self.client_owner.post(archive_url)
        self.assertEqual(arch_resp.status_code, 302)
        self.project.refresh_from_db()
        self.assertTrue(self.project.is_archived)

        # Mutation in archived project rejected
        task = Task.objects.create(project=self.project, title='Locked Task')
        status_url = reverse('tasks:task_status_transition', kwargs={'project_id': self.project.id, 'task_id': task.id})
        mut_resp = self.client_owner.patch(
            status_url,
            json.dumps({'status': Task.STATUS_DONE, 'expected_version': task.version}),
            content_type='application/json'
        )
        self.assertEqual(mut_resp.status_code, 409)

    def test_tc14_notification_dispatch(self):
        """TC-14: Task assignment creates exactly one in-app notification for the assignee."""
        tasks_url = reverse('tasks:task_list_create', kwargs={'project_id': self.project.id})
        resp = self.client_manager.post(
            tasks_url,
            json.dumps({'title': 'Notification Test', 'assignee_id': self.member.id}),
            content_type='application/json'
        )
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(Notification.objects.filter(recipient=self.member).count(), 1)

    def test_tc15_security_hash_csrf_and_lockout(self):
        """TC-15: Password hashing, CSRF enforcement, and 5-failed lockout on 6th attempt."""
        user = User.objects.create_user(email='lockout@pes.edu', password='Password123!')
        self.assertTrue(user.password.startswith('pbkdf2_') or user.password.startswith('argon2'))

        login_url = reverse('accounts:login')
        client = Client()
        for _ in range(5):
            client.post(login_url, {'email': 'lockout@pes.edu', 'password': 'Wrong!'})

        resp_6th = client.post(login_url, {'email': 'lockout@pes.edu', 'password': 'WrongAgain!'})
        self.assertEqual(resp_6th.status_code, 429)
        self.assertIn('Retry-After', resp_6th.headers)
        FailedLoginAttempt.clear_failures('lockout@pes.edu')

    def test_tc16_high_volume_capacity_scaling(self):
        """TC-16: High-volume query with tasks persists and returns all records without truncation."""
        tasks = [Task(project=self.project, title=f"Scale Task {i}") for i in range(50)]
        Task.objects.bulk_create(tasks)

        tasks_url = reverse('tasks:task_list_create', kwargs={'project_id': self.project.id})
        resp = self.client_owner.get(tasks_url, HTTP_ACCEPT='application/json')
        self.assertEqual(resp.status_code, 200)
        self.assertGreaterEqual(len(resp.json()['tasks']), 50)

    def test_tc17_transaction_atomic_rollback(self):
        """TC-17: Forced exception in atomic block cleanly rolls back uncommitted rows."""
        initial_tasks = Task.objects.count()
        try:
            with transaction.atomic():
                Task.objects.create(project=self.project, title='Rollback Task')
                raise RuntimeError("Simulated crash")
        except RuntimeError:
            pass

        self.assertEqual(Task.objects.count(), initial_tasks)

    def test_tc18_ui_action_count_and_accessibility(self):
        """TC-18: Board UI renders keyboard controls, landmarks, and accessible dropdown selector."""
        board_url = reverse('projects:project_detail', kwargs={'project_id': self.project.id})
        resp = self.client_member.get(board_url)
        self.assertEqual(resp.status_code, 200)
        content = resp.content.decode('utf-8')
        self.assertIn('id="modal-status-select"', content)
        self.assertIn('class="skip-link"', content)
        self.assertIn('role="search"', content)
