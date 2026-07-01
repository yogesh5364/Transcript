const API = '/api/transcripts';
let currentId = null;
let statusInterval = null;
let activeTab = 'file';

// CSRF Token Helper
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

// Tab Switch
function switchTab(tab) {
    activeTab = tab;
    document.getElementById('tab-file').classList.toggle('active', tab === 'file');
    document.getElementById('tab-youtube').classList.toggle('active', tab === 'youtube');
    document.getElementById('file-tab').style.display = tab === 'file' ? 'block' : 'none';
    document.getElementById('youtube-tab').style.display = tab === 'youtube' ? 'block' : 'none';
}

// Upload Transcript
async function uploadTranscript() {
    const btn = document.getElementById('upload-btn');
    const lang = document.getElementById('language').value;
    const formData = new FormData();
    formData.append('language', lang);

    if (activeTab === 'file') {
        const file = document.getElementById('audio-file').files[0];
        if (!file) {
            alert('Pehle file select karo!');
            return;
        }
        formData.append('audio_file', file);
        formData.append('source_type', 'file');
    } else {
        const url = document.getElementById('youtube-url').value.trim();
        if (!url) {
            alert('YouTube URL daalo!');
            return;
        }
        formData.append('youtube_url', url);
        formData.append('source_type', 'youtube');
    }

    btn.disabled = true;
    btn.innerHTML = '<span class="spinner"></span> Processing...';
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
            showStatus('failed', `❌ Error: ${JSON.stringify(data)}`);
            resetBtn();
            return;
        }

        currentId = data.id;
        showStatus('pending', `Transcript ID: ${currentId} — Processing shuru ho gaya...`);
        startPolling();
        loadHistory();

    } catch (e) {
        showStatus('failed', '❌ Error: Server se connect nahi ho saka!');
        resetBtn();
    }
}

// Status Polling
function startPolling() {
    if (statusInterval) clearInterval(statusInterval);
    statusInterval = setInterval(async () => {
        try {
            const res = await fetch(`${API}/${currentId}/status/`);
            const data = await res.json();

            if (data.status === 'done') {
                clearInterval(statusInterval);
                showStatus('done', '✅ Transcript tayar ho gaya!');
                loadResult();
                resetBtn();
            } else if (data.status === 'failed') {
                clearInterval(statusInterval);
                showStatus('failed', `❌ Error: ${data.error_message || 'Kuch galat hua'}`);
                resetBtn();
            } else {
                showStatus(data.status, `⏳ Status: ${data.status}...`);
            }
        } catch (e) {}
    }, 3000);
}

// Load Result
async function loadResult() {
    const res = await fetch(`${API}/${currentId}/`);
    const data = await res.json();
    console.log('Response:', data);  // temporarily add karo
    currentId = data.id;
    
    document.getElementById('full-text').innerText = data.full_text || 'No text found';
    document.getElementById('result-box').style.display = 'block';
    document.getElementById('export-btns').style.display = 'flex';

    // Segments
    const segList = document.getElementById('segments-list');
    segList.innerHTML = '';

    if (data.segments && data.segments.length > 0) {
        data.segments.forEach(seg => {
            segList.innerHTML += `
                <div class="segment">
                    <div class="time">⏱ ${seg.start_time_formatted} → ${seg.end_time_formatted}</div>
                    <div class="text">${seg.text}</div>
                </div>`;
        });
        document.getElementById('segments-box').style.display = 'block';
    }

    loadHistory();
}

// Export
function exportTranscript(format) {
    if (!currentId) {
        alert('Pehle transcript select karo!');
        return;
    }
    window.open(`${API}/${currentId}/export/${format}/`, '_blank');
}

// Show Status
function showStatus(type, message) {
    const box = document.getElementById('status-box');
    box.className = `status-box status-${type}`;
    box.style.display = 'block';
    document.getElementById('status-text').innerHTML = message;
}

// Hide Results
function hideResults() {
    document.getElementById('result-box').style.display = 'none';
    document.getElementById('export-btns').style.display = 'none';
    document.getElementById('segments-box').style.display = 'none';
    document.getElementById('status-box').style.display = 'none';
}

// Reset Button
function resetBtn() {
    const btn = document.getElementById('upload-btn');
    btn.disabled = false;
    btn.innerHTML = '🚀 Transcript Banao';
}

// Load History
async function loadHistory() {
    try {
        const res = await fetch(`${API}/`);
        const data = await res.json();
        const list = document.getElementById('history-list');

        if (!data.length) {
            list.innerHTML = '<p style="color:#888; padding:10px;">Koi transcript nahi hai abhi.</p>';
            return;
        }

        list.innerHTML = data.map(t => `
            <div class="history-item" onclick="loadFromHistory(${t.id})">
                <div>
                    <strong>ID: ${t.id}</strong> —
                    ${t.source_type === 'youtube' ? '▶️ YouTube' : '📁 File'}
                    (${t.language})
                    ${t.youtube_url ? `<br><small style="color:#888">${t.youtube_url.substring(0, 50)}...</small>` : ''}
                </div>
                <span class="badge badge-${t.status}">${t.status}</span>
            </div>
        `).join('');
    } catch (e) {
        document.getElementById('history-list').innerHTML = '<p style="color:red;">History load nahi ho saki.</p>';
    }
}

// Load From History
async function loadFromHistory(id) {
    currentId = id;
    hideResults();
    showStatus('done', `Transcript ID ${id} load ho raha hai...`);
    await loadResult();
    showStatus('done', `✅ Transcript ID ${id} load ho gaya!`);
}

// Page Load
loadHistory();
setInterval(loadHistory, 60000);