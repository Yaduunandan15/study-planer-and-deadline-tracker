import os
import unittest
from app import app
from database import get_db, init_db

class StudyFlowTestCase(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        app.config['SECRET_KEY'] = 'test-secret'
        self.client = app.test_client()
        init_db()

    def test_unauthenticated_redirect(self):
        # Accessing dashboard without login should redirect to /login
        response = self.client.get('/', follow_redirects=False)
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login', response.headers['Location'])

    def test_demo_login(self):
        # Demo login should succeed and redirect to dashboard
        response = self.client.get('/auth/demo-login', follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Alex Chen', response.data)
        self.assertIn(b'Study Dashboard', response.data)

    def test_planner_view(self):
        # Log in first
        self.client.get('/auth/demo-login', follow_redirects=True)
        response = self.client.get('/planner', follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Study Planner', response.data)
        self.assertIn(b'Data Structures', response.data)

    def test_tasks_view_and_toggle(self):
        self.client.get('/auth/demo-login', follow_redirects=True)
        response = self.client.get('/tasks', follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Task Management', response.data)

        # Find a task ID to test toggle
        db = get_db()
        task = db.execute("SELECT id, status FROM tasks LIMIT 1").fetchone()
        db.close()

        if task:
            toggle_resp = self.client.post(f"/api/tasks/{task['id']}/toggle")
            self.assertEqual(toggle_resp.status_code, 200)
            data = toggle_resp.get_json()
            self.assertTrue(data['success'])

    def test_deadlines_view(self):
        self.client.get('/auth/demo-login', follow_redirects=True)
        response = self.client.get('/deadlines', follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Deadline Tracker', response.data)

    def test_notifications_view_and_api(self):
        self.client.get('/auth/demo-login', follow_redirects=True)
        response = self.client.get('/notifications', follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Reminders & Notification', response.data)

        api_resp = self.client.get('/api/notifications/latest')
        self.assertEqual(api_resp.status_code, 200)
        json_data = api_resp.get_json()
        self.assertIn('unread_count', json_data)

    def test_progress_charts_api(self):
        self.client.get('/auth/demo-login', follow_redirects=True)
        response = self.client.get('/progress', follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Progress Tracker', response.data)

        charts_resp = self.client.get('/api/progress/charts')
        self.assertEqual(charts_resp.status_code, 200)
        charts_data = charts_resp.get_json()
        self.assertIn('subjects', charts_data)
        self.assertIn('daily', charts_data)
        self.assertIn('tasks', charts_data)
        self.assertIn('deadlines', charts_data)

    def test_profile_and_export(self):
        self.client.get('/auth/demo-login', follow_redirects=True)
        response = self.client.get('/profile', follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Student Profile', response.data)

        export_resp = self.client.get('/profile/export-data')
        self.assertEqual(export_resp.status_code, 200)
        self.assertIn('application/json', export_resp.headers['Content-Type'])

if __name__ == '__main__':
    unittest.main()
