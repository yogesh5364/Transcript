/* ==========================================================================
   Config
   ========================================================================== */

const API = '/api/transcripts';

let currentId = null;
let statusInterval = null;
let activeTab = 'file';

/* ==========================================================================
   CSRF helper
   ========================================================================== */

function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

/* ==========================================================================
   Tab switching
   ========================================================================== */

function switchTab(tab) {
    activeTab = tab;
    document.getElementById('tab-file').classList.toggle('active', tab === 'file');
    document.getElementById('tab-youtube').classList.toggle('active', tab === 'youtube');
    document.getElementById('file-tab').style.display = tab === 'file' ? 'block' : 'none';
    document.getElementById('youtube-tab').style.display = tab === 'youtube' ? 'block' : 'none';
}

/* ==========================================================================
   Upload flow
   ========================================================================== */

async function uploadTranscript() {
    const btn = document.getElementById('upload-btn');
    const lang = document.getElementById('language').value;
    const formData = new FormData();
    formData.append('language', lang);

    if (activeTab === 'file') {
        const file = document.getElementById('audio-file').files[0];
        if (!file) {
            alert('Please select a file first.');
            return;
        }
        formData.append('audio_file', file);
        formData.append('source_type', 'file');
    } else {
        const url = document.getElementById('youtube-url').value.trim();
        if (!url) {
            alert('Please enter a YouTube URL.');
            return;
        }
        formData.append('youtube_url', url);
        formData.append('source_type', 'youtube');
    }

    setButtonLoading(btn, true);
    hideResults();

    try {
        const res = await fetch(`${API}/upload/`, {
            method: 'POST',
            body: formData,
            headers: {
                'X-CSRFToken': getCookie('csrftoken'),
            },
        });

        const data = await res.json();

        if (!data.id) {
            showStatus('failed', `Error: ${JSON.stringify(data)}`);
            setButtonLoading(btn, false);
            return;
        }

        currentId = data.id;
        showStatus('pending', `Transcript ID ${currentId} — processing started…`);
        startPolling();
        loadHistory();

    } catch (e) {
        showStatus('failed', 'Error: could not connect to the server.');
        setButtonLoading(btn, false);
    }
}

function setButtonLoading(btn, isLoading) {
    if (isLoading) {
        btn.disabled = true;
        btn.innerHTML = `
            <span class="eq-spinner"><span></span><span></span><span></span><span></span></span>
            Processing…`;
    } else {
        btn.disabled = false;
        btn.innerHTML = `
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2a3 3 0 0 0-3 3v6a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z"/><path d="M19 10v1a7 7 0 0 1-14 0v-1"/><line x1="12" y1="18" x2="12" y2="22"/></svg>
            Generate Transcript`;
    }
}

/* ==========================================================================
   Status polling
   ========================================================================== */

function startPolling() {
    if (statusInterval) clearInterval(statusInterval);
    statusInterval = setInterval(async () => {
        try {
            const res = await fetch(`${API}/${currentId}/status/`);
            const data = await res.json();

            if (data.status === 'done') {
                clearInterval(statusInterval);
                showStatus('done', 'Transcript is ready.');
                loadResult();
                setButtonLoading(document.getElementById('upload-btn'), false);
            } else if (data.status === 'failed') {
                clearInterval(statusInterval);
                showStatus('failed', `Error: ${data.error_message || 'Something went wrong.'}`);
                setButtonLoading(document.getElementById('upload-btn'), false);
            } else {
                showStatus(data.status, `Status: ${data.status}…`);
            }
        } catch (e) {}
    }, 3000);
}

/* ==========================================================================
   Result rendering
   ========================================================================== */

async function loadResult() {
    const res = await fetch(`${API}/${currentId}/`);
    const data = await res.json();
    currentId = data.id;

    document.getElementById('full-text').innerText = data.full_text || 'No text found.';
    document.getElementById('result-box').style.display = 'block';
    document.getElementById('export-btns').style.display = 'flex';

    const segList = document.getElementById('segments-list');
    segList.innerHTML = '';

    if (data.segments && data.segments.length > 0) {
        data.segments.forEach(seg => {
            segList.innerHTML += `
                <div class="segment">
                    <div class="time">${seg.start_time_formatted} → ${seg.end_time_formatted}</div>
                    <div class="text">${seg.text}</div>
                </div>`;
        });
        document.getElementById('segments-box').style.display = 'block';
    }

    loadHistory();
}

/* ==========================================================================
   Export
   ========================================================================== */

function exportTranscript(format) {
    if (!currentId) {
        alert('Please select a transcript first.');
        return;
    }
    window.open(`${API}/${currentId}/export/${format}/`, '_blank');
}

/* ==========================================================================
   Status / result visibility helpers
   ========================================================================== */

function showStatus(type, message) {
    const box = document.getElementById('status-box');
    box.className = `status-box status-${type}`;
    box.style.display = 'flex';
    document.getElementById('status-text').innerHTML = message;
}

function hideResults() {
    document.getElementById('result-box').style.display = 'none';
    document.getElementById('export-btns').style.display = 'none';
    document.getElementById('segments-box').style.display = 'none';
    document.getElementById('status-box').style.display = 'none';
}

/* ==========================================================================
   History
   ========================================================================== */

function updateStats(data) {
    const total = data.length;
    const done = data.filter(t => t.status === 'done').length;
    const processing = data.filter(t => t.status === 'processing' || t.status === 'pending').length;
    const failed = data.filter(t => t.status === 'failed').length;

    document.getElementById('stat-total').textContent = total;
    document.getElementById('stat-done').textContent = done;
    document.getElementById('stat-processing').textContent = processing;
    document.getElementById('stat-failed').textContent = failed;
}

async function loadHistory() {
    try {
        const res = await fetch(`${API}/`);
        const data = await res.json();
        const list = document.getElementById('history-list');

        updateStats(data);

        if (!data.length) {
            list.innerHTML = '<div class="history-empty">No transcripts yet.</div>';
            return;
        }

        list.innerHTML = data.map(t => `
            <div class="history-item ${t.id === currentId ? 'is-active' : ''}" onclick="loadFromHistory(${t.id})">
                <span class="history-status-dot ${t.status}"></span>
                <div class="history-body">
                    <div class="history-id">#${t.id} · ${t.source_type === 'youtube' ? 'YouTube' : 'File'} · ${t.language}</div>
                    ${t.youtube_url ? `<div class="history-meta">${t.youtube_url.substring(0, 50)}…</div>` : ''}
                </div>
                <span class="badge badge-${t.status}">${t.status}</span>
            </div>
        `).join('');
    } catch (e) {
        document.getElementById('history-list').innerHTML = '<div class="history-error">Could not load history.</div>';
    }
}

async function loadFromHistory(id) {
    currentId = id;
    hideResults();
    showStatus('done', `Loading transcript ID ${id}…`);
    await loadResult();
    showStatus('done', `Transcript ID ${id} loaded.`);
}

/* ==========================================================================
   Misc UI niceties
   ========================================================================== */

document.addEventListener('DOMContentLoaded', () => {
    const fileInput = document.getElementById('audio-file');
    const fileText = document.getElementById('file-drop-text');
    if (fileInput) {
        fileInput.addEventListener('change', () => {
            fileText.textContent = fileInput.files[0]
                ? fileInput.files[0].name
                : 'Click to choose a file, or drag it here';
        });
    }
});

/* ==========================================================================
   Init
   ========================================================================== */

loadHistory();
setInterval(loadHistory, 60000);