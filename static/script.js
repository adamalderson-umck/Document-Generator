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

let sourceFileUploaded = false;
let sessionId = null;

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
