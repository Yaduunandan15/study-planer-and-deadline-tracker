/**
 * StudyFlow: Core JavaScript Utilities
 * Theme management, Audio synthesizer, Notifications, Modals & AJAX actions
 */

// 1. Web Audio API Chime Generator
const SoundManager = {
  ctx: null,
  enabled: true,

  init() {
    try {
      const AudioCtx = window.AudioContext || window.webkitAudioContext;
      if (AudioCtx) {
        this.ctx = new AudioCtx();
      }
    } catch (e) {
      console.warn("Web Audio API not supported", e);
    }
  },

  playChime(type = 'bell') {
    if (!this.enabled) return;
    if (!this.ctx) this.init();
    if (!this.ctx) return;

    if (this.ctx.state === 'suspended') {
      this.ctx.resume();
    }

    const now = this.ctx.currentTime;
    const osc = this.ctx.createOscillator();
    const gain = this.ctx.createGain();

    osc.connect(gain);
    gain.connect(this.ctx.destination);

    if (type === 'bell' || type === 'success') {
      // Pleasant multi-harmonic chime
      osc.type = 'sine';
      osc.frequency.setValueAtTime(587.33, now); // D5
      osc.frequency.exponentialRampToValueAtTime(880, now + 0.15); // A5
      gain.gain.setValueAtTime(0.3, now);
      gain.gain.exponentialRampToValueAtTime(0.001, now + 1.2);
      osc.start(now);
      osc.stop(now + 1.2);
    } else if (type === 'alert') {
      // Attention alert
      osc.type = 'triangle';
      osc.frequency.setValueAtTime(659.25, now); // E5
      osc.frequency.setValueAtTime(783.99, now + 0.15); // G5
      gain.gain.setValueAtTime(0.35, now);
      gain.gain.exponentialRampToValueAtTime(0.001, now + 0.8);
      osc.start(now);
      osc.stop(now + 0.8);
    }
  }
};

// 2. Browser Notifications Helper
const NotificationManager = {
  isSupported: 'Notification' in window,

  async requestPermission() {
    if (!this.isSupported) {
      alert("Desktop notifications are not supported by this browser.");
      return false;
    }
    const permission = await Notification.requestPermission();
    if (permission === 'granted') {
      this.sendNotification("Notifications Active! 🚀", "StudyFlow will keep you informed of deadlines and study sessions.");
      return true;
    }
    return false;
  },

  sendNotification(title, body, icon = null) {
    if (!this.isSupported || Notification.permission !== 'granted') return;
    try {
      new Notification(title, {
        body: body,
        icon: icon || '/static/img/favicon.png'
      });
      SoundManager.playChime('bell');
    } catch (e) {
      console.warn("Could not dispatch desktop notification", e);
    }
  }
};

// 3. Theme Toggle & Persistence
function initTheme() {
  const savedTheme = localStorage.getItem('studyflow_theme') || document.documentElement.getAttribute('data-theme') || 'dark';
  setTheme(savedTheme);

  const toggleBtn = document.getElementById('themeToggleBtn');
  if (toggleBtn) {
    toggleBtn.addEventListener('click', () => {
      const current = document.documentElement.getAttribute('data-theme');
      const nextTheme = current === 'dark' ? 'light' : 'dark';
      setTheme(nextTheme);
      // Optional: Save preference to backend if logged in
      fetch('/profile/preferences', {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: `theme=${nextTheme}&sound_enabled=1`
      }).catch(err => console.log('Preference auto-sync:', err));
    });
  }
}

function setTheme(theme) {
  document.documentElement.setAttribute('data-theme', theme);
  localStorage.setItem('studyflow_theme', theme);
  const icon = document.getElementById('themeToggleIcon');
  if (icon) {
    icon.className = theme === 'dark' ? 'fas fa-sun' : 'fas fa-moon';
  }
}

// 4. Modal Helpers
function openModal(modalId) {
  const modal = document.getElementById(modalId);
  if (modal) {
    modal.classList.add('active');
    document.body.style.overflow = 'hidden';
  }
}

function closeModal(modalId) {
  const modal = document.getElementById(modalId);
  if (modal) {
    modal.classList.remove('active');
    document.body.style.overflow = '';
  }
}

// 5. Notification Bell Dropdown
function initNotificationDropdown() {
  const bellBtn = document.getElementById('notifBellBtn');
  const dropdown = document.getElementById('notifDropdown');

  if (bellBtn && dropdown) {
    bellBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      dropdown.classList.toggle('show');
    });

    document.addEventListener('click', (e) => {
      if (!dropdown.contains(e.target) && e.target !== bellBtn) {
        dropdown.classList.remove('show');
      }
    });
  }
}

// 6. Mobile Sidebar Toggle
function initMobileSidebar() {
  const toggleBtn = document.getElementById('mobileNavToggle');
  const sidebar = document.getElementById('mainSidebar');

  if (toggleBtn && sidebar) {
    toggleBtn.addEventListener('click', () => {
      sidebar.classList.toggle('open');
    });

    document.addEventListener('click', (e) => {
      if (!sidebar.contains(e.target) && !toggleBtn.contains(e.target) && sidebar.classList.contains('open')) {
        sidebar.classList.remove('open');
      }
    });
  }
}

// 7. Interactive Task Status Toggle
async function toggleTaskStatus(taskId, btnElem) {
  try {
    const res = await fetch(`/api/tasks/${taskId}/toggle`, { method: 'POST' });
    const data = await res.json();
    if (data.success) {
      SoundManager.playChime('success');
      const card = document.getElementById(`task-card-${taskId}`);
      if (card) {
        if (data.new_status === 'Completed') {
          card.classList.add('task-completed-style');
          const titleElem = card.querySelector('.task-title-text');
          if (titleElem) titleElem.classList.add('line-through', 'text-muted');
          const statusBadge = card.querySelector('.task-status-badge');
          if (statusBadge) {
            statusBadge.className = 'badge badge-completed task-status-badge';
            statusBadge.textContent = 'Completed';
          }
          if (btnElem) {
            btnElem.innerHTML = '<i class="fas fa-check-circle text-success"></i>';
          }
        } else {
          card.classList.remove('task-completed-style');
          const titleElem = card.querySelector('.task-title-text');
          if (titleElem) titleElem.classList.remove('line-through', 'text-muted');
          const statusBadge = card.querySelector('.task-status-badge');
          if (statusBadge) {
            statusBadge.className = 'badge badge-pending task-status-badge';
            statusBadge.textContent = 'Pending';
          }
          if (btnElem) {
            btnElem.innerHTML = '<i class="far fa-circle"></i>';
          }
        }
      } else {
        window.location.reload();
      }
    }
  } catch (err) {
    console.error('Error toggling task:', err);
  }
}

// 8. Toggle Subtask Checklist Item
async function toggleSubtask(taskId, subtaskIndex, checkboxElem) {
  try {
    const res = await fetch(`/api/tasks/${taskId}/subtask`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ index: subtaskIndex })
    });
    const data = await res.json();
    if (data.success) {
      SoundManager.playChime('bell');
      const label = checkboxElem.closest('label');
      if (label) {
        label.classList.toggle('line-through');
        label.classList.toggle('text-muted');
      }
      if (data.task_status === 'Completed') {
        const statusBadge = document.querySelector(`#task-card-${taskId} .task-status-badge`);
        if (statusBadge) {
          statusBadge.className = 'badge badge-completed task-status-badge';
          statusBadge.textContent = 'Completed';
        }
      }
    }
  } catch (err) {
    console.error('Error toggling subtask:', err);
  }
}

// 9. Toggle Deadline Submitted
async function toggleDeadlineSubmitted(deadlineId, checkElem) {
  try {
    const res = await fetch(`/api/deadlines/${deadlineId}/toggle-submitted`, { method: 'POST' });
    const data = await res.json();
    if (data.success) {
      SoundManager.playChime('success');
      window.location.reload();
    }
  } catch (err) {
    console.error('Error toggling deadline:', err);
  }
}

// 10. Mark Notification as Read
async function markNotificationAsRead(notifId, itemElem) {
  try {
    const res = await fetch(`/api/notifications/${notifId}/read`, { method: 'POST' });
    const data = await res.json();
    if (data.success && itemElem) {
      itemElem.classList.remove('unread');
      // Decrement bell badge
      const badge = document.getElementById('notifBellBadge');
      if (badge) {
        let count = parseInt(badge.textContent || '1') - 1;
        if (count <= 0) {
          badge.style.display = 'none';
        } else {
          badge.textContent = count;
        }
      }
    }
  } catch (err) {
    console.error('Error marking notification read:', err);
  }
}

// Initialize on DOM ready
document.addEventListener('DOMContentLoaded', () => {
  initTheme();
  initNotificationDropdown();
  initMobileSidebar();

  // Close modals on clicking overlay or pressing Escape
  document.querySelectorAll('.modal-overlay').forEach(modal => {
    modal.addEventListener('click', (e) => {
      if (e.target === modal) {
        modal.classList.remove('active');
        document.body.style.overflow = '';
      }
    });
  });

  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
      document.querySelectorAll('.modal-overlay.active').forEach(modal => {
        modal.classList.remove('active');
        document.body.style.overflow = '';
      });
    }
  });

  // Enable audio context upon first user gesture
  document.addEventListener('click', () => {
    if (!SoundManager.ctx) SoundManager.init();
  }, { once: true });
});
