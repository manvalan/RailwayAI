
// ==================== AI Management Functions ====================

async function loadAIManagement() {
    await Promise.all([
        fetchAIStatus(),
        fetchScenarios(),
        fetchModelStats(),
        loadAIConfig(),
        populateScenarioDropdown(),
        fetchAIQualityMetrics(),
        fetchNetworkStats()
    ]);

    // Slider listener
    const slider = document.getElementById('config-threshold');
    const valDisplay = document.getElementById('config-threshold-val');
    if (slider && valDisplay) {
        slider.addEventListener('input', (e) => {
            valDisplay.textContent = e.target.value + 's';
        });
    }

    // Subscribe to training logs via WebSocket
    if (ws && ws.readyState === WebSocket.OPEN) {
        // Logs will come through existing WebSocket connection
    }
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
                indicator.style.background = 'var(--success)';
                indicator.style.boxShadow = '0 0 8px var(--success)';
                statusText.innerHTML = `<span style="color:var(--success)">Training in corso:</span> ${data.current_scenario}`;
                statusText.style.fontWeight = '600';
            } else {
                indicator.style.background = 'var(--text-secondary)';
                indicator.style.boxShadow = 'none';
                if (data.seconds_until_next_run > 0) {
                    statusText.textContent = `Attesa (${data.seconds_until_next_run}s) - Next: ${data.queued_scenario}`;
                } else {
                    statusText.textContent = `Avvio in corso...`;
                }
                statusText.style.fontWeight = 'normal';
            }

            // 2. Logs Preview
            const logsContainer = document.getElementById('ai-logs');
            if (logsContainer) {
                if (data.logs_preview && data.logs_preview.length > 0) {
                    logsContainer.innerHTML = data.logs_preview.map(l => `<div style="margin-bottom:2px;">${l}</div>`).join('');
                    // Auto scroll to bottom
                    logsContainer.scrollTop = logsContainer.scrollHeight;
                } else {
                    // Show history if no active logs
                    if (data.history && data.history.length > 0) {
                        const historyHtml = data.history.map(h => {
                            const color = h.status === 'completed' ? 'var(--success)' : 'var(--accent)';
                            return `
                                <div style="border-left: 2px solid ${color}; padding-left: 0.5rem; margin-bottom: 0.5rem;">
                                    <div style="font-size: 0.75rem; color: var(--text-secondary);">${new Date(h.timestamp).toLocaleTimeString()}</div>
                                    <div>${h.scenario} - <span style="color:${color}">${h.status}</span> (${h.duration_seconds}s)</div>
                                </div>
                             `;
                        }).join('');
                        logsContainer.innerHTML = `<div style="color:var(--text-secondary); margin-bottom:0.5rem; font-weight:600;">Last Activity:</div>` + historyHtml;
                    } else {
                        logsContainer.innerHTML = '<div style="color:var(--text-secondary)">Nessuna attività recente.</div>';
                    }
                }
            }

            // 3. Update Sliders/Inputs if not focused (avoid fighting user)
            if (document.activeElement.id !== 'config-threshold') {
                // Update specific config fields if returned, but usually config is separate.
                // We trust get_status_report covers operational state.
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
                            if (selectEl) selectEl.value = s.filename;
                            // Reset styles
                            Array.from(listEl.children).forEach(c => c.style.background = 'transparent');
                            item.style.background = 'rgba(255,255,255,0.1)';
                        };

                        item.innerHTML = `
                            <div style="display: flex; justify-content: space-between; align-items: start;">
                                <div>
                                    <div style="font-weight: 600; font-size: 0.9rem; color: #fff;">${s.name}</div>
                                    <div style="font-size: 0.75rem; color: var(--text-secondary); margin-top: 2px;">
                                        ${s.stations} stazioni • ${s.tracks} binari
                                    </div>
                                </div>
                                <div style="font-size: 0.7rem; color: var(--text-secondary);">
                                    ${new Date(s.modified * 1000).toLocaleDateString('it-IT')}
                                </div>
                            </div>
                        `;
                        listEl.appendChild(item);
                    }

                    // Populate Dropdown
                    if (selectEl) {
                        const option = document.createElement('option');
                        option.value = s.filename;
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

// Intercept WebSocket messages for AI logs (only if handleWsMessage exists)
if (typeof handleWsMessage !== 'undefined') {
    const originalHandleWsMessage = handleWsMessage;
    handleWsMessage = function (data) {
        originalHandleWsMessage(data);

        // Forward training logs to AI Management panel
        if (data.type === 'log' && data.message.includes('training')) {
            addAILog(data.message, data.level);
        }
    };
}
