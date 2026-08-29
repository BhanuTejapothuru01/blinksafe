/**
 * SleepGuard — Charts JS
 *
 * Renders session report metrics and Chart.js timeline graph.
 */

document.addEventListener('DOMContentLoaded', () => {
    console.log('[SleepGuard] Charts module loaded.');

    const container = document.querySelector('main[data-session-id]');
    if (!container) return;

    const sessionId = container.getAttribute('data-session-id');
    if (!sessionId) return;

    const repDuration = document.getElementById('rep-duration');
    const repSafety = document.getElementById('rep-safety');
    const repDrowsy = document.getElementById('rep-drowsy');
    const repDanger = document.getElementById('rep-danger');
    const repYawns = document.getElementById('rep-yawns');
    const repBlinks = document.getElementById('rep-blinks');

    const recCard = document.getElementById('recommendation-card');
    const riskTitle = document.getElementById('risk-level-title');
    const recText = document.getElementById('recommendation-text');
    const dateSub = document.getElementById('report-date');

    async function loadReport() {
        try {
            const res = await fetch(`/api/report/${sessionId}`);
            if (!res.ok) return;
            const data = await res.json();

            if (data.error) {
                if (recText) recText.textContent = 'Session data not found.';
                return;
            }

            // Populate cards
            if (repDuration) repDuration.textContent = data.duration_str || '0s';
            if (repSafety) repSafety.textContent = `${data.safety_score}%`;
            if (repDrowsy) repDrowsy.textContent = data.drowsy_count || 0;
            if (repDanger) repDanger.textContent = data.danger_count || 0;
            if (repYawns) repYawns.textContent = data.yawn_count || 0;
            if (repBlinks) repBlinks.textContent = data.blink_count || 0;

            // Driver info
            const driverNameEl = document.getElementById('report-driver-name');
            if (driverNameEl) {
                const dName = data.driver_name || 'Unknown / Not recorded';
                const dPhone = data.driver_phone && data.driver_phone !== 'N/A' ? ` | 📞 ${data.driver_phone}` : '';
                driverNameEl.textContent = `👤 Driver: ${dName}${dPhone}`;
            }

            if (dateSub && data.start_time) {
                dateSub.textContent = `Recorded on ${new Date(data.start_time).toLocaleString()}`;
            }

            // Risk recommendation
            if (riskTitle) riskTitle.textContent = `${data.risk_level} — Score: ${data.safety_score}/100`;
            if (recText) recText.textContent = data.recommendation;

            if (recCard) {
                if (data.safety_score < 50) {
                    recCard.style.borderLeftColor = '#ef4444';
                } else if (data.safety_score < 80) {
                    recCard.style.borderLeftColor = '#f59e0b';
                } else {
                    recCard.style.borderLeftColor = '#10b981';
                }
            }

            // Chart.js timeline
            const chartCanvas = document.getElementById('timeline-chart');
            if (chartCanvas && typeof Chart !== 'undefined') {
                const ctx = chartCanvas.getContext('2d');
                const labels = data.timeline.labels.length > 0 ? data.timeline.labels : ['Start', 'End'];
                const confData = data.timeline.confidence.length > 0 ? data.timeline.confidence : [0.0, 0.0];
                const earData = data.timeline.ear.length > 0 ? data.timeline.ear : [0.3, 0.3];
                const marData = data.timeline.mar.length > 0 ? data.timeline.mar : [0.15, 0.15];

                new Chart(ctx, {
                    type: 'line',
                    data: {
                        labels: labels,
                        datasets: [
                            {
                                label: 'Confidence Score',
                                data: confData,
                                borderColor: '#ef4444',
                                backgroundColor: 'rgba(239, 68, 68, 0.1)',
                                borderWidth: 2,
                                fill: true,
                                tension: 0.3,
                            },
                            {
                                label: 'EAR (Eye Aspect Ratio)',
                                data: earData,
                                borderColor: '#3b82f6',
                                borderWidth: 2,
                                fill: false,
                                tension: 0.3,
                            },
                            {
                                label: 'MAR (Mouth Aspect Ratio)',
                                data: marData,
                                borderColor: '#10b981',
                                borderWidth: 2,
                                fill: false,
                                tension: 0.3,
                            },
                        ],
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        scales: {
                            x: {
                                grid: { color: 'rgba(255, 255, 255, 0.05)' },
                                ticks: { color: '#94a3b8' },
                            },
                            y: {
                                min: 0,
                                max: 1.0,
                                grid: { color: 'rgba(255, 255, 255, 0.05)' },
                                ticks: { color: '#94a3b8' },
                            },
                        },
                        plugins: {
                            legend: {
                                labels: { color: '#cbd5e1' },
                            },
                        },
                    },
                });
            }

        } catch (e) {
            console.error('Failed to load report data:', e);
        }
    }

    loadReport();
});
