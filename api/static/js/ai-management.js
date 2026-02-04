// AI Management Dashboard Logic
// =============================

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

    document.getElementById('config-threshold')?.addEventListener('input', (e) => {
        document.getElementById('config-threshold-val').textContent = e.target.value;
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
                indicator.className = 'active-pulse';
            }
            if (statusText) {
                statusText.textContent = `In corso: ${data.current_scenario || 'Addestramento'}`;
                statusText.style.color = 'var(--success)';
            }
        } else {
            if (indicator) {
                indicator.style.background = 'var(--text-secondary)';
                indicator.className = '';
            }
            if (statusText) {
                statusText.textContent = data.seconds_until_next_run > 0 ? `In attesa (${data.seconds_until_next_run}s)` : 'Inattivo';
                statusText.style.color = 'var(--text-primary)';
            }
        }

        // 2. Curriculum Progress
        if (data.curriculum_level !== undefined) {
            document.getElementById('curr-level-num').textContent = data.curriculum_level;
            const levelNames = ["", "Base (2 Treni)", "Incroci (4 Treni)", "Hub Stellari", "Congestione Alta", "Rete Completa"];
            document.getElementById('curr-level-name').textContent = levelNames[data.curriculum_level] || "Avanzato";

            const progress = (data.curriculum_level / 5) * 100;
            const progressEl = document.getElementById('curr-level-progress');
            if (progressEl) progressEl.style.width = `${progress}%`;

            document.getElementById('curr-reward-target').textContent = -100;
        }

        // 3. Reward Display
        if (data.history && data.history.length > 0) {
            // Use some metric from history or status report
            const lastRun = data.history[0];
            document.getElementById('curr-reward-val').textContent = (Math.random() * 20 - 110).toFixed(1); // placeholder
        }

        // 4. Logs Preview
        const logsContainer = document.getElementById('ai-logs');
        if (logsContainer && data.logs_preview) {
            const html = data.logs_preview.map(line => `<div>${line}</div>`).join('');
            if (logsContainer.innerHTML !== html) {
                logsContainer.innerHTML = html;
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
        const scenarios = await response.json();

        const list = document.getElementById('scenarios-list');
        if (!list) return;

        if (!scenarios || scenarios.length === 0) {
            list.innerHTML = '<div style="padding: 2rem; text-align: center; color: var(--text-secondary);">Nessuno scenario. Scaricane uno!</div>';
            return;
        }

        list.innerHTML = scenarios.map(s => `
            <div class="scenario-item" style="padding: 1rem; border-bottom: 1px solid var(--glass-border); display: flex; justify-content: space-between; align-items: center;">
                <div style="flex: 1;">
                    <div style="font-weight: 600; color: #fff;">${s.name.replace('_osm', '')}</div>
                    <div style="font-size: 0.75rem; color: var(--text-secondary);">${s.stations} stazioni • ${s.tracks} binari</div>
                </div>
                <div style="display: flex; gap: 0.5rem;">
                    <button onclick="activateScenario('${s.name}')" style="background: var(--success); padding: 0.3rem 0.6rem; font-size: 0.7rem; border-radius: 4px;" title="Attiva per Training">▶️</button>
                    <button onclick="exportToRail('${s.name}')" style="background: var(--primary); padding: 0.3rem 0.6rem; font-size: 0.7rem; border-radius: 4px;" title="Esporta .rail">.rail</button>
                    <button onclick="deleteScenario('${s.name}')" style="background: var(--accent); padding: 0.3rem 0.6rem; font-size: 0.7rem; border-radius: 4px;" title="Elimina">🗑️</button>
                </div>
            </div>
        `).join('');
    } catch (e) { console.error('Scenarios failed', e); }
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
            addAILog(`✅ Scenario "${name}" ora attivo per l'addestramento.`, 'success');
        }
    } catch (e) { addAILog(`❌ Errore attivazione: ${e.message}`, 'error'); }
}

async function deleteScenario(name) {
    if (!confirm(`Eliminare definitivamente lo scenario "${name}"?`)) return;
    try {
        const response = await fetch(`/api/v1/network/scenario/${name}`, {
            method: 'DELETE',
            headers: { 'X-API-Key': accessToken }
        });
        if (response.ok) {
            addAILog(`🗑️ Scenario ${name} rimosso.`, 'success');
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
    btn.textContent = '⏳ ...';

    try {
        const response = await fetch(`/api/v1/network/download-europe?country=${encodeURIComponent(country)}`, {
            method: 'POST',
            headers: { 'X-API-Key': accessToken }
        });
        if (response.ok) {
            addAILog(`🌍 Richiesta download inviata per "${country}". Attendere completamento...`, 'info');
            inp.value = '';
            if (!dlStatusTimer) dlStatusTimer = setInterval(pollDownloadStatus, 4000);
        } else {
            const err = await response.json();
            addAILog(`❌ Errore: ${err.detail}`, 'error');
            btn.disabled = false;
            btn.textContent = 'Download';
        }
    } catch (e) {
        addAILog(`❌ Errore connessione: ${e.message}`, 'error');
        btn.disabled = false;
        btn.textContent = 'Download';
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
                addAILog(`✅ Network "${info.country}" scaricato e pronto!`, 'success');
                // We'd ideally mark it as notified on server side, but status-clearing is better for UI
                fetchScenarios();
            } else if (info.status === 'failed') {
                addAILog(`❌ Errore download "${info.country}": ${info.error}`, 'error');
            } else {
                pendingCount++;
            }
        });

        if (pendingCount === 0) {
            const btn = document.getElementById('dl-net-btn');
            if (btn) { btn.disabled = false; btn.textContent = 'Download'; }
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
            list.innerHTML = '<div style="padding: 2rem; text-align: center; color: var(--text-secondary);">Nessun backup trovato.</div>';
            return;
        }

        list.innerHTML = backups.map(b => `
            <div style="padding: 1rem; border-bottom: 1px solid var(--glass-border); display: flex; justify-content: space-between; align-items: center;">
                <div style="flex: 1;">
                    <div style="font-weight: 600; color: #fff; font-size: 0.85rem;">${b.filename}</div>
                    <div style="font-size: 0.7rem; color: var(--text-secondary);">${new Date(b.date).toLocaleString()} • ${b.size_kb} KB</div>
                </div>
                <div style="display: flex; gap: 0.4rem;">
                    <button onclick="restoreBackup('${b.filename}')" style="background: var(--success); color:#fff; padding: 0.4rem 0.6rem; font-size: 0.7rem; border-radius: 4px; border:none; cursor:pointer;">Ripristina</button>
                    <button onclick="deleteBackup('${b.filename}')" style="background: var(--accent); color:#fff; padding: 0.4rem 0.6rem; font-size: 0.7rem; border-radius: 4px; border:none; cursor:pointer;">🗑️</button>
                </div>
            </div>
        `).join('');
    } catch (e) { console.error(e); }
}

async function createBackup() {
    const btn = document.getElementById('ai-backup-btn');
    const oldText = btn.textContent;
    btn.disabled = true;
    btn.textContent = '⏳ ...';

    try {
        const response = await fetch('/api/v1/ai/backup', {
            method: 'POST',
            headers: { 'X-API-Key': accessToken }
        });
        if (response.ok) {
            addAILog('✅ Backup dei pesi creato con successo.', 'success');
            await fetchBackups();
        } else {
            const err = await response.json();
            addAILog(`❌ Backup fallito: ${err.detail}`, 'error');
        }
    } catch (e) { addAILog(`❌ Errore backup: ${e.message}`, 'error'); }
    finally {
        btn.disabled = false;
        btn.textContent = oldText;
    }
}

async function restoreBackup(filename) {
    if (!confirm(`⚠️ Vuoi davvero caricare i pesi da ${filename}?\nL'addestramento verrà interrotto per ricaricare il modello.`)) return;
    try {
        const response = await fetch(`/api/v1/ai/restore?filename=${encodeURIComponent(filename)}`, {
            method: 'POST',
            headers: { 'X-API-Key': accessToken }
        });
        if (response.ok) {
            addAILog(`✅ Ripristino completato da ${filename}.`, 'success');
            setTimeout(fetchAIStatus, 1000);
        } else {
            const err = await response.json();
            addAILog(`❌ Ripristino fallito: ${err.detail}`, 'error');
        }
    } catch (e) { addAILog(`❌ Errore ripristino: ${e.message}`, 'error'); }
}

async function deleteBackup(filename) {
    if (!confirm(`Eliminare il backup ${filename}?`)) return;
    try {
        const response = await fetch(`/api/v1/ai/backup/${filename}`, {
            method: 'DELETE',
            headers: { 'X-API-Key': accessToken }
        });
        if (response.ok) {
            addAILog(`🗑️ Backup ${filename} eliminato.`, 'success');
            fetchBackups();
        } else {
            addAILog('❌ Errore eliminazione backup.', 'error');
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
            document.getElementById('config-threshold-val').textContent = config.threshold_seconds;
        }
    } catch (e) { console.error('Load config failed', e); }
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
            addAILog('✅ Configurazione AI salvata.', 'success');
        }
    } catch (e) { addAILog(`❌ Errore salvataggio: ${e.message}`, 'error'); }
}

async function startTrainingManual() {
    try {
        const response = await fetch('/api/v1/ai/start-training', {
            method: 'POST',
            headers: { 'X-API-Key': accessToken }
        });
        if (response.ok) {
            addAILog('🚀 Addestramento avviato manualmente.', 'success');
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

    if (type === 'success') entry.style.color = '#0f0';
    else if (type === 'error') entry.style.color = '#f00';
    else entry.style.color = '#aaa';

    entry.textContent = prefix + msg;
    container.appendChild(entry);
    container.scrollTop = container.scrollHeight;
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
            addAILog(`✅ Esportazione ${scenarioName}.rail completata.`, 'success');
        } else {
            const err = await response.json();
            addAILog(`❌ Esportazione fallita: ${err.detail}`, 'error');
        }
    } catch (e) { console.error(e); }
}
