let accessToken = localStorage.getItem('access_token');
let trainingChart = null;
let currentScenarioPath = null;

document.addEventListener('DOMContentLoaded', () => {
    if (accessToken) {
        document.getElementById('auth-overlay').classList.add('hidden');
        initDashboard();
    }

    document.getElementById('login-btn').addEventListener('click', login);

    // Sidebar Navigation
    document.getElementById('nav-monitoring').addEventListener('click', () => switchView('monitoring'));
    document.getElementById('nav-training').addEventListener('click', () => switchView('training'));
    document.getElementById('nav-settings').addEventListener('click', () => switchView('settings'));

    document.getElementById('nav-logout').addEventListener('click', () => {
        localStorage.removeItem('access_token');
        location.reload();
    });

    // Training Control Actions
    document.getElementById('start-train-btn').addEventListener('click', startScenarioGeneration);

    // Settings Actions
    document.getElementById('change-pass-btn').addEventListener('click', changePassword);
    document.getElementById('reactivate-btn').addEventListener('click', reactivateAccount);
});

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
        }
    } catch (err) {
        console.error('Login error:', err);
        errorEl.style.display = 'block';
    }
}

function initDashboard() {
    initChart();
    connectWebSocket();
    fetchStats();
}

function switchView(view) {
    const viewMon = document.getElementById('view-monitoring');
    const viewTrain = document.getElementById('view-training');
    const viewSettings = document.getElementById('view-settings');

    const navMon = document.getElementById('nav-monitoring');
    const navTrain = document.getElementById('nav-training');
    const navSettings = document.getElementById('nav-settings');

    // Reset visibility
    [viewMon, viewTrain, viewSettings].forEach(v => v.classList.add('hidden'));
    [navMon, navTrain, navSettings].forEach(n => n.classList.remove('active'));

    if (view === 'monitoring') {
        viewMon.classList.remove('hidden');
        navMon.classList.add('active');
    } else if (view === 'training') {
        viewTrain.classList.remove('hidden');
        navTrain.classList.add('active');
    } else if (view === 'settings') {
        viewSettings.classList.remove('hidden');
        navSettings.classList.add('active');
    }
}

async function changePassword() {
    const newPass = document.getElementById('new-password').value;
    const msgEl = document.getElementById('settings-status-msg');

    if (newPass.length < 6) {
        alert("La password deve essere di almeno 6 caratteri.");
        return;
    }

    try {
        const response = await fetch('/api/v1/user/change-password', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${accessToken}`
            },
            body: JSON.stringify({ new_password: newPass })
        });

        if (response.ok) {
            msgEl.textContent = "✅ Password aggiornata con successo!";
            msgEl.style.color = "var(--success)";
            document.getElementById('new-password').value = "";
        } else {
            const error = await response.json();
            msgEl.textContent = `❌ Errore: ${error.detail}`;
            msgEl.style.color = "var(--accent)";
        }
    } catch (err) {
        msgEl.textContent = "❌ Errore di connessione.";
        msgEl.style.color = "var(--accent)";
    }
}

async function reactivateAccount() {
    const username = document.getElementById('reactivate-username').value;
    const msgEl = document.getElementById('settings-status-msg');

    if (!username) {
        alert("Inserisci lo username da riattivare.");
        return;
    }

    try {
        const response = await fetch(`/api/v1/admin/reactivate?username=${encodeURIComponent(username)}`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${accessToken}`
            }
        });

        if (response.ok) {
            msgEl.textContent = `✅ Utente ${username} riattivato!`;
            msgEl.style.color = "var(--success)";
            document.getElementById('reactivate-username').value = "";
        } else {
            const error = await response.json();
            msgEl.textContent = `❌ Errore: ${error.detail}`;
            msgEl.style.color = "var(--accent)";
        }
    } catch (err) {
        msgEl.textContent = "❌ Errore di connessione.";
        msgEl.style.color = "var(--accent)";
    }
}

async function startScenarioGeneration() {
    const area = document.getElementById('train-area').value;
    const msgEl = document.getElementById('training-status-msg');

    if (!area) {
        alert("Inserisci un'area o regione!");
        return;
    }

    msgEl.textContent = "⚙️ Inizializzazione generazione scenario...";
    msgEl.style.color = "var(--primary)";

    try {
        const response = await fetch('/api/v1/scenario/generate', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${accessToken}`
            },
            body: JSON.stringify({ area: area })
        });

        if (response.ok) {
            addLog(`Richiesta generazione inviata per l'area: ${area}`, 'info');
        } else {
            const error = await response.json().catch(() => ({ detail: "Errore sconosciuto" }));
            const status = response.status;
            addLog(`Errore ${status}: ${error.detail || JSON.stringify(error)}`, 'error');
            msgEl.textContent = `❌ Errore ${status}: ${error.detail || "Verifica i log"}`;
            msgEl.style.color = "var(--accent)";
        }
    } catch (err) {
        addLog(`Errore di rete: ${err}`, 'error');
    }
}

async function triggerMarlTraining(scenarioPath) {
    const episodes = document.getElementById('train-episodes').value;
    const lr = document.getElementById('train-lr').value;
    const msgEl = document.getElementById('training-status-msg');

    msgEl.textContent = "🚀 Avvio addestramento MARL...";
    msgEl.style.color = "var(--success)";

    try {
        const response = await fetch('/api/v1/train', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${accessToken}`
            },
            body: JSON.stringify({
                scenario_path: scenarioPath,
                episodes: parseInt(episodes),
                lr: parseFloat(lr)
            })
        });

        if (response.ok) {
            addLog(`Addestramento avviato su: ${scenarioPath}`, 'success');
            // Switch back to monitoring to see the progress
            setTimeout(() => switchView('monitoring'), 2000);
        } else {
            const error = await response.json();
            addLog(`Errore avvio training: ${error.detail}`, 'error');
            msgEl.textContent = "❌ Errore avvio training.";
            msgEl.style.color = "var(--accent)";
        }
    } catch (err) {
        addLog(`Errore di rete: ${err}`, 'error');
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
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const ws = new WebSocket(`${protocol}//${window.location.host}/ws/monitoring`);

    ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        handleWsMessage(data);
    };

    ws.onclose = () => {
        addLog('Connessione WebSocket persa. Tentativo di riconnessione...', 'warning');
        setTimeout(connectWebSocket, 5000);
    };
}

function handleWsMessage(data) {
    if (data.type === 'training_update') {
        updateChart(data.episode, data.reward, data.conflicts);
        addLog(`Episode ${data.episode}: Reward ${data.reward.toFixed(2)}, Conflicts: ${data.conflicts}`, 'success');
    } else if (data.type === 'state_update') {
        if (data.train_count !== undefined) document.getElementById('train-count').textContent = data.train_count;
        if (data.conflicts !== undefined) document.getElementById('conflict-count').textContent = data.conflicts;
        if (data.efficiency !== undefined) document.getElementById('efficiency').textContent = (data.efficiency || 0).toFixed(1) + '%';
    } else if (data.type === 'log') {
        addLog(data.message, data.level);

        // Se lo scenario è stato generato con successo, avvia il training automaticamente
        if (data.level === 'success' && data.scenario_path) {
            triggerMarlTraining(data.scenario_path);
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

function addLog(message, level = 'info') {
    const container = document.getElementById('event-logs');
    if (!container) return;
    const entry = document.createElement('div');
    entry.className = `log-entry ${level}`;
    const now = new Date().toLocaleTimeString();
    entry.textContent = `[${now}] ${message}`;
    container.prepend(entry);
}

async function fetchStats() {
    try {
        const res = await fetch('/api/v1/metrics', {
            headers: { 'Authorization': `Bearer ${accessToken}` }
        });
        if (res.ok) {
            const data = await res.json();
        }
    } catch (err) { }
}
