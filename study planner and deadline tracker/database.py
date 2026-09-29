import sqlite3
import os
from datetime import datetime, timedelta, date
from werkzeug.security import generate_password_hash

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'study_planner.db')

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()

    # Users table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        full_name TEXT,
        bio TEXT,
        major TEXT,
        institution TEXT,
        target_weekly_hours REAL DEFAULT 20.0,
        avatar TEXT DEFAULT 'graduation-cap',
        theme TEXT DEFAULT 'dark',
        sound_enabled INTEGER DEFAULT 1,
        notifications_enabled INTEGER DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')

    # Timetable slots table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS timetable_slots (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        subject TEXT NOT NULL,
        day_of_week TEXT NOT NULL,
        start_time TEXT NOT NULL,
        end_time TEXT NOT NULL,
        color TEXT DEFAULT '#4F46E5',
        technique TEXT DEFAULT 'Lecture & Review',
        location TEXT,
        notes TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
    )
    ''')

    # Tasks table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        title TEXT NOT NULL,
        description TEXT,
        subject TEXT,
        priority TEXT DEFAULT 'Medium',
        status TEXT DEFAULT 'Pending',
        due_date TEXT,
        due_time TEXT,
        estimated_hours REAL DEFAULT 1.0,
        actual_hours REAL DEFAULT 0.0,
        subtasks_json TEXT DEFAULT '[]',
        completed_at TIMESTAMP,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
    )
    ''')

    # Deadlines table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS deadlines (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        title TEXT NOT NULL,
        subject TEXT NOT NULL,
        category TEXT DEFAULT 'Assignment',
        due_date TEXT NOT NULL,
        due_time TEXT NOT NULL,
        weight_percent REAL DEFAULT 10.0,
        description TEXT,
        is_submitted INTEGER DEFAULT 0,
        submitted_at TIMESTAMP,
        priority TEXT DEFAULT 'High',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
    )
    ''')

    # Study sessions logged table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS study_sessions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        subject TEXT NOT NULL,
        duration_minutes INTEGER NOT NULL,
        technique TEXT DEFAULT 'Pomodoro',
        session_date TEXT NOT NULL,
        notes TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
    )
    ''')

    # Notifications table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS notifications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        title TEXT NOT NULL,
        message TEXT NOT NULL,
        type TEXT DEFAULT 'deadline',
        link TEXT,
        is_read INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
    )
    ''')

    conn.commit()
    seed_demo_data(conn)
    conn.close()

def seed_demo_data(conn):
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM users WHERE username = 'alex_student'")
    existing_user = cursor.fetchone()

    if not existing_user:
        hashed = generate_password_hash('study123')
        cursor.execute('''
            INSERT INTO users (
                username, email, password_hash, full_name, bio,
                major, institution, target_weekly_hours, avatar, theme, sound_enabled
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            'alex_student',
            'alex.chen@studyflow.edu',
            hashed,
            'Alex Chen',
            'Final-year Computer Science student passionate about distributed systems and machine learning. Focusing on honors thesis and GPA excellence.',
            'Computer Science & Engineering',
            'Metropolitan University',
            24.0,
            'graduation-cap',
            'dark',
            1
        ))
        user_id = cursor.lastrowid

        # Seed Timetable
        slots = [
            (user_id, 'Data Structures & Algorithms', 'Monday', '09:00', '10:30', '#6366F1', 'Lecture & Active Recall', 'Hall B, Rm 302', 'Review tree rotations & heaps'),
            (user_id, 'Database Systems', 'Monday', '11:00', '12:30', '#06B6D4', 'Problem Solving', 'Lab 4', 'SQL optimization & index tuning'),
            (user_id, 'Machine Learning', 'Monday', '14:00', '16:00', '#EC4899', 'Deep Work', 'Library Study Rm 4', 'Neural network backprop derivations'),
            
            (user_id, 'Linear Algebra', 'Tuesday', '10:00', '11:30', '#F59E0B', 'Feynman Technique', 'Hall A, Rm 101', 'Eigenvalues and SVD decomposition'),
            (user_id, 'Operating Systems', 'Tuesday', '13:00', '15:00', '#10B981', 'Coding & Practice', 'Computer Lab 2', 'Process scheduling and mutex locks'),

            (user_id, 'Data Structures & Algorithms', 'Wednesday', '09:00', '10:30', '#6366F1', 'Problem Solving', 'Hall B, Rm 302', 'Graph traversal algorithms'),
            (user_id, 'Software Engineering', 'Wednesday', '11:00', '12:30', '#8B5CF6', 'Group Discussion', 'Seminar Rm 12', 'Agile sprint planning and design patterns'),
            (user_id, 'Machine Learning', 'Wednesday', '14:00', '16:00', '#EC4899', 'Deep Work', 'Library Quiet Zone', 'Convolutional neural networks notebook'),

            (user_id, 'Linear Algebra', 'Thursday', '10:00', '11:30', '#F59E0B', 'Feynman Technique', 'Hall A, Rm 101', 'Orthogonal projections and Gram-Schmidt'),
            (user_id, 'Operating Systems', 'Thursday', '13:00', '15:00', '#10B981', 'Coding & Practice', 'Computer Lab 2', 'Virtual memory and paging simulation'),

            (user_id, 'Database Systems', 'Friday', '10:00', '12:00', '#06B6D4', 'Project Work', 'Lab 4', 'Schema migrations and ACID properties'),
            (user_id, 'Honors Research', 'Friday', '14:00', '17:00', '#3B82F6', 'Deep Work', 'AI Lab, Rm 510', 'Model evaluation and latency benchmarking'),

            (user_id, 'Weekly Review & Planning', 'Sunday', '16:00', '18:00', '#14B8A6', 'Review & Organization', 'Home Desk', 'Review weekly goals, prep flashcards')
        ]
        cursor.executemany('''
            INSERT INTO timetable_slots (
                user_id, subject, day_of_week, start_time, end_time, color, technique, location, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', slots)

        # Dates for tasks and deadlines
        today = date.today()
        d_plus_1 = (today + timedelta(days=1)).strftime('%Y-%m-%d')
        d_plus_2 = (today + timedelta(days=2)).strftime('%Y-%m-%d')
        d_plus_4 = (today + timedelta(days=4)).strftime('%Y-%m-%d')
        d_plus_7 = (today + timedelta(days=7)).strftime('%Y-%m-%d')
        d_plus_14 = (today + timedelta(days=14)).strftime('%Y-%m-%d')
        d_minus_2 = (today - timedelta(days=2)).strftime('%Y-%m-%d')

        # Seed Tasks
        tasks = [
            (
                user_id,
                'Complete Dijkstra & A* Graph Assignment',
                'Implement pathfinding algorithms in Python with performance benchmarking against large graph inputs.',
                'Data Structures & Algorithms',
                'Urgent',
                'In Progress',
                d_plus_1,
                '23:59',
                3.5,
                2.0,
                '[{"title": "Implement Dijkstra Priority Queue", "done": true}, {"title": "Implement A* Heuristic", "done": true}, {"title": "Write Unit Tests", "done": false}, {"title": "Submit PDF Report", "done": false}]',
                None
            ),
            (
                user_id,
                'Derive Backpropagation Matrix Equations',
                'Write step-by-step mathematical proofs for vector-Jacobian products in multi-layer perceptron.',
                'Machine Learning',
                'High',
                'Pending',
                d_plus_2,
                '18:00',
                2.0,
                0.0,
                '[{"title": "Read Chapter 4 notes", "done": true}, {"title": "Compute partial derivatives", "done": false}, {"title": "Verify with Python script", "done": false}]',
                None
            ),
            (
                user_id,
                'Design Database E-R Diagram for E-Commerce App',
                'Create normalized 3NF database schema with foreign key constraints, indexes, and sample queries.',
                'Database Systems',
                'Medium',
                'In Progress',
                d_plus_4,
                '17:00',
                4.0,
                1.5,
                '[{"title": "Entities and Attributes definition", "done": true}, {"title": "Relationship Cardinality mapping", "done": true}, {"title": "Normalization to 3NF", "done": false}, {"title": "DDL SQL Script export", "done": false}]',
                None
            ),
            (
                user_id,
                'Linear Algebra Problem Set 5: SVD & PCA',
                'Exercises 12 through 28 on Singular Value Decomposition and dimension reduction.',
                'Linear Algebra',
                'Medium',
                'Pending',
                d_plus_7,
                '23:59',
                3.0,
                0.0,
                '[{"title": "Section 5.1 Problems 12-18", "done": false}, {"title": "Section 5.2 Problems 19-24", "done": false}, {"title": "PCA Python Demo Exercise", "done": false}]',
                None
            ),
            (
                user_id,
                'Review Operating Systems Mutex & Semaphores Quiz',
                'Study slides on race conditions, dining philosophers problem, and condition variables.',
                'Operating Systems',
                'High',
                'Completed',
                d_minus_2,
                '12:00',
                1.5,
                1.5,
                '[{"title": "Review lecture slides", "done": true}, {"title": "Practice textbook quiz", "done": true}]',
                datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            )
        ]
        cursor.executemany('''
            INSERT INTO tasks (
                user_id, title, description, subject, priority, status,
                due_date, due_time, estimated_hours, actual_hours, subtasks_json, completed_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', tasks)

        # Seed Deadlines
        deadlines = [
            (
                user_id,
                'Data Structures Midterm Programming Project',
                'Data Structures & Algorithms',
                'Project',
                d_plus_1,
                '23:59',
                20.0,
                'Complete implementation of Graph library with automated test suites and benchmark analysis.',
                0,
                None,
                'Urgent'
            ),
            (
                user_id,
                'Machine Learning Research Proposal',
                'Machine Learning',
                'Assignment',
                d_plus_4,
                '17:00',
                15.0,
                'A 5-page research proposal detailing model architecture, baseline comparisons, and dataset synthesis.',
                0,
                None,
                'High'
            ),
            (
                user_id,
                'Linear Algebra Midterm Examination',
                'Linear Algebra',
                'Exam',
                d_plus_7,
                '09:00',
                25.0,
                'Closed-book exam covering Matrix Vector Spaces, Orthogonality, Determinants, and Eigenvalues.',
                0,
                None,
                'Urgent'
            ),
            (
                user_id,
                'Operating Systems Kernel Module Lab',
                'Operating Systems',
                'Lab Report',
                d_plus_14,
                '23:59',
                15.0,
                'Write a custom Linux kernel character device driver with process locking and ring buffer.',
                0,
                None,
                'Medium'
            ),
            (
                user_id,
                'Database Systems Term Paper Part 1',
                'Database Systems',
                'Term Paper',
                d_minus_2,
                '23:59',
                10.0,
                'Literature review on distributed transactions and Paxos/Raft consensus algorithms.',
                1,
                datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'High'
            )
        ]
        cursor.executemany('''
            INSERT INTO deadlines (
                user_id, title, subject, category, due_date, due_time,
                weight_percent, description, is_submitted, submitted_at, priority
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', deadlines)

        # Seed Study Sessions (past 7 days for rich analytics)
        sessions = []
        for i in range(7, 0, -1):
            s_date = (today - timedelta(days=i)).strftime('%Y-%m-%d')
            if i % 2 == 0:
                sessions.append((user_id, 'Machine Learning', 90, 'Pomodoro (3x30m)', s_date, 'Implemented transformer attention layer'))
                sessions.append((user_id, 'Data Structures & Algorithms', 60, 'Deep Work', s_date, 'Solved 3 LeetCode hard graph problems'))
            else:
                sessions.append((user_id, 'Linear Algebra', 75, 'Feynman Technique', s_date, 'Practiced projection matrices and basis transformation'))
                sessions.append((user_id, 'Operating Systems', 80, 'Coding Practice', s_date, 'Debugged concurrency deadlocks in C'))

        # Today's study session
        sessions.append((user_id, 'Data Structures & Algorithms', 50, 'Pomodoro (2x25m)', today.strftime('%Y-%m-%d'), 'Completed Dijkstra queue logic'))
        sessions.append((user_id, 'Database Systems', 45, 'Active Recall', today.strftime('%Y-%m-%d'), 'Reviewed B+ Tree indexing'))

        cursor.executemany('''
            INSERT INTO study_sessions (
                user_id, subject, duration_minutes, technique, session_date, notes
            ) VALUES (?, ?, ?, ?, ?, ?)
        ''', sessions)

        # Seed Notifications
        notifications = [
            (
                user_id,
                '⚠️ Urgent Deadline Tomorrow!',
                f'Data Structures Midterm Programming Project is due tomorrow at 23:59. Make sure all unit tests pass!',
                'deadline',
                '/deadlines',
                0
            ),
            (
                user_id,
                '📅 Scheduled Class Alert',
                'Today at 14:00: Machine Learning deep work session scheduled in Library Quiet Zone.',
                'timetable',
                '/planner',
                0
            ),
            (
                user_id,
                '🔥 7-Day Study Streak Active!',
                'Awesome discipline! You have completed study sessions for 7 consecutive days. Keep the momentum!',
                'streak',
                '/progress',
                0
            ),
            (
                user_id,
                '📝 Task Reminder',
                'Derive Backpropagation Matrix Equations is due in 2 days.',
                'task',
                '/tasks',
                1
            )
        ]
        cursor.executemany('''
            INSERT INTO notifications (
                user_id, title, message, type, link, is_read
            ) VALUES (?, ?, ?, ?, ?, ?)
        ''', notifications)

        conn.commit()

if __name__ == '__main__':
    init_db()
    print("Database initialized successfully at:", DB_PATH)
