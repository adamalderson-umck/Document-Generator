const dropZone = document.getElementById('dropZone');
const fileInput = document.getElementById('fileInput');
const fileName = document.getElementById('fileName');
const email1 = document.getElementById('email1');
const email2 = document.getElementById('email2');
const analyzeBtn = document.getElementById('analyzeBtn'); // Renamed from generateBtn
const step3 = document.getElementById('step3');
const dynamicInputs = document.getElementById('dynamicInputs');
const generateFinalBtn = document.getElementById('generateFinalBtn');
const logContent = document.getElementById('logContent');
const warningBox = document.getElementById('warningBox');
const warningContent = document.getElementById('warningContent');
const weeklyReviewSection = document.getElementById('weeklyReviewSection');
const weeklyReviewSummary = document.getElementById('weeklyReviewSummary');
const weeklyReviewSources = document.getElementById('weeklyReviewSources');
const attentionFields = document.getElementById('attentionFields');
const allReviewFields = document.getElementById('allReviewFields');
const saveReviewBtn = document.getElementById('saveReviewBtn');
const generateFromReviewBtn = document.getElementById('generateFromReviewBtn');
const showManualBtn = document.getElementById('showManualBtn');
const manualWorkflow = document.getElementById('manualWorkflow');

let sourceFileUploaded = false;
let sessionId = null;
let currentReviewFilename = null;
let currentReviewData = null;

// Logger
function log(msg, type = 'info') {
    const line = document.createElement('div');
    line.className = `log-line log-${type}`;
    line.textContent = `> ${msg}`;
    logContent.appendChild(line);
    logContent.scrollTop = logContent.scrollHeight;
}

function renderWarnings(warnings) {
    warningContent.innerHTML = '';
    if (!warnings || warnings.length === 0) {
        warningBox.classList.add('hidden');
        return;
    }

    warnings.forEach(message => {
        const line = document.createElement('div');
        line.className = 'warning-line';
        line.textContent = message;
        warningContent.appendChild(line);
    });
    warningBox.classList.remove('hidden');
}

function getErrorMessage(data, fallback) {
    const detail = data && data.detail;
    if (!detail) {
        return fallback;
    }
    if (typeof detail === 'string') {
        return detail;
    }
    if (Array.isArray(detail)) {
        return detail.map(item => {
            if (typeof item === 'string') {
                return item;
            }
            if (item && item.msg) {
                return item.msg;
            }
            return JSON.stringify(item);
        }).join('; ');
    }
    if (detail.msg) {
        return detail.msg;
    }
    return JSON.stringify(detail);
}

function reviewMeta() {
    return (currentReviewData && currentReviewData._review) || {};
}

function reviewFieldLabel(field, reason) {
    return reason ? `${formatLabel(field)} - ${formatLabel(reason)}` : formatLabel(field);
}

function reviewInputValue(field) {
    const value = currentReviewData[field];
    return value === null || value === undefined ? '' : value;
}

function updateReviewField(field, value) {
    currentReviewData[field] = value;
    document.querySelectorAll(`[data-review-field="${field}"]`).forEach(input => {
        if (input.type === 'checkbox') {
            input.checked = Boolean(value);
        } else if (input.value !== String(value)) {
            input.value = value;
        }
    });
}

function createReviewFieldControl(field, reason = '') {
    const group = document.createElement('div');
    group.className = 'input-group review-field';

    const label = document.createElement('label');
    label.textContent = reviewFieldLabel(field, reason);
    group.appendChild(label);

    if (field === 'is_communion_sunday') {
        const checkboxLabel = document.createElement('label');
        checkboxLabel.className = 'checkbox-field';
        const input = document.createElement('input');
        input.type = 'checkbox';
        input.dataset.reviewField = field;
        input.checked = Boolean(currentReviewData[field]);
        input.addEventListener('change', () => updateReviewField(field, input.checked));
        checkboxLabel.appendChild(input);
        checkboxLabel.appendChild(document.createTextNode('Yes'));
        group.appendChild(checkboxLabel);
        return group;
    }

    const input = document.createElement('input');
    input.type = 'text';
    input.dataset.reviewField = field;
    input.value = reviewInputValue(field);
    input.placeholder = field;
    input.addEventListener('input', () => updateReviewField(field, input.value));
    group.appendChild(input);

    return group;
}

function normalizedAttentionItems(meta) {
    if (Array.isArray(meta.attention_fields) && meta.attention_fields.length) {
        return meta.attention_fields;
    }

    const items = [];
    (meta.low_confidence_fields || []).forEach(item => {
        items.push({ ...item, reason: item.reason || 'low_confidence' });
    });
    (meta.conflicts || []).forEach(item => {
        items.push({ ...item, reason: item.reason || 'conflict' });
    });
    (meta.missing_usual_fields || []).forEach(item => {
        items.push({ ...item, reason: item.reason || 'usually_present_blank' });
    });
    return items;
}

function renderSourceSummary(meta) {
    weeklyReviewSources.innerHTML = '';
    const sources = meta.sources || [];
    if (!sources.length) {
        weeklyReviewSources.textContent = 'No source metadata recorded.';
        return;
    }

    sources.forEach(source => {
        const row = document.createElement('div');
        row.className = 'review-source';
        const label = source.kind || source.folder || source.type || 'source';
        const detail = source.subject || source.path || source.filename || source.note || '';
        row.textContent = detail ? `${label}: ${detail}` : label;
        weeklyReviewSources.appendChild(row);
    });
}

function renderWeeklyReview() {
    const meta = reviewMeta();
    const targetDate = meta.target_service_date || currentReviewFilename || 'unspecified date';
    weeklyReviewSummary.textContent = `${targetDate} - ${meta.status || 'needs_review'}`;
    renderSourceSummary(meta);

    attentionFields.innerHTML = '';
    const attention = normalizedAttentionItems(meta).filter(item => item);
    if (!attention.length) {
        const empty = document.createElement('div');
        empty.className = 'empty-state';
        empty.textContent = 'No attention fields.';
        attentionFields.appendChild(empty);
    } else {
        attention.forEach(item => {
            if (!item.field) {
                const note = document.createElement('div');
                note.className = 'empty-state';
                note.textContent = item.message || reviewFieldLabel(item.reason || 'attention', '');
                attentionFields.appendChild(note);
                return;
            }
            const control = createReviewFieldControl(item.field, item.reason || '');
            if (item.message) {
                const note = document.createElement('div');
                note.className = 'field-note';
                note.textContent = item.message;
                control.appendChild(note);
            }
            attentionFields.appendChild(control);
        });
    }

    allReviewFields.innerHTML = '';
    Object.keys(currentReviewData)
        .filter(field => field !== '_review')
        .forEach(field => allReviewFields.appendChild(createReviewFieldControl(field)));
}

async function loadLatestWeeklyReview() {
    try {
        const res = await fetch('/weekly_reviews/latest');
        const data = await res.json();
        if (!res.ok) {
            log(`Weekly review unavailable: ${getErrorMessage(data, 'No weekly review found')}`, 'warning');
            return;
        }

        currentReviewFilename = data.filename;
        currentReviewData = data.review;
        renderWeeklyReview();
        weeklyReviewSection.classList.remove('hidden');
        manualWorkflow.classList.add('hidden');
        log(`Loaded weekly review: ${currentReviewFilename}`, 'success');
    } catch (err) {
        log(`Weekly review unavailable: ${err.message}`, 'warning');
    }
}

async function saveCurrentReview() {
    if (!currentReviewFilename || !currentReviewData) {
        return;
    }

    saveReviewBtn.disabled = true;
    saveReviewBtn.textContent = 'Saving...';
    try {
        const res = await fetch(`/weekly_reviews/${currentReviewFilename}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ review: currentReviewData })
        });
        const data = await res.json();
        if (!res.ok) {
            throw new Error(getErrorMessage(data, 'Save failed'));
        }
        log(`Saved weekly review: ${data.filename}`, 'success');
        if (data.review) {
            currentReviewData = data.review;
            renderWeeklyReview();
        }
        saveReviewBtn.textContent = 'Saved';
    } catch (err) {
        log(`Error: ${err.message}`, 'error');
        saveReviewBtn.textContent = 'Retry Save';
    } finally {
        saveReviewBtn.disabled = false;
    }
}

async function generateFromReview() {
    if (!currentReviewFilename || !currentReviewData) {
        return;
    }

    generateFromReviewBtn.disabled = true;
    generateFromReviewBtn.textContent = 'Generating...';
    log('Generating final documents from weekly review...');

    try {
        const res = await fetch(`/weekly_reviews/${currentReviewFilename}/generate`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ review: currentReviewData })
        });
        const data = await res.json();
        renderWarnings(data.warnings);
        if (!res.ok) {
            throw new Error(getErrorMessage(data, 'Generation failed'));
        }
        log('Success! Documents created.', 'success');
        log(`Output: ${data.output_dir}`);
        if (data.generated_files) {
            data.generated_files.forEach(path => log(`Created: ${path}`));
        }
        if (data.missing_fields && data.missing_fields.length) {
            log(`Still blank or absent in template data: ${data.missing_fields.join(', ')}`, 'warning');
        }
        generateFromReviewBtn.textContent = 'Done! Open Outputs Folder';
    } catch (err) {
        log(`Error: ${err.message}`, 'error');
        generateFromReviewBtn.textContent = 'Retry Generation';
    } finally {
        generateFromReviewBtn.disabled = false;
    }
}

function showManualWorkflow() {
    manualWorkflow.classList.remove('hidden');
    manualWorkflow.scrollIntoView({ behavior: 'smooth' });
}

if (saveReviewBtn) {
    saveReviewBtn.addEventListener('click', saveCurrentReview);
}
if (generateFromReviewBtn) {
    generateFromReviewBtn.addEventListener('click', generateFromReview);
}
if (showManualBtn) {
    showManualBtn.addEventListener('click', showManualWorkflow);
}

// Drag & Drop
dropZone.addEventListener('click', () => fileInput.click());
fileInput.addEventListener('change', handleFileSelect);

dropZone.addEventListener('dragover', (e) => {
    e.preventDefault();
    dropZone.classList.add('active');
});

dropZone.addEventListener('dragleave', () => {
    dropZone.classList.remove('active');
});

dropZone.addEventListener('drop', (e) => {
    e.preventDefault();
    dropZone.classList.remove('active');
    if (e.dataTransfer.files.length) {
        uploadSource(e.dataTransfer.files[0]);
    }
});

function handleFileSelect(e) {
    if (e.target.files.length) {
        uploadSource(e.target.files[0]);
    }
}

async function uploadSource(file) {
    fileName.textContent = "Uploading...";

    const formData = new FormData();
    formData.append('file', file);

    try {
        log(`Uploading source: ${file.name}...`);
        const res = await fetch('/upload_source', {
            method: 'POST',
            body: formData
        });

        if (!res.ok) throw new Error("Upload failed");

        const data = await res.json();
        renderWarnings(data.warnings);
        sessionId = data.session_id;
        fileName.textContent = file.name + " ✅";
        log(`Parsed ${Object.keys(data.data).length} items from source!`, 'success');
        sourceFileUploaded = true;
        checkReady();

    } catch (err) {
        fileName.textContent = "Error ❌";
        log(`Error: ${err.message}`, 'error');
    }
}

// State Check
function checkReady() {
    if (sourceFileUploaded && sessionId) {
        analyzeBtn.disabled = false;
        analyzeBtn.textContent = "Process & Check for Missing Info 🔍";
    }
}

// 1. Analyze Inputs
analyzeBtn.addEventListener('click', async () => {
    analyzeBtn.disabled = true;
    analyzeBtn.textContent = "Analyzing...";
    log("Analyzing inputs and checking templates...");

    // reset step 3
    step3.classList.add('hidden');
    dynamicInputs.innerHTML = '';

    const formData = new FormData();
    formData.append('session_id', sessionId);
    formData.append('email_1', email1.value);
    formData.append('email_2', email2.value);

    try {
        const res = await fetch('/analyze_inputs', {
            method: 'POST',
            body: formData
        });

        const data = await res.json();
        renderWarnings(data.warnings);

        if (!res.ok) {
            throw new Error(getErrorMessage(data, "Analysis failed"));
        }

        if (data.status === 'needs_input') {
            log(`Found ${data.missing_fields.length} missing fields!`, 'warning');
            renderDynamicInputs(data.missing_fields);
            step3.classList.remove('hidden');
            step3.scrollIntoView({ behavior: 'smooth' });
            analyzeBtn.textContent = "Inputs Analyzed ✅";
        } else if (data.status === 'ready') {
            log("No missing fields found! Generating...", 'success');
            // If nothing missing, go straight to generation
            triggerFinalGeneration({});
            analyzeBtn.textContent = "Done ✅";
        } else {
            throw new Error("Analysis failed");
        }
    } catch (err) {
        log(`Error: ${err.message}`, 'error');
        analyzeBtn.disabled = false;
        analyzeBtn.textContent = "Retry Analysis";
    }
});

function renderDynamicInputs(fields) {
    dynamicInputs.innerHTML = '';
    fields.forEach(field => {
        const group = document.createElement('div');
        group.className = 'input-group';

        const label = document.createElement('label');
        label.textContent = formatLabel(field);

        const input = document.createElement('input');
        input.type = 'text';
        input.dataset.key = field;
        input.placeholder = `Enter value for ${field}...`;

        group.appendChild(label);
        group.appendChild(input);
        dynamicInputs.appendChild(group);
    });
}

function formatLabel(key) {
    // snake_case to Title Case
    return key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
}

// 2. Generate Final
generateFinalBtn.addEventListener('click', () => {
    const extraFields = {};
    const inputs = dynamicInputs.querySelectorAll('input');
    inputs.forEach(input => {
        if (input.value.trim()) {
            extraFields[input.dataset.key] = input.value.trim();
        }
    });

    triggerFinalGeneration(extraFields);
});

async function triggerFinalGeneration(extraFields) {
    generateFinalBtn.disabled = true;
    generateFinalBtn.textContent = "Generating...";
    log("Generating final documents...");

    try {
        const res = await fetch('/generate_final', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ session_id: sessionId, extra_fields: extraFields })
        });

        const data = await res.json();
        renderWarnings(data.warnings);

        if (!res.ok) {
            throw new Error(getErrorMessage(data, "Generation failed"));
        }

        if (data.status === 'success') {
            log("Success! Documents created.", 'success');
            log(`Output: ${data.output_dir}`);
            if (data.generated_files) {
                data.generated_files.forEach(path => log(`Created: ${path}`));
            }
            generateFinalBtn.textContent = "Done! Open Outputs Folder";
            generateFinalBtn.disabled = false;
        } else {
            throw new Error("Generation failed");
        }
    } catch (err) {
        log(`Error: ${err.message}`, 'error');
        generateFinalBtn.disabled = false;
        generateFinalBtn.textContent = "Retry Generation";
    }
}

loadLatestWeeklyReview();
