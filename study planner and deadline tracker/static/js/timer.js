/**
 * StudyFlow: Focus & Pomodoro Timer Module
 * Handles session counting, audio alerts, browser notifications & auto-logging to database
 */

const StudyTimer = {
  duration: 25 * 60, // default 25 minutes
  remaining: 25 * 60,
  intervalId: null,
  isRunning: false,
  currentMode: 'pomodoro', // 'pomodoro' | 'shortBreak' | 'deepWork' | 'longBreak'
  modeDurations: {
    pomodoro: 25 * 60,
    shortBreak: 5 * 60,
    deepWork: 50 * 60,
    longBreak: 15 * 60
  },

  init() {
    this.display = document.getElementById('timerDisplay');
    this.toggleBtn = document.getElementById('timerToggleBtn');
    this.resetBtn = document.getElementById('timerResetBtn');
    this.subjectInput = document.getElementById('timerSubjectSelect');

    if (!this.display) return;

    this.updateDisplay();
    this.bindEvents();
  },

  bindEvents() {
    if (this.toggleBtn) {
      this.toggleBtn.addEventListener('click', () => this.toggle());
    }

    if (this.resetBtn) {
      this.resetBtn.addEventListener('click', () => this.reset());
    }

    // Mode buttons
    document.querySelectorAll('.timer-mode-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        const mode = e.target.dataset.mode;
        if (mode && this.modeDurations[mode]) {
          this.setMode(mode, e.target);
        }
      });
    });
  },

  setMode(mode, activeBtn) {
    this.pause();
    this.currentMode = mode;
    this.duration = this.modeDurations[mode];
    this.remaining = this.duration;
    this.updateDisplay();

    document.querySelectorAll('.timer-mode-btn').forEach(b => b.classList.remove('active'));
    if (activeBtn) activeBtn.classList.add('active');
  },

  toggle() {
    if (this.isRunning) {
      this.pause();
    } else {
      this.start();
    }
  },

  start() {
    if (this.isRunning) return;
    this.isRunning = true;
    if (this.toggleBtn) {
      this.toggleBtn.innerHTML = '<i class="fas fa-pause"></i> Pause';
      this.toggleBtn.classList.remove('btn-primary');
      this.toggleBtn.classList.add('btn-secondary');
    }

    this.intervalId = setInterval(() => {
      this.remaining--;
      this.updateDisplay();

      if (this.remaining <= 0) {
        this.completeSession();
      }
    }, 1000);
  },

  pause() {
    this.isRunning = false;
    clearInterval(this.intervalId);
    if (this.toggleBtn) {
      this.toggleBtn.innerHTML = '<i class="fas fa-play"></i> Start Focus';
      this.toggleBtn.classList.remove('btn-secondary');
      this.toggleBtn.classList.add('btn-primary');
    }
  },

  reset() {
    this.pause();
    this.remaining = this.duration;
    this.updateDisplay();
  },

  updateDisplay() {
    const mins = Math.floor(this.remaining / 60);
    const secs = this.remaining % 60;
    const timeFormatted = `${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;

    if (this.display) {
      this.display.textContent = timeFormatted;
    }

    // Update document title with remaining time if timer is active
    if (this.isRunning) {
      document.title = `(${timeFormatted}) StudyFlow Focus`;
    } else {
      document.title = 'StudyFlow - Study Planner and Deadline Tracker';
    }
  },

  async completeSession() {
    this.pause();
    this.remaining = this.duration;
    this.updateDisplay();

    // Trigger audio chime & browser alert
    if (window.SoundManager) {
      SoundManager.playChime('bell');
    }

    const sessionMinutes = Math.round(this.duration / 60);
    const subjectName = this.subjectInput ? this.subjectInput.value : 'General Study';

    if (window.NotificationManager) {
      NotificationManager.sendNotification(
        "🎉 Session Completed!",
        `Great job! You just finished ${sessionMinutes} minutes of focus on ${subjectName}.`
      );
    }

    // Only log actual study sessions, not short breaks
    if (this.currentMode === 'pomodoro' || this.currentMode === 'deepWork') {
      try {
        const formData = new FormData();
        formData.append('subject', subjectName || 'General Focus');
        formData.append('duration_minutes', sessionMinutes);
        formData.append('technique', this.currentMode === 'deepWork' ? 'Deep Work' : 'Pomodoro');
        formData.append('session_date', new Date().toISOString().split('T')[0]);
        formData.append('notes', 'Logged automatically via Focus Study Timer');

        const res = await fetch('/api/study-sessions/add', {
          method: 'POST',
          body: formData
        });

        if (res.ok) {
          alert(`🎉 Outstanding! ${sessionMinutes} minutes logged for ${subjectName}. Keep up the streak!`);
          window.location.reload();
        }
      } catch (e) {
        console.error("Failed to auto-log study session:", e);
      }
    } else {
      alert("Break complete! Ready to start your next study interval?");
    }
  }
};

document.addEventListener('DOMContentLoaded', () => {
  StudyTimer.init();
});
