/**
 * Live Cryptography Workflow Visualizer Client Logic.
 *
 * Connects to Server-Sent Events (SSE) stream, renders interactive pipeline
 * nodes, manages mode switching, and queries Explain Mode documentation.
 */

(function () {
    'use strict';

    // Application State
    let currentMode = 'single';
    let isExecuting = false;
    let explainDocs = {};
    let sseSource = null;
    let stagedFilePath = null;
    let stagedFolderPath = null;
    let stagedReportPath = null;

    // Mode Node Configurations (Mapping stage IDs to Explain Node keys)
    const MODE_DEFINITIONS = {
        single: {
            title: "Single-File Encryption & Verification",
            subtitle: "In-memory encryption, sidecar generation, and round-trip verification.",
            nodes: [
                { id: "STAGE_INPUT", label: "Input Ingestion", sub: "SHA-256 Preflight", explainKey: "node_pkcs7" },
                { id: "STAGE_KEY", label: "Key & IV Derivation", sub: "128/192/256-bit", explainKey: "node_cipher_service" },
                { id: "STAGE_ENCRYPT", label: "AES Core Engine", sub: "CBC/ECB Encrypt", explainKey: "node_aes_cipher" },
                { id: "STAGE_VERIFY", label: "Round-Trip Verify", sub: "Assert Dec(Enc(P))==P", explainKey: "node_aes_cipher" },
                { id: "STAGE_COMPLETE", label: "Summary & Artifacts", sub: "Sidecar Packaging", explainKey: "node_cipher_service" }
            ],
            controlsHtml: `
                <div class="file-picker-wrapper">
                    <input type="file" id="stagedFileInput" class="hidden-file-input">
                    <button type="button" class="file-choose-btn" id="stagedFileChooseBtn">📁 Choose File</button>
                    <div class="file-meta-pill" id="stagedFileMeta">No file chosen</div>
                </div>
                <div class="control-group">
                    <label>KEY SIZE</label>
                    <select id="ctrlKeySize" class="control-select">
                        <option value="256" selected>AES-256</option>
                        <option value="192">AES-192</option>
                        <option value="128">AES-128</option>
                    </select>
                </div>
                <div class="control-group">
                    <label>CIPHER MODE</label>
                    <select id="ctrlMode" class="control-select">
                        <option value="CBC" selected>CBC</option>
                        <option value="ECB">ECB</option>
                    </select>
                </div>
            `
        },
        decrypt: {
            title: "Standalone Decryption Workflow",
            subtitle: "Ciphertext validation, IV recovery, AES decryption, and PKCS#7 unpadding.",
            nodes: [
                { id: "STAGE_INGEST", label: "Ciphertext Ingestion", sub: "Buffer & Sidecar Read", explainKey: "node_cipher_service" },
                { id: "STAGE_DECRYPT", label: "AES Decryption Engine", sub: "Inverse Cipher Transformation", explainKey: "node_aes_cipher" },
                { id: "STAGE_UNPAD", label: "PKCS#7 Removal", sub: "Padding Verification", explainKey: "node_pkcs7" },
                { id: "STAGE_COMPLETE", label: "Plaintext Output", sub: "Integrity Verified", explainKey: "node_cipher_service" }
            ],
            controlsHtml: `
                <div class="file-picker-wrapper">
                    <input type="file" id="decryptEncInput" class="hidden-file-input" accept=".enc">
                    <button type="button" class="file-choose-btn" id="decryptEncBtn">📁 Choose .enc File</button>
                    <div class="file-meta-pill" id="decryptEncMeta">No .enc file chosen</div>
                </div>
                <div id="sidecarDetectionResult" style="color: var(--color-success); font-size: 12px; font-weight: bold; margin-bottom: 10px; display: none;"></div>
                <div class="file-picker-wrapper">
                    <input type="file" id="decryptKeyInput" class="hidden-file-input" accept=".key">
                    <button type="button" class="file-choose-btn" id="decryptKeyBtn">🔑 Choose .key File</button>
                    <div class="file-meta-pill" id="decryptKeyMeta">No .key file chosen</div>
                </div>
                <div class="file-picker-wrapper" id="decryptIvWrapper">
                    <input type="file" id="decryptIvInput" class="hidden-file-input" accept=".iv">
                    <button type="button" class="file-choose-btn" id="decryptIvBtn">🛡️ Choose .iv File (CBC)</button>
                    <div class="file-meta-pill" id="decryptIvMeta">No .iv file chosen</div>
                </div>
                <div class="control-group">
                    <label>CIPHER MODE</label>
                    <select id="ctrlMode" class="control-select">
                        <option value="CBC" selected>CBC</option>
                        <option value="ECB">ECB</option>
                    </select>
                </div>
            `
        },
        batch: {
            title: "Batch Directory Encryption",
            subtitle: "Flat-directory preflight, atomic file replacement, and real-time progress callbacks.",
            nodes: [
                { id: "STAGE_PREFLIGHT", label: "Directory Discovery", sub: "Collision Planning", explainKey: "node_batch_orchestrator" },
                { id: "STAGE_FILE_PROGRESS", label: "Sequential Processing", sub: "Per-file Isolation", explainKey: "node_batch_orchestrator" },
                { id: "STAGE_COMPLETE", label: "Batch Summary", sub: "Manifest Log CSV", explainKey: "node_batch_orchestrator" }
            ],
            controlsHtml: `
                <div class="file-picker-wrapper">
                    <input type="file" id="batchFolderInput" class="hidden-file-input" webkitdirectory directory multiple>
                    <button type="button" class="file-choose-btn" id="batchFolderChooseBtn">📁 Choose Input Folder</button>
                    <div class="file-meta-pill" id="batchFolderMeta">No folder chosen</div>
                </div>
            `
        },
        benchmark: {
            title: "Benchmark Performance Suite",
            subtitle: "5 warmup iterations, 30 sample iterations, MetricCollector synthesis, and Tukey IQR fences.",
            nodes: [
                { id: "STAGE_CONFIG", label: "Configuration Matrix", sub: "4-6 AES Setups", explainKey: "node_benchmark_service" },
                { id: "STAGE_WARMUP", label: "Warmup Phase (5x)", sub: "Cache Priming (Discarded)", explainKey: "node_performance_timer" },
                { id: "STAGE_COMPLETE", label: "Measurement (30x)", sub: "MetricCollector Aggregation", explainKey: "node_metric_collector" }
            ],
            controlsHtml: ``
        },
        security: {
            title: "Security & Cryptanalysis Lab",
            subtitle: "One-bit mutation avalanche effect, key sensitivity, and ECB bitmap leakage analysis.",
            nodes: [
                { id: "STAGE_MUTATION", label: "1-Bit Mutation", sub: "P1 vs P2 (Hamming=1)", explainKey: "node_security_evaluator" },
                { id: "STAGE_AVALANCHE", label: "Avalanche Evaluation", sub: "Target ~50% Diffusion", explainKey: "node_security_evaluator" },
                { id: "STAGE_KEY_SENSITIVITY", label: "Key Sensitivity", sub: "Target ~50% Diffusion", explainKey: "node_security_evaluator" },
                { id: "STAGE_COMPLETE", label: "Visual Cryptanalysis", sub: "CBC vs ECB Dispersion", explainKey: "node_security_evaluator" }
            ],
            controlsHtml: ``
        },
        file_lab: {
            title: "File-Specific Analysis Lab",
            subtitle: "Microbenchmarking matrix across all 6 AES configurations for a single target file.",
            nodes: [
                { id: "STAGE_PREFLIGHT", label: "Preflight Inspection", sub: "Size & SHA-256", explainKey: "node_file_analysis_runner" },
                { id: "STAGE_CONFIG_RUN", label: "Six AES Matrix", sub: "128/192/256 x CBC/ECB", explainKey: "node_file_analysis_runner" },
                { id: "STAGE_COMPLETE", label: "Comparative Analysis", sub: "Fastest Observed Config", explainKey: "node_file_analysis_runner" }
            ],
            controlsHtml: `
                <div class="file-picker-wrapper">
                    <input type="file" id="stagedFileInput" class="hidden-file-input">
                    <button type="button" class="file-choose-btn primary-file-btn" id="stagedFileChooseBtn">📁 Select Target File for Analysis</button>
                    <div class="file-meta-pill" id="stagedFileMeta">No file selected — click to choose file</div>
                </div>
            `
        }
    };

    // DOM Elements
    const elements = {
        modeBtns: document.querySelectorAll('.mode-btn'),
        stageTitle: document.getElementById('stageTitle'),
        stageSubtitle: document.getElementById('stageSubtitle'),
        modeControls: document.getElementById('modeControls'),
        runBtn: document.getElementById('runBtn'),
        pipelineFlow: document.getElementById('pipelineFlow'),
        telemetryGrid: document.getElementById('telemetryGrid'),
        statusPill: document.getElementById('statusPill'),
        statusText: document.getElementById('statusText'),
        explainToggleBtn: document.getElementById('explainToggleBtn'),
        explainDrawer: document.getElementById('explainDrawer'),
        explainTitle: document.getElementById('explainTitle'),
        explainContent: document.getElementById('explainContent'),
        closeDrawerBtn: document.getElementById('closeDrawerBtn'),
        shutdownBtn: document.getElementById('shutdownBtn'),
        serverUrl: document.getElementById('serverUrl')
    };

    // Initialize Application
    function init() {
        elements.serverUrl.textContent = window.location.host;
        setupEventListeners();
        fetchExplainDocs();
        switchMode('single');
        connectSSE();
    }

    function setupEventListeners() {
        elements.modeBtns.forEach(btn => {
            btn.addEventListener('click', () => {
                if (isExecuting) return;
                elements.modeBtns.forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                switchMode(btn.dataset.mode);
            });
        });

        elements.runBtn.addEventListener('click', executeActiveWorkflow);

        elements.explainToggleBtn.addEventListener('click', () => {
            elements.explainDrawer.classList.toggle('closed');
        });

        elements.closeDrawerBtn.addEventListener('click', () => {
            elements.explainDrawer.classList.add('closed');
        });

        const openReportBtn = document.getElementById('openReportBtn');
        if (openReportBtn) {
            openReportBtn.addEventListener('click', () => {
                if (window.stagedOutputDir) {
                    fetch('/api/open_folder?path=' + encodeURIComponent(window.stagedOutputDir))
                        .catch(err => alert("Failed to open output folder: " + err));
                } else if (stagedReportPath) {
                    fetch('/api/open_report?path=' + encodeURIComponent(stagedReportPath))
                        .catch(err => alert("Failed to open report: " + err));
                }
            });
        }

        elements.shutdownBtn.addEventListener('click', () => {
            if (confirm("Stop the visualizer server and return to the V2 command-line menu?")) {
                fetch('/api/shutdown', { method: 'POST' }).then(() => {
                    alert("Visualizer server stopped cleanly. You can return to your terminal.");
                    window.close();
                });
            }
        });
    }

    function fetchExplainDocs() {
        fetch('/api/explain')
            .then(res => res.json())
            .then(data => { explainDocs = data; })
            .catch(() => {});
    }

    function switchMode(mode) {
        currentMode = mode;
        const def = MODE_DEFINITIONS[mode];
        if (!def) return;

        stagedFilePath = null;
        stagedFolderPath = null;
        stagedReportPath = null;
        const reportAction = document.getElementById('reportActionContainer');
        if (reportAction) reportAction.style.display = 'none';

        elements.stageTitle.textContent = def.title;
        elements.stageSubtitle.textContent = def.subtitle;
        elements.modeControls.innerHTML = def.controlsHtml;

        setupFilePickers(mode);

        renderPipelineNodes(def.nodes);
        clearTelemetry();
    }

    function setupFilePickers(mode) {
        const fileInput = document.getElementById('stagedFileInput');
        const fileBtn = document.getElementById('stagedFileChooseBtn');
        const fileMeta = document.getElementById('stagedFileMeta');

        if (fileInput && fileBtn && fileMeta) {
            fileBtn.addEventListener('click', () => fileInput.click());
            fileInput.addEventListener('change', (e) => {
                if (e.target.files.length > 0) {
                    uploadFile(e.target.files[0], fileMeta, false);
                }
            });
        }

        const encInput = document.getElementById('decryptEncInput');
        const encBtn = document.getElementById('decryptEncBtn');
        const encMeta = document.getElementById('decryptEncMeta');
        const keyInput = document.getElementById('decryptKeyInput');
        const keyBtn = document.getElementById('decryptKeyBtn');
        const keyMeta = document.getElementById('decryptKeyMeta');
        const ivInput = document.getElementById('decryptIvInput');
        const ivBtn = document.getElementById('decryptIvBtn');
        const ivMeta = document.getElementById('decryptIvMeta');
        const modeSelect = document.getElementById('ctrlMode');
        const ivWrapper = document.getElementById('decryptIvWrapper');

        if (modeSelect && ivWrapper) {
            modeSelect.addEventListener('change', (e) => {
                if (e.target.value === 'ECB') {
                    ivWrapper.style.display = 'none';
                    if (window.currentInputs) delete window.currentInputs.iv_path;
                } else {
                    ivWrapper.style.display = 'block';
                }
            });
        }

        const setupSingleUploader = (input, btn, meta, fieldName, isEnc = false) => {
            if (input && btn && meta) {
                btn.addEventListener('click', () => input.click());
                input.addEventListener('change', async (e) => {
                    if (e.target.files.length > 0) {
                        const path = await uploadFile(e.target.files[0], meta, false, null, null, fieldName);
                        if (isEnc && path) {
                            // Trigger sidecar detection
                            try {
                                const res = await fetch(`/api/detect_sidecars?path=${encodeURIComponent(path)}`);
                                if (res.ok) {
                                    const data = await res.json();
                                    const alertDiv = document.getElementById('sidecarDetectionResult');
                                    if (data.key || data.iv) {
                                        alertDiv.style.display = 'block';
                                        alertDiv.textContent = '✓ Matching sidecar files detected';

                                        if (data.key) {
                                            window.currentInputs = window.currentInputs || {};
                                            window.currentInputs.key_path = data.key;
                                            keyMeta.textContent = `Auto-detected: ${data.key.split(/[\\/]/).pop()}`;
                                        }
                                        if (data.iv) {
                                            window.currentInputs = window.currentInputs || {};
                                            window.currentInputs.iv_path = data.iv;
                                            ivMeta.textContent = `Auto-detected: ${data.iv.split(/[\\/]/).pop()}`;
                                        }
                                    }
                                }
                            } catch (err) {
                                console.error('Sidecar detection failed', err);
                            }
                        }
                    }
                });
            }
        };

        setupSingleUploader(encInput, encBtn, encMeta, "enc_path", true);
        setupSingleUploader(keyInput, keyBtn, keyMeta, "key_path");
        setupSingleUploader(ivInput, ivBtn, ivMeta, "iv_path");

        const folderInput = document.getElementById('batchFolderInput');
        const folderBtn = document.getElementById('batchFolderChooseBtn');
        const folderMeta = document.getElementById('batchFolderMeta');

        if (folderInput && folderBtn && folderMeta) {
            folderBtn.addEventListener('click', () => folderInput.click());
            folderInput.addEventListener('change', async (e) => {
                const files = e.target.files;
                if (files.length > 0) {
                    folderMeta.textContent = `Uploading ${files.length} files...`;
                    const batchId = Date.now().toString() + Math.floor(Math.random() * 1000).toString();
                    let successCount = 0;
                    for (let i = 0; i < files.length; i++) {
                        const isLast = (i === files.length - 1);
                        const ok = await uploadFile(files[i], folderMeta, true, isLast ? `Staged ${files.length} files` : null, batchId);
                        if (ok) successCount++;
                    }
                    if (successCount !== files.length) {
                        stagedFolderPath = null;
                        folderMeta.textContent = "Upload failed partially";
                    }
                }
            });
        }
    }

    async function uploadFile(file, metaEl, isBatch, finalMetaText=null, batchId=null, fieldName=null) {
        if (file.size > 100 * 1024 * 1024) {
            alert("File exceeds 100MB limit.");
            return null;
        }
        metaEl.textContent = `Uploading ${file.name}...`;

        try {
            const headers = {
                'X-Filename': encodeURIComponent(file.name)
            };
            if (isBatch && batchId) {
                headers['X-Batch-ID'] = batchId;
            }

            const res = await fetch(isBatch ? '/api/stage_batch_file' : '/api/stage_file', {
                method: 'POST',
                headers: headers,
                body: file
            });
            const data = await res.json();
            if (res.ok) {
                if (!isBatch) {
                    if (fieldName) {
                        window.currentInputs = window.currentInputs || {};
                        window.currentInputs[fieldName] = data.file_path;
                    } else {
                        stagedFilePath = data.file_path;
                    }
                    metaEl.textContent = `📄 ${file.name} (${(file.size/1024).toFixed(1)} KB)`;
                } else {
                    stagedFolderPath = data.folder_path;
                    if (finalMetaText) {
                        metaEl.textContent = `📁 ${finalMetaText}`;
                    }
                }
                return data.file_path || data.folder_path || true;
            } else {
                metaEl.textContent = "Upload failed";
                alert(data.error || "Upload failed");
                return null;
            }
        } catch (err) {
            metaEl.textContent = "Upload error";
            alert("Upload error: " + err);
            return null;
        }
    }

    function renderPipelineNodes(nodes) {
        elements.pipelineFlow.innerHTML = '';

        nodes.forEach((node, idx) => {
            const nodeEl = document.createElement('div');
            nodeEl.className = 'pipeline-node';
            nodeEl.id = `node_${node.id}`;
            nodeEl.dataset.explainKey = node.explainKey;

            nodeEl.innerHTML = `
                <div class="node-title">${node.label}</div>
                <div class="node-sub">${node.sub}</div>
                <div class="node-badge">STEP ${idx + 1}</div>
            `;

            nodeEl.addEventListener('click', () => showExplain(node.explainKey));
            elements.pipelineFlow.appendChild(nodeEl);

            if (idx < nodes.length - 1) {
                const connector = document.createElement('div');
                connector.className = 'pipeline-connector';
                connector.id = `conn_${idx}`;
                elements.pipelineFlow.appendChild(connector);
            }
        });
    }

    function showExplain(key) {
        const doc = explainDocs[key];
        elements.explainDrawer.classList.remove('closed');

        if (!doc) {
            elements.explainTitle.textContent = "Component Architecture";
            elements.explainContent.innerHTML = `<p class="drawer-hint">No architectural metadata found for this component.</p>`;
            return;
        }

        elements.explainTitle.textContent = doc.title;
        elements.explainContent.innerHTML = `
            <div class="explain-block">
                <h4>Module Path</h4>
                <p><code>${doc.module}</code></p>
            </div>
            <div class="explain-block">
                <h4>Architectural Role</h4>
                <p>${doc.role}</p>
            </div>
            <div class="explain-block">
                <h4>Cryptographic Invariants</h4>
                <ul>
                    ${doc.invariants.map(inv => `<li>${inv}</li>`).join('')}
                </ul>
            </div>
            <div class="explain-block">
                <h4>Timing Boundary</h4>
                <p>${doc.timing_boundary}</p>
            </div>
            ${doc.formula ? `
                <div class="explain-block">
                    <h4>Mathematical Formulation</h4>
                    <p><code>${doc.formula}</code></p>
                </div>
            ` : ''}
            <div class="explain-block">
                <h4>Freeze Status</h4>
                <p>${doc.freeze_reference}</p>
            </div>
        `;
    }

    function executeActiveWorkflow() {
        if (isExecuting) return;

        setExecutionState(true);
        resetNodeStates();

        const payload = {};
        const ctrlKeySize = document.getElementById('ctrlKeySize');
        const ctrlMode = document.getElementById('ctrlMode');

        if (ctrlKeySize) payload.key_size = ctrlKeySize.value;
        if (ctrlMode) payload.mode = ctrlMode.value;
        if (stagedFilePath) payload.file_path = stagedFilePath;
        if (stagedFolderPath) payload.folder_path = stagedFolderPath;
        if (currentMode === 'decrypt' && window.currentInputs) {
            Object.assign(payload, window.currentInputs);
        }

        fetch(`/api/run/${currentMode}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        })
        .then(res => {
            if (res.status === 409) {
                alert("A workflow is already in progress. Please wait for it to complete.");
                setExecutionState(false);
            }
        })
        .catch(err => {
            alert(`Execution failed to start: ${err}`);
            setExecutionState(false);
        });
    }

    function setExecutionState(busy) {
        isExecuting = busy;
        elements.runBtn.disabled = busy;
        elements.runBtn.classList.toggle('running', busy);

        if (busy) {
            elements.statusPill.className = 'status-pill status-running';
            elements.statusText.textContent = 'EXECUTING';
        } else {
            elements.statusPill.className = 'status-pill status-idle';
            elements.statusText.textContent = 'IDLE';
        }
    }

    function resetNodeStates() {
        document.querySelectorAll('.pipeline-node').forEach(node => {
            node.className = 'pipeline-node';
        });
        document.querySelectorAll('.pipeline-connector').forEach(conn => {
            conn.classList.remove('active');
        });
    }

    function clearTelemetry() {
        elements.telemetryGrid.innerHTML = `
            <div class="telemetry-card">
                <span class="card-label">STATUS</span>
                <span class="card-value highlight-cyan">READY</span>
            </div>
            <div class="telemetry-card">
                <span class="card-label">ACTIVE MODE</span>
                <span class="card-value">${currentMode.toUpperCase()}</span>
            </div>
        `;
    }

    function connectSSE() {
        if (sseSource) sseSource.close();

        sseSource = new EventSource('/api/events');

        sseSource.addEventListener('connect', (e) => {
            const data = JSON.parse(e.data);
            if (data.active_workflow) {
                setExecutionState(true);
            }
        });

        sseSource.addEventListener('workflow_event', (e) => {
            const evt = JSON.parse(e.data);
            handleWorkflowEvent(evt);
        });

        sseSource.onerror = () => {
            elements.statusPill.className = 'status-pill status-idle';
            elements.statusText.textContent = 'RECONNECTING';
        };
    }

    function handleWorkflowEvent(evt) {
        if (evt.workflow !== currentMode) return;

        // Update pipeline nodes
        const activeNode = document.getElementById(`node_${evt.stage}`);
        if (activeNode) {
            if (evt.status === 'ACTIVE') {
                activeNode.classList.add('active');
            } else if (evt.status === 'COMPLETE') {
                activeNode.classList.remove('active');
                activeNode.classList.add('complete');
            } else if (evt.status === 'ERROR') {
                activeNode.classList.add('error');
            }
        }

        // Render Telemetry Cards
        if (evt.data && Object.keys(evt.data).length > 0) {
            const container = document.getElementById('reportActionContainer');
            const openReportBtn = document.getElementById('openReportBtn');
            if (evt.data.report_path) {
                stagedReportPath = evt.data.report_path;
                window.stagedOutputDir = null;
                if (container) container.style.display = 'block';
                if (openReportBtn) openReportBtn.textContent = '📄 Open Report';
            } else if (evt.data.output_dir) {
                stagedReportPath = null;
                window.stagedOutputDir = evt.data.output_dir;
                if (container) container.style.display = 'block';
                if (openReportBtn) openReportBtn.textContent = '📁 Open Output Folder';
            }
            renderTelemetryData(evt.stage, evt.data);
        }

        if (evt.stage === 'STAGE_FINISHED' || evt.stage === 'STAGE_ERROR' || evt.stage === 'STAGE_COMPLETE') {
            setExecutionState(false);
        }
    }

    function renderTelemetryData(stage, data) {
        // Rebuild cards from real event payload
        Object.entries(data).forEach(([key, val]) => {
            if (key === 'files' || key === 'all_configs_summary' || key === 'raw_times_ms') {
                return; // complex items handled in detailed views
            }

            const formattedKey = key.replace(/_/g, ' ').toUpperCase();
            let card = document.getElementById(`card_${key}`);

            if (!card) {
                card = document.createElement('div');
                card.className = 'telemetry-card';
                card.id = `card_${key}`;
                elements.telemetryGrid.appendChild(card);
            }

            let displayVal = typeof val === 'object' && val !== null ? JSON.stringify(val) : String(val);
            let highlightClass = '';

            if (typeof val === 'number') {
                highlightClass = 'highlight-cyan';
                displayVal = key.includes('ms') ? `${val} ms` : String(val);
            } else if (displayVal.includes('PASSED') || displayVal.includes('VERIFIED')) {
                highlightClass = 'highlight-emerald';
            }

            card.innerHTML = `
                <span class="card-label">${formattedKey}</span>
                <span class="card-value ${highlightClass}">${displayVal}</span>
            `;
        });
    }

    // Launch
    window.addEventListener('DOMContentLoaded', init);
})();
