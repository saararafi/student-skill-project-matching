"""
Covers the two problems that were reported.

- The pages must not be cached, so a browser never looks for elements
  that the current JavaScript no longer finds.
- A brand new account must start with an empty profile: no demo skills,
  no demo interests and no demo experiences.
"""
import io
import os
import sys
import unittest
import uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.app import create_app  # noqa: E402

FRONTEND = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'frontend')


class TestPagesAreNotCached(unittest.TestCase):

    def setUp(self):
        self.app = create_app()
        self.client = self.app.test_client()

    def test_a_page_is_sent_with_no_cache(self):
        res = self.client.get('/dashboard.html')
        self.assertEqual(res.status_code, 200)
        self.assertIn('no-cache', res.headers.get('Cache-Control', ''))

    def test_the_registration_page_is_sent_with_no_cache(self):
        res = self.client.get('/register.html')
        self.assertEqual(res.status_code, 200)
        self.assertIn('no-cache', res.headers.get('Cache-Control', ''))

    def test_the_landing_page_is_sent_with_no_cache(self):
        res = self.client.get('/')
        self.assertEqual(res.status_code, 200)
        self.assertIn('no-cache', res.headers.get('Cache-Control', ''))

    def test_the_stylesheets_can_still_be_cached(self):
        res = self.client.get('/css/style.css')
        self.assertEqual(res.status_code, 200)
        self.assertNotIn('no-cache', res.headers.get('Cache-Control', ''))


class TestRegistrationPage(unittest.TestCase):

    def setUp(self):
        self.app = create_app()
        self.client = self.app.test_client()

    def test_the_registration_page_exists(self):
        res = self.client.get('/register.html')
        self.assertEqual(res.status_code, 200)

    def test_the_registration_form_is_visible_without_a_toggle(self):
        with io.open(os.path.join(FRONTEND, 'register.html'),
                     encoding='utf-8') as f:
            raw = f.read()

        self.assertIn('id="registerForm"', raw)
        # The form must not start hidden.
        self.assertNotIn('id="registerForm" style="display: none;"', raw)

    def test_the_sign_in_page_links_to_the_registration_page(self):
        with io.open(os.path.join(FRONTEND, 'login.html'),
                     encoding='utf-8') as f:
            raw = f.read()

        self.assertIn('href="register.html"', raw)


class TestAFreshAccountStartsEmpty(unittest.TestCase):

    def setUp(self):
        self.app = create_app()
        self.client = self.app.test_client()

    def register(self, email):
        # A unique address, so the test can be run more than once against
        # the same database.
        unique = f'{uuid.uuid4().hex[:8]}'
        res = self.client.post('/api/auth/register', json={
            'name': 'Ivy Green',
            'email': f'{unique}-{email}',
            'password': 'fresh-password',
            'role': 'student',
        })
        self.assertEqual(res.status_code, 201)
        return res.get_json()

    def test_a_new_account_has_no_skills_interests_or_experiences(self):
        self.register('fresh.account@example.com')

        res = self.client.get('/api/student/profile')
        self.assertEqual(res.status_code, 200)
        profile = res.get_json()['profile']

        self.assertEqual(profile['skills'], [])
        self.assertEqual(profile['interests'], [])
        self.assertEqual(profile['experiences'], [])

    def test_a_new_account_has_empty_statistics(self):
        self.register('fresh.stats@example.com')

        res = self.client.get('/api/matching/dashboard')
        self.assertEqual(res.status_code, 200)
        payload = res.get_json()
        dashboard = payload.get('dashboard') or payload

        stats = dashboard['stats']
        self.assertEqual(stats['skills'], 0)
        self.assertEqual(stats['interests'], 0)
        self.assertEqual(stats['experiences'], 0)
        self.assertEqual(stats['applications'], 0)

    def test_a_new_account_scores_almost_nothing(self):
        self.register('fresh.score@example.com')

        res = self.client.get('/api/matching/recommendations')
        self.assertEqual(res.status_code, 200)

        for project in res.get_json()['recommendations']:
            self.assertLess(project['match_score'], 30,
                            'a student with no skills should not match well')

    def test_the_pages_do_not_carry_the_demo_account_details(self):
        """No page may hardcode a name from the seeded demo accounts."""
        demo_names = ('Saara Rafi', 'Aisha Khan', 'Rahul Verma', 'Meera Patel',
                      'Arjun Nair', 'saara@example.com')

        for name in os.listdir(FRONTEND):
            if not name.endswith('.html'):
                continue
            if name == 'index.html':
                # The landing page shows example skills as an illustration.
                continue

            with io.open(os.path.join(FRONTEND, name), encoding='utf-8') as f:
                raw = f.read()

            for demo in demo_names:
                self.assertNotIn(
                    demo, raw,
                    f'{name} still shows the demo account "{demo}"')

    def test_the_dashboard_does_not_greet_the_demo_account(self):
        with io.open(os.path.join(FRONTEND, 'dashboard.html'),
                     encoding='utf-8') as f:
            raw = f.read()

        self.assertNotIn('WELCOME BACK, SAARA', raw)
        self.assertIn('data-dashboard-welcome', raw)


if __name__ == '__main__':
    unittest.main()
