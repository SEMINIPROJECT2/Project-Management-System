# Backend API Reference

This document defines the backend foundation for ENG-03 (Issue #31). All task
and project endpoints are scoped to the authenticated user's project
membership. State-changing browser requests require Django's CSRF token.

## Response conventions

Successful JSON responses contain the affected resource fields and a concise
`message`. Validation and authorization failures use this stable shape:

```json
{
  "error": {
    "code": "INVALID_ESTIMATE",
    "message": "Estimate must be a non-negative number in 0.5-hour increments."
  }
}
```

Common status codes are `200` (read/update), `201` (create), `400`
(validation), `403` (forbidden), `404` (missing or cross-project resource),
`409` (archived project or stale task version), and `429` (login lockout).

## Accounts and projects

| Method | Route | Purpose |
| --- | --- | --- |
| `POST` | `/accounts/register/` | Register a unique-email account |
| `POST` | `/accounts/login/` | Open an authenticated session |
| `POST` or `GET` | `/accounts/logout/` | Invalidate the current session |
| `GET`, `POST` | `/projects/` | List accessible projects or create one |
| `GET` | `/projects/{project_id}/` | Render the project board |
| `GET`, `POST` | `/projects/{project_id}/members/` | List members or invite one (Owner only) |
| `POST` | `/projects/{project_id}/members/{user_id}/role/` | Change a member role (Owner only) |
| `POST` | `/projects/{project_id}/archive/` | Archive a project (Owner only) |

## Tasks and reporting

| Method | Route | Purpose |
| --- | --- | --- |
| `GET`, `POST` | `/tasks/projects/{project_id}/tasks/` | Filter/list tasks or create a Backlog task |
| `GET`, `PATCH`, `PUT`, `POST` | `/tasks/projects/{project_id}/tasks/{task_id}/` | Read or update a task |
| `PATCH`, `POST` | `/tasks/projects/{project_id}/tasks/{task_id}/status/` | Move a task with optional `expected_version` |
| `POST` | `/tasks/projects/{project_id}/tasks/{task_id}/time/` | Log positive time in 0.25-hour steps |
| `PUT`, `POST`, `DELETE` | `/tasks/projects/{project_id}/tasks/{task_id}/time/{entry_id}/` | Edit/delete the caller's time entry |
| `POST` | `/tasks/projects/{project_id}/tasks/{task_id}/comments/` | Add a task comment |
| `GET` | `/tasks/projects/{project_id}/dashboard/` | Return progress totals and status counts |
| `GET` | `/tasks/projects/{project_id}/tasks.csv` | Export project tasks as CSV |

The task list supports intersection filters: `assignee`, `priority`,
`due_status`, and project-scoped search through `q`.

## Security and concurrency

- `CsrfViewMiddleware` protects state-changing requests.
- Session cookies are HTTP-only, SameSite `Lax`, and expire when the browser
  closes. Set `DJANGO_SECURE_COOKIES=True` when serving over HTTPS.
- The authorization decorator checks membership and archived-project state on
  the server; client controls are never trusted as authorization.
- Status transitions accept `expected_version`. A stale version returns HTTP
  `409` with code `CONFLICT`, preventing silent overwrites.

## Iteration 2 effort and history contract

Estimates are finite decimal values in 0.5-hour steps, from 0 through 9999.5
(the largest allowed step within `DecimalField(max_digits=6, decimal_places=2)`).
Time-entry hours are finite, strictly positive quarter-hour values through 999.75
within the existing five-digit, two-decimal storage field. Invalid values return
HTTP 400 with `INVALID_ESTIMATE` or `INVALID_HOURS`.

Time-entry creation accepts `hours`, optional `date` and optional textual `note`.
Omitting `date` uses the application's local date; supplying a blank, null or invalid
date returns `INVALID_DATE`. Notes may be blank and are trimmed; non-text notes
return `INVALID_NOTE`. Time-entry PUT/POST requires `hours`; supplied `date` and
`note` are updated, and omitted ones are retained. Create/edit responses include
`date`, `note` and recomputed `actual_hours`. Only the entry creator may edit/delete,
including when another caller is an Owner or Manager.

`GET /audit/projects/{project_id}/activity/` returns all project events in the
existing `events` array, ordered by descending creation timestamp and ID. It has
no silent 100-event cutoff. Project membership remains required.
