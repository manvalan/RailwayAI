
// ==================== AI Management Functions ====================

async function loadAIManagement() {
    await Promise.all([
        fetchAIStatus(),
        fetchScenarios(),
        fetchModelStats()
    ]);

    // Subscribe to training logs via WebSocket
    if (ws && ws.readyState === WebSocket.OPEN) {
        // Logs will come through existing WebSocket connection
    }
}

async function fetchAIStatus() {
    try {
        const response = await fetch('/api/v1/ai/status', {
            headers: { 'X-API-Key': accessToken }
        });

        if (response.ok) {
            const data = await response.json();
            document.getElementById('ai-status').textContent = data.status === 'active' ? 'Attivo' : 'Inattivo';
            document.getElementById('ai-status').style.color = data.status === 'active' ? 'var(--success)' : 'var(--accent)';
            document.getElementById('ai-threshold').textContent = `${data.threshold_seconds}s`;
            document.getElementById('ai-last-run').textContent = data.last_run ? new Date(data.last_run).toLocaleString('it-IT') : '--';
            document.getElementById('ai-next-run').textContent = data.is_training ? 'Training in corso...' : data.next_run_estimate;
        }
    } catch (error) {
        console.error('Error fetching AI status:', error);
    }
}

async function fetchScenarios() {
    try {
        const response = await fetch('/api/v1/ai/scenarios', {
            headers: { 'X-API-Key': accessToken }
        });

        if (response.ok) {
            const data = await response.json();
            const listEl = document.getElementById('scenarios-list');

            if (data.total === 0) {
                listEl.innerHTML = '<div style="text-align: center; color: var(--text-secondary); padding: 2rem;">Nessuno scenario disponibile. Generane uno dalla sezione Training.</div>';
            } else {
                listEl.innerHTML = data.scenarios.map(s => `
                    <div style="padding: 1rem; background: rgba(255,255,255,0.05); border-radius: 8px; margin-bottom: 0.5rem;">
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <div>
                                <div style="font-weight: 600;">${s.name}</div>
                                <div style="font-size: 0.85rem; color: var(--text-secondary);">
                                    ${s.stations} stazioni • ${s.tracks} binari • ${s.size_kb} KB
                                </div>
                            </div>
                            <div style="font-size: 0.8rem; color: var(--text-secondary);">
                                ${new Date(s.modified * 1000).toLocaleDateString('it-IT')}
                            </div>
                        </div>
                    </div>
                `).join('');
            }
        }
    } catch (error) {
        console.error('Error fetching scenarios:', error);
    }
}

async function fetchModelStats() {
    try {
        const response = await fetch('/api/v1/ai/model-stats', {
            headers: { 'X-API-Key': accessToken }
        });

        if (response.ok) {
            const data = await response.json();
            document.getElementById('model-episodes').textContent = data.episodes_completed || 0;
            document.getElementById('model-reward').textContent = data.avg_reward ? data.avg_reward.toFixed(2) : '--';
            document.getElementById('model-conflicts').textContent = data.conflicts_resolved || 0;
            document.getElementById('model-accuracy').textContent = data.accuracy ? `${(data.accuracy * 100).toFixed(1)}%` : '--%';
        }
    } catch (error) {
        console.error('Error fetching model stats:', error);
    }
}

async function startManualTraining() {
    try {
        const response = await fetch('/api/v1/ai/start-training', {
            method: 'POST',
            headers: { 'X-API-Key': accessToken }
        });

        if (response.ok) {
            const data = await response.json();
            addAILog(`✅ ${data.message}`, 'success');
            setTimeout(fetchAIStatus, 1000);
        } else {
            const error = await response.json();
            addAILog(`❌ Errore: ${error.detail}`, 'error');
        }
    } catch (error) {
        addAILog(`❌ Errore di connessione: ${error.message}`, 'error');
    }
}

async function stopAutoTraining() {
    if (!confirm('Sei sicuro di voler fermare l\'auto-training?')) return;

    try {
        const response = await fetch('/api/v1/ai/stop-training', {
            method: 'POST',
            headers: { 'X-API-Key': accessToken }
        });

        if (response.ok) {
            const data = await response.json();
            addAILog(`⚠️ ${data.message}`, 'warning');
            setTimeout(fetchAIStatus, 1000);
        }
    } catch (error) {
        addAILog(`❌ Errore: ${error.message}`, 'error');
    }
}

function addAILog(message, level = 'info') {
    const logsEl = document.getElementById('ai-logs');
    const timestamp = new Date().toLocaleTimeString('it-IT');
    const colors = {
        success: 'var(--success)',
        error: 'var(--accent)',
        warning: '#ff9800',
        info: 'var(--text-secondary)'
    };

    const logEntry = document.createElement('div');
    logEntry.style.color = colors[level] || colors.info;
    logEntry.style.marginBottom = '0.5rem';
    logEntry.textContent = `[${timestamp}] ${message}`;

    if (logsEl.firstChild?.textContent === 'In attesa di log...') {
        logsEl.innerHTML = '';
    }

    logsEl.appendChild(logEntry);
    logsEl.scrollTop = logsEl.scrollHeight;
}

function clearAILogs() {
    document.getElementById('ai-logs').innerHTML = '<div style="color: var(--text-secondary);">Logs puliti.</div>';
}

// Intercept WebSocket messages for AI logs
const originalHandleWsMessage = handleWsMessage;
handleWsMessage = function (data) {
    originalHandleWsMessage(data);

    // Forward training logs to AI Management panel
    if (data.type === 'log' && data.message.includes('training')) {
        addAILog(data.message, data.level);
    }
};
