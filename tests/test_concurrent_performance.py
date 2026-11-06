"""STP TC-16: one application, 20 users and 100 real HTTP requests."""
from concurrent.futures import ThreadPoolExecutor
import json
import math
import os
import re
from pathlib import Path
import threading
import time
from unittest import skipUnless
from urllib.request import Request, urlopen
from urllib.error import HTTPError

from django.conf import settings
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.core.servers.basehttp import ThreadedWSGIServer
from django.test import Client
from django.test.testcases import LiveServerThread

from accounts.models import User
from audit.models import ActivityEvent
from projects.models import Membership, Project
from tasks.models import Task


class LoadWSGIServer(ThreadedWSGIServer):
    # Admit the complete 20-user burst instead of timing the development
    # server's default 10-connection TCP backlog and SYN retransmissions.
    request_queue_size = 64


class LoadServerThread(LiveServerThread):
    server_class = LoadWSGIServer


@skipUnless(os.environ.get('RUN_PERFORMANCE_TESTS') == '1', 'Set RUN_PERFORMANCE_TESTS=1 for STP concurrent load.')
class ConcurrentPerformanceTests(StaticLiveServerTestCase):
    server_thread_class = LoadServerThread
    def test_twenty_users_and_one_hundred_http_requests(self):
        users = User.objects.bulk_create([User(email=f'load{i}@example.test') for i in range(20)])
        project = Project.objects.create(name='Concurrent load', owner=users[0])
        Membership.objects.bulk_create([Membership(project=project, user=user, role='Owner' if i == 0 else 'Member') for i, user in enumerate(users)])
        Task.objects.bulk_create([Task(project=project, title=f'Load task {i}') for i in range(500)])
        ActivityEvent.objects.bulk_create([ActivityEvent(project=project, actor=users[0], action='LOAD_FIXTURE', entity_id=str(i)) for i in range(2000)])
        cookies = []
        for user in users:
            client = Client()
            client.force_login(user)
            cookies.append(f'{settings.SESSION_COOKIE_NAME}={client.cookies[settings.SESSION_COOKIE_NAME].value}')
        barrier = threading.Barrier(20)
        paths = {'board': f'/projects/{project.pk}/', 'tasks': f'/tasks/projects/{project.pk}/tasks/'}

        def worker(index):
            samples = []
            barrier.wait(timeout=30)
            for iteration in range(5):
                endpoint = 'board' if (iteration + index) % 2 == 0 else 'tasks'
                request = Request(self.live_server_url + paths[endpoint], headers={'Cookie': cookies[index]})
                started = time.perf_counter()
                try:
                    with urlopen(request, timeout=30) as response:
                        body = response.read()
                        status = response.status
                except HTTPError as error:
                    body = error.read().decode(errors='replace')
                    diagnostic = os.environ.get('PART3_HTTP_DIAGNOSTIC')
                    if diagnostic:
                        Path(diagnostic).write_text(body)
                    detail = re.search(r'<pre class="exception_value">(.*?)</pre>', body, re.S)
                    raise AssertionError(f'HTTP {error.code}: {detail.group(1) if detail else body[:1500]}') from error
                duration = time.perf_counter() - started
                if status != 200:
                    raise AssertionError(f'HTTP {status}')
                if endpoint == 'tasks' and len(json.loads(body)['tasks']) != 500:
                    raise AssertionError('Task response truncated')
                samples.append({'user': index, 'endpoint': endpoint, 'seconds': duration, 'status': status})
            return samples

        with ThreadPoolExecutor(max_workers=20) as executor:
            samples = [sample for result in executor.map(worker, range(20)) for sample in result]
        self.assertEqual(len(samples), 100)
        self.assertEqual(len({sample['user'] for sample in samples}), 20)
        summary = {}
        for endpoint in paths:
            values = sorted(sample['seconds'] for sample in samples if sample['endpoint'] == endpoint)
            summary[endpoint] = {'requests': len(values), 'p95_seconds': values[math.ceil(.95 * len(values)) - 1], 'maximum_seconds': max(values)}
        evidence = {'fixture': {'tasks': 500, 'members': 20, 'events': 2000}, 'users': 20, 'requests': 100, 'summary': summary, 'samples': samples}
        target = os.environ.get('PART3_LOAD_EVIDENCE')
        if target:
            Path(target).parent.mkdir(parents=True, exist_ok=True)
            Path(target).write_text(json.dumps(evidence, indent=2) + '\n')
        print('[TC-16 concurrent HTTP] ' + json.dumps(summary), flush=True)
        self.assertEqual(Task.objects.filter(project=project).count(), 500)
        self.assertEqual(Membership.objects.filter(project=project).count(), 20)
        self.assertEqual(ActivityEvent.objects.filter(project=project).count(), 2000)
        for endpoint, result in summary.items():
            self.assertLessEqual(result['p95_seconds'], 2.0, f'{endpoint} p95 exceeded STP 2-second threshold')
