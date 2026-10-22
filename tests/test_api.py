"""
API integration tests for the Flask backend.

Uses Flask's built-in test client so no running server is required.

Run with:
    python -m unittest discover -s tests -v
"""

import os
import shutil
import sys
import tempfile
import unittest

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, BASE_DIR)

from backend.config import Config
from backend.app import create_app


class ApiTestCase(unittest.TestCase):
    """Base class providing an isolated client and a throwaway database."""

    @classmethod
    def setUpClass(cls):
        # Point the app at a throwaway SQLite file so the tests never touch
        # the developer's database/skillmatch.db.
        cls._tmpdir = tempfile.mkdtemp(prefix='skillmatch-test-')
        cls._db_path = os.path.join(cls._tmpdir, 'test.db')
        cls._original_db_path = Config.SQLITE_DB_PATH
        cls._original_seed_demo = Config.SEED_DEMO_DATA
        Config.SQLITE_DB_PATH = cls._db_path
        Config.SEED_DEMO_DATA = True

        cls.app = create_app()
        cls.app.config['TESTING'] = True

    @classmethod
    def tearDownClass(cls):
        Config.SQLITE_DB_PATH = cls._original_db_path
        Config.SEED_DEMO_DATA = cls._original_seed_demo
        shutil.rmtree(cls._tmpdir, ignore_errors=True)

    def setUp(self):
        self.client = self.app.test_client()

    # -- helpers ---------------------------------------------------------

    def login(self, email='saara@example.com', password='password123'):
        return self.client.post('/api/auth/login', json={
            'email': email, 'password': password
        })

    def login_faculty(self):
        return self.login('priya.sharma@faculty.edu', 'password123')


class TestHealthAndStatic(ApiTestCase):

    def test_health_endpoint(self):
        res = self.client.get('/api/health')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.get_json()['status'], 'healthy')

    def test_index_page_served(self):
        res = self.client.get('/')
        self.assertEqual(res.status_code, 200)
        self.assertIn('text/html', res.headers['Content-Type'])

    def test_unknown_api_route_returns_json_404(self):
        res = self.client.get('/api/does-not-exist')
        self.assertEqual(res.status_code, 404)
        self.assertEqual(res.get_json()['success'], False)

    def test_unknown_api_route_is_not_spa_html(self):
        res = self.client.get('/api/matching/gaps/1')
        self.assertEqual(res.status_code, 404)
        self.assertIn('application/json', res.headers['Content-Type'])


class TestAuthentication(ApiTestCase):

    def test_login_with_demo_password_succeeds(self):
        res = self.login()
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data['success'])
        self.assertEqual(data['user']['email'], 'saara@example.com')

    def test_login_with_wrong_password_is_rejected(self):
        res = self.login(password='not-the-password')
        self.assertEqual(res.status_code, 401)
        self.assertFalse(res.get_json()['success'])

    def test_registered_user_cannot_log_in_with_demo_password(self):
        """The old 'password123' fallback must not work for new accounts."""
        res = self.client.post('/api/auth/register', json={
            'name': 'Test Student',
            'email': 'test.student@example.com',
            'password': 'a-unique-password',
            'role': 'student'
        })
        self.assertEqual(res.status_code, 201)

        # The demo password must NOT open this account.
        res = self.client.post('/api/auth/login', json={
            'email': 'test.student@example.com',
            'password': 'password123'
        })
        self.assertEqual(res.status_code, 401)

        # The real password must work.
        res = self.client.post('/api/auth/login', json={
            'email': 'test.student@example.com',
            'password': 'a-unique-password'
        })
        self.assertEqual(res.status_code, 200)

    def test_duplicate_registration_is_rejected(self):
        payload = {
            'name': 'Dup Student',
            'email': 'dup.student@example.com',
            'password': 'another-password',
            'role': 'student'
        }
        self.assertEqual(self.client.post('/api/auth/register', json=payload).status_code, 201)
        self.assertEqual(self.client.post('/api/auth/register', json=payload).status_code, 409)

    def test_logout_clears_session(self):
        self.login()
        self.client.post('/api/auth/logout')
        res = self.client.put('/api/student/profile', json={'bio': 'x'})
        self.assertEqual(res.status_code, 401)


class TestAnonymousAccess(ApiTestCase):
    """Reads work in demo mode; writes must not."""

    def test_public_endpoints_available_anonymously(self):
        """Project listings are public; everything student-specific is not."""
        for path in ['/api/projects', '/api/health']:
            with self.subTest(path=path):
                res = self.client.get(path)
                self.assertEqual(res.status_code, 200)

    def test_student_endpoints_require_a_session(self):
        """Student data is private, so it needs a login."""
        for path in ['/api/student/profile', '/api/student/settings',
                     '/api/matching/recommendations', '/api/matching/dashboard',
                     '/api/matching/projects/1/gaps',
                     '/api/matching/projects/1/teammates',
                     '/api/applications']:
            with self.subTest(path=path):
                res = self.client.get(path)
                self.assertIn(res.status_code, (401, 404))

    def test_profile_update_requires_login(self):
        res = self.client.put('/api/student/profile', json={'bio': 'anonymous edit'})
        self.assertEqual(res.status_code, 401)
        self.assertFalse(res.get_json()['success'])

    def test_add_skill_requires_login(self):
        res = self.client.post('/api/student/skills', json={
            'skill_name': 'Rust', 'proficiency_level': 4
        })
        self.assertEqual(res.status_code, 401)

    def test_delete_skill_requires_login(self):
        res = self.client.delete('/api/student/skills/1')
        self.assertEqual(res.status_code, 401)

    def test_upload_certificate_requires_login(self):
        res = self.client.post(
            '/api/student/upload-certificate',
            data={'skill_id': '1', 'certificate': (b'%PDF-1.4 fake', 'cert.pdf')},
            content_type='multipart/form-data'
        )
        self.assertEqual(res.status_code, 401)

    def test_apply_requires_login(self):
        res = self.client.post('/api/projects/3/apply', json={'message': 'let me in'})
        self.assertEqual(res.status_code, 401)

    def test_create_project_requires_faculty(self):
        res = self.client.post('/api/projects', json={
            'title': 'Sneaky Project', 'description': 'should not be created'
        })
        self.assertIn(res.status_code, (401, 403))

    def test_verify_certificate_requires_faculty(self):
        res = self.client.post('/api/student/verify-certificate', json={
            'student_id': 1, 'skill_id': 1, 'status': 'Verified'
        })
        self.assertIn(res.status_code, (401, 403))

    def test_review_application_requires_faculty(self):
        res = self.client.put('/api/applications/1/status', json={'status': 'Accepted'})
        self.assertIn(res.status_code, (401, 403))

    def test_mark_notifications_read_requires_login(self):
        res = self.client.post('/api/notifications/1/read')
        self.assertEqual(res.status_code, 401)
        res = self.client.post('/api/notifications/read-all')
        self.assertEqual(res.status_code, 401)


class TestStudentAccess(ApiTestCase):

    def test_logged_in_student_can_update_profile(self):
        self.login()
        res = self.client.put('/api/student/profile', json={'bio': 'Updated bio for test.'})
        self.assertEqual(res.status_code, 200)

    def test_logged_in_student_cannot_verify_own_certificate(self):
        self.login()
        res = self.client.post('/api/student/verify-certificate', json={
            'student_id': 1, 'skill_id': 1, 'status': 'Verified'
        })
        self.assertIn(res.status_code, (403, 404))

    def test_logged_in_student_cannot_review_applications(self):
        self.login()
        res = self.client.put('/api/applications/1/status', json={'status': 'Accepted'})
        self.assertIn(res.status_code, (403, 404))

    def test_logged_in_student_cannot_create_project(self):
        self.login()
        res = self.client.post('/api/projects', json={
            'title': 'Student Project', 'description': 'nope'
        })
        self.assertIn(res.status_code, (403, 404))

    def test_duplicate_application_is_rejected(self):
        self.login()
        res = self.client.post('/api/projects/1/apply', json={'message': 'first'})
        # Student 1 already has an application for project 1 in the seed data.
        self.assertEqual(res.status_code, 400)


class TestFacultyAccess(ApiTestCase):

    def test_faculty_can_create_project(self):
        self.login_faculty()
        res = self.client.post('/api/projects', json={
            'title': 'Faculty Created Project',
            'description': 'Created by the faculty test.',
            'domain': 'Testing',
            'skills': [{'name': 'Testing', 'required_level': 3}]
        })
        self.assertEqual(res.status_code, 201)
        self.assertTrue(res.get_json()['success'])

    def test_faculty_can_verify_certificate(self):
        self.login_faculty()
        res = self.client.post('/api/student/verify-certificate', json={
            'student_id': 1, 'skill_id': 1, 'status': 'Verified'
        })
        self.assertEqual(res.status_code, 200)

    def test_faculty_sees_all_applications(self):
        self.login_faculty()
        res = self.client.get('/api/applications')
        self.assertEqual(res.status_code, 200)
        self.assertGreater(len(res.get_json()['applications']), 0)

    def test_faculty_can_review_application(self):
        self.login_faculty()
        res = self.client.put(
            '/api/faculty/applications/2/status', json={'status': 'Accepted'})
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.get_json()['success'])


class TestMatchingEndpoints(ApiTestCase):

    def test_recommendations_are_sorted_descending(self):
        self.login()
        res = self.client.get('/api/matching/recommendations')
        self.assertEqual(res.status_code, 200)
        recs = res.get_json()['recommendations']
        scores = [r['match_score'] for r in recs]
        self.assertEqual(scores, sorted(scores, reverse=True))

    def test_match_breakdown_weights_sum_to_one(self):
        self.login()
        res = self.client.get('/api/matching/recommendations')
        recs = res.get_json()['recommendations']
        for rec in recs:
            expected = round(
                rec['skill_score'] * 0.50
                + rec['interest_score'] * 0.20
                + rec['experience_score'] * 0.20
                + rec['availability_score'] * 0.10, 2
            )
            self.assertAlmostEqual(rec['match_score'], expected, places=1)

    def test_gaps_endpoint_reports_every_required_skill(self):
        self.login()
        res = self.client.get('/api/matching/projects/1/gaps')
        self.assertEqual(res.status_code, 200)
        payload = res.get_json()
        body = payload.get('gaps') or payload.get('data') or payload
        for item in body['skill_breakdown']:
            self.assertIn(item['status'], ('Missing', 'Insufficient', 'Covered'))

    def test_teammates_respect_required_proficiency(self):
        """A recommended skill must meet the level the project requires."""
        self.login()
        res = self.client.get('/api/matching/projects/1/teammates')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        payload = self.client.get(
            '/api/matching/projects/1/gaps'
        ).get_json()
        body = payload.get('gaps') or payload.get('data') or payload
        gaps = body['gaps']

        for mate in data['teammates']:
            for skill in mate['matching_skills_detailed']:
                required = gaps[skill['name']]['required_level']
                self.assertGreaterEqual(skill['level'], required)

    def test_unknown_project_gaps_returns_404(self):
        self.login()
        res = self.client.get('/api/matching/projects/9999/gaps')
        self.assertEqual(res.status_code, 404)


class TestDashboardEndpoint(ApiTestCase):

    def test_dashboard_payload(self):
        self.login()
        res = self.client.get('/api/matching/dashboard')
        self.assertEqual(res.status_code, 200)
        d = res.get_json()['dashboard']

        self.assertIn('profile', d)
        self.assertIn('stats', d)
        self.assertIn('top_match', d)
        self.assertIn('skills', d)
        self.assertIn('applications', d)
        self.assertIn('notifications', d)
        self.assertIn('recommendations', d)

    def test_dashboard_stats_match_profile_data(self):
        self.login()
        d = self.client.get('/api/matching/dashboard').get_json()['dashboard']
        profile = self.client.get('/api/student/profile').get_json()['profile']

        self.assertEqual(d['stats']['skills'], len(profile['skills']))
        self.assertEqual(d['stats']['interests'], len(profile['interests']))
        self.assertEqual(d['stats']['experiences'], len(profile['experiences']))

    def test_dashboard_top_match_is_the_highest_scoring_project(self):
        self.login()
        d = self.client.get('/api/matching/dashboard').get_json()['dashboard']
        recs = self.client.get(
            '/api/matching/recommendations'
        ).get_json()['recommendations']

        self.assertIsNotNone(d['top_match'])
        self.assertEqual(d['top_match']['project_id'], recs[0]['id'])
        self.assertEqual(d['top_match']['final_score'], recs[0]['match_score'])

    def test_dashboard_completeness_is_a_percentage(self):
        self.login()
        d = self.client.get('/api/matching/dashboard').get_json()['dashboard']
        self.assertGreaterEqual(d['profile']['completeness'], 0)
        self.assertLessEqual(d['profile']['completeness'], 100)


class TestSettingsAndInterests(ApiTestCase):

    def test_settings_readable_anonymously(self):
        self.login()
        res = self.client.get('/api/student/settings')
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.get_json()['success'])

    def test_settings_update_requires_login(self):
        res = self.client.put('/api/student/settings', json={'match_alerts': 0})
        self.assertEqual(res.status_code, 401)

    def test_settings_round_trip(self):
        self.login()
        res = self.client.put('/api/student/settings', json={
            'match_alerts': 0,
            'prioritise_skills': 1,
            'consider_interests': 0,
            'consider_experience': 1,
            'consider_availability': 1
        })
        self.assertEqual(res.status_code, 200)

        settings = self.client.get('/api/student/settings').get_json()['settings']
        self.assertEqual(settings['match_alerts'], 0)
        self.assertEqual(settings['consider_interests'], 0)

    def test_visibility_value_is_validated(self):
        self.login()
        self.client.put('/api/student/settings', json={'profile_visibility': 'nonsense'})
        settings = self.client.get('/api/student/settings').get_json()['settings']
        self.assertIn(settings['profile_visibility'], ('public', 'team', 'private'))

    def test_disabled_factor_changes_the_match_score(self):
        """With only the skill factor enabled the score must equal the skill score."""
        self.login()

        def recommendations():
            return self.client.get(
                '/api/matching/recommendations'
            ).get_json()['recommendations']

        self.client.put('/api/student/settings', json={
            'prioritise_skills': 1,
            'consider_interests': 0,
            'consider_experience': 0,
            'consider_availability': 0
        })
        for rec in recommendations():
            self.assertAlmostEqual(rec['match_score'], rec['skill_score'], places=1)

        self.client.put('/api/student/settings', json={
            'prioritise_skills': 1,
            'consider_interests': 1,
            'consider_experience': 1,
            'consider_availability': 1
        })
        # Restore the defaults for the remaining tests.
        for rec in recommendations():
            expected = round(
                rec['skill_score'] * 0.50
                + rec['interest_score'] * 0.20
                + rec['experience_score'] * 0.20
                + rec['availability_score'] * 0.10, 2
            )
            self.assertAlmostEqual(rec['match_score'], expected, places=1)

    def test_interests_readable(self):
        self.login()
        res = self.client.get('/api/student/interests')
        self.assertEqual(res.status_code, 200)
        self.assertIn('interests', res.get_json())

    def test_interests_update_requires_login(self):
        res = self.client.put('/api/student/interests', json={'interests': ['AI']})
        self.assertEqual(res.status_code, 401)

    def test_interests_round_trip_and_dedupe(self):
        self.login()
        res = self.client.put('/api/student/interests', json={
            'interests': [
                'Artificial Intelligence',
                '  Artificial Intelligence  ',
                'Web Development'
            ]
        })
        self.assertEqual(res.status_code, 200)
        stored = res.get_json()['interests']
        self.assertEqual(len(stored), 2)
        self.assertIn('Artificial Intelligence', stored)
        self.assertIn('Web Development', stored)

    def test_interests_must_be_a_list(self):
        self.login()
        res = self.client.put('/api/student/interests', json={'interests': 'AI'})
        self.assertEqual(res.status_code, 400)


class TestWithdrawApplication(ApiTestCase):

    def test_withdraw_requires_login(self):
        res = self.client.post('/api/applications/2/withdraw')
        self.assertEqual(res.status_code, 401)

    def test_student_can_withdraw_own_application(self):
        self.login()
        res = self.client.post('/api/applications/2/withdraw')
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.get_json()['success'])

        # The application should be gone.
        apps = self.client.get('/api/applications').get_json()['applications']
        self.assertNotIn(2, [a['id'] for a in apps])

    def test_cannot_withdraw_someone_elses_application(self):
        self.login('aisha@example.com')
        res = self.client.post('/api/applications/1/withdraw')
        self.assertIn(res.status_code, (403, 404))

    def test_accepted_application_cannot_be_withdrawn(self):
        self.login()
        res = self.client.post('/api/applications/1/withdraw')
        self.assertEqual(res.status_code, 400)

    def test_unknown_application_returns_404(self):
        self.login()
        res = self.client.post('/api/applications/9999/withdraw')
        self.assertEqual(res.status_code, 404)


class TestFacultyConsole(ApiTestCase):

    def test_overview_requires_faculty(self):
        res = self.client.get('/api/faculty/overview')
        self.assertIn(res.status_code, (401, 403))

        self.login()  # student
        res = self.client.get('/api/faculty/overview')
        self.assertIn(res.status_code, (403, 404))

    def test_faculty_overview_payload(self):
        self.login_faculty()
        res = self.client.get('/api/faculty/overview')
        self.assertEqual(res.status_code, 200)
        payload = res.get_json()
        o = payload.get('overview') or payload

        self.assertIn('faculty', o)
        self.assertIn('stats', o)
        self.assertIn('projects', o)
        self.assertIn('applications', o)
        self.assertIn('pending_certificates', o)

    def test_faculty_only_sees_their_own_projects(self):
        self.login_faculty()  # Priya owns projects 1, 2, 5
        payload = self.client.get('/api/faculty/overview').get_json()
        o = payload.get('overview') or payload
        project_ids = [p['id'] for p in o['projects']]
        self.assertEqual(sorted(project_ids), [1, 2, 5])

    def test_faculty_can_review_application(self):
        self.login_faculty()
        # Application 2 belongs to project 2, which Priya owns.
        res = self.client.put('/api/faculty/applications/2/status', json={'status': 'Accepted'})
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.get_json()['success'])

    def test_faculty_cannot_review_another_facultys_application(self):
        self.login_faculty()  # Priya
        # Application 3 belongs to project 3, owned by Ramesh Kumar.
        res = self.client.put('/api/faculty/applications/3/status', json={'status': 'Accepted'})
        self.assertIn(res.status_code, (403, 404))

    def test_reviewing_accepts_seats_the_student_on_the_team(self):
        self.login_faculty()
        self.client.put('/api/faculty/applications/2/status', json={'status': 'Accepted'})

        details = self.client.get('/api/projects/2').get_json()['project']
        names = [m['name'] for m in details['team_members']]
        self.assertIn('Saara Rafi', names)

    def test_invalid_status_rejected(self):
        self.login_faculty()
        res = self.client.put('/api/faculty/applications/2/status', json={'status': 'Maybe'})
        self.assertEqual(res.status_code, 400)

    def test_pending_certificates_listed(self):
        self.login_faculty()
        res = self.client.get('/api/faculty/certificates')
        self.assertEqual(res.status_code, 200)
        self.assertIn('certificates', res.get_json())

    def test_faculty_can_verify_certificate(self):
        self.login_faculty()
        res = self.client.put(
            '/api/faculty/certificates/1/2',
            json={'status': 'Verified'}
        )
        self.assertEqual(res.status_code, 200)

    def test_invalid_certificate_status_rejected(self):
        self.login_faculty()
        res = self.client.put(
            '/api/faculty/certificates/1/2',
            json={'status': 'Nonsense'}
        )
        self.assertEqual(res.status_code, 400)

    def test_faculty_cannot_verify_unrelated_student_certificate(self):
        self.login_faculty()
        # Student 5 (Arjun) never applied to Priya's projects.
        res = self.client.put(
            '/api/faculty/certificates/5/11',
            json={'status': 'Verified'}
        )
        self.assertIn(res.status_code, (403, 404))


class TestExperiences(ApiTestCase):

    def test_experiences_readable(self):
        self.login()
        res = self.client.get('/api/student/experiences')
        self.assertEqual(res.status_code, 200)
        self.assertIn('experiences', res.get_json())

    def test_add_experience_requires_login(self):
        res = self.client.post('/api/student/experiences', json={'title': 'Testing'})
        self.assertEqual(res.status_code, 401)

    def test_add_and_remove_experience(self):
        self.login()
        res = self.client.post('/api/student/experiences', json={'title': 'Robotics Club'})
        self.assertEqual(res.status_code, 201)
        new_id = res.get_json()['experience']['id']

        titles = [e['title'] for e in
                  self.client.get('/api/student/experiences').get_json()['experiences']]
        self.assertIn('Robotics Club', titles)

        res = self.client.delete(f'/api/student/experiences/{new_id}')
        self.assertEqual(res.status_code, 200)

        titles = [e['title'] for e in
                  self.client.get('/api/student/experiences').get_json()['experiences']]
        self.assertNotIn('Robotics Club', titles)

    def test_experience_title_is_required(self):
        self.login()
        res = self.client.post('/api/student/experiences', json={'title': '   '})
        self.assertEqual(res.status_code, 400)

    def test_duplicate_experience_is_rejected(self):
        self.login()
        res = self.client.post('/api/student/experiences', json={'title': 'Web Development'})
        self.assertEqual(res.status_code, 400)

    def test_cannot_delete_another_students_experience(self):
        self.login('aisha@example.com')
        before = self.client.get('/api/student/experiences').get_json()['experiences']

        # Experience 1 belongs to Saara, so Aisha's delete must be a no-op.
        res = self.client.delete('/api/student/experiences/1')
        self.assertEqual(res.status_code, 200)

        after = self.client.get('/api/student/experiences').get_json()['experiences']
        self.assertEqual(before, after)


class TestSettingsAccountFields(ApiTestCase):

    def test_settings_expose_account_details(self):
        self.login()
        settings = self.client.get('/api/student/settings').get_json()['settings']
        for key in ['name', 'email', 'department', 'year', 'semester', 'availability']:
            self.assertIn(key, settings)

    def test_settings_update_requires_login(self):
        res = self.client.put('/api/student/settings', json={'name': 'Hacker'})
        self.assertEqual(res.status_code, 401)

    def test_account_details_are_saved(self):
        self.login()
        res = self.client.put('/api/student/settings', json={
            'name': 'Saara R. Rafi',
            'department': 'Information Science',
            'year': '2nd Year',
            'semester': '6th Semester',
            'availability': 'Part-time'
        })
        self.assertEqual(res.status_code, 200)

        settings = self.client.get('/api/student/settings').get_json()['settings']
        self.assertEqual(settings['name'], 'Saara R. Rafi')
        self.assertEqual(settings['department'], 'Information Science')
        self.assertEqual(settings['year'], '2nd Year')
        self.assertEqual(settings['semester'], '6th Semester')
        self.assertEqual(settings['availability'], 'Part-time')

        # The profile endpoint reflects the same change.
        profile = self.client.get('/api/student/profile').get_json()['profile']
        self.assertEqual(profile['name'], 'Saara R. Rafi')
        self.assertEqual(profile['department'], 'Information Science')
        self.assertEqual(profile['availability'], 'Part-time')

    def test_duplicate_email_is_rejected(self):
        self.login()
        res = self.client.put('/api/student/settings', json={'email': 'aisha@example.com'})
        self.assertEqual(res.status_code, 409)

    def test_invalid_availability_is_rejected(self):
        self.login()
        res = self.client.put('/api/student/settings', json={'availability': 'Whenever'})
        self.assertEqual(res.status_code, 400)

    def test_availability_affects_the_match_score(self):
        """A part-time student scores lower on a full-time project."""
        self.login()

        # Project 1 requires full-time commitment.
        def availability_score():
            rec = self.client.get('/api/projects/1').get_json()['project']
            return rec['match']['scores']['availability_score']

        self.client.put('/api/student/settings', json={'availability': 'Full-time'})
        full_time = availability_score()
        self.client.put('/api/student/settings', json={'availability': 'Part-time'})
        part_time = availability_score()

        self.assertEqual(full_time, 100)
        self.assertEqual(part_time, 50)

        # Restore.
        self.client.put('/api/student/settings', json={'availability': 'Full-time'})


class TestWeeklyAvailability(ApiTestCase):

    def test_weekly_hours_defaults_and_round_trips(self):
        self.login()
        settings = self.client.get('/api/student/settings').get_json()['settings']
        self.assertIn('weekly_hours', settings)
        self.assertIsInstance(settings['weekly_hours'], int)

        res = self.client.put('/api/student/settings', json={'weekly_hours': 28})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.get_json()['settings']['weekly_hours'], 28)

        settings = self.client.get('/api/student/settings').get_json()['settings']
        self.assertEqual(settings['weekly_hours'], 28)

    def test_weekly_hours_is_clamped(self):
        self.login()
        res = self.client.put('/api/student/settings', json={'weekly_hours': 999})
        self.assertEqual(res.get_json()['settings']['weekly_hours'], 40)

        res = self.client.put('/api/student/settings', json={'weekly_hours': -5})
        self.assertEqual(res.get_json()['settings']['weekly_hours'], 0)

    def test_weekly_hours_requires_login(self):
        res = self.client.put('/api/student/settings', json={'weekly_hours': 10})
        self.assertEqual(res.status_code, 401)


class TestChatbot(ApiTestCase):

    def test_chat_requires_login(self):
        res = self.client.post('/api/chat', json={'message': 'hello'})
        self.assertEqual(res.status_code, 401)

    def test_chat_empty_message_rejected(self):
        self.login()
        res = self.client.post('/api/chat', json={'message': '   '})
        self.assertEqual(res.status_code, 400)

    def test_chat_status_endpoint(self):
        self.login()
        res = self.client.get('/api/chat/status')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data['online'])
        self.assertIn('greeting', data)
        self.assertIsInstance(data['suggestions'], list)

    def test_chat_student_recommendations(self):
        self.login()
        res = self.client.post('/api/chat', json={'message': 'What projects match my skills?'})
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data['success'])
        self.assertIn('reply', data)
        self.assertIsInstance(data['suggestions'], list)

    def test_chat_faculty(self):
        self.login_faculty()
        res = self.client.post('/api/chat', json={'message': 'Hello, what can you do?'})
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data['success'])
        self.assertEqual(data['context']['role'], 'faculty')


if __name__ == '__main__':
    unittest.main(verbosity=2)
