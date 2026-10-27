import json
from django.contrib.auth import get_user_model
from django.test import TestCase, Client
from django.urls import reverse
from accounts.models import FailedLoginAttempt

User = get_user_model()


class AuthSessionsTests(TestCase):
    """
    Focused acceptance tests for SRS FR-02: Authentication and sessions (Issue #2, TC-02).
    """

    def setUp(self):
        self.client = Client()
        self.login_url = reverse('accounts:login')
        self.logout_url = reverse('accounts:logout')
        self.project_list_url = reverse('projects:project_list')
        self.user = User.objects.create_user(
            email='alice@example.com',
            password='ValidPassword123!',
            full_name='Alice Smith'
        )

    def test_valid_login_form_creates_session_and_redirects(self):
        """Valid sign-in establishes an authenticated session and redirects to projects."""
        resp = self.client.post(self.login_url, {
            'email': 'alice@example.com',
            'password': 'ValidPassword123!'
        })
        self.assertEqual(resp.status_code, 302)
        self.assertRedirects(resp, self.project_list_url)
        self.assertEqual(int(self.client.session['_auth_user_id']), self.user.id)

    def test_valid_login_json_api(self):
        """JSON sign-in returns 200 with user payload and sets session cookie."""
        resp = self.client.post(
            self.login_url,
            json.dumps({'email': 'alice@example.com', 'password': 'ValidPassword123!'}),
            content_type='application/json'
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data['id'], self.user.id)
        self.assertEqual(data['email'], 'alice@example.com')
        self.assertEqual(data['message'], 'Login successful')
        self.assertEqual(int(self.client.session['_auth_user_id']), self.user.id)

    def test_invalid_password_returns_401(self):
        """Incorrect password returns HTTP 401 and decrements remaining attempts."""
        resp = self.client.post(self.login_url, {
            'email': 'alice@example.com',
            'password': 'WrongPassword!'
        })
        self.assertEqual(resp.status_code, 401)
        self.assertNotIn('_auth_user_id', self.client.session)
        self.assertEqual(resp.context['attempts_remaining'], 4)

    def test_invalid_password_json_returns_401(self):
        """Incorrect password via JSON returns 401 with structured error."""
        resp = self.client.post(
            self.login_url,
            json.dumps({'email': 'alice@example.com', 'password': 'WrongPassword!'}),
            content_type='application/json'
        )
        self.assertEqual(resp.status_code, 401)
        data = resp.json()
        self.assertEqual(data['error']['code'], 'INVALID_CREDENTIALS')
        self.assertEqual(data['error']['attempts_remaining'], 4)

    def test_nonexistent_email_returns_401(self):
        """Unregistered email returns 401 without creating session."""
        resp = self.client.post(self.login_url, {
            'email': 'nonexistent@example.com',
            'password': 'AnyPassword123!'
        })
        self.assertEqual(resp.status_code, 401)
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_blank_credentials_rejected_with_400(self):
        """Missing email or password returns HTTP 400 Bad Request."""
        resp = self.client.post(self.login_url, {
            'email': '',
            'password': ''
        })
        self.assertEqual(resp.status_code, 400)

        resp_json = self.client.post(
            self.login_url,
            json.dumps({'email': '', 'password': ''}),
            content_type='application/json'
        )
        self.assertEqual(resp_json.status_code, 400)
        self.assertEqual(resp_json.json()['error']['code'], 'BAD_REQUEST')

    def test_email_case_insensitivity(self):
        """Email matching is case-insensitive during login."""
        resp = self.client.post(self.login_url, {
            'email': 'ALICE@EXAMPLE.COM',
            'password': 'ValidPassword123!'
        })
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(int(self.client.session['_auth_user_id']), self.user.id)

    def test_email_whitespace_trimmed(self):
        """Leading and trailing whitespace in email is trimmed during login."""
        resp = self.client.post(self.login_url, {
            'email': '  alice@example.com  ',
            'password': 'ValidPassword123!'
        })
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(int(self.client.session['_auth_user_id']), self.user.id)

    def test_sign_out_closes_session(self):
        """Sign-out terminates the authenticated session and redirects to login."""
        self.client.force_login(self.user)
        self.assertIn('_auth_user_id', self.client.session)

        resp = self.client.get(self.logout_url)
        self.assertEqual(resp.status_code, 302)
        self.assertRedirects(resp, self.login_url)
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_sign_out_json_api(self):
        """JSON sign-out terminates session and returns 200."""
        self.client.force_login(self.user)
        resp = self.client.post(
            self.logout_url,
            content_type='application/json'
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()['message'], 'Logged out successfully')
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_authenticated_user_accessing_login_redirects(self):
        """Already signed-in user accessing login view is redirected to projects."""
        self.client.force_login(self.user)
        resp = self.client.get(self.login_url)
        self.assertEqual(resp.status_code, 302)
        self.assertRedirects(resp, self.project_list_url)

    def test_unauthenticated_protected_route_redirects_to_login(self):
        """Unauthenticated user accessing protected project dashboard is redirected to login."""
        resp = self.client.get(self.project_list_url)
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(resp.url.startswith(self.login_url))
