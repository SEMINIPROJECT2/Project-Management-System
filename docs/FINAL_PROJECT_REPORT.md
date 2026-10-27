# Final Project Report & Sprint Demonstration Guide
**Project 27: Project Management System**  
**Course:** Software Engineering Mini-Project  
**Project Team (Group 27):**
- **Tilak** &bull; `PES1UG24CS696`
- **Shravankumar Patil** &bull; `PES1UG24CS692`
- **Sachin** &bull; `PES1UG24CS688`
- **Prasanna** &bull; `PES1UG24CS684`

**Deliverable Reference:** DOC-03 (Issue #41)

---

## 1. Project Background & Iteration Outcomes
The Project Management System is a robust web-based workflow management platform built using a clean, layered monolithic architecture in Django. During the development iterations, all requirements defined across **SRS v1.0**, **SAD v1.0**, and **STP v1.0** were implemented, tested, and integrated.

### Summary of Completed Modules:
1. **Security & Accounts Module**: Custom user model with unique email identity, PBKDF2 password hashing, and brute-force lockout enforcing a 15-minute freeze after 5 failed sign-in attempts within 15 minutes (`SR-05`), complete with standard RFC 6585 `Retry-After` HTTP headers, attempt countdown warnings, and an animated client-side live lockout countdown.
2. **Project & Multi-Tenant Authorization**: Project workspace scoping where creators become Owners. Owner can invite members as `Owner`, `Manager`, or `Member`. Server-side centralized authorization rejects cross-project requests with HTTP 403 or 404. Archiving locks the project into a read-only state, returning HTTP 409 Conflict upon mutation attempts.
3. **Task & Kanban Board Engine**: Full 5-stage lifecycle (`Backlog`, `To Do`, `In Progress`, `Review`, `Done`) featuring drag-and-drop mechanics, keyboard navigation, optimistic concurrency version checks, and multi-filter intersection (Assignee, Priority, Due Status).
4. **Effort Tracking & Dashboard**: Estimation bounds (0.5h step $\ge 0$), time logging (0.25h step), progress dashboard calculating status counts, overdue counts, and total hours, and CSV task export.
5. **Audit Trail & In-App Notifications**: Transactional `ActivityEvent` recording actor, action, entity, and timestamp, alongside real-time notification generation for task assignments and invitations.
6. **CI/CD Automation**: GitHub Actions workflow automatically validating syntax, database migrations, and executing acceptance tests on every push and pull request.

---

## 2. Sprint Demonstration Video Script (Walkthrough)

When recording your project evaluation demonstration or presenting to evaluators, follow this recommended walkthrough sequence:

### Part 1: Registration & Brute-Force Security (2 mins)
1. **Account Registration (`FR-01`, `TC-01`)**:
   - Navigate to `/accounts/register/`.
   - Register a user with email `alice@example.com` and password.
   - Attempt to register the exact same email again &rarr; Demonstrate the duplicate rejection error message.
2. **Brute-Force Rate Limiting (`SR-05`, `TC-15`)**:
   - Attempt to log in with an incorrect password. Demonstrate the dynamic security notice displaying remaining attempts (e.g., "4 attempts remaining before a 15-minute account lockout").
   - Continue entering incorrect passwords until 5 failed attempts are reached.
   - Show that on the 6th attempt, the application locks out the account with HTTP 429 (`Too Many Requests`), returns a standard `Retry-After` header, disables input controls, and renders a glassmorphic animated banner with a live minute:second countdown (`#lockout-countdown`).
   - Demonstrate that upon timer expiry, form inputs and submit button are re-enabled automatically.

### Part 2: Project Creation & Role Management (2 mins)
1. **Create Project (`FR-03`, `TC-03`)**:
   - Log in as `alice@example.com`.
   - Click "New Project" (&le; 2 clicks per NFR-04). Create "Sprint Alpha". Creator is designated `Owner`.
2. **Invite Members & Role Control (`FR-04`, `TC-04`)**:
   - Click "Invite Member". Invite `bob@example.com` as `Manager` and `charlie@example.com` as `Member`.
   - Show the in-app notification bell badge incrementing for `bob@example.com`.

### Part 3: Task Lifecycle & Kanban Workflow (3 mins)
1. **Task Creation (`FR-05`, `TC-05`)**:
   - Click "New Task". Enter title "Build Payment Gateway", estimate "4.5" hours, priority "High", and assign to Charlie.
   - Show that it immediately appears in the `Backlog` column with version `1`.
2. **Drag-and-Drop & Accessible Status Transition (`FR-07`, `NFR-05`)**:
   - Drag the card from `Backlog` &rarr; `In Progress`.
   - Open task modal and demonstrate the accessible keyboard dropdown selector changing status to `Review`.
3. **Concurrency Conflict Protection (SAD §3.7)**:
   - Demonstrate that if another user tries to update a task with a stale version, the application prevents overwriting and returns a clean 409 Conflict.

### Part 4: Effort Tracking, Comments & Scoped Search (2 mins)
1. **Time Logging (`FR-10`, `TC-10`)**:
   - In task modal, log `1.25` hours with note "Initial API wiring".
   - Show that actual logged hours immediately update on the task card and the top dashboard summary.
2. **Task Comments (`FR-12`, `TC-12`)**:
   - Post a comment "Draft PR submitted". Show the chronological feed.
3. **Board Multi-Filtering & Scoped Search (`FR-08`, `FR-14`)**:
   - Use the filter toolbar: Select Assignee "Charlie" + Priority "High" &rarr; Show intersection filtering.
   - Search by keyword &rarr; Show project-scoped results.

### Part 5: Export, Archival & Automated CI (2 mins)
1. **CSV Export (`FR-15`, `TC-13`)**:
   - Click "Export CSV". Open the downloaded file to display task IDs, titles, assignees, estimates, and actual hours.
2. **Project Archival (`FR-16`, `TC-13`)**:
   - Click "Archive Project". Project card updates to "Archived (Read-Only)".
   - Show that task drag-and-drop is disabled and creation attempts return a conflict.
3. **Automated CI Test Suite (`ENG-06`, `TEST-01`–`TEST-04`)**:
   - Open terminal and run `python manage.py test --verbosity=2`.
   - Show that all 20 automated test methods covering `TC-01` through `TC-18` pass with 100% success rate.

---

## 3. Known Limitations and Future Roadmap
- **Attachments & Media**: File attachments (PDFs, images) on task cards are planned for Version 2.0.
- **External Notifications**: Version 1 implements in-app notification toasts; email/webhook delivery (SendGrid/Slack) can be integrated in future sprints.
- **Calendar Synchronization**: iCal / Google Calendar export for due dates.
