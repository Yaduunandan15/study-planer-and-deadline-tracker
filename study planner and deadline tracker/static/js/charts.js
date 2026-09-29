/**
 * StudyFlow: Progress Tracker & Analytics Charts
 * Visualizes study hours, task status, deadline urgency and daily activity via Chart.js
 */

async function initProgressCharts() {
  if (typeof Chart === 'undefined') {
    console.warn("Chart.js not loaded. Skipping chart initialization.");
    return;
  }

  const subjectsCanvas = document.getElementById('subjectHoursChart');
  const dailyCanvas = document.getElementById('dailyActivityChart');
  const tasksCanvas = document.getElementById('taskStatusChart');
  const deadlinesCanvas = document.getElementById('deadlineUrgencyChart');

  if (!subjectsCanvas && !dailyCanvas && !tasksCanvas && !deadlinesCanvas) return;

  try {
    const res = await fetch('/api/progress/charts');
    const data = await res.json();

    const isDark = document.documentElement.getAttribute('data-theme') !== 'light';
    const textColor = isDark ? '#94A3B8' : '#475569';
    const gridColor = isDark ? 'rgba(255, 255, 255, 0.06)' : 'rgba(0, 0, 0, 0.06)';

    // Modern color palette
    const colors = [
      '#6366F1', '#EC4899', '#06B6D4', '#10B981', '#F59E0B', 
      '#8B5CF6', '#3B82F6', '#14B8A6', '#F43F5E', '#A855F7'
    ];

    // 1. Subject Study Hours (Doughnut)
    if (subjectsCanvas && data.subjects) {
      new Chart(subjectsCanvas, {
        type: 'doughnut',
        data: {
          labels: data.subjects.labels,
          datasets: [{
            data: data.subjects.data,
            backgroundColor: colors.slice(0, data.subjects.labels.length),
            borderWidth: 0,
            hoverOffset: 6
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: {
              position: 'bottom',
              labels: { color: textColor, font: { size: 11 } }
            },
            tooltip: {
              callbacks: {
                label: (ctx) => ` ${ctx.label}: ${ctx.raw} hrs`
              }
            }
          },
          cutout: '70%'
        }
      });
    }

    // 2. Daily Activity (Bar Chart)
    if (dailyCanvas && data.daily) {
      new Chart(dailyCanvas, {
        type: 'bar',
        data: {
          labels: data.daily.labels,
          datasets: [{
            label: 'Hours Studied',
            data: data.daily.data,
            backgroundColor: 'rgba(99, 102, 241, 0.75)',
            borderColor: '#6366F1',
            borderWidth: 1,
            borderRadius: 6,
            hoverBackgroundColor: '#818CF8'
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          scales: {
            y: {
              beginAtZero: true,
              grid: { color: gridColor },
              ticks: { color: textColor, callback: (v) => `${v}h` }
            },
            x: {
              grid: { display: false },
              ticks: { color: textColor }
            }
          },
          plugins: {
            legend: { display: false },
            tooltip: {
              callbacks: {
                label: (ctx) => ` ${ctx.raw} hours studied`
              }
            }
          }
        }
      });
    }

    // 3. Task Status Breakdown (Pie)
    if (tasksCanvas && data.tasks) {
      new Chart(tasksCanvas, {
        type: 'pie',
        data: {
          labels: data.tasks.labels,
          datasets: [{
            data: data.tasks.data,
            backgroundColor: ['#F59E0B', '#06B6D4', '#10B981'],
            borderWidth: 0
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: {
              position: 'bottom',
              labels: { color: textColor, font: { size: 11 } }
            }
          }
        }
      });
    }

    // 4. Deadline Urgency (Bar)
    if (deadlinesCanvas && data.deadlines) {
      new Chart(deadlinesCanvas, {
        type: 'bar',
        data: {
          labels: data.deadlines.labels,
          datasets: [{
            label: 'Deadlines',
            data: data.deadlines.data,
            backgroundColor: [
              '#EF4444', // Overdue
              '#F59E0B', // Due Today
              '#818CF8', // This week
              '#10B981', // Upcoming
              '#64748B'  // Submitted
            ],
            borderRadius: 6
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          scales: {
            y: {
              beginAtZero: true,
              ticks: { stepSize: 1, color: textColor },
              grid: { color: gridColor }
            },
            x: {
              ticks: { color: textColor },
              grid: { display: false }
            }
          },
          plugins: {
            legend: { display: false }
          }
        }
      });
    }

  } catch (err) {
    console.error("Failed to load charts data:", err);
  }
}

document.addEventListener('DOMContentLoaded', () => {
  initProgressCharts();
});
