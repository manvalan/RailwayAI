let accessToken = localStorage.getItem('access_token');
let trainingChart = null;
let currentScenarioPath = null;
const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
const wsUrl = `${protocol}//${window.location.host}/ws/monitoring`;
let ws = new WebSocket(wsUrl);

document.addEventListener('DOMContentLoaded', () => {
    if (accessToken) {
        document.getElementById('auth-overlay').classList.add('hidden');
        initDashboard();
    }

    // Sidebar Navigation (Tradotto in Italiano)
    document.getElementById('nav-monitoring').addEventListener('click', () => switchView('monitoring'));
    document.getElementById('nav-optimization').addEventListener('click', () => switchView('optimization'));
    document.getElementById('nav-ai-management').addEventListener('click', () => {
        switchView('ai-management');
        if (window.refreshAIManagementData) window.refreshAIManagementData();
    });
    document.getElementById('nav-users').addEventListener('click', () => {
        switchView('users');
        fetchUsers();
    });
    document.getElementById('nav-smtp').addEventListener('click', () => {
        switchView('smtp');
        fetchSMTPConfig();
    });
    document.getElementById('nav-settings').addEventListener('click', () => switchView('settings'));
    document.getElementById('nav-topology')?.addEventListener('click', () => {
        switchView('topology');
        if (window.loadTopology) window.loadTopology();
    });
    document.getElementById('nav-api-keys')?.addEventListener('click', () => switchView('api-keys'));

    // Sidebar Logout - Fixed and robust
    const logoutBtn = document.getElementById('nav-logout');
    if (logoutBtn) {
        logoutBtn.addEventListener('click', () => {
            console.log("🔒 System sign-out initiated...");
            localStorage.removeItem('access_token');
            sessionStorage.clear();
            window.location.href = '/';
        });
    }

    // Actions
    document.getElementById('start-train-btn')?.addEventListener('click', () => {
        if (window.startScenarioGeneration) window.startScenarioGeneration();
    });
    document.getElementById('optimize-btn')?.addEventListener('click', triggerOptimization);
    document.getElementById('admin-add-user-btn')?.addEventListener('click', addUser);

    // Settings Actions
    document.getElementById('change-pass-btn')?.addEventListener('click', changePassword);
    document.getElementById('reactivate-btn')?.addEventListener('click', reactivateAccount);
    document.getElementById('delete-me-btn')?.addEventListener('click', deleteMeAccount);

    // SMTP Actions
    document.getElementById('save-smtp-btn')?.addEventListener('click', saveSMTPConfig);
    document.getElementById('test-smtp-btn')?.addEventListener('click', testSMTP);

    // AI Management specific actions are handled in ai-management.js
    // API Keys
    document.getElementById('generate-key-btn')?.addEventListener('click', generateApiKey);
    document.getElementById('copy-key-btn')?.addEventListener('click', () => {
        const keyInput = document.getElementById('generated-key');
        keyInput.select();
        document.execCommand('copy');
        alert('API Key copied to clipboard!');
    });

    // Login button
    document.getElementById('login-btn')?.addEventListener('click', login);

    // Allow login with Enter key
    const authFields = ['username', 'password'];
    authFields.forEach(id => {
        document.getElementById(id)?.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') login();
        });
    });
});

async function checkUserRole() {
    if (!accessToken) return;
    try {
        const response = await fetch('/api/v1/users/me', {
            headers: {
                'Authorization': `Bearer ${accessToken}`,
                'X-API-Key': accessToken
            }
        });

        if (response.ok) {
            const user = await response.json();
            window.isUserAdmin = (user.privilege === 'admin');
            window.isUserViewer = (user.privilege === 'viewer' || user.privilege === 'admin');
            console.log(`👤 Identity verified: ${user.username} (Role: ${user.privilege})`);

            document.querySelectorAll('.admin-only').forEach(el => {
                el.style.display = window.isUserAdmin ? '' : 'none';
            });
            document.querySelectorAll('.viewer-plus').forEach(el => {
                el.style.display = window.isUserViewer ? '' : 'none';
            });
        } else if (response.status === 401) {
            console.warn("⚠️ Session expired. Forcing re-auth.");
            localStorage.removeItem('access_token');
            location.reload();
        }
    } catch (error) {
        console.error('Role Verification Failure:', error);
    }
}

async function generateApiKey() {
    const name = document.getElementById('api-key-name').value || 'Default Key';
    const btn = document.getElementById('generate-key-btn');

    btn.disabled = true;
    btn.textContent = 'Generating...';

    try {
        const formData = new FormData();
        formData.append('name', name);

        const response = await fetch('/api/v1/users/api-key', {
            method: 'POST',
            headers: { 'X-API-Key': accessToken }, // Or Bearer token if using JWT
            body: formData
        });

        if (response.ok) {
            const data = await response.json();
            document.getElementById('generated-key').value = data.api_key;
            document.getElementById('api-key-result').style.display = 'block';
        } else {
            alert('Error generating API key');
        }
    } catch (error) {
        console.error('Error generating API key:', error);
        alert('Connection error');
    } finally {
        btn.disabled = false;
        btn.textContent = 'Generate New Key';
    }
}


async function login() {
    const user = document.getElementById('username').value;
    const pass = document.getElementById('password').value;
    const errorEl = document.getElementById('auth-error');

    const formData = new FormData();
    formData.append('username', user);
    formData.append('password', pass);

    try {
        const response = await fetch('/token', {
            method: 'POST',
            body: formData
        });

        if (response.ok) {
            const data = await response.json();
            accessToken = data.access_token;
            localStorage.setItem('access_token', accessToken);
            document.getElementById('auth-overlay').classList.add('hidden');
            initDashboard();
        } else {
            errorEl.style.display = 'block';
            errorEl.textContent = "Nome utente o password non validi";
        }
    } catch (err) {
        console.error('Login error:', err);
        errorEl.style.display = 'block';
        errorEl.textContent = "Connection lost. Try again.";
    }
}

function initDashboard() {
    console.log("🚀 Initializing Operational Intelligence Dashboard...");
    try {
        initChart();
        connectWebSocket();
        fetchStats();
        checkUserRole();
    } catch (err) {
        console.error("Dashboard Init Error:", err);
    }
}

function switchView(view) {
    const viewMon = document.getElementById('view-monitoring');
    const viewTrain = document.getElementById('view-training');
    const viewOpt = document.getElementById('view-optimization');
    const viewUsers = document.getElementById('view-users');
    const viewSMTP = document.getElementById('view-smtp');
    const viewSettings = document.getElementById('view-settings');
    const viewApiKeys = document.getElementById('view-api-keys');
    const viewAI = document.getElementById('view-ai-management');
    const viewTopology = document.getElementById('view-topology');

    const navMon = document.getElementById('nav-monitoring');
    const navTrain = document.getElementById('nav-training');
    const navOpt = document.getElementById('nav-optimization');
    const navUsers = document.getElementById('nav-users');
    const navSMTP = document.getElementById('nav-smtp');
    const navSettings = document.getElementById('nav-settings');
    const navApiKeys = document.getElementById('nav-api-keys');
    const navAI = document.getElementById('nav-ai-management');
    const navTopology = document.getElementById('nav-topology');

    // Reset visibility
    [viewMon, viewOpt, viewUsers, viewSMTP, viewSettings, viewApiKeys, viewAI, viewTopology].forEach(v => {
        if (v) v.classList.add('hidden');
    });
    [navMon, navOpt, navUsers, navSMTP, navSettings, navApiKeys, navAI, navTopology].forEach(n => {
        if (n) n.classList.remove('active');
    });

    if (view === 'monitoring') {
        viewMon.classList.remove('hidden');
        navMon.classList.add('active');
        document.getElementById('page-title').textContent = "Operational Intelligence";
        document.getElementById('page-desc').textContent = "Live monitoring and neural predictive dashboard.";
        if (trainingChart) {
            trainingChart.resize();
            trainingChart.update();
        }
    } else if (view === 'optimization') {
        viewOpt.classList.remove('hidden');
        navOpt.classList.add('active');
        document.getElementById('page-title').textContent = "Neural Optimizer";
        document.getElementById('page-desc').textContent = "C++ Core algorithm execution panel.";
    } else if (view === 'users') {
        viewUsers.classList.remove('hidden');
        navUsers.classList.add('active');
        document.getElementById('page-title').textContent = "Operator Registry";
        document.getElementById('page-desc').textContent = "System access and privilege management.";
    } else if (view === 'smtp') {
        viewSMTP.classList.remove('hidden');
        navSMTP.classList.add('active');
        document.getElementById('page-title').textContent = "Comms Stack";
        document.getElementById('page-desc').textContent = "SMTP Gateway configuration for automated mail.";
    } else if (view === 'settings') {
        viewSettings.classList.remove('hidden');
        navSettings.classList.add('active');
        document.getElementById('page-title').textContent = "Security Protocols";
        document.getElementById('page-desc').textContent = "User credentials and authentication settings.";
    } else if (view === 'api-keys') {
        viewApiKeys.classList.remove('hidden');
        navApiKeys.classList.add('active');
        document.getElementById('page-title').textContent = "Neural Bridge Keys";
        document.getElementById('page-desc').textContent = "Generate private tokens for external API integration.";
    } else if (view === 'ai-management') {
        if (viewAI) viewAI.classList.remove('hidden');
        if (navAI) navAI.classList.add('active');
        document.getElementById('page-title').textContent = "AI Intelligence";
        document.getElementById('page-desc').textContent = "MARL training control and model weights management.";
    } else if (view === 'topology') {
        if (viewTopology) viewTopology.classList.remove('hidden');
        if (navTopology) navTopology.classList.add('active');
        document.getElementById('page-title').textContent = "Infrastructure Map";
        document.getElementById('page-desc').textContent = "Spatial topology of the railway network.";
        if (window.loadTopology) window.loadTopology();
    }
}

async function changePassword() {
    const newPass = document.getElementById('new-password').value;
    const msgEl = document.getElementById('settings-status-msg');

    if (newPass.length < 6) {
        alert("Password must be at least 6 characters.");
        return;
    }

    try {
        const response = await fetch('/api/v1/user/change-password', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-API-Key': accessToken
            },
            body: JSON.stringify({ new_password: newPass })
        });

        if (response.ok) {
            msgEl.textContent = "✅ Password updated successfully!";
            msgEl.style.color = "var(--success)";
            document.getElementById('new-password').value = "";
        } else {
            const error = await response.json();
            msgEl.textContent = `❌ Error: ${error.detail}`;
            msgEl.style.color = "var(--accent)";
        }
    } catch (err) {
        msgEl.textContent = "❌ Connection error.";
        msgEl.style.color = "var(--accent)";
    }
}

async function reactivateAccount() {
    const username = document.getElementById('reactivate-username').value;
    const msgEl = document.getElementById('settings-status-msg');

    if (!username) {
        alert("Enter the username to reactivate.");
        return;
    }

    try {
        const response = await fetch(`/api/v1/admin/reactivate?username=${encodeURIComponent(username)}`, {
            method: 'POST',
            headers: {
                'X-API-Key': accessToken
            }
        });

        if (response.ok) {
            msgEl.textContent = `✅ User ${username} reactivated!`;
            msgEl.style.color = "var(--success)";
            document.getElementById('reactivate-username').value = "";
        } else {
            const error = await response.json();
            msgEl.textContent = `❌ Error: ${error.detail}`;
            msgEl.style.color = "var(--accent)";
        }
    } catch (err) {
        msgEl.textContent = "❌ Connection error.";
        msgEl.style.color = "var(--accent)";
    }
}

async function deleteMeAccount() {
    if (!confirm("⚠️ ARE YOU SURE? This action is irreversible and your account will be permanently deleted.")) return;

    try {
        const response = await fetch('/api/v1/user/me', {
            method: 'DELETE',
            headers: { 'X-API-Key': accessToken }
        });

        if (response.ok) {
            alert("Account deleted successfully. Goodbye.");
            localStorage.removeItem('access_token');
            location.reload();
        } else {
            const error = await response.json();
            alert(`❌ Error: ${error.detail}`);
        }
    } catch (err) {
        alert("❌ Connection error.");
    }
}

async function startScenarioGeneration() {
    const area = document.getElementById('train-area').value;
    const msgEl = document.getElementById('training-status-msg');
    const btn = document.getElementById('start-train-btn');

    if (!area) {
        alert("Inserisci un'area o regione!");
        return;
    }

    btn.disabled = true;
    btn.textContent = "GENERAZIONE...";
    msgEl.textContent = "⚙️ Inizializzazione generazione scenario...";
    msgEl.style.color = "var(--primary)";

    try {
        const response = await fetch('/api/v1/scenario/generate', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-API-Key': accessToken
            },
            body: JSON.stringify({ area: area })
        });

        if (response.ok) {
            addLog(`Richiesta inviata per: ${area}`, 'info');
            document.getElementById('train-area').value = "";
        } else {
            btn.disabled = false;
            btn.textContent = "Genera & Addestra";
            const error = await response.json().catch(() => ({ detail: "Errore sconosciuto" }));
            const status = response.status;
            addLog(`Errore ${status}: ${error.detail || JSON.stringify(error)}`, 'error');
            msgEl.textContent = `❌ Errore ${status}: ${error.detail || "Controlla i log"}`;
            msgEl.style.color = "var(--accent)";
        }
    } catch (err) {
        btn.disabled = false;
        btn.textContent = "Genera & Addestra";
        addLog(`Errore di rete: ${err}`, 'error');
    }
}

async function triggerMarlTraining(scenarioPath) {
    const episodes = document.getElementById('train-episodes').value;
    const lr = document.getElementById('train-lr').value;
    const curriculum = document.getElementById('train-curriculum')?.checked || false;
    const msgEl = document.getElementById('training-status-msg');

    msgEl.textContent = "🚀 Starting MARL training...";
    msgEl.style.color = "var(--success)";

    try {
        const response = await fetch('/api/v1/train', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-API-Key': accessToken
            },
            body: JSON.stringify({
                scenario_path: scenarioPath,
                episodes: parseInt(episodes),
                lr: parseFloat(lr),
                use_curriculum: curriculum
            })
        });

        if (response.ok) {
            addLog(`Training started on: ${scenarioPath}`, 'success');
            // Switch back to monitoring to see the progress
            setTimeout(() => switchView('monitoring'), 2000);
        } else {
            const error = await response.json();
            addLog(`Training start failure: ${error.detail}`, 'error');
            msgEl.textContent = "❌ Training start failed.";
            msgEl.style.color = "var(--accent)";
        }
    } catch (err) {
        addLog(`Network error: ${err}`, 'error');
    }
}

function initChart() {
    const ctx = document.getElementById('training-chart').getContext('2d');
    trainingChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: [],
            datasets: [{
                label: 'Episode Reward',
                data: [],
                borderColor: '#4f46e5',
                tension: 0.4,
                yAxisID: 'y'
            }, {
                label: 'Conflicts',
                data: [],
                borderColor: '#f43f5e',
                tension: 0.4,
                yAxisID: 'y1'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: { type: 'linear', display: true, position: 'left', grid: { color: 'rgba(255,255,255,0.05)' } },
                y1: { type: 'linear', display: true, position: 'right', grid: { drawOnChartArea: false } }
            },
            plugins: {
                legend: { labels: { color: '#f8fafc' } }
            }
        }
    });
}

function connectWebSocket() {
    ws.onopen = () => {
        const placeholder = document.getElementById('event-logs').querySelector('.log-entry');
        if (placeholder && placeholder.textContent.includes('waiting')) {
            placeholder.remove();
        }
        addLog('Link neurale stabilito.', 'success');
    };

    ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        handleWsMessage(data);
    };

    ws.onerror = (err) => {
        addLog('Errore link neurale. Controlla firewall/proxy.', 'error');
    };

    ws.onclose = () => {
        addLog('Link neurale disconnesso. Riconnessione in 5s...', 'warning');
        setTimeout(() => {
            ws = new WebSocket(wsUrl);
            connectWebSocket();
        }, 5000);
    };
}

function handleWsMessage(data) {
    if (data.type === 'ping') return; // Silence heartbeat

    if (data.type === 'training_update') {
        updateChart(data.episode, data.reward, data.conflicts);
        // Log every 10 episodes to UI log to keep it readable
        if (data.episode % 10 === 0) {
            addLog(`Episodio ${data.episode}: Ricompensa ${data.reward.toFixed(2)}, Conflitti: ${data.conflicts}`, 'success');
        }
    } else if (data.type === 'state_update') {
        if (data.train_count !== undefined) document.getElementById('train-count').textContent = data.train_count;
        if (data.conflicts !== undefined) document.getElementById('conflict-count').textContent = data.conflicts;
        if (data.efficiency !== undefined) document.getElementById('efficiency').textContent = (data.efficiency || 0).toFixed(1) + '%';
    } else if (data.type === 'log') {
        addLog(data.message, data.level);

        // If scenario generated successfully, auto-trigger training
        if (data.level === 'success' && data.scenario_path) {
            // Restore button
            const btn = document.getElementById('start-train-btn');
            if (btn) {
                btn.disabled = false;
                btn.textContent = "Genera & Addestra";
            }
            // Refresh scenarios list if we are in AI management view
            if (window.refreshAIManagementData) window.refreshAIManagementData();

            triggerMarlTraining(data.scenario_path);
        } else if (data.level === 'error') {
            const btn = document.getElementById('start-train-btn');
            if (btn) {
                btn.disabled = false;
                btn.textContent = "Genera & Addestra";
            }
        }
    }
}

function updateChart(episode, reward, conflicts) {
    if (!trainingChart) return;
    trainingChart.data.labels.push(episode);
    trainingChart.data.datasets[0].data.push(reward);
    trainingChart.data.datasets[1].data.push(conflicts);

    if (trainingChart.data.labels.length > 50) {
        trainingChart.data.labels.shift();
        trainingChart.data.datasets[0].data.shift();
        trainingChart.data.datasets[1].data.shift();
    }
    trainingChart.update('none');
}

async function fetchUsers() {
    try {
        const response = await fetch('/api/v1/admin/users', {
            headers: { 'X-API-Key': accessToken }
        });
        if (response.ok) {
            const users = await response.json();
            const body = document.getElementById('user-table-body');
            body.innerHTML = '';

            // Count by privilege
            const counts = { admin: 0, normal: 0, viewer: 0, guest: 0 };
            users.forEach(u => counts[u.privilege || 'normal']++);

            document.getElementById('total-users-count').textContent = users.length;
            document.getElementById('admin-count').textContent = counts.admin;
            document.getElementById('normal-count').textContent = counts.normal;
            document.getElementById('viewer-count').textContent = counts.viewer;
            document.getElementById('guest-count').textContent = counts.guest;

            users.forEach(u => {
                const tr = document.createElement('tr');
                tr.style.borderBottom = "1px solid rgba(255,255,255,0.05)";

                const privilegeColors = {
                    admin: 'var(--accent)',
                    normal: 'var(--primary)',
                    viewer: 'var(--success)',
                    guest: 'var(--text-secondary)'
                };

                const createdDate = u.created_at ? new Date(u.created_at).toLocaleDateString('it-IT') : 'N/A';

                tr.innerHTML = `
                    <td style="padding: 1rem; font-weight: 600;">${u.username}</td>
                    <td style="padding: 1rem;">
                        <select onchange="changeUserPrivilege('${u.username}', this.value)" 
                                style="background: rgba(255,255,255,0.05); border: 1px solid var(--glass-border); padding: 0.4rem; border-radius: 6px; color: ${privilegeColors[u.privilege || 'normal']}; font-weight: 600; font-size: 0.85rem; ${u.username === 'admin' ? 'pointer-events:none; opacity:0.5;' : ''}">
                            <option value="guest" ${u.privilege === 'guest' ? 'selected' : ''}>Guest</option>
                            <option value="viewer" ${u.privilege === 'viewer' ? 'selected' : ''}>Viewer</option>
                            <option value="normal" ${(u.privilege === 'normal' || !u.privilege) ? 'selected' : ''}>Normal</option>
                            <option value="admin" ${u.privilege === 'admin' ? 'selected' : ''}>Admin</option>
                        </select>
                    </td>
                    <td style="padding: 1rem;">
                        <span style="color: ${u.is_active ? 'var(--success)' : 'var(--accent)'}; font-weight: 600; font-size: 0.85rem;">
                            ${u.is_active ? '✓ Attivo' : '✗ Bloccato'}
                        </span>
                        <button onclick="changeUserStatus('${u.username}', ${!u.is_active})" 
                                style="background: rgba(255,255,255,0.05); padding: 0.3rem 0.7rem; font-size: 0.7rem; margin-left: 0.5rem; border-radius: 6px; ${u.username === 'admin' ? 'display:none' : ''}">
                            ${u.is_active ? 'Blocca' : 'Sblocca'}
                        </button>
                    </td>
                    <td style="padding: 1rem; color: var(--text-secondary); font-size: 0.85rem;">${createdDate}</td>
                    <td style="padding: 1rem; text-align: right;">
                        <button onclick="deleteUser('${u.username}')" 
                                style="background: var(--accent); padding: 0.4rem 0.8rem; font-size: 0.75rem; border-radius: 6px; ${u.username === 'admin' ? 'display:none' : ''}">
                            🗑️ Elimina
                        </button>
                    </td>
                `;
                body.appendChild(tr);
            });
        }
    } catch (err) {
        console.error("Failed to fetch users:", err);
    }
}

async function changeUserStatus(username, newStatus) {
    if (!confirm(`Change status of ${username} to ${newStatus ? 'Active' : 'Locked'}?`)) return;

    try {
        const response = await fetch(`/api/v1/admin/users/${username}/status`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-API-Key': accessToken
            },
            body: JSON.stringify({ is_active: newStatus })
        });

        if (response.ok) {
            fetchUsers();
            addLog(`User ${username} ${newStatus ? 'activated' : 'suspended'}.`, 'info');
        } else {
            const err = await response.json();
            alert(`Error: ${err.detail}`);
        }
    } catch (err) {
        alert("Connection failure.");
    }
}

async function addUser() {
    const user = document.getElementById('admin-new-username').value;
    const pass = document.getElementById('admin-new-password').value;
    const privilege = document.getElementById('admin-new-privilege').value;

    if (!user || pass.length < 6) {
        alert("Inserisci username e password (min 6 caratteri).");
        return;
    }

    try {
        const response = await fetch('/api/v1/admin/users', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-API-Key': accessToken
            },
            body: JSON.stringify({ username: user, password: pass, privilege: privilege })
        });

        if (response.ok) {
            document.getElementById('admin-new-username').value = '';
            document.getElementById('admin-new-password').value = '';
            document.getElementById('admin-new-privilege').value = 'normal';
            fetchUsers();
            addLog(`Nuovo utente creato: ${user} (${privilege})`, 'success');
        } else {
            const err = await response.json();
            alert(`Errore: ${err.detail}`);
        }
    } catch (err) {
        alert("Errore di connessione.");
    }
}

async function changeUserPrivilege(username, newPrivilege) {
    if (username === 'admin') return;

    try {
        const response = await fetch(`/api/v1/admin/users/${username}/privilege`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-API-Key': accessToken
            },
            body: JSON.stringify({ privilege: newPrivilege })
        });

        if (response.ok) {
            fetchUsers();
            addLog(`Privilegio di ${username} cambiato a: ${newPrivilege}`, 'info');
        } else {
            const err = await response.json();
            alert(`Errore: ${err.detail}`);
            fetchUsers(); // Reload to reset select
        }
    } catch (err) {
        alert("Errore di connessione.");
        fetchUsers();
    }
}

async function deleteUser(username) {
    if (!confirm(`Revoke access for operator: ${username}?`)) return;

    try {
        const response = await fetch(`/api/v1/admin/users/${username}`, {
            method: 'DELETE',
            headers: { 'X-API-Key': accessToken }
        });

        if (response.ok) {
            fetchUsers();
        } else {
            const err = await response.json();
            alert(`Error: ${err.detail}`);
        }
    } catch (err) {
        alert("Connection failure.");
    }
}

async function triggerOptimization() {
    const path = document.getElementById('optimize-scenario-path').value;
    const msgEl = document.getElementById('optimize-status-msg');

    if (!path) {
        alert("Enter scenario path.");
        return;
    }

    msgEl.textContent = "⚙️ Executing optimization sequence...";
    msgEl.style.color = "var(--primary)";

    try {
        const response = await fetch('/api/v1/optimize', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-API-Key': accessToken
            },
            body: JSON.stringify({ scenario_path: path })
        });

        if (response.ok) {
            msgEl.textContent = "✅ Optimization complete!";
            msgEl.style.color = "var(--success)";
            addLog(`Optimization executed for ${path}`, 'success');
        } else {
            const err = await response.json();
            msgEl.textContent = `❌ Error: ${err.detail}`;
            msgEl.style.color = "var(--accent)";
        }
    } catch (err) {
        msgEl.textContent = "❌ Connection error.";
        msgEl.style.color = "var(--accent)";
    }
}

function addLog(message, level = 'info') {
    const container = document.getElementById('event-logs');
    if (!container) return;

    const entry = document.createElement('div');
    entry.className = `log-entry ${level}`;

    const now = new Date().toLocaleTimeString([], { hour12: false });
    entry.innerHTML = `<span class="log-timestamp">${now}</span> ${message}`;

    container.appendChild(entry);
    container.scrollTop = container.scrollHeight;

    if (container.children.length > 50) {
        container.removeChild(container.firstChild);
    }
}

async function fetchStats() {
    try {
        const res = await fetch('/api/v1/metrics', {
            headers: { 'X-API-Key': accessToken }
        });
        if (res.ok) {
            const data = await res.json();
        }
    } catch (err) { }
}

async function fetchSMTPConfig() {
    try {
        const response = await fetch('/api/v1/admin/smtp', {
            headers: { 'X-API-Key': accessToken }
        });
        if (response.ok) {
            const data = await response.json();
            document.getElementById('smtp-host').value = data.host || '';
            document.getElementById('smtp-port').value = data.port || 587;
            document.getElementById('smtp-user').value = data.username || '';
            document.getElementById('smtp-sender').value = data.sender_email || '';
            document.getElementById('smtp-tls').checked = data.use_tls !== 0;
            document.getElementById('smtp-active').checked = data.is_active !== 0;
            document.getElementById('smtp-pass').value = '';
        }
    } catch (err) {
        console.error("Failed to fetch SMTP config:", err);
    }
}

async function saveSMTPConfig() {
    const msgEl = document.getElementById('smtp-status-msg');
    const config = {
        host: document.getElementById('smtp-host').value,
        port: parseInt(document.getElementById('smtp-port').value),
        username: document.getElementById('smtp-user').value,
        sender_email: document.getElementById('smtp-sender').value,
        use_tls: document.getElementById('smtp-tls').checked,
        is_active: document.getElementById('smtp-active').checked
    };

    const pass = document.getElementById('smtp-pass').value;
    if (pass) config.password = pass;

    msgEl.textContent = "💾 Synchronizing gateway config...";
    msgEl.style.color = "var(--primary)";

    try {
        const response = await fetch('/api/v1/admin/smtp', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-API-Key': accessToken
            },
            body: JSON.stringify(config)
        });

        if (response.ok) {
            msgEl.textContent = "✅ Gateway configuration synced!";
            msgEl.style.color = "var(--success)";
        } else {
            const err = await response.json();
            msgEl.textContent = `❌ Sync failure: ${err.detail}`;
            msgEl.style.color = "var(--accent)";
        }
    } catch (err) {
        msgEl.textContent = "❌ Connection failure.";
    }
}

async function testSMTP() {
    const email = document.getElementById('smtp-test-email').value;
    const msgEl = document.getElementById('smtp-status-msg');

    if (!email) {
        alert("Target required for probe.");
        return;
    }

    msgEl.textContent = "📧 Firing probe pulse...";
    msgEl.style.color = "var(--primary)";

    try {
        const response = await fetch('/api/v1/admin/smtp/test', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-API-Key': accessToken
            },
            body: JSON.stringify({ email: email })
        });

        if (response.ok) {
            msgEl.textContent = "✅ Probe delivered. Check target inbox.";
            msgEl.style.color = "var(--success)";
        } else {
            const err = await response.json();
            msgEl.textContent = `❌ Probe failure: ${err.detail}`;
            msgEl.style.color = "var(--accent)";
        }
    } catch (err) {
        msgEl.textContent = "❌ Connection breach.";
    }
}
