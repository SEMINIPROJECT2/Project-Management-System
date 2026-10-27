import os
from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase, Client
from django.urls import reverse
from projects.models import Project, Membership
from tasks.models import Task

User = get_user_model()


class KeyboardAccessibilityTests(TestCase):
    """
    Verification tests for SRS NFR-05: Keyboard accessibility (Issue #22).
    Ensures keyboard-only operation, visible focus indicators, skip-to-content,
    programmatic labels, and accessible status transition controls.
    """

    def setUp(self):
        self.client = Client()
        self.owner = User.objects.create_user(
            email='lead@example.com',
            password='LeadPassword123!',
            full_name='Lead Dev'
        )
        self.client.force_login(self.owner)
        self.project = Project.objects.create(name='Accessibility Project', owner=self.owner)
        Membership.objects.create(project=self.project, user=self.owner, role=Membership.ROLE_OWNER)
        self.project_detail_url = reverse('projects:project_detail', kwargs={'project_id': self.project.id})

    def test_skip_to_main_content_link_rendered(self):
        """Verify skip-to-content link is present and targets #main-content."""
        resp = self.client.get(self.project_detail_url)
        self.assertEqual(resp.status_code, 200)
        content = resp.content.decode('utf-8')
        self.assertIn('class="skip-link"', content)
        self.assertIn('href="#main-content"', content)
        self.assertIn('id="main-content"', content)
        self.assertIn('tabindex="-1"', content)

    def test_form_inputs_have_programmatic_labels(self):
        """Verify filter toolbar controls and search input have programmatic accessible labels."""
        resp = self.client.get(self.project_detail_url)
        self.assertEqual(resp.status_code, 200)
        content = resp.content.decode('utf-8')

        self.assertIn('id="task-search"', content)
        self.assertIn('aria-label="Search tasks"', content)
        self.assertIn('id="filter-assignee"', content)
        self.assertIn('aria-label="Filter by Assignee"', content)
        self.assertIn('id="filter-priority"', content)
        self.assertIn('aria-label="Filter by Priority"', content)
        self.assertIn('id="filter-due"', content)
        self.assertIn('aria-label="Filter by Due Status"', content)

    def test_kanban_columns_have_accessible_labels(self):
        """Verify all 5 Kanban column bodies define accessible labels for screen readers."""
        resp = self.client.get(self.project_detail_url)
        self.assertEqual(resp.status_code, 200)
        content = resp.content.decode('utf-8')

        for status in ['Backlog', 'To Do', 'In Progress', 'Review', 'Done']:
            self.assertIn(f'aria-label="{status} column"', content)
            self.assertIn(f'data-status="{status}"', content)

    def test_modal_keyboard_status_selector_rendered(self):
        """Verify the modal includes an accessible dropdown selector for keyboard-only status transitions."""
        resp = self.client.get(self.project_detail_url)
        self.assertEqual(resp.status_code, 200)
        content = resp.content.decode('utf-8')

        self.assertIn('id="modal-status-select"', content)
        self.assertIn('aria-label="Change Status"', content)
        for status in ['Backlog', 'To Do', 'In Progress', 'Review', 'Done']:
            self.assertIn(f'<option value="{status}">{status}</option>', content)

    def test_board_script_contains_keyboard_bindings(self):
        """Verify board.js contains keyboard listeners for card activation and Escape dismissal."""
        js_path = os.path.join(settings.BASE_DIR, 'static', 'js', 'board.js')
        with open(js_path, 'r', encoding='utf-8') as f:
            js_content = f.read()

        # Keyboard activation for cards
        self.assertIn("card.tabIndex = 0", js_content)
        self.assertIn("card.setAttribute('role', 'button')", js_content)
        self.assertIn("e.key === 'Enter'", js_content)
        self.assertIn("e.key === ' '", js_content)

        # Global modal dismissal via Escape key
        self.assertIn("e.key === 'Escape'", js_content)

    def test_style_sheet_contains_focus_visible_rules(self):
        """Verify style.css provides explicit :focus-visible indicators and skip-link styles."""
        css_path = os.path.join(settings.BASE_DIR, 'static', 'css', 'style.css')
        with open(css_path, 'r', encoding='utf-8') as f:
            css_content = f.read()

        self.assertIn('.skip-link', css_content)
        self.assertIn(':focus-visible', css_content)
        self.assertIn('.task-card:focus-visible', css_content)
