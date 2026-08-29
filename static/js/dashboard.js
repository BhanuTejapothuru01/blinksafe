/**
 * SleepGuard — Dashboard JS
 *
 * Fetches past session history and populates overview stats.
 */

document.addEventListener('DOMContentLoaded', () => {
    console.log('[SleepGuard] Dashboard loaded.');

    const statSessions = document.querySelector('#stat-sessions .stat-value');
    const statAlerts = document.querySelector('#stat-alerts .stat-value');
    const statDuration = document.querySelector('#stat-duration .stat-value');
    const statSafety = document.querySelector('#stat-safety .stat-value');
    const sessionListEl = document.getElementById('session-list');

    async function loadDashboardData() {
        try {
            const res = await fetch('/api/sessions');
            if (!res.ok) return;
            const data = await res.json();
            const sessions = data.sessions || [];

            if (sessions.length === 0) {
                return; // Keep empty state
            }

            // Calculate aggregate statistics
            let totalAlerts = 0;
            let totalSec = 0;
            let safetyScores = [];

            sessionListEl.innerHTML = '';

            sessions.forEach(sess => {
                const alerts = (sess.drowsy_count || 0) + (sess.danger_count || 0);
                totalAlerts += alerts;
                totalSec += sess.duration_seconds || 0;

                const penalty = ((sess.drowsy_count || 0) * 10) + ((sess.danger_count || 0) * 25);
                const score = Math.max(0, Math.min(100, 100 - penalty));
                safetyScores.push(score);

                const dateStr = sess.start_time ? new Date(sess.start_time).toLocaleString() : 'Session';
                const durMins = Math.round((sess.duration_seconds || 0) / 60);

                const card = document.createElement('div');
                card.className = 'session-card';
                card.style.display = 'flex';
                card.style.alignItems = 'center';
                card.style.justifyContent = 'space-between';
                card.style.padding = '1rem';
                card.style.marginBottom = '0.75rem';
                card.style.background = 'var(--surface-dark)';
                card.style.borderRadius = 'var(--radius)';
                card.style.border = '1px solid var(--border)';

                card.innerHTML = `
                    <div>
                        <div style="font-weight: 600; font-size: 1rem;">Session #${sess.id} — ${dateStr}</div>
                        <div class="text-muted" style="font-size: 0.85rem; margin-top: 0.25rem;">
                            ⏱️ ${durMins} mins | 🚨 ${alerts} alerts | 🥱 ${sess.yawn_count || 0} yawns
                        </div>
                    </div>
                    <div>
                        <a href="/report/${sess.id}" class="btn btn-outline btn-sm">View Report →</a>
                    </div>
                `;
                sessionListEl.appendChild(card);
            });

            if (statSessions) statSessions.textContent = sessions.length;
            if (statAlerts) statAlerts.textContent = totalAlerts;
            if (statDuration) {
                const hrs = (totalSec / 3600).toFixed(1);
                statDuration.textContent = `${hrs}h`;
            }
            if (statSafety && safetyScores.length > 0) {
                const avgScore = Math.round(safetyScores.reduce((a, b) => a + b, 0) / safetyScores.length);
                statSafety.textContent = `${avgScore}%`;
            }

        } catch (e) {
            console.error('Error loading dashboard data:', e);
        }
    }

    loadDashboardData();
});
