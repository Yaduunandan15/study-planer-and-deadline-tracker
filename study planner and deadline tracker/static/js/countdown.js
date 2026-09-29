/**
 * StudyFlow: Live Deadline Countdown Clock
 * Calculates remaining days, hours, minutes and seconds in real-time
 */

function initDeadlineCountdowns() {
  const clocks = document.querySelectorAll('[data-countdown-target]');
  if (!clocks.length) return;

  function updateAllClocks() {
    const now = new Date().getTime();

    clocks.forEach(clock => {
      const targetStr = clock.getAttribute('data-countdown-target');
      if (!targetStr) return;

      const targetDate = new Date(targetStr).getTime();
      const distance = targetDate - now;

      const isSubmitted = clock.getAttribute('data-submitted') === 'true';
      if (isSubmitted) {
        clock.innerHTML = '<span class="text-muted"><i class="fas fa-check-circle"></i> Submitted</span>';
        return;
      }

      if (distance < 0) {
        clock.innerHTML = '<span class="text-danger font-bold"><i class="fas fa-exclamation-triangle"></i> OVERDUE</span>';
        return;
      }

      const days = Math.floor(distance / (1000 * 60 * 60 * 24));
      const hours = Math.floor((distance % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
      const minutes = Math.floor((distance % (1000 * 60 * 60)) / (1000 * 60));
      const seconds = Math.floor((distance % (1000 * 60)) / 1000);

      // Check if miniature clock or standard full block clock
      const isMini = clock.classList.contains('countdown-mini');

      if (isMini) {
        if (days > 0) {
          clock.textContent = `${days}d ${hours}h left`;
        } else if (hours > 0) {
          clock.textContent = `${hours}h ${minutes}m left`;
        } else {
          clock.textContent = `${minutes}m ${seconds}s left`;
        }
      } else {
        clock.innerHTML = `
          <div class="countdown-unit">
            <div class="countdown-num">${String(days).padStart(2, '0')}</div>
            <div class="countdown-lbl">Days</div>
          </div>
          <div class="countdown-unit">
            <div class="countdown-num">${String(hours).padStart(2, '0')}</div>
            <div class="countdown-lbl">Hours</div>
          </div>
          <div class="countdown-unit">
            <div class="countdown-num">${String(minutes).padStart(2, '0')}</div>
            <div class="countdown-lbl">Mins</div>
          </div>
          <div class="countdown-unit">
            <div class="countdown-num">${String(seconds).padStart(2, '0')}</div>
            <div class="countdown-lbl">Secs</div>
          </div>
        `;
      }
    });
  }

  updateAllClocks();
  setInterval(updateAllClocks, 1000);
}

document.addEventListener('DOMContentLoaded', () => {
  initDeadlineCountdowns();
});
