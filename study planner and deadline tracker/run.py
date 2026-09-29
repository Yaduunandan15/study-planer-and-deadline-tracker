"""
StudyFlow: Study Planner and Deadline Tracker
Runner Script
"""

from app import app
from database import init_db

if __name__ == '__main__':
    print("=" * 60)
    print(" 🎓 StudyFlow - Study Planner & Deadline Tracker")
    print("=" * 60)
    print(" Initializing database & tables...")
    init_db()
    print(" Database ready!")
    print(" Server starting on: http://127.0.0.1:5000")
    print(" Demo Login available on the login page (1-Click Login)")
    print(" Demo Username: alex_student | Password: study123")
    print("=" * 60)
    app.run(host='127.0.0.1', port=5000, debug=True)
