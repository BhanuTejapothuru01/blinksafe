/**
 * SleepGuard — Live Monitoring JS
 *
 * Handles session timer, start/stop session API calls, status polling, and real-time Chart.js EAR trend.
 */

document.addEventListener('DOMContentLoaded', () => {
    console.log('[SleepGuard] Monitoring page loaded.');

    const btnStart = document.getElementById('btn-start-session');
    const btnStop = document.getElementById('btn-stop-session');
    const btnTestAlarm = document.getElementById('btn-test-alarm');
    const timerEl = document.getElementById('session-timer');

    if (btnTestAlarm) {
        btnTestAlarm.addEventListener('click', async () => {
            btnTestAlarm.disabled = true;
            btnTestAlarm.textContent = '🔊 Playing...';
            try {
                const res = await fetch('/api/test-alarm', { method: 'POST' });
                const data = await res.json();
                console.log('[Test Alarm Response]', data);
            } catch (err) {
                console.error('[Test Alarm Error]', err);
            } setTimeout(() => {
                btnTestAlarm.disabled = false;
                btnTestAlarm.textContent = '🔊 Test Alarm';
            }, 1200);
        });
    }

    const statusBadge = document.getElementById('status-badge');
    const sidebarState = document.getElementById('sidebar-state');
    const fpsDisplay = document.getElementById('fps-display');

    const earValue = document.getElementById('ear-value');
    const marValue = document.getElementById('mar-value');
    const pitchValue = document.getElementById('pitch-value');
    const yawValue = document.getElementById('yaw-value');

    const blinkCount = document.getElementById('blink-count');
    const yawnCount = document.getElementById('yawn-count');
    const nodCount = document.getElementById('nod-count');
    const alertCount = document.getElementById('alert-count');

    const confidencePct = document.getElementById('confidence-pct');
    const confidenceBar = document.getElementById('confidence-bar');

    let timerInterval = null;
    let elapsedSeconds = 0;
    let pollInterval = null;

    // ── EAR Live Chart Setup ──────────────────────────────────────────
    const ctx = document.getElementById('ear-chart')?.getContext('2d');
    let earChart = null;

    if (ctx && typeof Chart !== 'undefined') {
        earChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: Array(20).fill(''),
                datasets: [{
                    label: 'EAR',
                    data: Array(20).fill(0.3),
                    borderColor: '#3b82f6',
                    borderWidth: 2,
                    fill: false,
                    tension: 0.3,
                    pointRadius: 0,
                }],
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                animation: false,
                scales: {
                    x: { display: false },
                    y: {
                        min: 0,
                        max: 0.5,
                        grid: { color: 'rgba(255,255,255,0.05)' },
                        ticks: { color: '#64748b', font: { size: 10 } },
                    },
                },
                plugins: { legend: { display: false } },
            },
        });
    }

    // ── Helpers ──────────────────────────────────────────────────────
    function formatTime(totalSec) {
        const h = String(Math.floor(totalSec / 3600)).padStart(2, '0');
        const m = String(Math.floor((totalSec % 3600) / 60)).padStart(2, '0');
        const s = String(totalSec % 60).padStart(2, '0');
        return `${h}:${m}:${s}`;
    }

    function startTimer() {
        elapsedSeconds = 0;
        timerEl.textContent = formatTime(0);
        timerInterval = setInterval(() => {
            elapsedSeconds++;
            timerEl.textContent = formatTime(elapsedSeconds);
        }, 1000);
    }

    function stopTimer() {
        if (timerInterval) clearInterval(timerInterval);
        timerInterval = null;
    }

    function updateBadge(el, state) {
        if (!el) return;
        el.textContent = state;
        el.className = 'badge ';

        if (state === 'ALERT') {
            el.classList.add('badge--alert');
            el.style.background = 'rgba(16, 185, 129, 0.2)';
            el.style.color = '#34d399';
        } else if (state === 'DROWSY') {
            el.classList.add('badge--drowsy');
            el.style.background = 'rgba(245, 158, 11, 0.2)';
            el.style.color = '#fbbf24';
        } else if (state === 'DANGER') {
            el.classList.add('badge--danger');
            el.style.background = 'rgba(239, 68, 68, 0.2)';
            el.style.color = '#f87171';
        } else {
            el.style.background = 'rgba(148, 163, 184, 0.2)';
            el.style.color = '#94a3b8';
        }
    }

    // ── Status Polling ───────────────────────────────────────────────
    async function pollStatus() {
        try {
            const res = await fetch('/api/status');
            if (!res.ok) return;
            const data = await res.json();

            // FPS & Badge
            if (fpsDisplay) fpsDisplay.textContent = `${data.fps || 0} FPS`;
            updateBadge(statusBadge, data.state);
            updateBadge(sidebarState, data.state);

            // Metrics
            if (earValue) earValue.textContent = data.ear !== null ? data.ear.toFixed(2) : '—';
            if (marValue) marValue.textContent = data.mar !== null ? data.mar.toFixed(2) : '—';
            if (pitchValue) pitchValue.textContent = data.pitch !== null ? `${data.pitch}°` : '—';
            if (yawValue) yawValue.textContent = data.yaw !== null ? `${data.yaw}°` : '—';

            // Counts
            if (blinkCount) blinkCount.textContent = data.blink_count || 0;
            if (yawnCount) yawnCount.textContent = data.yawn_count || 0;
            if (nodCount) nodCount.textContent = data.nod_count || 0;
            if (alertCount) alertCount.textContent = (data.drowsy_count || 0) + (data.danger_count || 0);

            // Driver Recognition Card Update
            const driverNameEl = document.getElementById('driver-name-display');
            const driverPhoneEl = document.getElementById('driver-phone-display');
            const driverBadgeEl = document.getElementById('driver-status-badge');

            if (driverNameEl) driverNameEl.textContent = data.driver_name || 'Unknown Driver';
            if (driverPhoneEl) driverPhoneEl.textContent = data.driver_phone || 'N/A';

            if (driverBadgeEl) {
                const status = data.driver_status || 'VERIFYING';
                if (status === 'CONFIRMED') {
                    driverBadgeEl.textContent = '✓ CONFIRMED';
                    driverBadgeEl.style.background = 'rgba(16, 185, 129, 0.15)';
                    driverBadgeEl.style.color = '#34d399';
                    driverBadgeEl.style.border = '1px solid rgba(16, 185, 129, 0.3)';
                } else if (status === 'VERIFYING') {
                    driverBadgeEl.textContent = 'VERIFYING...';
                    driverBadgeEl.style.background = 'rgba(234, 179, 8, 0.15)';
                    driverBadgeEl.style.color = '#facc15';
                    driverBadgeEl.style.border = '1px solid rgba(234, 179, 8, 0.3)';
                } else if (status === 'MULTIPLE_FACES') {
                    driverBadgeEl.textContent = 'MULTIPLE FACES';
                    driverBadgeEl.style.background = 'rgba(168, 85, 247, 0.15)';
                    driverBadgeEl.style.color = '#c084fc';
                    driverBadgeEl.style.border = '1px solid rgba(168, 85, 247, 0.3)';
                } else {
                    driverBadgeEl.textContent = 'UNKNOWN DRIVER';
                    driverBadgeEl.style.background = 'rgba(239, 68, 68, 0.15)';
                    driverBadgeEl.style.color = '#f87171';
                    driverBadgeEl.style.border = '1px solid rgba(239, 68, 68, 0.3)';
                }
            }

            // Confidence bar
            const confPct = Math.round((data.confidence || 0) * 100);
            if (confidencePct) confidencePct.textContent = `${confPct}%`;
            if (confidenceBar) {
                confidenceBar.style.width = `${confPct}%`;
                if (data.state === 'DANGER') {
                    confidenceBar.style.background = '#ef4444';
                } else if (data.state === 'DROWSY') {
                    confidenceBar.style.background = '#f59e0b';
                } else {
                    confidenceBar.style.background = '#10b981';
                }
            }

            // Update EAR Chart
            if (earChart && data.ear !== undefined) {
                earChart.data.datasets[0].data.shift();
                earChart.data.datasets[0].data.push(data.ear);
                earChart.update('none');
            }

            // Sync button state if session already active on backend
            if (data.session_active && btnStart.disabled === false) {
                btnStart.disabled = true;
                btnStop.disabled = false;
                if (!timerInterval) startTimer();
            }

        } catch (e) {
            console.error('Error polling /api/status:', e);
        }
    }

    pollInterval = setInterval(pollStatus, 400);

    // ── Start / Stop Buttons ─────────────────────────────────────────
    btnStart.addEventListener('click', async () => {
        btnStart.disabled = true;
        try {
            const res = await fetch('/api/session/start', { method: 'POST' });
            const data = await res.json();
            btnStop.disabled = false;
            startTimer();
            console.log('[SleepGuard] Session started:', data);
        } catch (e) {
            console.error('Failed to start session:', e);
            btnStart.disabled = false;
        }
    });

    btnStop.addEventListener('click', async () => {
        btnStop.disabled = true;
        try {
            const res = await fetch('/api/session/stop', { method: 'POST' });
            const data = await res.json();
            stopTimer();
            console.log('[SleepGuard] Session stopped:', data);
            if (data.redirect_url) {
                window.location.href = data.redirect_url;
            }
        } catch (e) {
            console.error('Failed to stop session:', e);
            btnStop.disabled = false;
        }
    });
});
