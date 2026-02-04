
// ==================== AI Management Functions ====================

let aiStatusInterval = null;

async function loadAIManagement() {
    // Initial load
    await refreshAIManagementData();

    // Set refresh interval to 1 second
    if (aiStatusInterval) clearInterval(aiStatusInterval);
    aiStatusInterval = setInterval(async () => {
        // Only refresh if the AI Management view is still visible
        const aiView = document.getElementById('view-ai-management');
        if (aiView && !aiView.classList.contains('hidden')) {
            await fetchAIStatus();
            // We can also refresh model stats less frequently, but user asked for "ogny secondo" for the page
        } else {
            clearInterval(aiStatusInterval);
            aiStatusInterval = null;
        }
    }, 1000);

    // Curriculum Settings listeners
    document.getElementById('config-curriculum')?.addEventListener('change', (e) => {
        const lvlGroup = document.getElementById('config-level-group');
        if (lvlGroup) lvlGroup.style.display = e.target.checked ? 'block' : 'none';
    });

    // Backup Actions
    document.getElementById('ai-backup-btn')?.addEventListener('click', createBackup);

    // Network Download
    document.getElementById('dl-net-btn')?.addEventListener('click', downloadGlobalNetwork);

    // Slider listener
    const slider = document.getElementById('config-threshold');
    const valDisplay = document.getElementById('config-threshold-val');
    if (slider && valDisplay) {
        slider.addEventListener('input', (e) => {
            valDisplay.textContent = e.target.value + 's';
        });
    }
}

async function refreshAIManagementData() {
    return Promise.all([
        fetchAIStatus(),
        fetchScenarios(),
        fetchModelStats(),
        loadAIConfig(),
        populateScenarioDropdown(),
        fetchAIQualityMetrics(),
        fetchNetworkStats(),
        fetchBackups()
    ]);
}


async function fetchNetworkStats() {
    try {
        const response = await fetch('/api/v1/network/statistics', {
            headers: { 'X-API-Key': accessToken }
        });
        if (response.ok) {
            const data = await response.json();
            document.getElementById('net-name').textContent = data.network_name;
            document.getElementById('net-stations').textContent = data.total_stations;
            document.getElementById('net-tracks').textContent = data.total_tracks;
            document.getElementById('net-junctions').textContent = data.total_junctions;
            document.getElementById('net-trains').textContent = data.active_trains;
        }
    } catch (e) { console.error('Error fetching network stats:', e); }
}

async function fetchAIStatus() {
    try {
        const response = await fetch('/api/v1/ai/status', {
            headers: { 'X-API-Key': accessToken }
        });

        if (response.ok) {
            const data = await response.json();

            // 1. Status Indicator
            const indicator = document.getElementById('status-indicator');
            const statusText = document.getElementById('ai-status-text');

            if (data.status === 'training') {
                if (indicator) {
                    indicator.style.background = 'var(--success)';
                    indicator.style.boxShadow = '0 0 8px var(--success)';
                }
                if (statusText) {
                    statusText.innerHTML = `<span style="color:var(--success)">Training in corso:</span> ${data.current_scenario || 'Scenario'}`;
                    statusText.style.fontWeight = '600';
                }
            } else {
                if (indicator) {
                    indicator.style.background = 'var(--text-secondary)';
                    indicator.style.boxShadow = 'none';
                }
                if (statusText) {
                    if (data.seconds_until_next_run > 0) {
                        statusText.textContent = `Attesa (${data.seconds_until_next_run}s) - Next: ${data.queued_scenario}`;
                    } else {
                        statusText.textContent = `Avvio in corso...`;
                    }
                    statusText.style.fontWeight = 'normal';
                }
            }

            // 2. Logs Preview
            const logsContainer = document.getElementById('ai-logs');
            if (logsContainer) {
                if (data.logs_preview && data.logs_preview.length > 0) {
                    logsContainer.innerHTML = data.logs_preview.map(l => `<div style="margin-bottom:2px;">${l}</div>`).join('');
                    logsContainer.scrollTop = logsContainer.scrollHeight;
                } else if (data.history && data.history.length > 0) {
                    const historyHtml = data.history.map(h => {
                        const color = h.status === 'completed' ? 'var(--success)' : 'var(--accent)';
                        return `
                            <div style="border-left: 2px solid ${color}; padding-left: 0.5rem; margin-bottom: 0.5rem;">
                                <div style="font-size: 0.75rem; color: var(--text-secondary);">${new Date(h.timestamp).toLocaleTimeString()}</div>
                                <div style="font-size: 0.8rem;">${h.scenario} - <span style="color:${color}">${h.status}</span></div>
                            </div>
                         `;
                    }).join('');
                    logsContainer.innerHTML = `<div style="color:var(--text-secondary); margin-bottom:0.5rem; font-weight:600; font-size:0.8rem;">Last Activity:</div>` + historyHtml;
                } else {
                    logsContainer.innerHTML = '<div style="color:var(--text-secondary); font-size:0.8rem;">Nessuna attività recente.</div>';
                }
            }

            // 3. Curriculum Progress
            const levelNum = document.getElementById('curr-level-num');
            if (levelNum && data.curriculum_level !== undefined) {
                levelNum.textContent = data.curriculum_level;
                const levelNames = [
                    "",
                    "Basic Conflict (2 Trains)",
                    "Bottleneck Mgmt (4 Trains)",
                    "Junctions (Star Topology)",
                    "Linear Congestion (20 Trains)",
                    "Full Network Analysis"
                ];
                const nameEl = document.getElementById('curr-level-name');
                if (nameEl) nameEl.textContent = levelNames[data.curriculum_level] || "Advanced Training";

                const progress = (data.curriculum_level / 5) * 100;
                const progressBar = document.getElementById('curr-level-progress');
                if (progressBar) progressBar.style.width = `${progress}%`;

                const targetEl = document.getElementById('curr-reward-target');
                if (targetEl) targetEl.textContent = -100;
            }

            // 4. Config Sync
            if (document.activeElement.id !== 'config-threshold') {
                // threshold logic if needed
            }
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
            const selectEl = document.getElementById('config-scenario');

            // Clear both
            if (listEl) listEl.innerHTML = '';
            if (selectEl) selectEl.innerHTML = '<option value="">Auto (primo disponibile)</option>';

            if (data.total === 0) {
                if (listEl) listEl.innerHTML = '<div style="text-align: center; color: var(--text-secondary); padding: 2rem;">Nessuno scenario disponibile.</div>';
            } else {
                data.scenarios.forEach(s => {
                    // Populate List
                    if (listEl) {
                        const item = document.createElement('div');
                        item.className = 'scenario-item'; // Add CSS class for hover effect
                        item.style.padding = '0.8rem';
                        item.style.borderBottom = '1px solid var(--glass-border)';
                        item.style.cursor = 'pointer';

                        // Click to select in config
                        item.onclick = () => {
                            if (selectEl) selectEl.value = s.path;
                            // Reset styles
                            Array.from(listEl.children).forEach(c => c.style.background = 'transparent');
                            item.style.background = 'rgba(255,255,255,0.1)';
                        };

                        item.innerHTML = `
                            <div style="display: flex; justify-content: space-between; align-items: start;">
                                <div style="flex: 1;">
                                    <div style="font-weight: 600; font-size: 0.9rem; color: #fff;">${s.name}</div>
                                    <div style="font-size: 0.75rem; color: var(--text-secondary); margin-top: 2px;">
                                        ${s.stations} stazioni • ${s.tracks} binari
                                    </div>
                                    <div style="font-size: 0.7rem; color: var(--text-secondary); margin-top: 4px;">
                                        ${new Date(s.modified * 1000).toLocaleDateString('it-IT')}
                                    </div>
                                </div>
                                <div style="display: flex; gap: 0.5rem; align-items: center;">
                                    <button onclick="exportToRail('${s.name}')" 
                                            style="padding: 0.3rem 0.6rem; font-size: 0.65rem; background: var(--primary); border:none; border-radius:4px; color:white; cursor:pointer;"
                                            title="Esporta per App Swift">.rail</button>
                                </div>
                            </div>
                        `;
                        listEl.appendChild(item);
                    }

                    // Populate Dropdown
                    if (selectEl) {
                        const option = document.createElement('option');
                        option.value = s.path;
                        option.textContent = `${s.name} (${s.stations} staz.)`;
                        selectEl.appendChild(option);
                    }
                });
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

async function loadAIConfig() {
    try {
        const response = await fetch('/api/v1/ai/config', {
            headers: { 'X-API-Key': accessToken }
        });

        if (response.ok) {
            const config = await response.json();
            document.getElementById('config-threshold').value = config.threshold_seconds || 300;
            document.getElementById('config-episodes').value = config.episodes_per_run || 100;
            document.getElementById('config-scenario').value = config.scenario_path || '';
            document.getElementById('config-enabled').checked = config.enabled !== false;
        }
    } catch (error) {
        console.error('Error loading AI config:', error);
    }
}

async function saveAIConfig() {
    const threshold = parseInt(document.getElementById('config-threshold').value);
    const episodes = parseInt(document.getElementById('config-episodes').value);
    const scenario = document.getElementById('config-scenario').value || null;
    const enabled = document.getElementById('config-enabled').checked;

    const msgEl = document.getElementById('config-status-msg');
    msgEl.textContent = '⏳ Salvando...';
    msgEl.style.color = 'var(--primary)';

    try {
        const response = await fetch('/api/v1/ai/config', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-API-Key': accessToken
            },
            body: JSON.stringify({ threshold, episodes, scenario, enabled })
        });

        if (response.ok) {
            msgEl.textContent = '✅ Configurazione salvata!';
            msgEl.style.color = 'var(--success)';
            setTimeout(() => { msgEl.textContent = ''; }, 3000);
            fetchAIStatus(); // Refresh status
        } else {
            const error = await response.json();
            msgEl.textContent = `❌ Errore: ${error.detail}`;
            msgEl.style.color = 'var(--accent)';
        }
    } catch (error) {
        msgEl.textContent = `❌ Errore di connessione`;
        msgEl.style.color = 'var(--accent)';
    }
}

async function populateScenarioDropdown() {
    try {
        const response = await fetch('/api/v1/ai/scenarios', {
            headers: { 'X-API-Key': accessToken }
        });

        if (response.ok) {
            const data = await response.json();
            const select = document.getElementById('config-scenario');

            // Keep "Auto" option
            select.innerHTML = '<option value="">Auto (primo disponibile)</option>';

            // Add scenarios
            data.scenarios.forEach(s => {
                const option = document.createElement('option');
                option.value = s.path;
                option.textContent = `${s.name} (${s.stations} stazioni)`;
                select.appendChild(option);
            });
        }
    } catch (error) {
        console.error('Error populating scenarios:', error);
    }
}

async function fetchAIQualityMetrics() {
    try {
        const response = await fetch('/api/v1/ai/quality-metrics', {
            headers: { 'X-API-Key': accessToken }
        });

        if (response.ok) {
            const data = await response.json();

            // Test Set Performance
            document.getElementById('test-accuracy').textContent = data.test_accuracy ? `${(data.test_accuracy * 100).toFixed(1)}%` : '--%';
            document.getElementById('test-precision').textContent = data.test_precision ? `${(data.test_precision * 100).toFixed(1)}%` : '--%';
            document.getElementById('test-recall').textContent = data.test_recall ? `${(data.test_recall * 100).toFixed(1)}%` : '--%';
            document.getElementById('test-f1').textContent = data.test_f1 ? `${(data.test_f1 * 100).toFixed(1)}%` : '--%';
            document.getElementById('test-loss').textContent = data.test_loss ? data.test_loss.toFixed(4) : '--';

            // Training History
            document.getElementById('train-loss').textContent = data.train_loss ? data.train_loss.toFixed(4) : '--';
            document.getElementById('val-loss').textContent = data.val_loss ? data.val_loss.toFixed(4) : '--';
            document.getElementById('convergence-status').textContent = data.convergence_status || 'In attesa di dati...';
            document.getElementById('convergence-status').style.color = data.is_converged ? 'var(--success)' : 'var(--accent)';
            document.getElementById('last-checkpoint').textContent = data.last_checkpoint || '--';

            // Model Confidence
            document.getElementById('avg-confidence').textContent = data.avg_confidence ? `${(data.avg_confidence * 100).toFixed(1)}%` : '--%';
            document.getElementById('uncertain-predictions').textContent = data.uncertain_predictions || '--';
            document.getElementById('model-stability').textContent = data.model_stability || '--';
            document.getElementById('quality-assessment').textContent = data.quality_assessment || 'In attesa di dati...';
            document.getElementById('quality-assessment').style.color = getQualityColor(data.quality_assessment);

            // Dataset Info
            document.getElementById('training-scenarios').textContent = data.training_scenarios || 0;
            document.getElementById('total-examples').textContent = data.total_examples || 0;
            document.getElementById('dataset-updated').textContent = data.dataset_updated ? new Date(data.dataset_updated).toLocaleString('it-IT') : '--';

            // Benchmark Comparison
            if (data.benchmarks) {
                updateBenchmark('vs-random', data.benchmarks.vs_random);
                updateBenchmark('vs-greedy', data.benchmarks.vs_greedy);
                updateBenchmark('vs-optimal', data.benchmarks.vs_optimal);
                document.getElementById('overall-improvement').textContent = data.benchmarks.overall_improvement || '--';
            }
        }
    } catch (error) {
        console.error('Error fetching AI quality metrics:', error);
    }
}

function getQualityColor(assessment) {
    if (!assessment) return 'var(--text-secondary)';
    if (assessment.includes('Eccellente') || assessment.includes('Ottimo')) return 'var(--success)';
    if (assessment.includes('Buono')) return 'var(--primary)';
    if (assessment.includes('Sufficiente')) return '#ff9800';
    return 'var(--accent)';
}

function updateBenchmark(id, value) {
    if (!value) return;

    const textEl = document.getElementById(id);
    const barEl = document.getElementById(id + '-bar');

    const improvement = parseFloat(value);
    textEl.textContent = `+${improvement.toFixed(1)}%`;
    barEl.style.width = `${Math.min(improvement, 100)}%`;
}

// ==================== Global Network Download ====================

async function downloadGlobalNetwork() {
    const countryInp = document.getElementById('dl-country');
    const country = countryInp.value.trim();
    if (!country) return;

    const btn = document.getElementById('dl-net-btn');
    const oldText = btn.textContent;
    btn.disabled = true;
    btn.textContent = '⏳ ...';

    try {
        const response = await fetch(`/api/v1/network/download-europe?country=${encodeURIComponent(country)}`, {
            method: 'POST',
            headers: { 'X-API-Key': accessToken }
        });

        if (response.ok) {
            const data = await response.json();
            addAILog(`🌍 Download avviato per ${country}. Ci vorrà qualche minuto.`, 'info');
            countryInp.value = '';
            // Refresh list eventually
            setTimeout(fetchScenarios, 5000);
        } else {
            const err = await response.json();
            addAILog(`❌ Download fallito: ${err.detail}`, 'error');
        }
    } catch (e) { addAILog(`❌ Errore download: ${e.message}`, 'error'); }
    finally {
        btn.disabled = false;
        btn.textContent = oldText;
    }
}

async function exportToRail(scenarioName) {
    try {
        const url = `/api/v1/network/export-rail?scenario=${encodeURIComponent(scenarioName)}`;
        // Trigger download
        const a = document.createElement('a');
        a.href = url + `&token=${accessToken}`; // Note: simplified for direct download, better use fetch or temp link

        // Use fetch to handle headers if token is needed
        const response = await fetch(url, {
            headers: { 'X-API-Key': accessToken }
        });

        if (response.ok) {
            const blob = await response.blob();
            const downloadUrl = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = downloadUrl;
            a.download = `${scenarioName}.rail`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            window.URL.revokeObjectURL(downloadUrl);
            addAILog(`✅ Esportazione ${scenarioName}.rail completata.`, 'success');
        } else {
            const err = await response.json();
            addAILog(`❌ Esportazione fallita: ${err.detail}`, 'error');
        }
    } catch (e) { addAILog(`❌ Errore esportazione: ${e.message}`, 'error'); }
}

// ==================== Backup & Weights ====================

async function fetchBackups() {
    try {
        const response = await fetch('/api/v1/ai/backups', {
            headers: { 'X-API-Key': accessToken }
        });
        if (response.ok) {
            const backups = await response.json();
            const listEl = document.getElementById('backups-list');
            if (!listEl) return;

            if (backups.length === 0) {
                listEl.innerHTML = '<div style="color: var(--text-secondary); text-align: center; padding: 1rem; font-size: 0.8rem;">Nessun backup trovato.</div>';
                return;
            }

            listEl.innerHTML = backups.map(b => `
                <div style="display: flex; justify-content: space-between; align-items: center; padding: 0.6rem; border-bottom: 1px solid var(--glass-border); font-size: 0.8rem;">
                    <div>
                        <div style="font-weight: 600; color: #fff;">${b.filename}</div>
                        <div style="font-size: 0.7rem; color: var(--text-secondary);">${new Date(b.date).toLocaleString()} • ${b.size_kb} KB</div>
                    </div>
                    <button onclick="restoreBackup('${b.filename}')" 
                            style="background: transparent; border: 1px solid var(--primary); color: var(--primary); padding: 0.2rem 0.6rem; font-size: 0.7rem;">
                        Restore
                    </button>
                </div>
            `).join('');
        }
    } catch (e) { console.error('Error fetching backups:', e); }
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
            addAILog('✅ Backup creato con successo.', 'success');
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
    if (!confirm(`⚠️ Ripristinare i pesi dal backup ${filename}?\nL'addestramento in corso verrà interrotto.`)) return;

    try {
        const response = await fetch(`/api/v1/ai/restore?filename=${encodeURIComponent(filename)}`, {
            method: 'POST',
            headers: { 'X-API-Key': accessToken }
        });
        if (response.ok) {
            addAILog(`✅ Ripristino completato da ${filename}.`, 'success');
            setTimeout(refreshAIManagementData, 1000);
        } else {
            const err = await response.json();
            addAILog(`❌ Ripristino fallito: ${err.detail}`, 'error');
        }
    } catch (e) { addAILog(`❌ Errore ripristino: ${e.message}`, 'error'); }
}

// Intercept WebSocket messages for AI logs
if (typeof handleWsMessage !== 'undefined') {
    const originalHandleWsMessage = handleWsMessage;
    handleWsMessage = function (data) {
        originalHandleWsMessage(data);

        // Forward training logs to AI Management panel
        if (data.type === 'log' && (data.message.includes('training') || data.message.includes('complexity'))) {
            addAILog(data.message, data.level);
        }

        // Update reward indicator if available
        if (data.type === 'training_update') {
            const rewardVal = document.getElementById('curr-reward-val');
            if (rewardVal) {
                rewardVal.textContent = data.reward.toFixed(1);
                rewardVal.style.color = data.reward > -100 ? 'var(--success)' : 'var(--accent)';
            }
        }
    };
}
