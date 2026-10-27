# Project Management System (PMS)
**Software Engineering Mini-Project &bull; Group 27**  
*Comprehensive Web-Based Project Management, Kanban Workflow, and Traceability Platform*

**Project Team (Group 27):**
- **Tilak** (`PES1UG24CS696`)
- **Shravankumar Patil** (`PES1UG24CS692`)
- **Sachin** (`PES1UG24CS688`)
- **Prasanna** (`PES1UG24CS84`)

---

## 1. Overview & System Scope
This repository implements the complete Software Requirements Specification (**SRS v1.0**), Software Architecture & Design (**SAD v1.0**), and Software Test Plan (**STP v1.0**) for **Project 27: Project Management System**.

The platform provides:
- **Authentication & Security (`FR-01`, `FR-02`, `SR-01`–`SR-05`)**: Unique-email registration, PBKDF2 adaptive password hashing, strict CSRF/session protection, 15-minute brute-force lockout after 5 consecutive failures, and centralized server-side authorization (`Owner`, `Manager`, `Member`).
- **Project Lifecycle & Archiving (`FR-03`, `FR-04`, `FR-16`)**: Multi-tenant project workspace creation, member invitations with role delegation, and project archival rendering projects read-only (rejecting mutations with HTTP 409 Conflict).
- **Kanban Board & Workflow (`FR-05`–`FR-09`, `ENG-05`)**: 5-stage lifecycle (`Backlog` &rarr; `To Do` &rarr; `In Progress` &rarr; `Review` &rarr; `Done`) with drag-and-drop, accessible keyboard selectors, optimistic concurrency version checks, and multi-filter intersection (Assignee + Priority + Due Date).
- **Effort Tracking & Progress Visibility (`FR-09`, `FR-10`, `FR-11`, `FR-15`)**: 0.5-hour estimation bounds, 0.25-hour time logging with retained actual sums, live status & overdue metrics dashboard, and CSV task export.
- **Audit History & Collaboration (`FR-12`, `FR-13`, `FR-17`)**: Chronological task comments, transactional audit trail (`ActivityEvent`), and instant in-app notifications on task assignment and invitations.

---

## 2. Architecture & Technology Stack
Per SAD §3.5, the system is designed as a **Layered Monolith**:
```
┌─────────────────────────────────────────────────────────────┐
│                       Presentation Layer                    │
│   (HTML5, Vanilla CSS Glassmorphic UI, Modern Vanilla JS)    │
└──────────────────────────────┬──────────────────────────────┘
                               │ HTTP / JSON REST APIs / CSRF
┌──────────────────────────────▼──────────────────────────────┐
│                    Application / Route Layer                │
│    (Django 5.x URL Routing, Session Middleware, Security)   │
└──────────────────────────────┬──────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────┐
│                  Authorization & Service Layer              │
│ (projects.permissions, audit.services, notifications.services│
└──────────────────────────────┬──────────────────────────────┘
                               │ Atomic Transactions
┌──────────────────────────────▼──────────────────────────────┐
│                      Persistence Layer                      │
│ (accounts.User, projects.Project, Membership, Task, Audit)  │
└─────────────────────────────────────────────────────────────┘
```

- **Backend**: Python 3.11+, Django 5.2 (ORM, Auth, Session & CSRF engines)
- **Database**: SQLite (local development / testing) with transactional integrity; PostgreSQL ready
- **Frontend**: Responsive CSS (dark/light modern palette, 1280x720 compliant per NFR-04)
- **CI/CD**: GitHub Actions automated workflow running all unit and acceptance tests (`.github/workflows/ci.yml`)

---

## 3. Getting Started

### Prerequisites
- Python 3.10 or higher
- Git

### Setup Virtual Environment & Install Dependencies
```bash
# Clone the repository
git clone https://github.com/SEMINIPROJECT2/Project-Management-System.git
cd Project-Management-System

# Create and activate virtual environment
python -m venv venv

# Windows:
.\venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

# Install required dependencies
pip install -r requirements.txt
```

### Apply Migrations & Run Development Server
```bash
# Apply database migrations
python manage.py migrate

# Start the development server
python manage.py runserver
```
Access the application at: `http://127.0.0.1:8000/`

For HTTPS deployments, set `DJANGO_DEBUG=False` and
`DJANGO_SECURE_COOKIES=True` so Django marks session and CSRF cookies as
`Secure`. The complete JSON endpoint contract is documented in
[`docs/API_REFERENCE.md`](docs/API_REFERENCE.md).

---

## 4. Automated Testing & Verification
The test suite validates requirements against the official **Software Test Plan (TC-01 through TC-18)**:
```bash
python manage.py test --verbosity=2
```

---

## 5. Requirements Traceability Matrix

| SRS ID | Requirement Name | Test Case | Target GitHub Issue | Implementation Location |
| :--- | :--- | :--- | :--- | :--- |
| **FR-01** | Account registration | `TC-01` | Issue #1 | [`accounts/views.py`](file:///d:/SE%20MINI%20PROJ/accounts/views.py) |
| **FR-02** | Authentication and sessions | `TC-02` | Issue #2 | [`accounts/views.py`](file:///d:/SE%20MINI%20PROJ/accounts/views.py) |
| **FR-03** | Project creation | `TC-03` | Issue #3 | [`projects/views.py`](file:///d:/SE%20MINI%20PROJ/projects/views.py) |
| **FR-04** | Membership and roles | `TC-04` | Issue #4 | [`projects/permissions.py`](file:///d:/SE%20MINI%20PROJ/projects/permissions.py) |
| **FR-05** | Task creation and validation | `TC-05` | Issue #5 | [`tasks/views.py`](file:///d:/SE%20MINI%20PROJ/tasks/views.py) |
| **FR-06** | Task editing and permissions | `TC-06` | Issue #6 | [`tasks/views.py`](file:///d:/SE%20MINI%20PROJ/tasks/views.py) |
| **FR-07** | Kanban transitions | `TC-07` | Issue #7 | [`tasks/views.py`](file:///d:/SE%20MINI%20PROJ/tasks/views.py), [`static/js/board.js`](file:///d:/SE%20MINI%20PROJ/static/js/board.js) |
| **FR-08** | Board filtering | `TC-08` | Issue #8 | [`tasks/views.py`](file:///d:/SE%20MINI%20PROJ/tasks/views.py) |
| **FR-09** | Task effort estimation | `TC-09` | Issue #9 | [`tasks/models.py`](file:///d:/SE%20MINI%20PROJ/tasks/models.py) |
| **FR-10** | Time logging | `TC-10` | Issue #10 | [`tasks/views.py`](file:///d:/SE%20MINI%20PROJ/tasks/views.py) |
| **FR-11** | Progress dashboard | `TC-11` | Issue #11 | [`tasks/views.py`](file:///d:/SE%20MINI%20PROJ/tasks/views.py) |
| **FR-12** | Task comments | `TC-12` | Issue #12 | [`tasks/views.py`](file:///d:/SE%20MINI%20PROJ/tasks/views.py) |
| **FR-13** | Activity history and audit | `TC-07` | Issue #13 | [`audit/services.py`](file:///d:/SE%20MINI%20PROJ/audit/services.py) |
| **FR-14** | Task search | `TC-12` | Issue #14 | [`tasks/views.py`](file:///d:/SE%20MINI%20PROJ/tasks/views.py) |
| **FR-15** | CSV task export | `TC-13` | Issue #15 | [`tasks/views.py`](file:///d:/SE%20MINI%20PROJ/tasks/views.py) |
| **FR-16** | Project archiving | `TC-13` | Issue #16 | [`projects/views.py`](file:///d:/SE%20MINI%20PROJ/projects/views.py) |
| **FR-17** | In-app notifications | `TC-14` | Issue #17 | [`notifications/services.py`](file:///d:/SE%20MINI%20PROJ/notifications/services.py) |
| **SR-01** | Server-side authorization | `TC-04` | Issue #24 | [`projects/permissions.py`](file:///d:/SE%20MINI%20PROJ/projects/permissions.py) |
| **SR-02** | Secure password storage | `TC-15` | Issue #25 | [`accounts/models.py`](file:///d:/SE%20MINI%20PROJ/accounts/models.py) |
| **SR-03** | CSRF & session protection | `TC-15` | Issue #26 | [`config/settings.py`](file:///d:/SE%20MINI%20PROJ/config/settings.py) |
| **SR-04** | Input validation / encoding | `TC-15` | Issue #27 | [`templates/`](file:///d:/SE%20MINI%20PROJ/templates/) |
| **SR-05** | Failed-login rate limiting | `TC-15` | Issue #28 | [`accounts/models.py`](file:///d:/SE%20MINI%20PROJ/accounts/models.py) |
| **ENG-01**| Repository setup | CI | Issue #29 | Full project scaffolding |
| **ENG-02**| DB schema & migrations | Unit | Issue #30 | App migrations |
| **ENG-03**| Backend API foundation | API | Issue #31 | REST endpoints |
| **ENG-04**| Frontend layout & nav | `NFR-04` | Issue #32 | [`templates/base.html`](file:///d:/SE%20MINI%20PROJ/templates/base.html) |
| **ENG-05**| Kanban board UI | `NFR-05` | Issue #33 | [`templates/projects/detail.html`](file:///d:/SE%20MINI%20PROJ/templates/projects/detail.html) |
| **ENG-06**| CI test workflow | GitHub | Issue #34 | [`.github/workflows/ci.yml`](file:///d:/SE%20MINI%20PROJ/.github/workflows/ci.yml) |
| **TEST-01**| Unit testing | All | Issue #35 | [`tests/`](file:///d:/SE%20MINI%20PROJ/tests/) |
| **TEST-02**| Integration testing | All | Issue #36 | [`tests/`](file:///d:/SE%20MINI%20PROJ/tests/) |
| **TEST-03**| Acceptance testing (TC-01–18)| All | Issue #37 | [`tests/`](file:///d:/SE%20MINI%20PROJ/tests/) |
| **TEST-04**| Regression testing | CI | Issue #38 | Automated regression pipeline |
| **DOC-01** | Architecture documentation | DOC | Issue #39 | [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) |
| **DOC-02** | Traceability & test report | DOC | Issue #40 | [`docs/TEST_RESULTS_AND_TRACEABILITY_REPORT.md`](docs/TEST_RESULTS_AND_TRACEABILITY_REPORT.md) |
| **DOC-03** | Final project report & demo | DOC | Issue #41 | [`docs/FINAL_PROJECT_REPORT.md`](docs/FINAL_PROJECT_REPORT.md) |

---

## 8. Documentation Artifacts & Architecture Specifications
- **[Software Architecture Document (SAD v1.1)](docs/ARCHITECTURE.md)**: Monolithic layered design, Django component boundaries, Mermaid database ER schema, and REST interface contracts.
- **[System and Acceptance Test Report](docs/SYSTEM_AND_ACCEPTANCE_TEST_REPORT.md)**: Full verification record for acceptance cases TC-01 through TC-18 with 100% pass rate.
- **[Test Results and Traceability Report](docs/TEST_RESULTS_AND_TRACEABILITY_REPORT.md)**: Comprehensive SRS-to-SAD-to-STP requirements traceability matrix.
- **[Final Project Report & Sprint Guide](docs/FINAL_PROJECT_REPORT.md)**: Complete sprint demonstration guide and evaluation walkthrough.
- **[API Reference](docs/API_REFERENCE.md)**: Complete REST endpoint catalog with payload specifications.
