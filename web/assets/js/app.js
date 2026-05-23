/**
 * AI Data Framework - Frontend Application
 */

let selectedFile = null;

const dropZone = document.getElementById('dropZone');
const fileInput = document.getElementById('fileInput');
const runBtn = document.getElementById('runBtn');
const progress = document.getElementById('progress');
const results = document.getElementById('results');
const problemInput = document.getElementById('problemInput');
const llmSelect = document.getElementById('llmSelect');

// File input handlers
dropZone.addEventListener('click', () => fileInput.click());
dropZone.addEventListener('dragover', (e) => {
    e.preventDefault();
    dropZone.classList.add('dragover');
});
dropZone.addEventListener('dragleave', () => dropZone.classList.remove('dragover'));
dropZone.addEventListener('drop', (e) => {
    e.preventDefault();
    dropZone.classList.remove('dragover');
    if (e.dataTransfer.files.length) {
        setFile(e.dataTransfer.files[0]);
    }
});
fileInput.addEventListener('change', () => {
    if (fileInput.files.length) {
        setFile(fileInput.files[0]);
    }
});

/**
 * Set selected file and update UI
 * @param {File} f
 */
function setFile(f) {
    selectedFile = f;
    dropZone.querySelector('.upload-text').innerHTML =
        `<strong>${f.name}</strong> — ${(f.size / 1024).toFixed(1)} KB`;
}

/**
 * Update progress step UI
 * @param {string} step
 * @param {string} status - 'done' | 'active' | ''
 */
function setStep(step, status) {
    const el = document.querySelector(`.progress-step[data-step="${step}"]`);
    if (!el) return;
    el.classList.remove('done', 'active');
    if (status === 'done') el.classList.add('done');
    else if (status === 'active') el.classList.add('active');
}

/**
 * Switch between tabs
 * @param {string} name
 */
function showTab(name) {
    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
    document.querySelector(`.tab[onclick*="${name}"]`).classList.add('active');
    document.getElementById(`tab-${name}`).classList.add('active');
}

/**
 * Run the analytics pipeline
 */
async function runPipeline() {
    if (!selectedFile) {
        alert('Selecione um arquivo primeiro');
        return;
    }

    runBtn.disabled = true;
    runBtn.innerHTML = '<span class="spinner"></span>Executando...';
    progress.style.display = 'block';
    results.classList.remove('visible');

    const steps = ['load', 'profile', 'hypotheses', 'validate', 'insights'];
    steps.forEach(s => setStep(s, ''));
    steps.forEach(s => setStep(s, 'active'));

    const formData = new FormData();
    formData.append('file', selectedFile);
    formData.append('problem', problemInput.value || 'Análise geral');
    formData.append('llm', llmSelect.value);

    try {
        const resp = await fetch('/api/run', {
            method: 'POST',
            body: formData,
        });
        const data = await resp.json();

        if (data.status === 'success') {
            steps.forEach(s => setStep(s, 'done'));
            renderResults(data);
        } else {
            alert('Erro: ' + (data.detail || JSON.stringify(data)));
        }
    } catch (e) {
        alert('Erro: ' + e.message);
    } finally {
        runBtn.disabled = false;
        runBtn.innerHTML = '▶ Executar';
    }
}

/**
 * Render pipeline results in UI
 * @param {Object} data
 */
function renderResults(data) {
    results.classList.add('visible');

    const ds = data.dataset;
    const confirmed = data.hypotheses.filter(h => h.status === 'CONFIRMADA').length;
    const refuted = data.hypotheses.filter(h => h.status === 'REFUTADA').length;

    // Stats grid
    document.getElementById('statsGrid').innerHTML = `
        <div class="stat">
            <div class="value">${ds.rows.toLocaleString()}</div>
            <div class="label">Linhas</div>
        </div>
        <div class="stat">
            <div class="value">${ds.columns}</div>
            <div class="label">Colunas</div>
        </div>
        <div class="stat">
            <div class="value">${data.hypotheses.length}</div>
            <div class="label">Hipóteses</div>
        </div>
        <div class="stat">
            <div class="value">${data.insights.length}</div>
            <div class="label">Insights</div>
        </div>`;

    // Completeness color
    const completenessColor = ds.quality.completeness > 80
        ? 'var(--success)'
        : ds.quality.completeness > 50
            ? 'var(--warning)'
            : 'var(--danger)';

    // Overview tab
    document.getElementById('tab-overview').innerHTML = `
        <div class="card">
            <h2>📊 ${escapeHtml(ds.name)}</h2>
            <div class="quality-metrics">
                <div class="quality-metric">
                    <div class="value" style="color:${completenessColor}">${ds.quality.completeness}%</div>
                    <div class="label">Completude</div>
                </div>
                <div class="quality-metric">
                    <div class="value" style="color:${ds.quality.duplicates === 0 ? 'var(--success)' : 'var(--danger)'}">${ds.quality.duplicates}</div>
                    <div class="label">Duplicados</div>
                </div>
                <div class="quality-metric">
                    <div class="value">${Object.keys(ds.quality.nulls || {}).length}</div>
                    <div class="label">Cols c/ Nulos</div>
                </div>
            </div>
            <div class="quality-bar">
                <div class="quality-bar-fill" style="width:${ds.quality.completeness}%;background:${completenessColor}"></div>
            </div>
        </div>
        <div class="card">
            <h2>📈 Hipóteses</h2>
            <span class="badge badge-success">${confirmed} Confirmadas</span>
            <span class="badge badge-danger">${refuted} Refutadas</span>
            <span class="badge badge-warning">${data.hypotheses.length - confirmed - refuted} Parciais</span>
        </div>`;

    // Hypotheses tab
    document.getElementById('tab-hypotheses').innerHTML = data.hypotheses.length
        ? data.hypotheses.map(h => `
            <div class="hypothesis-item ${h.status.toLowerCase()}">
                <div class="title">${escapeHtml(h.title)}</div>
                <div class="meta">
                    <span class="badge badge-${h.status === 'CONFIRMADA' ? 'success' : h.status === 'REFUTADA' ? 'danger' : 'warning'}">${h.status}</span>
                    <span>Confiança: ${Math.round(h.confidence * 100)}%</span>
                    <span>Impacto: ${h.expected_impact}</span>
                </div>
                <p style="color:var(--text-dim);font-size:0.9rem;margin-top:0.5rem">${escapeHtml(h.description)}</p>
            </div>`).join('')
        : '<div class="empty">Nenhuma hipótese gerada</div>';

    // Insights tab
    document.getElementById('tab-insights').innerHTML = data.insights.length
        ? data.insights.map(i => `
            <div class="insight-item">
                <div class="title">💡 ${escapeHtml(i.title)}</div>
                <div class="desc">${escapeHtml(i.description)}</div>
                <div class="meta">
                    <span class="badge badge-${i.business_impact === 'Alto' ? 'danger' : i.business_impact === 'Médio' ? 'warning' : 'info'}">${i.business_impact}</span>
                    <span>Confiança: ${Math.round(i.confidence * 100)}%</span>
                </div>
                <div class="recs">
                    <strong>Recomendações:</strong>
                    <ul>${i.recommendations.map(r => `<li>${escapeHtml(r)}</li>`).join('')}</ul>
                </div>
            </div>`).join('')
        : '<div class="empty">Nenhum insight gerado</div>';

    // Quality tab
    const nulls = ds.quality.nulls || {};
    document.getElementById('tab-quality').innerHTML = Object.keys(nulls).length
        ? Object.entries(nulls).map(([col, pct]) => `
            <div style="margin-bottom:1rem">
                <div style="display:flex;justify-content:space-between;font-size:0.9rem">
                    <span>${escapeHtml(col)}</span>
                    <span style="color:${pct > 20 ? 'var(--danger)' : 'var(--text-dim)'}">${pct}%</span>
                </div>
                <div class="quality-bar">
                    <div class="quality-bar-fill" style="width:${pct}%;background:${pct > 20 ? 'var(--danger)' : 'var(--accent)'}"></div>
                </div>
            </div>`).join('')
        : '<div class="empty">Nenhuma coluna com nulos</div>';

    showTab('overview');
}

/**
 * Escape HTML to prevent XSS
 * @param {string} str
 * @returns {string}
 */
function escapeHtml(str) {
    if (!str) return '';
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}

// Make functions globally available
window.runPipeline = runPipeline;
window.showTab = showTab;