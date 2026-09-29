from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify, send_file
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import json
import io
from datetime import datetime, date, timedelta
from database import get_db, init_db

app = Flask(__name__)
app.secret_key = 'studyflow-secret-super-key-2026-secure-session'

# Ensure database tables exist on startup
init_db()

# ----------------- Decorators & Helpers ----------------- #
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

def get_current_user():
    if 'user_id' not in session:
        return None
    db = get_db()
    user = db.execute("SELECT * FROM users WHERE id = ?", (session['user_id'],)).fetchone()
    db.close()
    return user

@app.context_processor
def inject_global_data():
    user = get_current_user()
    unread_notifications = 0
    recent_notifications = []
    if user:
        db = get_db()
        # Auto-generate alerts if needed
        check_and_generate_alerts(db, user['id'])
        
        unread_notifications = db.execute(
            "SELECT COUNT(*) as count FROM notifications WHERE user_id = ? AND is_read = 0",
            (user['id'],)
        ).fetchone()['count']

        recent_notifications = db.execute(
            "SELECT * FROM notifications WHERE user_id = ? ORDER BY created_at DESC LIMIT 5",
            (user['id'],)
        ).fetchall()
        db.close()

    return {
        'current_user': user,
        'unread_notifications_count': unread_notifications,
        'recent_notifications': recent_notifications,
        'today_date_str': date.today().strftime('%Y-%m-%d'),
        'today_day_name': date.today().strftime('%A'),
        'now_year': datetime.now().year
    }

def check_and_generate_alerts(db, user_id):
    """Dynamically creates notifications for deadlines due in <= 24 hours or overdue."""
    now = datetime.now()
    today_str = now.strftime('%Y-%m-%d')
    tomorrow_str = (now + timedelta(days=1)).strftime('%Y-%m-%d')

    deadlines = db.execute('''
        SELECT * FROM deadlines 
        WHERE user_id = ? AND is_submitted = 0 AND due_date <= ?
    ''', (user_id, tomorrow_str)).fetchall()

    for d in deadlines:
        due_datetime_str = f"{d['due_date']} {d['due_time'] or '23:59'}"
        try:
            due_dt = datetime.strptime(due_datetime_str, "%Y-%m-%d %H:%M")
        except ValueError:
            due_dt = datetime.strptime(f"{d['due_date']} 23:59", "%Y-%m-%d %H:%M")

        is_overdue = due_dt < now
        alert_title = f"🚨 Overdue: {d['title']}" if is_overdue else f"⏰ Due Soon: {d['title']}"
        alert_msg = f"{d['title']} for {d['subject']} is {'already overdue!' if is_overdue else f'due on {d['due_date']} at {d['due_time']}.'}"

        # Check if already notified recently to prevent duplicate spam
        existing = db.execute('''
            SELECT id FROM notifications 
            WHERE user_id = ? AND title = ? AND date(created_at) = ?
        ''', (user_id, alert_title, today_str)).fetchone()

        if not existing:
            db.execute('''
                INSERT INTO notifications (user_id, title, message, type, link, is_read)
                VALUES (?, ?, ?, ?, ?, 0)
            ''', (user_id, alert_title, alert_msg, 'deadline', '/deadlines'))
    db.commit()

def calculate_study_streak(db, user_id):
    """Calculates consecutive days with at least one logged study session."""
    rows = db.execute('''
        SELECT DISTINCT session_date 
        FROM study_sessions 
        WHERE user_id = ? 
        ORDER BY session_date DESC
    ''', (user_id,)).fetchall()

    if not rows:
        return 0

    session_dates = {datetime.strptime(r['session_date'], '%Y-%m-%d').date() for r in rows}
    today = date.today()
    streak = 0
    current_check = today

    # If user hasn't studied today yet, check starting yesterday
    if current_check not in session_dates:
        current_check = today - timedelta(days=1)
        if current_check not in session_dates:
            return 0

    while current_check in session_dates:
        streak += 1
        current_check -= timedelta(days=1)

    return streak

# ----------------- Auth Routes ----------------- #
@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        login_id = request.form.get('login_id', '').strip()
        password = request.form.get('password', '').strip()

        if not login_id or not password:
            flash('Please enter both username/email and password.', 'error')
            return render_template('auth/login.html')

        db = get_db()
        user = db.execute(
            "SELECT * FROM users WHERE username = ? OR email = ?",
            (login_id, login_id)
        ).fetchone()
        db.close()

        if user and check_password_hash(user['password_hash'], password):
            session['user_id'] = user['id']
            session['username'] = user['username']
            flash(f"Welcome back, {user['full_name'] or user['username']}!", 'success')
            next_url = request.args.get('next')
            return redirect(next_url or url_for('dashboard'))
        else:
            flash('Invalid username/email or password. Try again or use Demo Login.', 'error')

    return render_template('auth/login.html')

@app.route('/auth/demo-login')
def demo_login():
    db = get_db()
    demo_user = db.execute("SELECT * FROM users WHERE username = 'alex_student'").fetchone()
    db.close()
    if demo_user:
        session['user_id'] = demo_user['id']
        session['username'] = demo_user['username']
        flash("Logged in with Demo Account (Alex Chen). Explore all features!", 'success')
        return redirect(url_for('dashboard'))
    flash('Demo user not found. Please register.', 'error')
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip().lower()
        full_name = request.form.get('full_name', '').strip()
        major = request.form.get('major', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')

        if not username or not email or not password:
            flash('Username, email, and password are required.', 'error')
            return render_template('auth/register.html')

        if password != confirm_password:
            flash('Passwords do not match.', 'error')
            return render_template('auth/register.html')

        if len(password) < 6:
            flash('Password must be at least 6 characters long.', 'error')
            return render_template('auth/register.html')

        db = get_db()
        existing = db.execute(
            "SELECT * FROM users WHERE username = ? OR email = ?",
            (username, email)
        ).fetchone()

        if existing:
            db.close()
            flash('Username or Email already registered. Please login.', 'error')
            return render_template('auth/register.html')

        hashed_password = generate_password_hash(password)
        cursor = db.cursor()
        cursor.execute('''
            INSERT INTO users (username, email, password_hash, full_name, major, target_weekly_hours, theme, sound_enabled)
            VALUES (?, ?, ?, ?, ?, 20.0, 'dark', 1)
        ''', (username, email, hashed_password, full_name, major))
        new_user_id = cursor.lastrowid

        # Insert a welcome notification
        cursor.execute('''
            INSERT INTO notifications (user_id, title, message, type, link, is_read)
            VALUES (?, ?, ?, 'system', '/planner', 0)
        ''', (new_user_id, '🎉 Welcome to StudyFlow!', 'Start by setting up your weekly timetable and adding your first deadlines.'))

        db.commit()
        db.close()

        session['user_id'] = new_user_id
        session['username'] = username
        flash('Account created successfully! Welcome aboard.', 'success')
        return redirect(url_for('dashboard'))

    return render_template('auth/register.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out successfully.', 'info')
    return redirect(url_for('login'))

# ----------------- Dashboard Route ----------------- #
@app.route('/')
@login_required
def dashboard():
    user = get_current_user()
    user_id = user['id']
    db = get_db()

    today = date.today()
    today_str = today.strftime('%Y-%m-%d')
    today_day = today.strftime('%A')

    # Timetable for today
    today_slots = db.execute('''
        SELECT * FROM timetable_slots 
        WHERE user_id = ? AND day_of_week = ?
        ORDER BY start_time ASC
    ''', (user_id, today_day)).fetchall()

    # Task metrics
    total_tasks = db.execute("SELECT COUNT(*) as c FROM tasks WHERE user_id = ?", (user_id,)).fetchone()['c']
    pending_tasks = db.execute("SELECT COUNT(*) as c FROM tasks WHERE user_id = ? AND status != 'Completed'", (user_id,)).fetchone()['c']
    completed_tasks = db.execute("SELECT COUNT(*) as c FROM tasks WHERE user_id = ? AND status = 'Completed'", (user_id,)).fetchone()['c']

    # Deadlines: upcoming (next 7 days) and urgent
    upcoming_deadlines = db.execute('''
        SELECT * FROM deadlines 
        WHERE user_id = ? AND is_submitted = 0 
        ORDER BY due_date ASC, due_time ASC 
        LIMIT 5
    ''', (user_id,)).fetchall()

    # Total study time this week
    start_of_week = (today - timedelta(days=today.weekday())).strftime('%Y-%m-%d')
    week_study = db.execute('''
        SELECT SUM(duration_minutes) as total_mins 
        FROM study_sessions 
        WHERE user_id = ? AND session_date >= ?
    ''', (user_id, start_of_week)).fetchone()
    total_week_hours = round((week_study['total_mins'] or 0) / 60.0, 1)

    # Today's study time
    today_study = db.execute('''
        SELECT SUM(duration_minutes) as today_mins 
        FROM study_sessions 
        WHERE user_id = ? AND session_date = ?
    ''', (user_id, today_str)).fetchone()
    today_hours = round((today_study['today_mins'] or 0) / 60.0, 1)

    # Streak
    streak_days = calculate_study_streak(db, user_id)

    # Top pending tasks
    recent_tasks = db.execute('''
        SELECT * FROM tasks 
        WHERE user_id = ? AND status != 'Completed'
        ORDER BY 
            CASE priority 
                WHEN 'Urgent' THEN 1 
                WHEN 'High' THEN 2 
                WHEN 'Medium' THEN 3 
                ELSE 4 
            END,
            due_date ASC
        LIMIT 5
    ''', (user_id,)).fetchall()

    # Parse subtasks for display
    tasks_with_progress = []
    for t in recent_tasks:
        td = dict(t)
        try:
            subtasks = json.loads(td['subtasks_json'] or '[]')
        except Exception:
            subtasks = []
        td['subtasks'] = subtasks
        total_sub = len(subtasks)
        done_sub = sum(1 for s in subtasks if s.get('done'))
        td['subtask_summary'] = f"{done_sub}/{total_sub}" if total_sub > 0 else None
        tasks_with_progress.append(td)

    db.close()

    return render_template(
        'index.html',
        today_slots=today_slots,
        total_tasks=total_tasks,
        pending_tasks=pending_tasks,
        completed_tasks=completed_tasks,
        upcoming_deadlines=upcoming_deadlines,
        total_week_hours=total_week_hours,
        today_hours=today_hours,
        streak_days=streak_days,
        recent_tasks=tasks_with_progress,
        today_str=today_str,
        today_day=today_day
    )

# ----------------- Study Planner / Timetable Routes ----------------- #
@app.route('/planner')
@login_required
def planner():
    user = get_current_user()
    db = get_db()
    day_filter = request.args.get('day', 'all')

    days_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']

    if day_filter and day_filter != 'all' and day_filter in days_order:
        slots = db.execute('''
            SELECT * FROM timetable_slots 
            WHERE user_id = ? AND day_of_week = ?
            ORDER BY start_time ASC
        ''', (user['id'], day_filter)).fetchall()
    else:
        slots = db.execute('''
            SELECT * FROM timetable_slots 
            WHERE user_id = ?
            ORDER BY 
                CASE day_of_week
                    WHEN 'Monday' THEN 1
                    WHEN 'Tuesday' THEN 2
                    WHEN 'Wednesday' THEN 3
                    WHEN 'Thursday' THEN 4
                    WHEN 'Friday' THEN 5
                    WHEN 'Saturday' THEN 6
                    WHEN 'Sunday' THEN 7
                END,
                start_time ASC
        ''', (user['id'],)).fetchall()

    # Group by day for the timetable weekly view
    slots_by_day = {d: [] for d in days_order}
    for s in slots:
        if s['day_of_week'] in slots_by_day:
            slots_by_day[s['day_of_week']].append(dict(s))

    # Distinct subjects for quick auto-suggest
    subjects = db.execute(
        "SELECT DISTINCT subject FROM timetable_slots WHERE user_id = ? ORDER BY subject",
        (user['id'],)
    ).fetchall()

    db.close()
    return render_template(
        'planner.html',
        slots=slots,
        slots_by_day=slots_by_day,
        days_order=days_order,
        active_day=day_filter,
        subjects=[s['subject'] for s in subjects]
    )

@app.route('/api/timetable/add', methods=['POST'])
@login_required
def api_timetable_add():
    user = get_current_user()
    subject = request.form.get('subject', '').strip()
    day_of_week = request.form.get('day_of_week', '').strip()
    start_time = request.form.get('start_time', '').strip()
    end_time = request.form.get('end_time', '').strip()
    color = request.form.get('color', '#4F46E5').strip()
    technique = request.form.get('technique', 'Lecture & Review').strip()
    location = request.form.get('location', '').strip()
    notes = request.form.get('notes', '').strip()

    if not subject or not day_of_week or not start_time or not end_time:
        flash('Subject, day, start time, and end time are required.', 'error')
        return redirect(url_for('planner'))

    db = get_db()
    db.execute('''
        INSERT INTO timetable_slots (
            user_id, subject, day_of_week, start_time, end_time, color, technique, location, notes
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (user['id'], subject, day_of_week, start_time, end_time, color, technique, location, notes))
    db.commit()
    db.close()

    flash(f"Timetable slot for '{subject}' added successfully!", 'success')
    return redirect(url_for('planner', day=day_of_week))

@app.route('/api/timetable/edit/<int:slot_id>', methods=['POST'])
@login_required
def api_timetable_edit(slot_id):
    user = get_current_user()
    subject = request.form.get('subject', '').strip()
    day_of_week = request.form.get('day_of_week', '').strip()
    start_time = request.form.get('start_time', '').strip()
    end_time = request.form.get('end_time', '').strip()
    color = request.form.get('color', '#4F46E5').strip()
    technique = request.form.get('technique', 'Lecture & Review').strip()
    location = request.form.get('location', '').strip()
    notes = request.form.get('notes', '').strip()

    db = get_db()
    db.execute('''
        UPDATE timetable_slots 
        SET subject = ?, day_of_week = ?, start_time = ?, end_time = ?,
            color = ?, technique = ?, location = ?, notes = ?
        WHERE id = ? AND user_id = ?
    ''', (subject, day_of_week, start_time, end_time, color, technique, location, notes, slot_id, user['id']))
    db.commit()
    db.close()

    flash(f"Timetable slot updated successfully.", 'success')
    return redirect(url_for('planner', day=day_of_week))

@app.route('/api/timetable/delete/<int:slot_id>', methods=['POST'])
@login_required
def api_timetable_delete(slot_id):
    user = get_current_user()
    db = get_db()
    db.execute("DELETE FROM timetable_slots WHERE id = ? AND user_id = ?", (slot_id, user['id']))
    db.commit()
    db.close()
    flash("Timetable slot deleted.", 'info')
    return redirect(url_for('planner'))

# ----------------- Task Management Routes ----------------- #
@app.route('/tasks')
@login_required
def tasks():
    user = get_current_user()
    status_filter = request.args.get('status', 'all')
    priority_filter = request.args.get('priority', 'all')
    subject_filter = request.args.get('subject', 'all')
    search_query = request.args.get('q', '').strip()

    db = get_db()
    query = "SELECT * FROM tasks WHERE user_id = ?"
    params = [user['id']]

    if status_filter != 'all':
        query += " AND status = ?"
        params.append(status_filter)
    if priority_filter != 'all':
        query += " AND priority = ?"
        params.append(priority_filter)
    if subject_filter != 'all':
        query += " AND subject = ?"
        params.append(subject_filter)
    if search_query:
        query += " AND (title LIKE ? OR description LIKE ? OR subject LIKE ?)"
        like_term = f"%{search_query}%"
        params.extend([like_term, like_term, like_term])

    query += """
        ORDER BY 
            CASE status WHEN 'Pending' THEN 1 WHEN 'In Progress' THEN 2 ELSE 3 END,
            CASE priority WHEN 'Urgent' THEN 1 WHEN 'High' THEN 2 WHEN 'Medium' THEN 3 ELSE 4 END,
            due_date ASC
    """

    task_rows = db.execute(query, params).fetchall()

    tasks_list = []
    for r in task_rows:
        td = dict(r)
        try:
            td['subtasks'] = json.loads(td['subtasks_json'] or '[]')
        except Exception:
            td['subtasks'] = []
        total_sub = len(td['subtasks'])
        done_sub = sum(1 for s in td['subtasks'] if s.get('done'))
        td['completed_subtasks'] = done_sub
        td['total_subtasks'] = total_sub
        td['subtask_percent'] = int((done_sub / total_sub) * 100) if total_sub > 0 else 0
        tasks_list.append(td)

    # Distinct subjects for filter
    subjects = db.execute("SELECT DISTINCT subject FROM tasks WHERE user_id = ? AND subject IS NOT NULL", (user['id'],)).fetchall()

    # Count stats
    total_count = db.execute("SELECT COUNT(*) as c FROM tasks WHERE user_id = ?", (user['id'],)).fetchone()['c']
    pending_count = db.execute("SELECT COUNT(*) as c FROM tasks WHERE user_id = ? AND status = 'Pending'", (user['id'],)).fetchone()['c']
    in_progress_count = db.execute("SELECT COUNT(*) as c FROM tasks WHERE user_id = ? AND status = 'In Progress'", (user['id'],)).fetchone()['c']
    completed_count = db.execute("SELECT COUNT(*) as c FROM tasks WHERE user_id = ? AND status = 'Completed'", (user['id'],)).fetchone()['c']

    db.close()

    return render_template(
        'tasks.html',
        tasks=tasks_list,
        subjects=[s['subject'] for s in subjects if s['subject']],
        status_filter=status_filter,
        priority_filter=priority_filter,
        subject_filter=subject_filter,
        search_query=search_query,
        counts={
            'total': total_count,
            'pending': pending_count,
            'in_progress': in_progress_count,
            'completed': completed_count
        }
    )

@app.route('/tasks/add', methods=['POST'])
@login_required
def add_task():
    user = get_current_user()
    title = request.form.get('title', '').strip()
    description = request.form.get('description', '').strip()
    subject = request.form.get('subject', '').strip()
    priority = request.form.get('priority', 'Medium')
    status = request.form.get('status', 'Pending')
    due_date = request.form.get('due_date', '').strip() or None
    due_time = request.form.get('due_time', '23:59').strip()
    estimated_hours = float(request.form.get('estimated_hours', 1.0) or 1.0)

    # Subtasks
    subtasks_raw = request.form.getlist('subtasks[]')
    subtasks_list = [{'title': s.strip(), 'done': False} for s in subtasks_raw if s.strip()]

    if not title:
        flash('Task title is required.', 'error')
        return redirect(url_for('tasks'))

    db = get_db()
    db.execute('''
        INSERT INTO tasks (
            user_id, title, description, subject, priority, status,
            due_date, due_time, estimated_hours, actual_hours, subtasks_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0.0, ?)
    ''', (user['id'], title, description, subject, priority, status, due_date, due_time, estimated_hours, json.dumps(subtasks_list)))
    db.commit()
    db.close()

    flash(f"Task '{title}' created successfully!", 'success')
    return redirect(url_for('tasks'))

@app.route('/tasks/edit/<int:task_id>', methods=['POST'])
@login_required
def edit_task(task_id):
    user = get_current_user()
    title = request.form.get('title', '').strip()
    description = request.form.get('description', '').strip()
    subject = request.form.get('subject', '').strip()
    priority = request.form.get('priority', 'Medium')
    status = request.form.get('status', 'Pending')
    due_date = request.form.get('due_date', '').strip() or None
    due_time = request.form.get('due_time', '23:59').strip()
    estimated_hours = float(request.form.get('estimated_hours', 1.0) or 1.0)
    actual_hours = float(request.form.get('actual_hours', 0.0) or 0.0)

    completed_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S') if status == 'Completed' else None

    db = get_db()
    db.execute('''
        UPDATE tasks 
        SET title = ?, description = ?, subject = ?, priority = ?, status = ?,
            due_date = ?, due_time = ?, estimated_hours = ?, actual_hours = ?,
            completed_at = CASE WHEN ? = 'Completed' THEN COALESCE(completed_at, CURRENT_TIMESTAMP) ELSE NULL END
        WHERE id = ? AND user_id = ?
    ''', (title, description, subject, priority, status, due_date, due_time, estimated_hours, actual_hours, status, task_id, user['id']))
    db.commit()
    db.close()

    flash(f"Task '{title}' updated successfully.", 'success')
    return redirect(url_for('tasks'))

@app.route('/api/tasks/<int:task_id>/toggle', methods=['POST'])
@login_required
def toggle_task(task_id):
    user = get_current_user()
    db = get_db()
    task = db.execute("SELECT * FROM tasks WHERE id = ? AND user_id = ?", (task_id, user['id'])).fetchone()
    if not task:
        db.close()
        return jsonify({'success': False, 'message': 'Task not found'}), 404

    new_status = 'Pending' if task['status'] == 'Completed' else 'Completed'
    completed_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S') if new_status == 'Completed' else None

    db.execute('''
        UPDATE tasks 
        SET status = ?, completed_at = ? 
        WHERE id = ? AND user_id = ?
    ''', (new_status, completed_at, task_id, user['id']))
    db.commit()
    db.close()

    return jsonify({'success': True, 'new_status': new_status})

@app.route('/api/tasks/<int:task_id>/subtask', methods=['POST'])
@login_required
def toggle_subtask(task_id):
    user = get_current_user()
    data = request.get_json() or {}
    subtask_index = data.get('index')

    db = get_db()
    task = db.execute("SELECT * FROM tasks WHERE id = ? AND user_id = ?", (task_id, user['id'])).fetchone()
    if not task:
        db.close()
        return jsonify({'success': False, 'message': 'Task not found'}), 404

    try:
        subtasks = json.loads(task['subtasks_json'] or '[]')
    except Exception:
        subtasks = []

    if 0 <= subtask_index < len(subtasks):
        subtasks[subtask_index]['done'] = not subtasks[subtask_index].get('done', False)
        
        # Check if all subtasks are done
        all_done = len(subtasks) > 0 and all(s.get('done') for s in subtasks)
        new_status = 'Completed' if all_done else task['status']
        completed_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S') if new_status == 'Completed' else task['completed_at']

        db.execute('''
            UPDATE tasks 
            SET subtasks_json = ?, status = ?, completed_at = ? 
            WHERE id = ? AND user_id = ?
        ''', (json.dumps(subtasks), new_status, completed_at, task_id, user['id']))
        db.commit()
        db.close()
        return jsonify({'success': True, 'subtasks': subtasks, 'task_status': new_status})

    db.close()
    return jsonify({'success': False, 'message': 'Invalid subtask index'}), 400

@app.route('/tasks/delete/<int:task_id>', methods=['POST'])
@login_required
def delete_task(task_id):
    user = get_current_user()
    db = get_db()
    db.execute("DELETE FROM tasks WHERE id = ? AND user_id = ?", (task_id, user['id']))
    db.commit()
    db.close()
    flash('Task deleted.', 'info')
    return redirect(url_for('tasks'))

# ----------------- Deadline Tracker Routes ----------------- #
@app.route('/deadlines')
@login_required
def deadlines():
    user = get_current_user()
    filter_type = request.args.get('filter', 'all')
    db = get_db()

    now = datetime.now()
    now_str = now.strftime('%Y-%m-%d %H:%M:%S')

    deadlines_query = "SELECT * FROM deadlines WHERE user_id = ?"
    params = [user['id']]

    if filter_type == 'pending':
        deadlines_query += " AND is_submitted = 0"
    elif filter_type == 'submitted':
        deadlines_query += " AND is_submitted = 1"

    deadlines_query += " ORDER BY due_date ASC, due_time ASC"
    rows = db.execute(deadlines_query, params).fetchall()

    deadline_items = []
    for r in rows:
        d = dict(r)
        due_str = f"{d['due_date']} {d['due_time'] or '23:59'}"
        try:
            due_dt = datetime.strptime(due_str, "%Y-%m-%d %H:%M")
        except ValueError:
            due_dt = datetime.strptime(f"{d['due_date']} 23:59", "%Y-%m-%d %H:%M")

        d['due_datetime_iso'] = due_dt.isoformat()
        diff = due_dt - now

        if d['is_submitted']:
            d['urgency'] = 'submitted'
            d['urgency_label'] = 'Submitted'
            d['badge_class'] = 'badge-submitted'
        elif diff.total_seconds() < 0:
            d['urgency'] = 'overdue'
            d['urgency_label'] = 'Overdue'
            d['badge_class'] = 'badge-overdue'
        elif diff.total_seconds() <= 86400: # < 24 hrs
            d['urgency'] = 'today'
            d['urgency_label'] = 'Due Today / Urgent'
            d['badge_class'] = 'badge-today'
        elif diff.total_seconds() <= 86400 * 7: # < 7 days
            d['urgency'] = 'this_week'
            d['urgency_label'] = 'Due This Week'
            d['badge_class'] = 'badge-week'
        else:
            d['urgency'] = 'upcoming'
            d['urgency_label'] = 'Upcoming'
            d['badge_class'] = 'badge-upcoming'

        d['days_remaining'] = diff.days
        d['hours_remaining'] = int((diff.seconds // 3600))
        d['minutes_remaining'] = int((diff.seconds % 3600) // 60)

        deadline_items.append(d)

    # Categories for filters
    categories = ['Assignment', 'Exam', 'Project', 'Quiz', 'Term Paper', 'Lab Report', 'Presentation']
    subjects = db.execute("SELECT DISTINCT subject FROM deadlines WHERE user_id = ?", (user['id'],)).fetchall()

    db.close()
    return render_template(
        'deadlines.html',
        deadlines=deadline_items,
        categories=categories,
        subjects=[s['subject'] for s in subjects],
        filter_type=filter_type
    )

@app.route('/deadlines/add', methods=['POST'])
@login_required
def add_deadline():
    user = get_current_user()
    title = request.form.get('title', '').strip()
    subject = request.form.get('subject', '').strip()
    category = request.form.get('category', 'Assignment').strip()
    due_date = request.form.get('due_date', '').strip()
    due_time = request.form.get('due_time', '23:59').strip()
    weight_percent = float(request.form.get('weight_percent', 10.0) or 10.0)
    priority = request.form.get('priority', 'High').strip()
    description = request.form.get('description', '').strip()

    if not title or not subject or not due_date:
        flash('Title, subject, and due date are required for a deadline.', 'error')
        return redirect(url_for('deadlines'))

    db = get_db()
    db.execute('''
        INSERT INTO deadlines (
            user_id, title, subject, category, due_date, due_time,
            weight_percent, priority, description, is_submitted
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
    ''', (user['id'], title, subject, category, due_date, due_time, weight_percent, priority, description))

    # Also automatically add an in-app reminder
    db.execute('''
        INSERT INTO notifications (user_id, title, message, type, link, is_read)
        VALUES (?, ?, ?, 'deadline', '/deadlines', 0)
    ''', (user['id'], f"📌 New Deadline Added: {title}", f"Due on {due_date} at {due_time} ({subject})."))

    db.commit()
    db.close()

    flash(f"Deadline '{title}' set for {due_date}!", 'success')
    return redirect(url_for('deadlines'))

@app.route('/deadlines/edit/<int:deadline_id>', methods=['POST'])
@login_required
def edit_deadline(deadline_id):
    user = get_current_user()
    title = request.form.get('title', '').strip()
    subject = request.form.get('subject', '').strip()
    category = request.form.get('category', 'Assignment').strip()
    due_date = request.form.get('due_date', '').strip()
    due_time = request.form.get('due_time', '23:59').strip()
    weight_percent = float(request.form.get('weight_percent', 10.0) or 10.0)
    priority = request.form.get('priority', 'High').strip()
    description = request.form.get('description', '').strip()
    is_submitted = 1 if request.form.get('is_submitted') else 0

    db = get_db()
    db.execute('''
        UPDATE deadlines 
        SET title = ?, subject = ?, category = ?, due_date = ?, due_time = ?,
            weight_percent = ?, priority = ?, description = ?, is_submitted = ?,
            submitted_at = CASE WHEN ? = 1 THEN COALESCE(submitted_at, CURRENT_TIMESTAMP) ELSE NULL END
        WHERE id = ? AND user_id = ?
    ''', (title, subject, category, due_date, due_time, weight_percent, priority, description, is_submitted, is_submitted, deadline_id, user['id']))
    db.commit()
    db.close()

    flash(f"Deadline '{title}' updated.", 'success')
    return redirect(url_for('deadlines'))

@app.route('/api/deadlines/<int:deadline_id>/toggle-submitted', methods=['POST'])
@login_required
def toggle_deadline_submitted(deadline_id):
    user = get_current_user()
    db = get_db()
    d = db.execute("SELECT * FROM deadlines WHERE id = ? AND user_id = ?", (deadline_id, user['id'])).fetchone()
    if not d:
        db.close()
        return jsonify({'success': False, 'message': 'Deadline not found'}), 404

    new_val = 0 if d['is_submitted'] else 1
    submitted_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S') if new_val == 1 else None

    db.execute('''
        UPDATE deadlines 
        SET is_submitted = ?, submitted_at = ? 
        WHERE id = ? AND user_id = ?
    ''', (new_val, submitted_at, deadline_id, user['id']))
    db.commit()
    db.close()

    return jsonify({'success': True, 'is_submitted': new_val})

@app.route('/deadlines/delete/<int:deadline_id>', methods=['POST'])
@login_required
def delete_deadline(deadline_id):
    user = get_current_user()
    db = get_db()
    db.execute("DELETE FROM deadlines WHERE id = ? AND user_id = ?", (deadline_id, user['id']))
    db.commit()
    db.close()
    flash('Deadline deleted.', 'info')
    return redirect(url_for('deadlines'))

# ----------------- Notifications & Reminders Routes ----------------- #
@app.route('/notifications')
@login_required
def notifications():
    user = get_current_user()
    db = get_db()
    items = db.execute('''
        SELECT * FROM notifications 
        WHERE user_id = ? 
        ORDER BY created_at DESC
    ''', (user['id'],)).fetchall()
    db.close()
    return render_template('notifications.html', notifications=items)

@app.route('/api/notifications/latest')
@login_required
def api_latest_notifications():
    user = get_current_user()
    db = get_db()
    check_and_generate_alerts(db, user['id'])
    
    unread_count = db.execute(
        "SELECT COUNT(*) as c FROM notifications WHERE user_id = ? AND is_read = 0",
        (user['id'],)
    ).fetchone()['c']

    rows = db.execute('''
        SELECT * FROM notifications 
        WHERE user_id = ? 
        ORDER BY created_at DESC LIMIT 8
    ''', (user['id'],)).fetchall()
    db.close()

    return jsonify({
        'unread_count': unread_count,
        'notifications': [dict(r) for r in rows]
    })

@app.route('/api/notifications/<int:notif_id>/read', methods=['POST'])
@login_required
def mark_notification_read(notif_id):
    user = get_current_user()
    db = get_db()
    db.execute("UPDATE notifications SET is_read = 1 WHERE id = ? AND user_id = ?", (notif_id, user['id']))
    db.commit()
    db.close()
    return jsonify({'success': True})

@app.route('/api/notifications/mark-all-read', methods=['POST'])
@login_required
def mark_all_notifications_read():
    user = get_current_user()
    db = get_db()
    db.execute("UPDATE notifications SET is_read = 1 WHERE user_id = ?", (user['id'],))
    db.commit()
    db.close()
    flash('All notifications marked as read.', 'success')
    return redirect(url_for('notifications'))

@app.route('/api/notifications/<int:notif_id>/delete', methods=['POST'])
@login_required
def delete_notification(notif_id):
    user = get_current_user()
    db = get_db()
    db.execute("DELETE FROM notifications WHERE id = ? AND user_id = ?", (notif_id, user['id']))
    db.commit()
    db.close()
    return jsonify({'success': True})

# ----------------- Progress Tracker & Analytics Routes ----------------- #
@app.route('/progress')
@login_required
def progress():
    user = get_current_user()
    user_id = user['id']
    db = get_db()

    today = date.today()
    start_of_week = (today - timedelta(days=today.weekday())).strftime('%Y-%m-%d')
    start_of_month = today.replace(day=1).strftime('%Y-%m-%d')

    # Streak
    streak_days = calculate_study_streak(db, user_id)

    # Total study hours (all-time, month, week)
    all_time_mins = db.execute("SELECT SUM(duration_minutes) as m FROM study_sessions WHERE user_id = ?", (user_id,)).fetchone()['m'] or 0
    month_mins = db.execute("SELECT SUM(duration_minutes) as m FROM study_sessions WHERE user_id = ? AND session_date >= ?", (user_id, start_of_month)).fetchone()['m'] or 0
    week_mins = db.execute("SELECT SUM(duration_minutes) as m FROM study_sessions WHERE user_id = ? AND session_date >= ?", (user_id, start_of_week)).fetchone()['m'] or 0

    all_time_hours = round(all_time_mins / 60.0, 1)
    month_hours = round(month_mins / 60.0, 1)
    week_hours = round(week_mins / 60.0, 1)

    target_hours = user['target_weekly_hours'] or 20.0
    week_goal_percent = min(100, int((week_hours / target_hours) * 100)) if target_hours > 0 else 0

    # Task completion rate
    total_tasks = db.execute("SELECT COUNT(*) as c FROM tasks WHERE user_id = ?", (user_id,)).fetchone()['c']
    completed_tasks = db.execute("SELECT COUNT(*) as c FROM tasks WHERE user_id = ? AND status = 'Completed'", (user_id,)).fetchone()['c']
    task_rate = int((completed_tasks / total_tasks) * 100) if total_tasks > 0 else 0

    # Deadline on-time rate
    total_deadlines = db.execute("SELECT COUNT(*) as c FROM deadlines WHERE user_id = ?", (user_id,)).fetchone()['c']
    submitted_deadlines = db.execute("SELECT COUNT(*) as c FROM deadlines WHERE user_id = ? AND is_submitted = 1", (user_id,)).fetchone()['c']
    deadline_rate = int((submitted_deadlines / total_deadlines) * 100) if total_deadlines > 0 else 0

    # Recent study sessions log
    recent_sessions = db.execute('''
        SELECT * FROM study_sessions 
        WHERE user_id = ? 
        ORDER BY session_date DESC, created_at DESC 
        LIMIT 10
    ''', (user_id,)).fetchall()

    # Subjects for the logger dropdown
    timetable_subjects = db.execute("SELECT DISTINCT subject FROM timetable_slots WHERE user_id = ?", (user_id,)).fetchall()

    db.close()
    return render_template(
        'progress.html',
        streak_days=streak_days,
        all_time_hours=all_time_hours,
        month_hours=month_hours,
        week_hours=week_hours,
        target_hours=target_hours,
        week_goal_percent=week_goal_percent,
        task_rate=task_rate,
        total_tasks=total_tasks,
        completed_tasks=completed_tasks,
        deadline_rate=deadline_rate,
        total_deadlines=total_deadlines,
        submitted_deadlines=submitted_deadlines,
        recent_sessions=recent_sessions,
        subjects=[s['subject'] for s in timetable_subjects]
    )

@app.route('/api/progress/charts')
@login_required
def api_progress_charts():
    user = get_current_user()
    user_id = user['id']
    db = get_db()

    # 1. Study Hours by Subject (last 30 days)
    subject_rows = db.execute('''
        SELECT subject, SUM(duration_minutes) as mins
        FROM study_sessions 
        WHERE user_id = ?
        GROUP BY subject 
        ORDER BY mins DESC
    ''', (user_id,)).fetchall()

    subjects_labels = [r['subject'] for r in subject_rows]
    subjects_hours = [round(r['mins'] / 60.0, 1) for r in subject_rows]

    # 2. Daily Study Activity (last 14 days)
    today = date.today()
    daily_labels = []
    daily_hours = []
    for i in range(13, -1, -1):
        day_val = today - timedelta(days=i)
        day_str = day_val.strftime('%Y-%m-%d')
        daily_labels.append(day_val.strftime('%b %d'))
        
        row = db.execute('''
            SELECT SUM(duration_minutes) as mins 
            FROM study_sessions 
            WHERE user_id = ? AND session_date = ?
        ''', (user_id, day_str)).fetchone()
        mins = row['mins'] or 0
        daily_hours.append(round(mins / 60.0, 1))

    # 3. Tasks Breakdown
    pending = db.execute("SELECT COUNT(*) as c FROM tasks WHERE user_id = ? AND status = 'Pending'", (user_id,)).fetchone()['c']
    in_prog = db.execute("SELECT COUNT(*) as c FROM tasks WHERE user_id = ? AND status = 'In Progress'", (user_id,)).fetchone()['c']
    completed = db.execute("SELECT COUNT(*) as c FROM tasks WHERE user_id = ? AND status = 'Completed'", (user_id,)).fetchone()['c']

    # 4. Deadlines Breakdown
    now_str = today.strftime('%Y-%m-%d')
    week_str = (today + timedelta(days=7)).strftime('%Y-%m-%d')

    overdue = db.execute("SELECT COUNT(*) as c FROM deadlines WHERE user_id = ? AND is_submitted = 0 AND due_date < ?", (user_id, now_str)).fetchone()['c']
    due_today = db.execute("SELECT COUNT(*) as c FROM deadlines WHERE user_id = ? AND is_submitted = 0 AND due_date = ?", (user_id, now_str)).fetchone()['c']
    due_week = db.execute("SELECT COUNT(*) as c FROM deadlines WHERE user_id = ? AND is_submitted = 0 AND due_date > ? AND due_date <= ?", (user_id, now_str, week_str)).fetchone()['c']
    upcoming = db.execute("SELECT COUNT(*) as c FROM deadlines WHERE user_id = ? AND is_submitted = 0 AND due_date > ?", (user_id, week_str)).fetchone()['c']
    submitted = db.execute("SELECT COUNT(*) as c FROM deadlines WHERE user_id = ? AND is_submitted = 1", (user_id,)).fetchone()['c']

    db.close()

    return jsonify({
        'subjects': {
            'labels': subjects_labels or ['No Sessions Yet'],
            'data': subjects_hours or [0]
        },
        'daily': {
            'labels': daily_labels,
            'data': daily_hours
        },
        'tasks': {
            'labels': ['Pending', 'In Progress', 'Completed'],
            'data': [pending, in_prog, completed]
        },
        'deadlines': {
            'labels': ['Overdue', 'Due Today', 'Due This Week', 'Upcoming', 'Submitted'],
            'data': [overdue, due_today, due_week, upcoming, submitted]
        }
    })

@app.route('/api/study-sessions/add', methods=['POST'])
@login_required
def add_study_session():
    user = get_current_user()
    subject = request.form.get('subject', '').strip()
    duration = int(request.form.get('duration_minutes', 25) or 25)
    technique = request.form.get('technique', 'Pomodoro').strip()
    session_date = request.form.get('session_date', date.today().strftime('%Y-%m-%d')).strip()
    notes = request.form.get('notes', '').strip()

    if not subject or duration <= 0:
        flash('Subject and valid duration are required.', 'error')
        return redirect(url_for('progress'))

    db = get_db()
    db.execute('''
        INSERT INTO study_sessions (user_id, subject, duration_minutes, technique, session_date, notes)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (user['id'], subject, duration, technique, session_date, notes))
    db.commit()
    db.close()

    flash(f"Logged {duration} minutes of study for '{subject}'!", 'success')
    return redirect(url_for('progress'))

@app.route('/api/study-sessions/delete/<int:session_id>', methods=['POST'])
@login_required
def delete_study_session(session_id):
    user = get_current_user()
    db = get_db()
    db.execute("DELETE FROM study_sessions WHERE id = ? AND user_id = ?", (session_id, user['id']))
    db.commit()
    db.close()
    flash('Study session record deleted.', 'info')
    return redirect(url_for('progress'))

# ----------------- User Profile Routes ----------------- #
@app.route('/profile')
@login_required
def profile():
    user = get_current_user()
    user_id = user['id']
    db = get_db()

    # Lifetime metrics
    total_sessions = db.execute("SELECT COUNT(*) as c FROM study_sessions WHERE user_id = ?", (user_id,)).fetchone()['c']
    total_mins = db.execute("SELECT SUM(duration_minutes) as m FROM study_sessions WHERE user_id = ?", (user_id,)).fetchone()['m'] or 0
    total_tasks_done = db.execute("SELECT COUNT(*) as c FROM tasks WHERE user_id = ? AND status = 'Completed'", (user_id,)).fetchone()['c']
    total_deadlines_met = db.execute("SELECT COUNT(*) as c FROM deadlines WHERE user_id = ? AND is_submitted = 1", (user_id,)).fetchone()['c']
    streak = calculate_study_streak(db, user_id)

    db.close()

    return render_template(
        'profile.html',
        stats={
            'total_sessions': total_sessions,
            'total_hours': round(total_mins / 60.0, 1),
            'total_tasks_done': total_tasks_done,
            'total_deadlines_met': total_deadlines_met,
            'streak': streak
        }
    )

@app.route('/profile/update', methods=['POST'])
@login_required
def update_profile():
    user = get_current_user()
    full_name = request.form.get('full_name', '').strip()
    email = request.form.get('email', '').strip().lower()
    bio = request.form.get('bio', '').strip()
    major = request.form.get('major', '').strip()
    institution = request.form.get('institution', '').strip()
    target_weekly_hours = float(request.form.get('target_weekly_hours', 20.0) or 20.0)
    avatar = request.form.get('avatar', 'graduation-cap').strip()

    if not email:
        flash('Email cannot be empty.', 'error')
        return redirect(url_for('profile'))

    db = get_db()
    # Check if email taken by someone else
    existing = db.execute("SELECT id FROM users WHERE email = ? AND id != ?", (email, user['id'])).fetchone()
    if existing:
        db.close()
        flash('Email address is already in use by another account.', 'error')
        return redirect(url_for('profile'))

    db.execute('''
        UPDATE users 
        SET full_name = ?, email = ?, bio = ?, major = ?,
            institution = ?, target_weekly_hours = ?, avatar = ?
        WHERE id = ?
    ''', (full_name, email, bio, major, institution, target_weekly_hours, avatar, user['id']))
    db.commit()
    db.close()

    flash('Profile updated successfully!', 'success')
    return redirect(url_for('profile'))

@app.route('/profile/preferences', methods=['POST'])
@login_required
def update_preferences():
    user = get_current_user()
    theme = request.form.get('theme', 'dark')
    sound_enabled = 1 if request.form.get('sound_enabled') else 0

    db = get_db()
    db.execute("UPDATE users SET theme = ?, sound_enabled = ? WHERE id = ?", (theme, sound_enabled, user['id']))
    db.commit()
    db.close()

    flash('Preferences saved.', 'success')
    return redirect(url_for('profile'))

@app.route('/profile/change-password', methods=['POST'])
@login_required
def change_password():
    user = get_current_user()
    current_password = request.form.get('current_password', '')
    new_password = request.form.get('new_password', '')
    confirm_password = request.form.get('confirm_password', '')

    if not check_password_hash(user['password_hash'], current_password):
        flash('Current password incorrect.', 'error')
        return redirect(url_for('profile'))

    if new_password != confirm_password:
        flash('New passwords do not match.', 'error')
        return redirect(url_for('profile'))

    if len(new_password) < 6:
        flash('New password must be at least 6 characters.', 'error')
        return redirect(url_for('profile'))

    hashed = generate_password_hash(new_password)
    db = get_db()
    db.execute("UPDATE users SET password_hash = ? WHERE id = ?", (hashed, user['id']))
    db.commit()
    db.close()

    flash('Password changed successfully.', 'success')
    return redirect(url_for('profile'))

@app.route('/profile/export-data')
@login_required
def export_data():
    user = get_current_user()
    user_id = user['id']
    db = get_db()

    data = {
        'exported_at': datetime.now().isoformat(),
        'user': dict(user),
        'timetable': [dict(r) for r in db.execute("SELECT * FROM timetable_slots WHERE user_id = ?", (user_id,)).fetchall()],
        'tasks': [dict(r) for r in db.execute("SELECT * FROM tasks WHERE user_id = ?", (user_id,)).fetchall()],
        'deadlines': [dict(r) for r in db.execute("SELECT * FROM deadlines WHERE user_id = ?", (user_id,)).fetchall()],
        'study_sessions': [dict(r) for r in db.execute("SELECT * FROM study_sessions WHERE user_id = ?", (user_id,)).fetchall()],
        'notifications': [dict(r) for r in db.execute("SELECT * FROM notifications WHERE user_id = ?", (user_id,)).fetchall()]
    }
    # Remove password hash from export
    if 'password_hash' in data['user']:
        del data['user']['password_hash']

    db.close()

    json_str = json.dumps(data, indent=2, default=str)
    buffer = io.BytesIO()
    buffer.write(json_str.encode('utf-8'))
    buffer.seek(0)

    filename = f"studyflow_backup_{user['username']}_{date.today().strftime('%Y%m%d')}.json"
    return send_file(buffer, as_attachment=True, download_name=filename, mimetype='application/json')

# ----------------- App Run ----------------- #
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
