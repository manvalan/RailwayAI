
// ==================== AI Management Functions ====================

async function loadAIManagement() {
    await Promise.all([
        fetchAIStatus(),
        fetchScenarios(),
        fetchModelStats(),
        loadAIConfig(),
        populateScenarioDropdown(),
        fetchAIQualityMetrics()
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
