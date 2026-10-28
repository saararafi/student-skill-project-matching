import os
import sys
import unittest
import io
import json

# Ensure project root is in sys.path
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from backend.config import Config
from backend.app import create_app
from backend.database import get_connection, execute_query, fetch_one
from algorithm.matching import calculate_skill_match
from algorithm.availability_matching import calculate_availability_match
from algorithm.interest_matching import calculate_interest_match
from algorithm.experience_matching import calculate_experience_match
from algorithm.weighted_matching import calculate_weighted_match
from algorithm.skill_gap import detect_skill_gaps
from algorithm.teammate_recommendation import recommend_teammates
from backend.services.matching_service import compute_match


class SecurityAndStabilizationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import tempfile, shutil
        cls._tmpdir = tempfile.mkdtemp(prefix='master-test-')
        cls._db_path = os.path.join(cls._tmpdir, 'test.db')
        cls._original_db_path = Config.SQLITE_DB_PATH
        cls._original_seed_demo = Config.SEED_DEMO_DATA
        Config.SQLITE_DB_PATH = cls._db_path
        Config.SEED_DEMO_DATA = True
        cls.app = create_app()
        cls.app.config['TESTING'] = True
        cls.client = cls.app.test_client()

    @classmethod
    def tearDownClass(cls):
        import shutil
        Config.SQLITE_DB_PATH = cls._original_db_path
        Config.SEED_DEMO_DATA = cls._original_seed_demo
        shutil.rmtree(cls._tmpdir, ignore_errors=True)

    def test_production_secret_key_rejection(self):
        """Production environment must not allow weak default secret key."""
        old_env = os.environ.get('FLASK_ENV')
        old_key = os.environ.get('SECRET_KEY')
        try:
            os.environ['FLASK_ENV'] = 'production'
            if 'SECRET_KEY' in os.environ:
                del os.environ['SECRET_KEY']
            with self.assertRaises(RuntimeError):
                # Reload or instantiate config check
                Config.validate_production_keys()
        finally:
            if old_env:
                os.environ['FLASK_ENV'] = old_env
            else:
                os.environ.pop('FLASK_ENV', None)
            if old_key:
                os.environ['SECRET_KEY'] = old_key
            else:
                os.environ.pop('SECRET_KEY', None)

    def test_cors_allowlist_configured(self):
        """CORS origins must be an explicit list, never wildcard with credentials."""
        self.assertIsInstance(Config.CORS_ALLOWED_ORIGINS, list)
        self.assertNotIn('*', Config.CORS_ALLOWED_ORIGINS)

    def test_algorithm_skill_match_edge_cases(self):
        """Skill matching must safely handle zero required level, None, negative, and case differences."""
        # Division by zero protection
        score, breakdown = calculate_skill_match({'python': 3}, {'python': 0})
        self.assertGreaterEqual(score, 0)
        self.assertLessEqual(score, 100)

        # Negative and non-numeric levels
        score, breakdown = calculate_skill_match({'python': -2}, {'python': 'invalid'})
        self.assertEqual(score, 0)

        # Case-insensitivity and whitespace
        score, breakdown = calculate_skill_match({'  Python  ': 5}, {'python': 5})
        self.assertEqual(score, 100)
        self.assertEqual(breakdown['python'], 100)

        # None / empty input
        score, breakdown = calculate_skill_match(None, None)
        self.assertEqual(score, 0)
        self.assertEqual(breakdown, {})

    def test_algorithm_availability_match_edge_cases(self):
        """Availability match must handle None, non-strings, whitespace, and hyphens."""
        self.assertEqual(calculate_availability_match(None, 'Full-time'), 0)
        self.assertEqual(calculate_availability_match('Full-time', None), 0)
        self.assertEqual(calculate_availability_match('full time', 'full-time'), 100)
        self.assertEqual(calculate_availability_match('part time', 'full-time'), 50)
        self.assertEqual(calculate_availability_match('not available', 'full-time'), 0)
        self.assertEqual(calculate_availability_match('', 'full-time'), 0)

    def test_algorithm_interest_and_experience_match_edge_cases(self):
        """Interest & experience algorithms must never divide by zero or crash on None/empty strings."""
        # Empty project interest returns 0 safely
        self.assertEqual(calculate_interest_match(['AI'], []), 0)
        self.assertEqual(calculate_interest_match(None, ['AI']), 0)
        self.assertEqual(calculate_interest_match(['AI', None, '   '], ['  ai  ']), 100)

        # Experience matching
        self.assertEqual(calculate_experience_match(['Web'], []), 0)
        self.assertEqual(calculate_experience_match(None, ['Web']), 0)
        self.assertEqual(calculate_experience_match(['Web Dev', ''], ['web dev']), 100)

    def test_algorithm_weighted_match_edge_cases(self):
        """Weighted match must handle NaN, inf, negative weights, and bound score within [0, 100]."""
        # Normal calculation
        score = calculate_weighted_match(100, 100, 100, 100)
        self.assertEqual(score, 100.0)

        # Zero / NaN / Inf values
        score = calculate_weighted_match(float('nan'), float('inf'), -50, 80)
        self.assertGreaterEqual(score, 0.0)
        self.assertLessEqual(score, 100.0)

        # Zero or negative weights fallback safely
        score = calculate_weighted_match(80, 80, 80, 80, weights={'skill': -1, 'interest': 0, 'experience': 0, 'availability': 0})
        self.assertEqual(score, 80.0)

    def test_algorithm_skill_gap_edge_cases(self):
        """Skill gap detection must safely handle case differences, None, and empty dictionaries."""
        gaps = detect_skill_gaps(None, {'Python': 4})
        self.assertIn('Python', gaps)
        self.assertEqual(gaps['Python']['status'], 'Missing')

        # Case-insensitive
        gaps = detect_skill_gaps({'python': 5}, {'Python': 4})
        self.assertEqual(gaps, {})

        gaps = detect_skill_gaps({'python': 2}, {'Python': 4})
        self.assertIn('Python', gaps)
        self.assertEqual(gaps['Python']['status'], 'Insufficient')

    def test_algorithm_teammate_recommendation_edge_cases(self):
        """Teammate recommendation must handle None inputs and case-insensitivity."""
        self.assertEqual(recommend_teammates(None, [], {}), [])
        self.assertEqual(recommend_teammates({'Alice': {'python': 4}}, None, None), [])

        recs = recommend_teammates(
            students={'Alice': {'python': 5}, 'Bob': {'python': 2}},
            current_team=[],
            skill_gaps={'Python': {'required_level': 4}}
        )
        self.assertEqual(len(recs), 1)
        self.assertEqual(recs[0]['name'], 'Alice')

    def test_idor_student_profile_isolation(self):
        """A student cannot access another student's profile by tampering with student_id param."""
        with self.client.session_transaction() as sess:
            sess['user_id'] = 2
            sess['role'] = 'student'

        res = self.client.get('/api/student/profile?student_id=9999')
        # Server must reject IDOR attempt with 403 Forbidden
        self.assertEqual(res.status_code, 403)

    def test_idor_student_skills_isolation(self):
        """A student cannot view another student's skills via student_id query param."""
        with self.client.session_transaction() as sess:
            sess['user_id'] = 2
            sess['role'] = 'student'

        res = self.client.get('/api/student/skills?student_id=9999')
        # Server must reject IDOR attempt with 403 Forbidden
        self.assertEqual(res.status_code, 403)

    def test_certificate_file_magic_bytes_validation(self):
        """Certificate upload must reject disguised executable/script files even with .pdf extension."""
        with self.client.session_transaction() as sess:
            sess['user_id'] = 2
            sess['role'] = 'student'

        # Fake PDF that contains raw executable script text
        fake_pdf = io.BytesIO(b"<?php echo 'malicious'; ?>")
        data = {
            'skill_id': 1,
            'certificate': (fake_pdf, 'exploit.pdf')
        }
        res = self.client.post('/api/student/upload-certificate', data=data, content_type='multipart/form-data')
        self.assertEqual(res.status_code, 400)
        json_data = res.get_json()
        self.assertFalse(json_data['success'])
        self.assertIn('file content does not match', json_data['message'].lower())

    def test_certificate_directory_traversal_blocked(self):
        """Attempting directory traversal in certificate filename must be blocked."""
        with self.client.session_transaction() as sess:
            sess['user_id'] = 2
            sess['role'] = 'student'

        res = self.client.get('/api/student/certificates/..%2f..%2fbackend%2fconfig.py')
        self.assertIn(res.status_code, (400, 403, 404))


if __name__ == '__main__':
    unittest.main()
