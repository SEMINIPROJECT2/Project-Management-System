"""Sprint regression: large task lists retain correct hours without N+1 queries."""
from decimal import Decimal

from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from accounts.models import User
from projects.models import Membership, Project
from tasks.models import Task, TimeEntry


class TaskListScalingTests(TestCase):
    def test_500_task_list_preserves_hours_with_bounded_query_count(self):
        owner = User.objects.create_user(email='query-owner@example.test')
        project = Project.objects.create(name='Query scaling', owner=owner)
        Membership.objects.create(project=project, user=owner, role='Owner')
        tasks = Task.objects.bulk_create([Task(project=project, title=f'Task {i}') for i in range(500)])
        TimeEntry.objects.create(task=tasks[0], user=owner, hours=Decimal('1.25'))
        TimeEntry.objects.create(task=tasks[0], user=owner, hours=Decimal('0.75'))
        self.client.force_login(owner)
        with CaptureQueriesContext(connection) as queries:
            response = self.client.get(reverse('tasks:task_list_create', args=[project.pk]))
        self.assertEqual(response.status_code, 200)
        returned = {task['id']: task for task in response.json()['tasks']}
        self.assertEqual(len(returned), 500)
        self.assertEqual(Decimal(returned[tasks[0].pk]['actual_hours']), Decimal('2'))
        self.assertEqual(Decimal(returned[tasks[1].pk]['actual_hours']), Decimal('0'))
        self.assertLessEqual(len(queries), 12, 'Task-list query count must remain bounded as task volume grows')
