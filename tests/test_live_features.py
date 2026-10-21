import json
import unittest
from backend.app import app
from backend.database import execute_query, fetch_one


class TestLiveFeatures(unittest.TestCase):
    def setUp(self):
        self.app = app
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()

        # Create a test student user
        with self.app.app_context():
            execute_query("DELETE FROM users WHERE email IN ('live_student@test.edu', 'target_student@test.edu')")
            
            # Register main student
            res = self.client.post("/api/auth/register", json={
                "name": "Live Student",
                "email": "live_student@test.edu",
                "password": "Password123!",
                "role": "student",
                "department": "Computer Science",
                "year": "3rd Year"
            })
            self.assertEqual(res.status_code, 201)

            # Register target student for invitations
            res2 = self.client.post("/api/auth/register", json={
                "name": "Target Teammate",
                "email": "target_student@test.edu",
                "password": "Password123!",
                "role": "student",
                "department": "Information Science",
                "year": "3rd Year"
            })
            self.assertEqual(res2.status_code, 201)

            # Fetch target student record
            target_user = fetch_one("SELECT id FROM users WHERE email = 'target_student@test.edu'")
            target_st = fetch_one("SELECT id FROM students WHERE user_id = %s", (target_user['id'],))
            self.target_student_id = target_st['id']

    def tearDown(self):
        with self.app.app_context():
            execute_query("DELETE FROM users WHERE email IN ('live_student@test.edu', 'target_student@test.edu')")

    def test_change_password_workflow(self):
        # Login
        login_res = self.client.post("/api/auth/login", json={
            "email": "live_student@test.edu",
            "password": "Password123!"
        })
        self.assertEqual(login_res.status_code, 200)

        # Mismatched confirmation
        res = self.client.post("/api/auth/change-password", json={
            "current_password": "Password123!",
            "new_password": "NewSecretPassword888!",
            "confirm_password": "DifferentPassword!"
        })
        self.assertEqual(res.status_code, 400)
        self.assertIn("match", res.get_json()["message"].lower())

        # Too short
        res = self.client.post("/api/auth/change-password", json={
            "current_password": "Password123!",
            "new_password": "short",
            "confirm_password": "short"
        })
        self.assertEqual(res.status_code, 400)

        # Wrong current password
        res = self.client.post("/api/auth/change-password", json={
            "current_password": "WrongPassword999!",
            "new_password": "NewSecretPassword888!",
            "confirm_password": "NewSecretPassword888!"
        })
        self.assertEqual(res.status_code, 400)
        self.assertIn("incorrect", res.get_json()["message"].lower())

        # Successful change
        res = self.client.post("/api/auth/change-password", json={
            "current_password": "Password123!",
            "new_password": "NewSecretPassword888!",
            "confirm_password": "NewSecretPassword888!"
        })
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.get_json()["success"])

        # Verify login with new password succeeds
        res_login_new = self.client.post("/api/auth/login", json={
            "email": "live_student@test.edu",
            "password": "NewSecretPassword888!"
        })
        self.assertEqual(res_login_new.status_code, 200)

    def test_reset_settings_workflow(self):
        self.client.post("/api/auth/login", json={
            "email": "live_student@test.edu",
            "password": "Password123!"
        })

        # Change settings first
        self.client.put("/api/student/settings", json={
            "prioritise_skills": 0,
            "weekly_hours": 35
        })

        # Reset
        res = self.client.post("/api/student/reset-settings")
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.get_json()["success"])

        # Fetch settings and verify reset
        res_get = self.client.get("/api/student/settings")
        settings = res_get.get_json()["settings"]
        self.assertEqual(settings["prioritise_skills"], 1)
        self.assertEqual(settings["weekly_hours"], 20)

    def test_invite_teammate_workflow(self):
        self.client.post("/api/auth/login", json={
            "email": "live_student@test.edu",
            "password": "Password123!"
        })

        # Get projects
        res_proj = self.client.get("/api/projects")
        projects = res_proj.get_json().get("projects") or []
        if projects:
            pid = projects[0]["id"]
            res = self.client.post(f"/api/matching/projects/{pid}/invite", json={
                "student_id": self.target_student_id,
                "student_name": "Target Teammate"
            })
            self.assertEqual(res.status_code, 200)
            self.assertTrue(res.get_json()["success"])


if __name__ == "__main__":
    unittest.main()
