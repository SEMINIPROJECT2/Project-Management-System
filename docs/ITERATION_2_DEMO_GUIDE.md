# Iteration 2 demonstration guide

Status: walkthrough scripts, actual API evidence and a reproducible renderer
are included. Video files are intentionally excluded from Git at the user's
request. This update does not complete the video-publication part of #41.
Evidence was captured from merged build `4c853b9` on 29 October 2026 using
synthetic accounts and temporary databases.

## Included source evidence

- [Actual API results and chapter text](demo/demo_evidence.json)
- [Fresh integrated test output](test-evidence/demo-delivery-tests.txt)
- [Demonstration capture and rendering script](../scripts/produce_demo_videos.py)

The renderer produces captioned backend/API demonstrations from actual Django
requests and test execution. They are not screen recordings of browser clicks
or recordings made during earlier sprints. The dates in example time entries
are fictional work dates. They do not establish a recording date. Current
browser compatibility and interface action-count checks remain unexecuted.

Locally generated videos are H.264, 1280 × 720, and silent. Their title is
"Demo of the Project"; no personal name or student identifier is added.

## Recording A — Estimates and time logging

1. Start the application with migrations applied, then sign in using fictional demo accounts with Owner, Manager and Member roles.
2. As Owner or Manager, create a task estimated at 2.5 hours. Show that 0 and 9999.5 are accepted, while -0.5, 0.25, NaN, Infinity and 10000 receive validation errors through the API. Show a Member cannot change the estimate.
3. As Member, log 1.25 hours dated 2026-10-20 with the note “Initial work”; log another 0.75. Show actual hours total 2.00 on the task detail and dashboard.
4. Through the time-entry API, PUT the first entry with hours 2.5, date 2026-10-21 and note “Revised work”. Read task detail again: the stored date/note changed and actual hours are 3.25. Explain that the board currently has no edit/date picker UI.
5. Attempt invalid quarter-hour inputs, malformed dates and non-text notes. Show HTTP 400 and unchanged stored values. As another user, attempt edit/delete and show HTTP 403. Delete as creator and show actual hours fall to 0.75.

## Recording B — Capacity, restart and rollback evidence

1. Run `python manage.py test tests.test_iteration2_effort_reliability --verbosity=2`.
2. Explain the capacity fixture: exactly 500 tasks, 20 members and 2000 activity events; test compares every returned ID, including events beyond the former 100-event cutoff.
3. Explain restart test: writer process migrates a temporary SQLite file, commits task create/edit and a time log, exits; reader process starts separately and checks title, version, estimate, time entry date/note, actual totals and audit actions.
4. Explain rollback test: failures are injected after audit/notification inserts in actual API operations; snapshots prove task/time entry, audit and notification rows are unchanged afterward.
5. Show the full test report and execution logs. Read the actual passed/skipped counts, and identify browser or other unexecuted checks explicitly. Do not claim all checks passed if skips exist.

## Completion checklist

- [x] Scoped walkthrough script prepared.
- [x] Final project report prepared.
- [x] Recording A produced and checked for duration, video decode and absence of audio.
- [x] Recording B produced and checked for duration, video decode and absence of audio.
- [ ] Video publication — intentionally excluded from this change.

The report, evidence and reproduction work are ready for review. #41 remains
open for any required video submission outside this change.

## Reproduce the artifacts

Use a Python environment with the project requirements and Pillow installed,
and FFmpeg/FFprobe available on PATH. The renderer uses DejaVu Sans fonts from
the standard Linux font directory. Run from the repository root:

```bash
export DJANGO_DEBUG=true
export ALLOWED_HOSTS=localhost,127.0.0.1,testserver
python manage.py test --verbosity=2 > /tmp/project-demo-tests.txt 2>&1
python scripts/produce_demo_videos.py /tmp/project-demo-tests.txt
```

The script starts a migrated temporary SQLite database, checks every shown HTTP
status and important stored result, runs the independent-process and injected
failure tests, then renders the clips. It never uses the development database.
