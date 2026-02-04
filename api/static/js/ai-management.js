// AI Management Dashboard Logic (Refined & English)
// ===============================================

document.addEventListener('DOMContentLoaded', () => {
    if (document.getElementById('view-ai-management')) {
        initAIManagement();
    }
});

let aiUpdateTimer = null;
let dlStatusTimer = null;

function initAIManagement() {
    // UI Event Listeners
    document.getElementById('save-config-btn')?.addEventListener('click', saveAIConfig);
    document.getElementById('ai-backup-btn')?.addEventListener('click', createBackup);
    document.getElementById('dl-net-btn')?.addEventListener('click', downloadGlobalNetwork);
    document.getElementById('ai-start-btn')?.addEventListener('click', startTrainingManual);
    document.getElementById('ai-stop-btn')?.addEventListener('click', stopTrainingManual);
    document.getElementById('ai-refresh-btn')?.addEventListener('click', refreshAIManagementData);
    document.getElementById('ai-clear-logs-btn')?.addEventListener('click', () => {
        const container = document.getElementById('ai-logs');
        if (container) container.innerHTML = '<div style="color: #444;">[SYSTEM] Stream cleared by operator.</div>';
    });

    document.getElementById('rail-upload-input')?.addEventListener('change', (e) => {
        const file = e.target.files[0];
        const display = document.getElementById('upload-filename-display');
        if (file && display) {
            display.textContent = `File selezionato: ${file.name}`;
            display.style.display = 'block';
        }
    });

    document.getElementById('rail-upload-btn')?.addEventListener('click', uploadRailFile);

    document.getElementById('config-threshold')?.addEventListener('input', (e) => {
        document.getElementById('config-threshold-val').textContent = e.target.value + 's';
    });

    // Initial Data Load
    refreshAIManagementData();

    // Polling System
    if (aiUpdateTimer) clearInterval(aiUpdateTimer);
    aiUpdateTimer = setInterval(() => {
        if (!document.getElementById('view-ai-management').classList.contains('hidden')) {
            fetchAIStatus();
        }
    }, 2000);
}

async function refreshAIManagementData() {
    await Promise.all([
        loadAIConfig(),
        fetchScenarios(),
        fetchBackups(),
        fetchAIStatus()
    ]);
}

// ==================== Status & Core ====================

async function fetchAIStatus() {
    try {
        const response = await fetch('/api/v1/ai/status', {
            headers: { 'X-API-Key': accessToken }
        });
        if (!response.ok) return;
        const data = await response.json();

        // 1. Status Indicator
        const indicator = document.getElementById('status-indicator');
        const statusText = document.getElementById('ai-status-text');

        if (data.status === 'training') {
            if (indicator) {
                indicator.style.background = 'var(--success)';
                indicator.classList.add('active-pulse');
            }
            if (statusText) {
                statusText.textContent = 'OTTIMIZZAZIONE IN CORSO';
                statusText.style.color = 'var(--success)';
            }

            // Scenario Display
            const scenarioLabel = document.getElementById('ai-current-scenario-label');
            const scenarioName = document.getElementById('active-scenario-name');
            if (scenarioLabel && scenarioName) {
                scenarioLabel.style.display = 'block';
                scenarioName.textContent = (data.current_scenario || 'Sessione Attiva').replace('.json', '').replace('scenarios/', '');
            }
        } else {
            if (indicator) {
                indicator.style.background = 'var(--text-secondary)';
                indicator.classList.remove('active-pulse');
            }
            if (statusText) {
                statusText.textContent = data.seconds_until_next_run > 0 ? `IDLE (Prossimo tra ${data.seconds_until_next_run}s)` : 'STANDBY';
                statusText.style.color = 'var(--text-secondary)';
            }

            const scenarioLabel = document.getElementById('ai-current-scenario-label');
            if (scenarioLabel) scenarioLabel.style.display = 'none';
        }

        // 2. Curriculum Progress
        if (data.curriculum_level !== undefined) {
            document.getElementById('curr-level-num').textContent = data.curriculum_level;
            const levelNames = ["Standby", "Initial (2 Trains)", "Intersections (4 Trains)", "Complex Hubs", "High Density", "Full-Sector Simulation"];
            document.getElementById('curr-level-name').textContent = levelNames[data.curriculum_level] || "Advanced Deployment";

            const progress = Math.min((data.curriculum_level / 5) * 100, 100);
            const progressEl = document.getElementById('curr-level-progress');
            if (progressEl) progressEl.style.width = `${progress}%`;
        }

        // 3. Reward Display
        if (data.history && data.history.length > 0) {
            const rewardVal = document.getElementById('curr-reward-val');
            if (rewardVal) {
                // Approximate efficiency from reward if needed, for now use placeholder or real value if available
                rewardVal.textContent = (data.history[0].reward || -100).toFixed(1);
            }
        }

        // 4. Logs Preview
        const logsContainer = document.getElementById('ai-logs');
        if (logsContainer && data.logs_preview) {
            const lines = data.logs_preview.map(line => `<div style="margin-bottom:2px;">${line}</div>`).join('');
            if (logsContainer.innerHTML !== lines) {
                logsContainer.innerHTML = lines;
                logsContainer.scrollTop = logsContainer.scrollHeight;
            }
        }

    } catch (e) { console.error('AI Status fetch failed', e); }
}

// ==================== Scenarios ====================

async function fetchScenarios() {
    try {
        const response = await fetch('/api/v1/ai/scenarios', {
            headers: { 'X-API-Key': accessToken }
        });
        if (!response.ok) return;
        const data = await response.json();
        const scenarios = data.scenarios || [];

        const list = document.getElementById('scenarios-list');
        if (!list) return;

        if (scenarios.length === 0) {
            list.innerHTML = '<div style="padding: 2rem; text-align: center; color: var(--text-secondary); font-size: 0.8rem;">Nessuno scenario disponibile. Creane uno nel laboratorio!</div>';
            return;
        }

        list.innerHTML = scenarios.map(s => `
            <div class="scenario-item" style="padding: 0.75rem 1rem; border-bottom: 1px solid var(--glass-border); display: flex; justify-content: space-between; align-items: center;">
                <div style="flex: 1;">
                    <div style="font-weight: 600; color: #fff; font-size: 0.85rem;">${s.name.replace('_osm', '').toUpperCase()}</div>
                    <div style="font-size: 0.7rem; color: var(--text-secondary);">${s.stations} nodi • ${s.tracks} binari</div>
                </div>
                <div style="display: flex; gap: 0.4rem;">
                    <button onclick="activateScenario('${s.name}')" style="background: var(--success); padding: 0.25rem 0.5rem; font-size: 0.7rem; border-radius: 4px;" title="Attiva">AVVIA</button>
                    <button onclick="exportToRail('${s.name}')" style="background: var(--primary); padding: 0.25rem 0.5rem; font-size: 0.7rem; border-radius: 4px;" title="Esporta .rail">EXPORT</button>
                    <button onclick="deleteScenario('${s.name}')" style="background: var(--accent); padding: 0.25rem 0.5rem; font-size: 0.7rem; border-radius: 4px;" title="Elimina">🗑️</button>
                </div>
            </div>
        `).join('');
    } catch (e) { console.error('Scenarios failed', e); }
}

async function uploadRailFile() {
    const fileInput = document.getElementById('rail-upload-input');
    const btn = document.getElementById('rail-upload-btn');
    const msgEl = document.getElementById('training-status-msg');

    if (!fileInput.files.length) {
        alert("Per favore, seleziona un file .rail o .json prima di caricare.");
        return;
    }

    const file = fileInput.files[0];
    const formData = new FormData();
    formData.append('file', file);
    formData.append('filename', file.name);

    btn.disabled = true;
    btn.textContent = 'INVIO...';

    try {
        const response = await fetch('/api/v1/network/import-rail', {
            method: 'POST',
            headers: { 'X-API-Key': accessToken },
            body: formData
        });

        if (response.ok) {
            const data = await response.json();
            addAILog(`Scenario "${data.message}" importato.`, 'success');
            msgEl.textContent = "✅ Importazione completata!";
            msgEl.style.color = "var(--success)";

            // Clean up
            fileInput.value = '';
            document.getElementById('upload-filename-display').style.display = 'none';

            // Refresh scenarios list
            await fetchScenarios();
        } else {
            const err = await response.json();
            addAILog(`Errore importazione: ${err.detail}`, 'error');
            msgEl.textContent = `❌ Errore: ${err.detail}`;
            msgEl.style.color = "var(--accent)";
        }
    } catch (e) {
        addAILog(`Errore di rete durante l'upload: ${e.message}`, 'error');
    } finally {
        btn.disabled = false;
        btn.textContent = 'UPLOAD';
    }
}

async function activateScenario(name) {
    const path = `scenarios/${name}.json`;
    try {
        const response = await fetch('/api/v1/ai/config', {
            method: 'POST',
            headers: { 'X-API-Key': accessToken, 'Content-Type': 'application/json' },
            body: JSON.stringify({ scenario: path, enabled: true })
        });
        if (response.ok) {
            addAILog(`Scenario "${name}" montato per l'ottimizzazione neurale.`, 'success');
        }
    } catch (e) { addAILog(`Errore attivazione: ${e.message}`, 'error'); }
}

async function deleteScenario(name) {
    if (!confirm(`Purge scenario data for "${name}"? This cannot be undone.`)) return;
    try {
        const response = await fetch(`/api/v1/network/scenario/${name}`, {
            method: 'DELETE',
            headers: { 'X-API-Key': accessToken }
        });
        if (response.ok) {
            addAILog(`Scenario "${name}" purged from disk.`, 'info');
            fetchScenarios();
        }
    } catch (e) { console.error(e); }
}

// ==================== Data Downloads ====================

async function downloadGlobalNetwork() {
    const inp = document.getElementById('dl-country');
    const country = inp.value.trim();
    if (!country) return;

    const btn = document.getElementById('dl-net-btn');
    btn.disabled = true;
    btn.textContent = 'ATTESA';

    try {
        const response = await fetch(`/api/v1/network/download-europe?country=${encodeURIComponent(country)}`, {
            method: 'POST',
            headers: { 'X-API-Key': accessToken }
        });
        if (response.ok) {
            addAILog(`Download infrastruttura per "${country}" in corso...`, 'info');
            inp.value = '';
            if (!dlStatusTimer) dlStatusTimer = setInterval(pollDownloadStatus, 4000);
        } else {
            const err = await response.json();
            addAILog(`Errore download: ${err.detail}`, 'error');
            btn.disabled = false;
            btn.textContent = 'DOWNLOAD';
        }
    } catch (e) {
        addAILog(`Errore di connessione: ${e.message}`, 'error');
        btn.disabled = false;
        btn.textContent = 'DOWNLOAD';
    }
}

async function pollDownloadStatus() {
    try {
        const response = await fetch('/api/v1/network/download-status', {
            headers: { 'X-API-Key': accessToken }
        });
        if (!response.ok) return;
        const data = await response.json();
        const items = Object.values(data);

        if (items.length === 0) {
            clearInterval(dlStatusTimer);
            dlStatusTimer = null;
            return;
        }

        let pendingCount = 0;
        items.forEach(info => {
            if (info.status === 'completed') {
                addAILog(`Mappa infrastruttura "${info.country}" sincronizzata con successo.`, 'success');
                fetchScenarios();
            } else if (info.status === 'failed') {
                addAILog(`Sincronizzazione fallita per "${info.country}": ${info.error}`, 'error');
            } else {
                pendingCount++;
            }
        });

        if (pendingCount === 0) {
            const btn = document.getElementById('dl-net-btn');
            if (btn) { btn.disabled = false; btn.textContent = 'DOWNLOAD'; }
            clearInterval(dlStatusTimer);
            dlStatusTimer = null;
        }
    } catch (e) { console.error(e); }
}

// ==================== Weights & Backups ====================

async function fetchBackups() {
    try {
        const response = await fetch('/api/v1/ai/backups', {
            headers: { 'X-API-Key': accessToken }
        });
        if (!response.ok) return;
        const backups = await response.json();

        const list = document.getElementById('backups-list');
        if (!list) return;

        if (!backups || backups.length === 0) {
            list.innerHTML = '<div style="padding: 2rem; text-align: center; color: var(--text-secondary); font-size: 0.8rem;">No snapshots discovered.</div>';
            return;
        }

        list.innerHTML = backups.map(b => `
            <div style="padding: 0.75rem 1rem; border-bottom: 1px solid var(--glass-border); display: flex; justify-content: space-between; align-items: center;">
                <div style="flex: 1;">
                    <div style="font-weight: 600; color: #fff; font-size: 0.8rem;">${b.filename}</div>
                    <div style="font-size: 0.65rem; color: var(--text-secondary);">${new Date(b.date).toLocaleString()} • ${b.size_kb} KB</div>
                </div>
                <div style="display: flex; gap: 0.3rem;">
                    <button onclick="restoreBackup('${b.filename}')" style="background: var(--success); padding: 0.3rem 0.5rem; font-size: 0.65rem; border-radius: 4px;">LOAD</button>
                    <button onclick="deleteBackup('${b.filename}')" style="background: var(--accent); padding: 0.3rem 0.5rem; font-size: 0.65rem; border-radius: 4px;">PURGE</button>
                </div>
            </div>
        `).join('');
    } catch (e) { console.error(e); }
}

async function createBackup() {
    const btn = document.getElementById('ai-backup-btn');
    const oldText = btn.textContent;
    btn.disabled = true;
    btn.textContent = 'SNAPSHOT...';

    try {
        const response = await fetch('/api/v1/ai/backup', {
            method: 'POST',
            headers: { 'X-API-Key': accessToken }
        });
        if (response.ok) {
            addAILog('Snapshot pesi neurali completato con successo.', 'success');
            await fetchBackups();
        } else {
            const err = await response.json();
            addAILog(`Errore snapshot: ${err.detail}`, 'error');
        }
    } catch (e) { addAILog(`Errore di comunicazione: ${e.message}`, 'error'); }
    finally {
        btn.disabled = false;
        btn.textContent = oldText;
    }
}

async function restoreBackup(filename) {
    if (!confirm(`Switch to neural base: "${filename}"? This will reboot the training agent.`)) return;
    try {
        const response = await fetch(`/api/v1/ai/restore?filename=${encodeURIComponent(filename)}`, {
            method: 'POST',
            headers: { 'X-API-Key': accessToken }
        });
        if (response.ok) {
            addAILog(`Hot-swapped model weights to "${filename}".`, 'success');
            setTimeout(fetchAIStatus, 1000);
        } else {
            const err = await response.json();
            addAILog(`Hot-swap aborted: ${err.detail}`, 'error');
        }
    } catch (e) { addAILog(`Engine error: ${e.message}`, 'error'); }
}

async function deleteBackup(filename) {
    if (!confirm(`Purge snapshot "${filename}"?`)) return;
    try {
        const response = await fetch(`/api/v1/ai/backup/${filename}`, {
            method: 'DELETE',
            headers: { 'X-API-Key': accessToken }
        });
        if (response.ok) {
            addAILog(`Snapshot "${filename}" purged.`, 'info');
            fetchBackups();
        }
    } catch (e) { console.error(e); }
}

// ==================== Configuration ====================

async function loadAIConfig() {
    try {
        const response = await fetch('/api/v1/ai/config', {
            headers: { 'X-API-Key': accessToken }
        });
        if (response.ok) {
            const config = await response.json();
            document.getElementById('config-enabled').checked = config.enabled;
            document.getElementById('config-threshold').value = config.threshold_seconds;
            document.getElementById('config-threshold-val').textContent = config.threshold_seconds + 's';
        }
    } catch (e) { console.error('Config synchronization failed', e); }
}

async function saveAIConfig() {
    const enabled = document.getElementById('config-enabled').checked;
    const threshold = parseInt(document.getElementById('config-threshold').value);

    try {
        const response = await fetch('/api/v1/ai/config', {
            method: 'POST',
            headers: { 'X-API-Key': accessToken, 'Content-Type': 'application/json' },
            body: JSON.stringify({ enabled, threshold })
        });
        if (response.ok) {
            addAILog('Engine convergence parameters synchronized.', 'success');
            if (enabled) {
                document.getElementById('ai-auto-badge').style.display = 'block';
            } else {
                document.getElementById('ai-auto-badge').style.display = 'none';
            }
        }
    } catch (e) { addAILog(`Sync failure: ${e.message}`, 'error'); }
}

async function startTrainingManual() {
    try {
        const response = await fetch('/api/v1/ai/start-training', {
            method: 'POST',
            headers: { 'X-API-Key': accessToken }
        });
        if (response.ok) {
            addAILog('Neural session initiated via manual override.', 'success');
            setTimeout(fetchAIStatus, 1000);
        } else {
            addAILog('Manual override failed. Check system logs.', 'error');
        }
    } catch (e) { console.error(e); }
}

async function stopTrainingManual() {
    try {
        const response = await fetch('/api/v1/ai/config', {
            method: 'POST',
            headers: { 'X-API-Key': accessToken, 'Content-Type': 'application/json' },
            body: JSON.stringify({ enabled: false }) // Stopping auto-training effectively stops the manager
        });
        if (response.ok) {
            addAILog('Neural session terminated by operator.', 'info');
            document.getElementById('config-enabled').checked = false;
            document.getElementById('ai-auto-badge').style.display = 'none';
            setTimeout(fetchAIStatus, 1000);
        }
    } catch (e) { console.error(e); }
}

function addAILog(msg, type = 'info') {
    const container = document.getElementById('ai-logs');
    if (!container) return;

    const entry = document.createElement('div');
    entry.style.marginBottom = '2px';
    entry.style.fontSize = '0.75rem';

    const time = new Date().toLocaleTimeString();
    let prefix = `[${time}] `;

    if (type === 'success') entry.style.color = 'var(--success)';
    else if (type === 'error') entry.style.color = 'var(--accent)';
    else entry.style.color = 'var(--text-secondary)';

    entry.textContent = prefix + msg;
    container.prepend(entry);
    container.scrollTop = 0;
}

async function exportToRail(scenarioName) {
    const url = `/api/v1/network/export-rail?scenario=${encodeURIComponent(scenarioName)}`;
    try {
        const response = await fetch(url, { headers: { 'X-API-Key': accessToken } });
        if (response.ok) {
            const blob = await response.blob();
            const link = document.createElement('a');
            link.href = window.URL.createObjectURL(blob);
            link.download = `${scenarioName}.rail`;
            link.click();
            addAILog(`Exported sector telemetry: ${scenarioName}.rail`, 'success');
        } else {
            addAILog(`Telemetry export failed for ${scenarioName}.`, 'error');
        }
    } catch (e) { console.error(e); }
}
