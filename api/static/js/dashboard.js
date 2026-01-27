let accessToken = localStorage.getItem('access_token');
let trainingChart = null;

document.addEventListener('DOMContentLoaded', () => {
    if (accessToken) {
        document.getElementById('auth-overlay').classList.add('hidden');
        initDashboard();
    }

    document.getElementById('login-btn').addEventListener('click', login);
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
            // Stat update could be done here if needed
        }
    } catch (err) { }
}
