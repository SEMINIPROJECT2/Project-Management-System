"""Iteration 2 regression evidence for #9, #10, #19 and #20."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from datetime import date
from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase, SimpleTestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import User
from audit.models import ActivityEvent
from audit.services import log_audit_event
from notifications.models import Notification
from projects.models import Membership, Project
from tasks.models import Task, TimeEntry


class Iteration2EffortTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = User.objects.create_user(email='owner@example.test')
        cls.manager = User.objects.create_user(email='manager@example.test')
        cls.member = User.objects.create_user(email='member@example.test')
        cls.outsider = User.objects.create_user(email='outsider@example.test')
        cls.project = Project.objects.create(name='Iteration 2', owner=cls.owner)
        for user, role in [(cls.owner, 'Owner'), (cls.manager, 'Manager'), (cls.member, 'Member')]:
            Membership.objects.create(project=cls.project, user=user, role=role)
        cls.task = Task.objects.create(project=cls.project, title='Effort', assignee=cls.member)

    def setUp(self):
        self.client.force_login(self.owner)
        self.tasks_url = reverse('tasks:task_list_create', args=[self.project.pk])
        self.detail_url = reverse('tasks:task_detail', args=[self.project.pk, self.task.pk])
        self.time_url = reverse('tasks:task_time_log', args=[self.project.pk, self.task.pk])

    def send(self, url, data, method='post'):
        return getattr(self.client, method)(url, json.dumps(data), content_type='application/json')

    def entry_url(self, entry):
        return reverse('tasks:time_entry_detail', args=[self.project.pk, self.task.pk, entry.pk])

    def test_estimate_rejects_invalid_create_and_edit_without_writes(self):
        invalid = ['NaN', 'sNaN', 'Infinity', '-Infinity', '-0.5', '0.25', '9999.99',
                   '10000', '1e1000000', '1e-1000000', None, True, '', 'abc']
        for value in invalid:
            for url, data, method in [(self.tasks_url, {'title': 'Invalid', 'estimate_hours': value}, 'post'),
                                      (self.detail_url, {'title': 'Should roll back', 'estimate_hours': value}, 'patch')]:
                with self.subTest(value=value, method=method):
                    response = self.send(url, data, method)
                    self.assertEqual(response.status_code, 400)
                    self.assertEqual(response.json()['error']['code'], 'INVALID_ESTIMATE')
                    self.task.refresh_from_db()
                    self.assertEqual((self.task.title, self.task.version, self.task.estimate_hours), ('Effort', 1, Decimal('0')))
                    self.assertEqual(Task.objects.count(), 1)
                    self.assertEqual(ActivityEvent.objects.count(), 0)

    def test_estimate_boundaries_and_authorized_roles(self):
        for user in (self.owner, self.manager):
            self.client.force_login(user)
            for value in ('0', '0.5', '9999.5'):
                with self.subTest(user=user.email, value=value):
                    response = self.send(self.tasks_url, {'title': 'Boundary', 'estimate_hours': value})
                    self.assertEqual(response.status_code, 201)
                    self.assertEqual(Task.objects.get(pk=response.json()['id']).estimate_hours, Decimal(value))
                    self.assertEqual(self.send(self.detail_url, {'estimate_hours': value}, 'patch').status_code, 200)
        for user, expected in [(self.member, 403), (self.outsider, 404)]:
            self.client.force_login(user)
            self.assertEqual(self.send(self.detail_url, {'estimate_hours': '1'}, 'patch').status_code, expected)
            self.assertEqual(self.send(self.tasks_url, {'title': 'Denied', 'estimate_hours': '1'}).status_code, expected)

    def test_time_invalid_hours_dates_notes_create_and_edit(self):
        entry = TimeEntry.objects.create(task=self.task, user=self.owner, hours='1.25', date='2026-10-20', note='Original')
        bad_payloads = [{'hours': v} for v in ['NaN', 'sNaN', 'Infinity', '-Infinity', '0', '-0.25', '0.1', '999.99', '1000', '1e999999', '1e-999999', None, True, 'abc']]
        bad_payloads += [{'hours': '1', 'date': v} for v in ['2026-02-30', 'not-a-date', '', None, 0, False, [], {}]]
        bad_payloads += [{'hours': '1', 'note': v} for v in [None, 1, [], {}]]
        for payload in bad_payloads:
            for url, method in [(self.time_url, 'post'), (self.entry_url(entry), 'put')]:
                with self.subTest(payload=payload, method=method):
                    self.assertEqual(self.send(url, payload, method).status_code, 400)
                    entry.refresh_from_db()
                    self.assertEqual((entry.hours, entry.date, entry.note), (Decimal('1.25'), date(2026, 10, 20), 'Original'))
                    self.assertEqual(TimeEntry.objects.count(), 1)
                    self.assertEqual(ActivityEvent.objects.count(), 0)

    def test_time_lifecycle_date_changes_notes_and_totals(self):
        self.client.force_login(self.member)
        response = self.send(self.time_url, {'hours': '1.25', 'date': '2026-10-20', 'note': '  Work <draft>  '})
        self.assertEqual(response.status_code, 201)
        entry = TimeEntry.objects.get(pk=response.json()['entry_id'])
        self.assertEqual(entry.user, self.member)
        self.assertEqual(entry.note, 'Work <draft>')
        self.assertEqual(self.send(self.time_url, {'hours': '0.75'}).status_code, 201)
        self.assertEqual(self.task.actual_hours, Decimal('2'))
        response = self.send(self.entry_url(entry), {'hours': '2.5', 'date': '2026-10-21', 'note': ' Revised '}, 'put')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Decimal(response.json()['actual_hours']), Decimal('3.25'))
        self.assertEqual(response.json()['date'], '2026-10-21')
        entry.refresh_from_db()
        self.assertEqual((entry.date, entry.note), (date(2026, 10, 21), 'Revised'))
        self.assertEqual(self.send(self.entry_url(entry), {'hours': '999.75'}, 'put').status_code, 200)
        entry.refresh_from_db()
        self.assertEqual((entry.date, entry.note), (date(2026, 10, 21), 'Revised'))
        self.assertEqual(self.task.actual_hours, Decimal('1000.5'))
        self.assertEqual(self.client.delete(self.entry_url(entry)).status_code, 200)
        self.assertEqual(self.task.actual_hours, Decimal('0.75'))
        task_data = self.client.get(self.detail_url).json()
        self.assertEqual(Decimal(task_data['actual_hours']), Decimal('0.75'))
        dashboard = self.client.get(reverse('tasks:project_dashboard', args=[self.project.pk])).json()
        self.assertEqual(Decimal(dashboard['actual_hours']), Decimal('0.75'))

    def test_time_ownership_scope_archival_and_forged_owner(self):
        self.client.force_login(self.member)
        response = self.send(self.time_url, {'hours': '0.25', 'user_id': self.owner.pk})
        entry = TimeEntry.objects.get(pk=response.json()['entry_id'])
        self.assertEqual(entry.user, self.member)
        for user in (self.owner, self.manager):
            self.client.force_login(user)
            self.assertEqual(self.send(self.entry_url(entry), {'hours': '1'}, 'put').status_code, 403)
            self.assertEqual(self.client.delete(self.entry_url(entry)).status_code, 403)
        self.client.force_login(self.outsider)
        self.assertEqual(self.send(self.time_url, {'hours': '1'}).status_code, 404)
        self.assertEqual(self.send(self.entry_url(entry), {'hours': '1'}, 'put').status_code, 404)
        self.client.force_login(self.member)
        other_task = Task.objects.create(project=self.project, title='Other')
        wrong_url = reverse('tasks:time_entry_detail', args=[self.project.pk, other_task.pk, entry.pk])
        self.assertEqual(self.client.delete(wrong_url).status_code, 404)
        self.project.archived_at = timezone.now()
        self.project.save()
        self.assertEqual(self.send(self.time_url, {'hours': '1'}).status_code, 409)
        self.assertEqual(self.send(self.entry_url(entry), {'hours': '1'}, 'put').status_code, 409)
        self.assertEqual(self.client.delete(self.entry_url(entry)).status_code, 409)

    def test_time_json_shape_errors(self):
        for payload in ([], None, 4, 'text'):
            self.assertEqual(self.send(self.time_url, payload).status_code, 400)
        self.assertEqual(self.client.post(self.time_url, '{', content_type='application/json').status_code, 400)

    def test_capacity_returns_all_tasks_members_events_and_isolates_projects(self):
        Task.objects.bulk_create([Task(project=self.project, title=f'Capacity {i}') for i in range(499)])
        users = User.objects.bulk_create([User(email=f'capacity{i}@example.test') for i in range(17)])
        Membership.objects.bulk_create([Membership(project=self.project, user=u, role='Member') for u in users])
        ActivityEvent.objects.bulk_create([ActivityEvent(project=self.project, actor=self.owner, action='CAPACITY', entity_id=str(i)) for i in range(2000)])
        other = Project.objects.create(name='Other', owner=self.outsider)
        ActivityEvent.objects.create(project=other, action='PRIVATE')
        self.assertEqual(Task.objects.filter(project=self.project).count(), 500)
        self.assertEqual(Membership.objects.filter(project=self.project).count(), 20)
        tasks = self.client.get(self.tasks_url).json()['tasks']
        self.assertSetEqual({t['id'] for t in tasks}, set(self.project.tasks.values_list('id', flat=True)))
        members = self.client.get(reverse('projects:project_members', args=[self.project.pk])).json()['members']
        self.assertSetEqual({m['user_id'] for m in members}, set(self.project.memberships.values_list('user_id', flat=True)))
        activity_url = reverse('audit:project_activity_api', args=[self.project.pk])
        events = self.client.get(activity_url).json()['events']
        self.assertEqual(len(events), 2000)
        self.assertSetEqual({e['id'] for e in events}, set(self.project.audit_events.values_list('id', flat=True)))
        self.assertEqual([e['id'] for e in events], [e['id'] for e in self.client.get(activity_url).json()['events']])
        self.client.force_login(self.outsider)
        self.assertEqual(self.client.get(activity_url, HTTP_ACCEPT='application/json').status_code, 404)

    def test_endpoint_failure_rolls_back_tasks_entries_audit_and_notifications(self):
        entry = TimeEntry.objects.create(task=self.task, user=self.owner, hours='1', note='Retained')
        operations = [(self.tasks_url, {'title': 'Aborted', 'assignee_id': self.member.pk}, 'post'),
                      (self.detail_url, {'title': 'Aborted', 'estimate_hours': '2', 'assignee_id': self.manager.pk}, 'patch'),
                      (self.time_url, {'hours': '2'}, 'post'),
                      (self.entry_url(entry), {'hours': '2', 'date': '2026-10-01', 'note': 'Aborted'}, 'put'),
                      (self.entry_url(entry), {}, 'delete')]
        def snapshot():
            return [list(model.objects.order_by('pk').values()) for model in (Task, TimeEntry, ActivityEvent, Notification)]
        def fail_after_audit(**kwargs):
            log_audit_event(**kwargs)
            raise RuntimeError('Injected failure after audit insert')
        for url, data, method in operations:
            with self.subTest(method=method, url=url):
                before = snapshot()
                with patch('tasks.views.log_audit_event', side_effect=fail_after_audit):
                    with self.assertRaisesMessage(RuntimeError, 'Injected failure'):
                        self.send(url, data, method)
                self.assertEqual(snapshot(), before)
        # Assignment notification is sent after audit on create: fail after its insert too.
        from notifications.services import send_notification
        def fail_after_notification(**kwargs):
            send_notification(**kwargs)
            raise RuntimeError('Notification failure')
        before = snapshot()
        with patch('tasks.views.send_notification', side_effect=fail_after_notification):
            with self.assertRaisesMessage(RuntimeError, 'Notification failure'):
                self.send(self.tasks_url, {'title': 'Aborted', 'assignee_id': self.member.pk})
        self.assertEqual(snapshot(), before)


class RestartPersistenceTests(SimpleTestCase):
    def test_committed_api_updates_survive_new_application_process(self):
        """Two independent Django processes use one temporary, migrated SQLite file."""
        script = r'''
import json, sys, django
from django.conf import settings
settings.DATABASES['default']['NAME'] = sys.argv[1]
django.setup()
from django.core.management import call_command
from django.test import Client
from accounts.models import User
from projects.models import Project, Membership
from tasks.models import Task, TimeEntry
from audit.models import ActivityEvent
if sys.argv[2] == 'write':
    call_command('migrate', verbosity=0)
    user = User.objects.create_user(email='restart@example.test')
    project = Project.objects.create(name='Restart', owner=user)
    Membership.objects.create(project=project, user=user, role='Owner')
    client = Client(); client.force_login(user)
    response = client.post(f'/tasks/projects/{project.pk}/tasks/', json.dumps({'title': 'Before', 'estimate_hours': '2.5'}), content_type='application/json')
    assert response.status_code == 201, response.content
    task_id = response.json()['id']
    base = f'/tasks/projects/{project.pk}/tasks/{task_id}/'
    response = client.patch(base, json.dumps({'title': 'After restart', 'estimate_hours': '4.5'}), content_type='application/json')
    assert response.status_code == 200, response.content
    response = client.post(base + 'time/', json.dumps({'hours': '1.25', 'date': '2026-10-20', 'note': 'Durable'}), content_type='application/json')
    assert response.status_code == 201, response.content
else:
    from decimal import Decimal
    task = Task.objects.get()
    assert task.title == 'After restart' and task.version == 2
    assert task.estimate_hours == Decimal('4.5') and task.actual_hours == Decimal('1.25')
    entry = TimeEntry.objects.get()
    assert entry.date.isoformat() == '2026-10-20' and entry.note == 'Durable'
    assert set(ActivityEvent.objects.values_list('action', flat=True)) == {'TASK_CREATED', 'TASK_EDITED', 'TIME_LOGGED'}
print(sys.argv[2] + ' verified')
'''
        env = dict(os.environ, DJANGO_SETTINGS_MODULE='config.settings', DJANGO_DEBUG='True', ALLOWED_HOSTS='testserver,localhost,127.0.0.1')
        with tempfile.TemporaryDirectory() as directory:
            db = str(Path(directory) / 'restart.sqlite3')
            for mode in ('write', 'read'):
                result = subprocess.run([sys.executable, '-c', script, db, mode], cwd=Path(__file__).resolve().parents[1], env=env, capture_output=True, text=True, timeout=90)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertIn(mode + ' verified', result.stdout)
