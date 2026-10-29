"""Capture real Django API evidence and render silent, captioned demo videos.

Run from a development environment after the tests:
  python scripts/produce_demo_videos.py /path/to/current-test-output.txt
Rendering requires Pillow and FFmpeg; no development database is used.
"""
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import textwrap

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'docs' / 'demo'
OUT.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(ROOT))
os.environ.setdefault('DJANGO_DEBUG', 'true')
os.environ.setdefault('ALLOWED_HOSTS', 'localhost,127.0.0.1,testserver')
os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings'
import config.settings as settings

scenes = []


def scene(part, title, note, evidence, seconds=15):
    scenes.append(dict(part=part, title=title, note=note, evidence=evidence, seconds=seconds))


def request(client, method, path, data=None, expected=200):
    kwargs = {'HTTP_ACCEPT': 'application/json'}
    if data is not None:
        kwargs.update(data=json.dumps(data), content_type='application/json')
    response = getattr(client, method)(path, **kwargs)
    assert response.status_code == expected, (path, response.status_code)
    content = response.json()
    return content, f'{method.upper()} {path}\nHTTP {response.status_code}\n' + json.dumps(content, indent=2)


with tempfile.TemporaryDirectory(prefix='project-demo-') as directory:
    settings.DATABASES['default']['NAME'] = str(Path(directory) / 'demo.sqlite3')
    import django
    django.setup()
    from django.core.management import call_command
    from django.test import Client
    from accounts.models import User
    from projects.models import Project, Membership
    from tasks.models import Task, TimeEntry
    from audit.models import ActivityEvent
    call_command('migrate', verbosity=0)
    owner, manager, member = Client(), Client(), Client()
    people = {}
    for client, role in ((owner, 'Owner'), (manager, 'Manager'), (member, 'Member')):
        user = User.objects.create_user(email=role.lower() + '@example.test', full_name=role + ' Demo')
        people[role] = user
        client.force_login(user)
    scene('A', 'Demo of the Project', 'Project Management System\nEstimates and time logging — backend API walkthrough', 'PROJECT WORKFLOW\n\nCreate a project and assign team roles\nSet and validate effort estimates\nLog work with dates and notes\nEdit and delete your own entries\nReview actual hours and project activity')
    project, evidence = request(owner, 'post', '/projects/', {'name': 'Sprint Demo', 'description': 'Feature walkthrough'}, 201)
    pid = project['id']
    for role in ('Manager', 'Member'):
        request(owner, 'post', f'/projects/{pid}/members/', {'email': people[role].email, 'role': role}, 201)
    scene('A', 'Project and roles', 'Owner creates the workspace and invites the project team.\nThe following task is assigned to the Member account.', evidence)
    tasks_url = f'/tasks/projects/{pid}/tasks/'
    task, evidence = request(manager, 'post', tasks_url, {'title': 'Implement project API', 'estimate_hours': '2.5', 'assignee_id': people['Member'].pk}, 201)
    detail = tasks_url + str(task['id']) + '/'
    scene('A', 'Set a task estimate', 'A Manager creates a task estimated at 2.5 hours.\nThe task starts in Backlog.', evidence)
    results = []
    for value in ('0', '9999.5', '2.5'):
        result, _ = request(manager, 'patch', detail, {'estimate_hours': value})
        results.append(f'Estimate {value:>7} hours  -> HTTP 200 / saved {result["estimate_hours"]}')
    for value in ('-0.5', '0.25', 'NaN', 'Infinity', '10000'):
        result, _ = request(manager, 'patch', detail, {'estimate_hours': value}, 400)
        results.append(f'Estimate {value:>7} hours  -> HTTP 400 / {result["error"]["code"]}')
    scene('A', 'Validate estimate boundaries', 'Estimates accept half-hour steps from 0 to 9999.5.\nInvalid input is rejected before any database write.', '\n'.join(results), 20)
    _, evidence = request(member, 'patch', detail, {'estimate_hours': '4'}, 403)
    scene('A', 'Protect estimate permissions', 'The assigned Member can work on the task.\nEstimate changes remain restricted to Owner and Manager.', evidence)
    first, _ = request(member, 'post', detail + 'time/', {'hours': '1.25', 'date': '2026-10-20', 'note': 'Initial work'}, 201)
    second, evidence = request(member, 'post', detail + 'time/', {'hours': '0.75', 'date': '2026-10-20', 'note': 'Verification'}, 201)
    scene('A', 'Record work and actual hours', 'Two retained entries: 1.25 + 0.75 = 2.00 hours.\nEach entry stores its creator, date and note.', evidence)
    entry_url = detail + f'time/{first["entry_id"]}/'
    result, evidence = request(member, 'put', entry_url, {'hours': '2.5', 'date': '2026-10-21', 'note': 'Revised work'})
    assert result['date'] == '2026-10-21' and result['actual_hours'] == '3.25'
    scene('A', 'Edit the date, note and hours', 'The creator revises the entry through the API.\nStored date and note change; actual hours become 3.25.', evidence)
    logs = []
    for payload in ({'hours': '0.1'}, {'hours': '1', 'date': '2026-02-30'}, {'hours': '1', 'note': None}):
        result, _ = request(member, 'put', entry_url, payload, 400)
        logs.append(json.dumps(payload) + '\nHTTP 400 / ' + result['error']['code'])
    entry = TimeEntry.objects.get(pk=first['entry_id'])
    assert str(entry.hours) == '2.50' and entry.date.isoformat() == '2026-10-21' and entry.note == 'Revised work'
    scene('A', 'Reject invalid edits without changes', 'Bad quarter-hour values, impossible dates and non-text notes fail.\nThe previous 2.50-hour entry, date and note remain intact.', '\n\n'.join(logs), 20)
    _, evidence = request(manager, 'put', entry_url, {'hours': '8'}, 403)
    scene('A', 'Protect time-entry ownership', 'Another user cannot edit the creator’s time entry.\nThe API returns HTTP 403.', evidence)
    _, evidence = request(member, 'delete', entry_url)
    assert str(Task.objects.get(pk=task['id']).actual_hours) == '0.75'
    scene('A', 'Delete an entry and recalculate', 'The creator deletes the revised entry.\nOnly the 0.75-hour entry remains in the actual total.', evidence)

    capacity = Project.objects.create(name='Capacity Demo', owner=people['Owner'])
    users = list(people.values()) + User.objects.bulk_create([User(email=f'capacity{i}@example.test') for i in range(17)])
    Membership.objects.bulk_create([Membership(project=capacity, user=user, role='Owner' if user == people['Owner'] else 'Member') for user in users])
    Task.objects.bulk_create([Task(project=capacity, title=f'Capacity task {i}') for i in range(500)])
    ActivityEvent.objects.bulk_create([ActivityEvent(project=capacity, actor=people['Owner'], action='CAPACITY', entity_id=str(i)) for i in range(2000)])
    returned_tasks, _ = request(owner, 'get', f'/tasks/projects/{capacity.pk}/tasks/')
    returned_members, _ = request(owner, 'get', f'/projects/{capacity.pk}/members/')
    returned_events, _ = request(owner, 'get', f'/audit/projects/{capacity.pk}/activity/')
    assert {t['id'] for t in returned_tasks['tasks']} == set(capacity.tasks.values_list('pk', flat=True))
    assert len(returned_members['members']) == 20
    assert {e['id'] for e in returned_events['events']} == set(capacity.audit_events.values_list('pk', flat=True))
    scene('B', 'Capacity and reliability', 'Project Management System\nCurrent build — verification walkthrough', 'DATASET\n\n500 project tasks\n20 project members\n2,000 project activity events\n\nAPI results are compared with the stored records.')
    scene('B', 'Retrieve the complete project dataset', 'Every task and activity identifier matches the stored fixture.\nActivity history includes records beyond the old 100-row limit.', f'GET /tasks/projects/{capacity.pk}/tasks/\nHTTP 200 / returned {len(returned_tasks["tasks"])} tasks\n\nGET /projects/{capacity.pk}/members/\nHTTP 200 / returned {len(returned_members["members"])} members\n\nGET /audit/projects/{capacity.pk}/activity/\nHTTP 200 / returned {len(returned_events["events"])} events\nUnique activity IDs: {len(set(e["id"] for e in returned_events["events"]))}\nStored and returned task/event ID sets: MATCH', 20)

for title, target, note in (
    ('Updates survive an application restart', 'tests.test_iteration2_effort_reliability.RestartPersistenceTests', 'Independent writer and reader processes share a temporary SQLite file.\nTask changes, time-entry details and audit actions survive restart.'),
    ('Roll back failed API operations', 'tests.test_iteration2_effort_reliability.Iteration2EffortTests.test_endpoint_failure_rolls_back_tasks_entries_audit_and_notifications', 'Injected failures occur after audit and notification writes.\nTask, time-entry, audit and notification snapshots remain unchanged.'),
):
    command = [sys.executable, 'manage.py', 'test', target, '--verbosity=2']
    completed = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=True)
    output = completed.stdout + completed.stderr
    visible = '\n'.join(line for line in output.splitlines() if 'test_' in line or 'verified' in line or 'Ran ' in line or line == 'OK' or 'System check' in line)
    scene('B', title, note, '$ python manage.py test\n  ' + target + '\n\n' + visible, 20)

full_output = Path(sys.argv[1]).read_text()
assert 'OK (skipped=3)' in full_output and 'Ran 133 tests' in full_output
summary = full_output[full_output.rfind('----------------------------------------------------------------------'):].strip()
scene('B', 'Run the integrated test suite', '133 discovered: 130 passed, 3 optional checks skipped.\nSkipped browser/performance checks are not counted as passes.', '$ python manage.py test --verbosity=2\n\n' + summary, 20)
scene('B', 'Demo complete', 'Project Management System\nIteration 2 outcomes', 'COMPLETED\n\nEstimate and time-entry validation\nTime-entry date/note edits and ownership checks\nComplete capacity-fixture retrieval\nPersistence across separate application processes\nRollback after injected API failures\n\nNEXT STEPS\nBrowser compatibility and usability measurements\nTime-entry editing controls in the web interface', 18)
(OUT / 'demo_evidence.json').write_text(json.dumps(scenes, indent=2) + '\n')

from PIL import Image, ImageDraw, ImageFont
FONT = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
MONO = '/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf'

def render(selected, filename):
    with tempfile.TemporaryDirectory(prefix='demo-render-') as directory:
        segments = []
        for i, item in enumerate(selected):
            im = Image.new('RGB', (1280, 720), '#0b1220')
            draw = ImageDraw.Draw(im)
            draw.rectangle((0, 0, 12, 720), fill='#38bdf8')
            draw.text((52, 28), 'PROJECT MANAGEMENT SYSTEM', font=ImageFont.truetype(FONT, 18), fill='#7dd3fc')
            draw.text((52, 68), item['title'], font=ImageFont.truetype(FONT, 34), fill='#f8fafc')
            for n, line in enumerate(item['note'].splitlines()):
                draw.text((54, 128 + n * 31), line, font=ImageFont.truetype(FONT, 21), fill='#cbd5e1')
            draw.rounded_rectangle((48, 214, 1232, 654), radius=14, fill='#111e32', outline='#2d425d', width=2)
            for size in range(20, 13, -1):
                font = ImageFont.truetype(MONO, size)
                width = math.floor(1110 / font.getlength('M'))
                lines = [piece for line in item['evidence'].splitlines() for piece in (textwrap.wrap(line, width=width) or [''])]
                if len(lines) * (size + 5) <= 400:
                    break
            assert len(lines) * (size + 5) <= 400, item['title']
            for n, line in enumerate(lines):
                draw.text((74, 236 + n * (size + 5)), line, font=font, fill='#dbeafe')
            draw.text((52, 678), 'Demo of the Project  |  Backend API walkthrough', font=ImageFont.truetype(FONT, 16), fill='#94a3b8')
            draw.text((1110, 678), f'{i+1:02d}/{len(selected):02d}', font=ImageFont.truetype(MONO, 16), fill='#94a3b8')
            png = Path(directory) / f'{i}.png'
            segment = Path(directory) / f'{i}.mp4'
            im.save(png)
            command = ['ffmpeg', '-y', '-v', 'error', '-loop', '1', '-framerate', '5', '-i', str(png), '-t', str(item['seconds']), '-an', '-c:v', 'libx264', '-preset', 'veryfast', '-tune', 'stillimage', '-crf', '24', '-pix_fmt', 'yuv420p', '-threads', '2', str(segment)]
            subprocess.run(command, check=True)
            duration = float(subprocess.check_output(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', str(segment)]))
            assert abs(duration - item['seconds']) < 0.5
            segments.append(segment)
        concat = Path(directory) / 'segments.txt'
        concat.write_text('\n'.join(f"file '{segment}'" for segment in segments))
        output = OUT / filename
        subprocess.run(['ffmpeg', '-y', '-v', 'error', '-f', 'concat', '-safe', '0', '-i', str(concat), '-c', 'copy', '-an', '-metadata', 'title=Demo of the Project', '-movflags', '+faststart', str(output)], check=True)
        subprocess.run(['ffmpeg', '-v', 'error', '-i', str(output), '-f', 'null', '-'], check=True)
        print(filename, sum(item['seconds'] for item in selected), 'seconds', flush=True)

render([s for s in scenes if s['part'] == 'A'], 'Demo_A_Estimates_and_Time_Logging.mp4')
render([s for s in scenes if s['part'] == 'B'], 'Demo_B_Capacity_and_Reliability.mp4')
render(scenes, 'Demo_of_the_Project.mp4')
