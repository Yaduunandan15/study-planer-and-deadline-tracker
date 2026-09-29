# StudyFlow - Study Planner and Deadline Tracker 🎓

A modern, responsive, full-stack web application designed for students and self-learners to plan study schedules, track deadlines with live countdown clocks, manage homework and coursework tasks, receive proactive notifications/reminders, and visualize learning progress.

---

## 🌟 Key Features

### 1. 🔒 User Authentication & Protected Access
- **Mandatory Login**: All routes and sensitive academic data are secured behind authentication.
- **Secure Password Hashing**: Utilizes `werkzeug.security` (PBKDF2/scrypt).
- **1-Click Demo Login**: Explore all features immediately using pre-loaded student data (`alex_student` / `study123`).
- **Multi-User Isolation**: Every student maintains their own independent timetable, tasks, deadlines, and study history.

### 2. 📅 Study Planner & Timetable
- **Weekly / Daily View**: Interactive timetable grid spanning Monday through Sunday.
- **Custom Time Slots**: Specify start/end times, location/link, and color coding.
- **Study Techniques**: Tag sessions with techniques such as *Pomodoro (25/5)*, *Deep Work*, *Feynman Technique*, *Active Recall & Flashcards*, or *Lecture & Review*.
- **Printable Timetable**: One-click printable layout.

### 3. ✅ Task Management
- **Task Organization**: Organize tasks by subject, priority (*Urgent*, *High*, *Medium*, *Low*), and status (*Pending*, *In Progress*, *Completed*).
- **Interactive Checklists**: Multi-item subtask lists with visual completion progress bars.
- **Instant Status Toggle**: Check off tasks without page reloads, accompanied by pleasant audio chimes.
- **Estimated vs. Actual Hours**: Compare estimated study time against actual hours spent.

### 4. ⏳ Deadline Tracker
- **Real-Time Countdown Clocks**: Live per-second timers displaying Days, Hours, Minutes, and Seconds remaining.
- **Urgency Tiers**:
  - 🔴 **Overdue** (Past due date)
  - 🟠 **Due Today / Urgent** (< 24 hours)
  - 🟡 **Due This Week** (< 7 days)
  - 🟢 **Upcoming** (> 7 days)
  - ⚪ **Submitted** (Marked as turned in)
- **Dual Views**: Switch between **Countdown Cards View** and interactive **Monthly Calendar View**.
- **Grade Weight Tracking**: Record the percentage weight of each deliverable (exams, assignments, lab reports, term papers).

### 5. 🔔 Reminders & Notifications
- **In-App Notification Center**: Notification dropdown with unread badge counter in the top bar.
- **Automated Deadline Alerts**: Generates reminders for deliverables due within 24 hours or overdue items.
- **Browser Desktop Notifications**: Integrates with the HTML5 `Notification` API.
- **Web Audio Chimes**: Synthesized audio alerts using the Web Audio API (zero external audio file dependencies).

### 6. 📈 Progress Tracker & Analytics
- **Daily Study Streak**: Consecutive study days tracker with celebratory milestones.
- **Weekly Study Target**: Visual progress bar tracking actual hours against your target weekly goal.
- **Chart.js Visualizations**:
  1. *Study Hours by Subject* (Doughnut Chart)
  2. *Daily Study Activity* (14-Day Activity Bar Chart)
  3. *Task Completion Status* (Pie Chart)
  4. *Deadline Urgency Distribution* (Bar Chart)
- **Focus & Pomodoro Timer**: Integrated timer that automatically logs finished study sessions directly into the database.
- **Manual Session Logger**: Manually log study sessions and maintain a detailed study history.

### 7. 👤 User Profile & Customization
- **Student Profile**: Customize avatar icons, full name, major, university, bio, and weekly study goal.
- **Lifetime Statistics**: Summary of total study hours, tasks completed, and deadlines met on time.
- **Dark / Light Theme Toggle**: Persistent interface theme switch.
- **Data Export & Backup**: Download all study data as a JSON file anytime.

---

## 🚀 How to Run the Application

### Prerequisites
- Python 3.10+ (Tested on Python 3.14)
- Flask (`pip install -r requirements.txt`)

### Quick Start

1. **Navigate to the project directory**:
   ```powershell
   cd "c:\study planner and deadline tracker"
   ```

2. **Install dependencies** (Flask is already installed if using standard Python environment):
   ```powershell
   py -m pip install -r requirements.txt
   ```

3. **Start the application**:
   ```powershell
   py run.py
   ```

4. **Open in your browser**:
   Visit [http://127.0.0.1:5000](http://127.0.0.1:5000)

5. **Login**:
   - Click **"1-Click Demo Login"** to inspect the fully populated demo profile (`alex_student`), OR
   - Click **"Create one here"** to register your own new account.

---

## 🧪 Running Automated Tests

Run the test suite to verify all endpoints, database operations, and templates:

```powershell
py test_app.py
```
*(All 8 test suites pass cleanly.)*

---

## 📁 Project Structure

```
study-planner-and-deadline-tracker/
├── app.py                     # Flask application & API routes
├── database.py                # SQLite schema and sample demo data
├── run.py                     # App runner script
├── test_app.py                # Automated test suite
├── requirements.txt           # Project dependencies
├── static/
│   ├── css/
│   │   └── style.css          # CSS styles, themes, and animations
│   └── js/
│       ├── main.js            # Core JS (Audio chime, theme, modals, AJAX)
│       ├── timer.js           # Focus / Pomodoro timer widget
│       ├── countdown.js       # Live deadline countdown clocks
│       └── charts.js          # Chart.js analytics dashboards
└── templates/
    ├── base.html              # Base shell layout & quick-add modal
    ├── auth/
    │   ├── login.html         # Login page with demo-fill button
    │   └── register.html      # Registration page
    ├── index.html             # Dashboard with overview & timer
    ├── planner.html           # Weekly / Daily timetable scheduler
    ├── tasks.html             # Task management board with checklists
    ├── deadlines.html         # Deadline tracker with countdowns & calendar
    ├── notifications.html     # Notification center & reminder settings
    ├── progress.html          # Analytics charts & study session logs
    └── profile.html           # User profile, goals, and settings
```
