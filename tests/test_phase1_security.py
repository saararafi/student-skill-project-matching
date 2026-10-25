"""
Phase 1 Security Hardening Tests.

Covers:
- Issue 1: XSS prevention & Security Headers (CSP, nosniff, DENY)
- Issue 19: Prohibition of public faculty/admin registration & secure admin user creation
- Issue 20: Safe certificate verification authorization and negative checks
- Issue 21: Login enumeration prevention (consistent 401) and rate limiting (429)
- Issue 22: ProxyFix configuration and CSRF origin validation
- Issue 23: Untrimmed password preservation and length policy enforcement (min 8 chars)
- Issue 25: Profile privacy restrictions and secure project invitation checks
- Issue 26: Complete prevention of orphaned certificate file access
"""

import os
import unittest
from backend.app import create_app
from backend.database import execute_query, fetch_one
from backend.rate_limiter import clear_all_rate_limits
from werkzeug.security import generate_password_hash


class Phase1SecurityTests(unittest.TestCase):
    def setUp(self):
        clear_all_rate_limits()
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.app.config['ENFORCE_CSRF_IN_TESTS'] = True
        self.app.config['ENFORCE_RATE_LIMIT_IN_TESTS'] = True
        self.client = self.app.test_client()

        # Create isolated test users for Phase 1
        with self.app.app_context():
            # Clean any old test users
            execute_query("DELETE FROM users WHERE email LIKE 'sec_%@example.com'")
            
            # Student 1 (Normal)
            execute_query("""
                INSERT INTO users (name, email, password_hash, role)
                VALUES ('Sec Student One', 'sec_stu1@example.com', %s, 'student')
            """, (generate_password_hash("password123"),))
            u1 = fetch_one("SELECT id FROM users WHERE email = 'sec_stu1@example.com'")
            execute_query("""
                INSERT INTO students (user_id, department, year, semester, availability, bio, profile_visibility)
                VALUES (%s, 'Computer Science', '3rd Year', '6th', 'Part-time', 'Student One bio', 'public')
            """, (u1['id'],))
            s1 = fetch_one("SELECT id FROM students WHERE user_id = %s", (u1['id'],))
            self.s1_id = s1['id']
            self.u1_id = u1['id']

            # Student 2 (Private profile)
            execute_query("""
                INSERT INTO users (name, email, password_hash, role)
                VALUES ('Sec Student Two', 'sec_stu2@example.com', %s, 'student')
            """, (generate_password_hash("password123"),))
            u2 = fetch_one("SELECT id FROM users WHERE email = 'sec_stu2@example.com'")
            execute_query("""
                INSERT INTO students (user_id, department, year, semester, availability, bio, profile_visibility)
                VALUES (%s, 'Information Science', '4th Year', '7th', 'Full-time', 'Private student bio', 'private')
            """, (u2['id'],))
            s2 = fetch_one("SELECT id FROM students WHERE user_id = %s", (u2['id'],))
            self.s2_id = s2['id']
            self.u2_id = u2['id']

            # Faculty 1
            execute_query("""
                INSERT INTO users (name, email, password_hash, role)
                VALUES ('Sec Faculty One', 'sec_fac1@example.com', %s, 'faculty')
            """, (generate_password_hash("facultyPass1"),))
            fac1 = fetch_one("SELECT id FROM users WHERE email = 'sec_fac1@example.com'")
            self.fac1_id = fac1['id']

            # Admin
            execute_query("""
                INSERT INTO users (name, email, password_hash, role)
                VALUES ('Sec Admin', 'sec_admin@example.com', %s, 'admin')
            """, (generate_password_hash("adminPass123"),))
            admin = fetch_one("SELECT id FROM users WHERE email = 'sec_admin@example.com'")
            self.admin_id = admin['id']

            # Project 1 (Owned by Faculty 1)
            execute_query("""
                INSERT INTO projects (title, description, domain, team_size, required_availability, faculty_id, status)
                VALUES ('Sec Hardened Project', 'Test project description', 'AI', 4, 'Medium', %s, 'Open')
            """, (self.fac1_id,))
            p1 = fetch_one("SELECT id FROM projects WHERE title = 'Sec Hardened Project'")
            self.p1_id = p1['id']

            # Closed Project
            execute_query("""
                INSERT INTO projects (title, description, domain, team_size, required_availability, faculty_id, status)
                VALUES ('Sec Closed Project', 'Closed description', 'AI', 4, 'Medium', %s, 'Closed')
            """, (self.fac1_id,))
            p_closed = fetch_one("SELECT id FROM projects WHERE title = 'Sec Closed Project'")
            self.p_closed_id = p_closed['id']

    def tearDown(self):
        clear_all_rate_limits()
        with self.app.app_context():
            execute_query("DELETE FROM users WHERE email LIKE 'sec_%@example.com'")

    # -------------------------------------------------------------
    # Issue 1: Security Headers & XSS Prevention
    # -------------------------------------------------------------
    def test_security_headers_present_on_responses(self):
        res = self.client.get('/api/health')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.headers.get('X-Content-Type-Options'), 'nosniff')
        self.assertEqual(res.headers.get('X-Frame-Options'), 'DENY')
        self.assertIn("default-src 'self'", res.headers.get('Content-Security-Policy', ''))
        self.assertIn("frame-ancestors 'none'", res.headers.get('Content-Security-Policy', ''))

    # -------------------------------------------------------------
    # Issue 19: Privilege Escalation Prevention
    # -------------------------------------------------------------
    def test_public_registration_forces_student_role(self):
        res = self.client.post('/api/auth/register', json={
            'name': 'Malicious Faculty',
            'email': 'sec_fake_fac@example.com',
            'password': 'StrongPassword123!',
            'role': 'faculty'  # Attacker tries to register as faculty
        })
        self.assertEqual(res.status_code, 201)
        data = res.get_json()
        self.assertEqual(data['user']['role'], 'student')  # Must be forced to student

        # Verify DB directly
        with self.app.app_context():
            u = fetch_one("SELECT role FROM users WHERE email = 'sec_fake_fac@example.com'")
            self.assertEqual(u['role'], 'student')

    def test_admin_create_user_workflow(self):
        # Non-admin cannot access create-user
        with self.client.session_transaction() as sess:
            sess['user_id'] = self.s1_id
            sess['role'] = 'student'
        res = self.client.post('/api/auth/admin/create-user', json={
            'name': 'New Faculty Member',
            'email': 'sec_new_fac@example.com',
            'password': 'StrongPassword123!',
            'role': 'faculty'
        })
        self.assertEqual(res.status_code, 403)

        # Authenticated Admin can create faculty
        with self.client.session_transaction() as sess:
            sess['user_id'] = self.admin_id
            sess['role'] = 'admin'
            sess['_csrf_token'] = 'test-token'
        res = self.client.post('/api/auth/admin/create-user', json={
            'name': 'New Faculty Member',
            'email': 'sec_new_fac@example.com',
            'password': 'StrongPassword123!',
            'role': 'faculty'
        }, headers={'X-CSRF-Token': 'test-token'})
        self.assertEqual(res.status_code, 201)
        data = res.get_json()
        self.assertEqual(data['user']['role'], 'faculty')

    # -------------------------------------------------------------
    # Issue 20: Safe Certificate Verification
    # -------------------------------------------------------------
    def test_certificate_verification_negative_checks(self):
        # 1. Student cannot verify certificate (403)
        with self.client.session_transaction() as sess:
            sess['user_id'] = self.u1_id
            sess['role'] = 'student'
            sess['_csrf_token'] = 'token'

        res = self.client.post('/api/student/verify-certificate', json={
            'student_id': self.s1_id,
            'skill_id': 1,
            'status': 'Verified'
        }, headers={'X-CSRF-Token': 'token'})
        self.assertEqual(res.status_code, 403)

        # 2. Faculty verifying student who never applied to their project (403)
        with self.client.session_transaction() as sess:
            sess['user_id'] = self.fac1_id
            sess['role'] = 'faculty'
            sess['_csrf_token'] = 'token'

        res = self.client.post('/api/student/verify-certificate', json={
            'student_id': self.s1_id,
            'skill_id': 99999,
            'status': 'Verified'
        }, headers={'X-CSRF-Token': 'token'})
        self.assertIn(res.status_code, (403, 404))

    # -------------------------------------------------------------
    # Issue 21: Login Enumeration & Rate Limiting
    # -------------------------------------------------------------
    def test_login_enumeration_returns_consistent_401(self):
        # Nonexistent user
        res_nonexistent = self.client.post('/api/auth/login', json={
            'email': 'sec_nonexistent@example.com',
            'password': 'password123'
        })
        self.assertEqual(res_nonexistent.status_code, 401)
        self.assertEqual(res_nonexistent.get_json()['message'], 'Invalid email or password.')

        # Existing user with wrong password
        res_wrong_pw = self.client.post('/api/auth/login', json={
            'email': 'sec_stu1@example.com',
            'password': 'wrongPassword99'
        })
        self.assertEqual(res_wrong_pw.status_code, 401)
        self.assertEqual(res_wrong_pw.get_json()['message'], 'Invalid email or password.')

    def test_login_rate_limiting(self):
        # 5 failed attempts allowed, 6th must return 429
        for _ in range(5):
            res = self.client.post('/api/auth/login', json={
                'email': 'sec_stu1@example.com',
                'password': 'wrongPassword'
            })
            self.assertEqual(res.status_code, 401)

        res_limited = self.client.post('/api/auth/login', json={
            'email': 'sec_stu1@example.com',
            'password': 'wrongPassword'
        })
        self.assertEqual(res_limited.status_code, 429)
        self.assertIn('Too many failed login attempts', res_limited.get_json()['message'])

    # -------------------------------------------------------------
    # Issue 22: CSRF Behind Proxy & Origin Checks
    # -------------------------------------------------------------
    def test_csrf_origin_validation(self):
        with self.client.session_transaction() as sess:
            sess['user_id'] = self.u1_id
            sess['role'] = 'student'
            sess['_csrf_token'] = 'valid-token'

        # Untrusted Origin header rejected with 403
        res = self.client.post(
            '/api/student/interests',
            json={'interests': ['Machine Learning']},
            headers={
                'X-CSRF-Token': 'valid-token',
                'Origin': 'https://evil-attacker-site.com'
            }
        )
        self.assertEqual(res.status_code, 403)
        self.assertIn("not trusted", res.get_json()['message'])

    # -------------------------------------------------------------
    # Issue 23: Untrimmed Passwords & Min Length Policy
    # -------------------------------------------------------------
    def test_password_policy_and_space_preservation(self):
        # Password under 8 characters rejected
        res = self.client.post('/api/auth/register', json={
            'name': 'Short PW',
            'email': 'sec_short@example.com',
            'password': 'short'
        })
        self.assertEqual(res.status_code, 400)
        self.assertIn('at least 8 characters', res.get_json()['message'])

        # Password with intentional leading/trailing spaces preserved
        spaced_pw = "  exactPasswordWithSpaces  "
        res = self.client.post('/api/auth/register', json={
            'name': 'Spaced PW User',
            'email': 'sec_spaced@example.com',
            'password': spaced_pw
        })
        self.assertEqual(res.status_code, 201)

        # Login with stripped password fails
        res_stripped = self.client.post('/api/auth/login', json={
            'email': 'sec_spaced@example.com',
            'password': spaced_pw.strip()
        })
        self.assertEqual(res_stripped.status_code, 401)

        # Login with exact spaced password succeeds
        res_exact = self.client.post('/api/auth/login', json={
            'email': 'sec_spaced@example.com',
            'password': spaced_pw
        })
        self.assertEqual(res_exact.status_code, 200)

    # -------------------------------------------------------------
    # Issue 25: Profile Privacy & Team Invitations
    # -------------------------------------------------------------
    def test_profile_privacy_enforcement(self):
        # Student 1 cannot view Student 2's private profile
        with self.client.session_transaction() as sess:
            sess['user_id'] = self.u1_id
            sess['role'] = 'student'

        res = self.client.get(f'/api/student/profile?student_id={self.s2_id}')
        self.assertEqual(res.status_code, 403)

        # Faculty 1 cannot view Student 2's private profile because Student 2 never applied to their project
        with self.client.session_transaction() as sess:
            sess['user_id'] = self.fac1_id
            sess['role'] = 'faculty'

        res_fac = self.client.get(f'/api/student/profile?student_id={self.s2_id}')
        self.assertEqual(res_fac.status_code, 403)

    def test_invite_teammate_validation(self):
        # Put Student 1 on project 1 team
        with self.app.app_context():
            execute_query("""
                INSERT INTO applications (project_id, student_id, status)
                VALUES (%s, %s, 'Accepted')
            """, (self.p1_id, self.s1_id))

        with self.client.session_transaction() as sess:
            sess['user_id'] = self.u1_id
            sess['role'] = 'student'
            sess['_csrf_token'] = 'token'

        # 1. Inviting to nonexistent project: 404
        res = self.client.post('/api/matching/projects/99999/invite', json={
            'student_id': self.s2_id
        }, headers={'X-CSRF-Token': 'token'})
        self.assertEqual(res.status_code, 404)

        # 2. Inviting to closed project: 400
        res = self.client.post(f'/api/matching/projects/{self.p_closed_id}/invite', json={
            'student_id': self.s2_id
        }, headers={'X-CSRF-Token': 'token'})
        self.assertEqual(res.status_code, 400)

        # 3. Inviting student with private profile: 403
        res = self.client.post(f'/api/matching/projects/{self.p1_id}/invite', json={
            'student_id': self.s2_id
        }, headers={'X-CSRF-Token': 'token'})
        self.assertEqual(res.status_code, 403)
        self.assertIn("private profile", res.get_json()['message'])

    # -------------------------------------------------------------
    # Issue 26: Orphaned Certificate Access Prohibition
    # -------------------------------------------------------------
    def test_orphaned_certificate_file_rejected(self):
        with self.client.session_transaction() as sess:
            sess['user_id'] = self.u1_id
            sess['role'] = 'student'

        # Accessing an orphaned file not in student_skills database
        res = self.client.get('/api/certificates/cert_orphaned_dummy.pdf')
        self.assertEqual(res.status_code, 404)
        self.assertIn("not found", res.get_json()['message'])


if __name__ == '__main__':
    unittest.main()
