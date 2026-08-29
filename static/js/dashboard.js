/**
 * SleepGuard — Dashboard JS
 *
 * Fetches past session history, manages driver registration, lists registered FAISS drivers.
 */

document.addEventListener('DOMContentLoaded', () => {
    console.log('[SleepGuard] Dashboard loaded.');

    const statSessions = document.querySelector('#stat-sessions .stat-value');
    const statAlerts = document.querySelector('#stat-alerts .stat-value');
    const statDuration = document.querySelector('#stat-duration .stat-value');
    const statSafety = document.querySelector('#stat-safety .stat-value');
    const sessionListEl = document.getElementById('session-list');

    const driversListContainer = document.getElementById('drivers-list-container');
    const registerModal = document.getElementById('register-driver-modal');
    const btnOpenRegister = document.getElementById('btn-open-register-modal');
    const btnCloseRegister = document.getElementById('btn-close-register-modal');
    const btnCancelRegister = document.getElementById('btn-cancel-register');
    const driverForm = document.getElementById('driver-register-form');
    const regMsg = document.getElementById('reg-msg');

    // ── Load Registered Drivers ───────────────────────────────────────────
    async function loadDrivers() {
        if (!driversListContainer) return;
        try {
            const res = await fetch('/api/drivers');
            if (!res.ok) return;
            const data = await res.json();
            const drivers = data.drivers || [];

            if (drivers.length === 0) {
                driversListContainer.innerHTML = `
                    <div class="empty-state" style="padding: 1.5rem; text-align: center; color: #94a3b8;">
                        <p>👤 No registered drivers found.</p>
                        <p style="font-size: 0.8rem; margin-top: 0.25rem;">Click '+ Register Driver' to create a face vector profile in FAISS.</p>
                    </div>
                `;
                return;
            }

            driversListContainer.innerHTML = '';
            drivers.forEach(driver => {
                const item = document.createElement('div');
                item.className = 'session-card';
                item.style.display = 'flex';
                item.style.alignItems = 'center';
                item.style.justifyContent = 'space-between';
                item.style.padding = '0.85rem 1rem';
                item.style.marginBottom = '0.5rem';
                item.style.background = 'rgba(30, 41, 59, 0.6)';
                item.style.borderRadius = '8px';
                item.style.border = '1px solid rgba(255, 255, 255, 0.08)';

                item.innerHTML = `
                    <div style="display: flex; align-items: center; gap: 0.75rem;">
                        <div style="font-size: 1.4rem; background: rgba(51, 65, 85, 0.8); padding: 6px 10px; border-radius: 8px;">👤</div>
                        <div>
                            <div style="font-weight: 600; font-size: 0.95rem; color: #f8fafc;">${driver.name} <span style="font-size:0.75rem; color:#38bdf8; font-weight:normal;">(ID #${driver.id})</span></div>
                            <div style="font-size: 0.8rem; color: #94a3b8;">📞 ${driver.phone} | Registered ${new Date(driver.created_at).toLocaleDateString()}</div>
                        </div>
                    </div>
                    <div>
                        <button class="btn btn-danger btn-sm btn-delete-driver" data-id="${driver.id}" style="padding: 4px 8px; font-size: 0.75rem;">Delete</button>
                    </div>
                `;
                driversListContainer.appendChild(item);
            });

            // Bind delete buttons
            document.querySelectorAll('.btn-delete-driver').forEach(btn => {
                btn.addEventListener('click', async (e) => {
                    const driverId = e.target.getAttribute('data-id');
                    if (confirm(`Are you sure you want to delete driver ID #${driverId}?`)) {
                        try {
                            const delRes = await fetch(`/api/drivers/${driverId}`, { method: 'DELETE' });
                            if (delRes.ok) {
                                loadDrivers();
                            }
                        } catch (err) {
                            console.error('Failed to delete driver:', err);
                        }
                    }
                });
            });

        } catch (e) {
            console.error('Error loading drivers:', e);
        }
    }

    const btnResetDrivers = document.getElementById('btn-reset-drivers');

    if (btnResetDrivers) {
        btnResetDrivers.addEventListener('click', async () => {
            if (confirm('Are you sure you want to reset all FAISS vector profiles?')) {
                try {
                    const res = await fetch('/api/drivers/reset', { method: 'POST' });
                    if (res.ok) {
                        alert('✓ FAISS vector index reset successfully.');
                        loadDrivers();
                    }
                } catch (err) {
                    console.error('Failed to reset vectors:', err);
                }
            }
        });
    }

    // ── Driver Registration Modal Handlers ─────────────────────────────────
    if (btnOpenRegister) {
        btnOpenRegister.addEventListener('click', () => {
            registerModal.style.display = 'flex';
            regMsg.style.display = 'none';
            driverForm.reset();
        });
    }

    function closeModal() {
        if (registerModal) registerModal.style.display = 'none';
    }

    if (btnCloseRegister) btnCloseRegister.addEventListener('click', closeModal);
    if (btnCancelRegister) btnCancelRegister.addEventListener('click', closeModal);

    if (driverForm) {
        driverForm.addEventListener('click', (e) => e.stopPropagation());
        if (registerModal) {
            registerModal.addEventListener('click', closeModal);
        }

        driverForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const name = document.getElementById('reg-driver-name').value.trim();
            const phone = document.getElementById('reg-driver-phone').value.trim();

            if (!name || !phone) return;

            regMsg.style.display = 'block';
            regMsg.style.background = 'rgba(59, 130, 246, 0.15)';
            regMsg.style.color = '#60a5fa';
            regMsg.style.border = '1px solid rgba(59, 130, 246, 0.3)';
            regMsg.textContent = '👀 Look at the camera... Capturing 20 face samples...';

            let count = 1;
            const progressInterval = setInterval(() => {
                if (count <= 20) {
                    regMsg.textContent = `📷 Capturing face samples... (${count} / 20)`;
                    count += 3;
                } else {
                    regMsg.textContent = `🧬 Generating face embeddings & indexing into FAISS...`;
                    clearInterval(progressInterval);
                }
            }, 250);

            try {
                const res = await fetch('/api/drivers/register', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ name, phone }),
                });

                clearInterval(progressInterval);
                const data = await res.json();
                if (res.ok && data.status === 'success') {
                    regMsg.style.background = 'rgba(16, 185, 129, 0.15)';
                    regMsg.style.color = '#34d399';
                    regMsg.style.border = '1px solid rgba(16, 185, 129, 0.3)';
                    regMsg.textContent = `✓ Driver '${name}' registered with ${data.embeddings_added || 20} face embeddings in FAISS!`;
                    setTimeout(() => {
                        closeModal();
                        loadDrivers();
                    }, 1500);
                } else {
                    regMsg.style.background = 'rgba(239, 68, 68, 0.15)';
                    regMsg.style.color = '#f87171';
                    regMsg.style.border = '1px solid rgba(239, 68, 68, 0.3)';
                    regMsg.textContent = `❌ ${data.message || 'Registration failed.'}`;
                }
            } catch (err) {
                console.error('Registration exception:', err);
                regMsg.style.background = 'rgba(239, 68, 68, 0.15)';
                regMsg.style.color = '#f87171';
                regMsg.textContent = '❌ Server connection failed.';
            }
        });
    }

    // ── Load Past Sessions ────────────────────────────────────────────────
    async function loadDashboardData() {
        try {
            const res = await fetch('/api/sessions');
            if (!res.ok) return;
            const data = await res.json();
            const sessions = data.sessions || [];

            if (sessions.length === 0) {
                return;
            }

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
                const driverName = sess.driver_name || 'Unknown Driver';

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
                            👤 Driver: <strong style="color:#f8fafc;">${driverName}</strong> | ⏱️ ${durMins} mins | 🚨 ${alerts} alerts | 🥱 ${sess.yawn_count || 0} yawns
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

    loadDrivers();
    loadDashboardData();
});
