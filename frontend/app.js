/* ==========================================================================
   Rizer AI Meeting Assistant - Frontend Application JavaScript
   ========================================================================== */

const API_BASE_URL = "/api";
let currentSelectedFile = null;
let currentMeetingData = null;
let allMeetingsHistory = [];

document.addEventListener("DOMContentLoaded", () => {
    checkApiHealth();
    fetchMeetingsHistory();
    setupDragAndDrop();
    
    // Keyboard shortcut for Cmd/Ctrl + K search focus
    document.addEventListener("keydown", (e) => {
        if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
            e.preventDefault();
            const searchInput = document.getElementById("globalSearchInput");
            if (searchInput) searchInput.focus();
        }
    });
});

/* --------------------------------------------------------------------------
   View & Navigation Switcher
   -------------------------------------------------------------------------- */
function showView(viewName) {
    const views = ["home", "workbench", "history", "files", "settings"];
    views.forEach(v => {
        const pane = document.getElementById(`view${v.charAt(0).toUpperCase() + v.slice(1)}`);
        const nav = document.getElementById(`nav${v.charAt(0).toUpperCase() + v.slice(1)}`);
        if (pane) pane.style.display = "none";
        if (nav) nav.classList.remove("active");
    });

    const activePane = document.getElementById(`view${viewName.charAt(0).toUpperCase() + viewName.slice(1)}`);
    const activeNav = document.getElementById(`nav${viewName.charAt(0).toUpperCase() + viewName.slice(1)}`);

    if (activePane) activePane.style.display = "block";
    if (activeNav) activeNav.classList.add("active");
}

function scrollToUpload() {
    showView("home");
    const dropzone = document.getElementById("dropzone");
    if (dropzone) dropzone.scrollIntoView({ behavior: "smooth" });
}

function toggleTheme() {
    const isDark = document.body.classList.toggle("dark-theme");
    const icon = document.querySelector("#themeToggleBtn i");
    if (icon) {
        icon.className = isDark ? "fa-regular fa-sun" : "fa-regular fa-moon";
    }
}

/* --------------------------------------------------------------------------
   API Health Check
   -------------------------------------------------------------------------- */
async function checkApiHealth() {
    try {
        const res = await fetch(`${API_BASE_URL}/health`);
        if (!res.ok) throw new Error("Health check failed");
        const data = await res.json();
        
        const statusText = document.getElementById("statusText");
        const settingsStatus = document.getElementById("settingsEngineStatus");
        const maxMb = data.max_file_size_mb || 40;
        
        let engineStr = "Ready";
        if (data.gemini_configured) engineStr = `Engine: Google Gemini AI (Max ${maxMb}MB)`;
        else if (data.groq_configured) engineStr = `Engine: Groq AI (Max ${maxMb}MB)`;
        else engineStr = `Engine: Rizer Speech Engine (Max ${maxMb}MB)`;

        if (statusText) statusText.textContent = engineStr;
        if (settingsStatus) settingsStatus.textContent = engineStr;
    } catch (err) {
        console.warn("API Health warning:", err);
        const statusText = document.getElementById("statusText");
        if (statusText) statusText.textContent = "Engine: Rizer Speech Engine (Max 40MB)";
    }
}

/* --------------------------------------------------------------------------
   Drag and Drop & File Selection
   -------------------------------------------------------------------------- */
function setupDragAndDrop() {
    const dropzone = document.getElementById("dropzone");
    if (!dropzone) return;

    ["dragenter", "dragover", "dragleave", "drop"].forEach(eventName => {
        dropzone.addEventListener(eventName, (e) => {
            e.preventDefault();
            e.stopPropagation();
        }, false);
    });

    ["dragenter", "dragover"].forEach(eventName => {
        dropzone.addEventListener(eventName, () => dropzone.classList.add("dragover"), false);
    });

    ["dragleave", "drop"].forEach(eventName => {
        dropzone.addEventListener(eventName, () => dropzone.classList.remove("dragover"), false);
    });

    dropzone.addEventListener("drop", (e) => {
        const dt = e.dataTransfer;
        const files = dt.files;
        if (files && files.length > 0) {
            handleFile(files[0]);
        }
    });
}

function handleFileSelect(event) {
    const files = event.target.files;
    if (files && files.length > 0) {
        handleFile(files[0]);
    }
}

function handleFile(file) {
    currentSelectedFile = file;
    
    const fileNameEl = document.getElementById("selectedFileName");
    const fileSizeEl = document.getElementById("selectedFileSize");
    const largeBadge = document.getElementById("largeFileBadge");
    const titleInput = document.getElementById("meetingTitleInput");
    
    const fileCard = document.getElementById("selectedFileCard");
    const dropzone = document.getElementById("dropzone");

    if (fileNameEl) fileNameEl.textContent = file.name;
    const sizeMb = (file.size / (1024 * 1024)).toFixed(2);
    if (fileSizeEl) fileSizeEl.textContent = `${sizeMb} MB`;

    if (largeBadge) {
        largeBadge.style.display = file.size > 15 * 1024 * 1024 ? "inline" : "none";
    }

    if (titleInput && !titleInput.value) {
        const defaultTitle = file.name.replace(/\.[^/.]+$/, "").replace(/[-_]/g, " ");
        titleInput.value = defaultTitle.charAt(0).toUpperCase() + defaultTitle.slice(1);
    }

    if (fileCard) fileCard.style.display = "block";
    if (dropzone) dropzone.style.display = "none";
}

function clearSelectedFile() {
    currentSelectedFile = null;
    const fileInput = document.getElementById("audioFileInput");
    if (fileInput) fileInput.value = "";
    
    const fileCard = document.getElementById("selectedFileCard");
    const dropzone = document.getElementById("dropzone");

    if (fileCard) fileCard.style.display = "none";
    if (dropzone) dropzone.style.display = "block";
}

/* --------------------------------------------------------------------------
   Upload & Sequential Processing
   -------------------------------------------------------------------------- */
async function uploadAndProcessAudio() {
    if (!currentSelectedFile) {
        showToast("Please select an audio file first.", "error");
        return;
    }

    const titleInput = document.getElementById("meetingTitleInput");
    const title = titleInput ? titleInput.value.trim() : "Meeting Audio";

    const fileCard = document.getElementById("selectedFileCard");
    const stepper = document.getElementById("processingStepper");
    const stepperText = document.getElementById("stepperStatusText");
    const progressFill = document.getElementById("progressFill");

    if (fileCard) fileCard.style.display = "none";
    if (stepper) stepper.style.display = "block";

    try {
        if (stepperText) stepperText.textContent = "Uploading audio & initializing ASR...";
        if (progressFill) progressFill.style.width = "25%";

        const formData = new FormData();
        formData.append("file", currentSelectedFile);
        formData.append("title", title);

        const uploadRes = await fetch(`${API_BASE_URL}/meetings/upload`, {
            method: "POST",
            body: formData
        });

        if (!uploadRes.ok) {
            const err = await uploadRes.json();
            throw new Error(err.detail || "Upload failed");
        }

        const uploadData = await uploadRes.json();

        if (progressFill) progressFill.style.width = "100%";
        if (stepperText) stepperText.textContent = "Complete!";

        showToast("Meeting processed successfully!", "success");

        setTimeout(() => {
            if (stepper) stepper.style.display = "none";
            clearSelectedFile();
            renderMeetingResults(uploadData);
            showView("workbench");
            fetchMeetingsHistory();
        }, 600);

    } catch (err) {
        console.error("Processing error:", err);
        showToast(`Processing failed: ${err.message}`, "error");
        if (stepper) stepper.style.display = "none";
        if (fileCard) fileCard.style.display = "block";
    }
}

/* --------------------------------------------------------------------------
   Render Meeting Results in Workbench
   -------------------------------------------------------------------------- */
function renderMeetingResults(data) {
    currentMeetingData = data;

    const resTitle = document.getElementById("resTitle");
    const resDate = document.getElementById("resDate");
    const resAsrTag = document.getElementById("resAsrTag");
    const resLlmTag = document.getElementById("resLlmTag");
    const audioPlayer = document.getElementById("meetingAudioPlayer");

    if (resTitle) resTitle.textContent = data.title || "Meeting Audio";
    if (resDate) {
        const d = data.created_at ? new Date(data.created_at) : new Date();
        resDate.textContent = d.toLocaleDateString() + " at " + d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    }
    if (resAsrTag) resAsrTag.textContent = `ASR: ${data.asr_provider_used || 'Gemini'}`;
    if (resLlmTag) resLlmTag.textContent = `AI: ${data.llm_provider_used || 'Rizer'}`;

    if (audioPlayer && data.audio_url) {
        audioPlayer.src = data.audio_url;
    }

    // Summary
    const summaryText = document.getElementById("resSummaryText");
    if (summaryText) summaryText.textContent = data.summary || "No summary available.";

    // Topics
    const topicsList = document.getElementById("resTopicsList");
    if (topicsList) {
        topicsList.innerHTML = "";
        if (data.topics && data.topics.length > 0) {
            data.topics.forEach(t => {
                const item = document.createElement("div");
                item.style.marginBottom = "10px";
                item.innerHTML = `<strong>${t.topic}:</strong> ${t.summary}`;
                topicsList.appendChild(item);
            });
        } else {
            topicsList.textContent = "Main audio topics processed.";
        }
    }

    // Key Decisions
    const decisionsList = document.getElementById("resDecisionsList");
    const decCount = document.getElementById("decisionsCount");
    if (decisionsList) {
        decisionsList.innerHTML = "";
        const decs = data.key_decisions || [];
        if (decCount) decCount.textContent = decs.length;
        if (decs.length > 0) {
            decs.forEach(d => {
                const li = document.createElement("li");
                li.textContent = d;
                decisionsList.appendChild(li);
            });
        } else {
            decisionsList.innerHTML = "<p class='muted-p'>No specific key decisions extracted.</p>";
        }
    }

    // Action Items
    const actionsList = document.getElementById("resActionItemsList");
    const actCount = document.getElementById("actionsCount");
    if (actionsList) {
        actionsList.innerHTML = "";
        const acts = data.action_items || [];
        if (actCount) actCount.textContent = acts.length;
        if (acts.length > 0) {
            acts.forEach(act => {
                const isDone = act.status === "Done";
                const row = document.createElement("div");
                row.style.display = "flex";
                row.style.justifyContent = "space-between";
                row.style.padding = "10px 14px";
                row.style.background = "var(--bg-card)";
                row.style.borderRadius = "10px";
                row.style.marginBottom = "8px";
                row.innerHTML = `
                    <div>
                        <input type="checkbox" ${isDone ? 'checked' : ''} onchange="toggleActionItem('${data.id}', '${act.id}', this.checked)">
                        <span style="${isDone ? 'text-decoration:line-through; opacity:0.6;' : ''}">${act.task}</span>
                    </div>
                    <span style="font-size:0.8rem; font-weight:600; color:var(--primary);">${act.assignee || 'Unassigned'}</span>
                `;
                actionsList.appendChild(row);
            });
        } else {
            actionsList.innerHTML = "<p class='muted-p'>No action items assigned.</p>";
        }
    }

    // Transcript
    const transcriptBody = document.getElementById("resTranscriptBody");
    if (transcriptBody) {
        transcriptBody.innerHTML = "";
        if (data.transcript_segments && data.transcript_segments.length > 0) {
            data.transcript_segments.forEach(seg => {
                const m = Math.floor(seg.start / 60).toString().padStart(2, '0');
                const s = Math.floor(seg.start % 60).toString().padStart(2, '0');
                const timeStr = `[${m}:${s}]`;
                const line = document.createElement("div");
                line.style.marginBottom = "8px";
                line.innerHTML = `<span class="timestamp-link" onclick="seekAudio(${seg.start})">${timeStr}</span> ${seg.text}`;
                transcriptBody.appendChild(line);
            });
        } else {
            transcriptBody.textContent = data.transcript || "No transcript recorded.";
        }
    }

    switchTab("overview");
}

function seekAudio(seconds) {
    const player = document.getElementById("meetingAudioPlayer");
    if (player) {
        player.currentTime = seconds;
        player.play();
    }
}

async function toggleActionItem(meetingId, actionItemId, isChecked) {
    const newStatus = isChecked ? "Done" : "To Do";
    try {
        const response = await fetch(`${API_BASE_URL}/meetings/${meetingId}/action-items`, {
            method: "PATCH",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ action_item_id: actionItemId, status: newStatus })
        });
        if (!response.ok) throw new Error("Failed to update status");
        showToast(`Task status updated to ${newStatus}`, "info");
    } catch (err) {
        showToast("Could not update task status.", "error");
    }
}

function switchTab(tabName) {
    const formattedTab = tabName.toLowerCase() === "action-items" ? "ActionItems" :
                         tabName.toLowerCase() === "qa" ? "Qa" :
                         tabName.charAt(0).toUpperCase() + tabName.slice(1);

    ["Overview", "Decisions", "ActionItems", "Transcript", "Qa"].forEach(t => {
        const btn = document.getElementById(`tabBtn${t}`);
        const pane = document.getElementById(`tab${t}`);
        if (btn) btn.classList.remove("active");
        if (pane) pane.classList.remove("active");
    });

    const activeBtn = document.getElementById(`tabBtn${formattedTab}`);
    const activePane = document.getElementById(`tab${formattedTab}`);
    
    if (activeBtn) activeBtn.classList.add("active");
    if (activePane) activePane.classList.add("active");
}

/* --------------------------------------------------------------------------
   Meeting History & Sidebar List Rendering
   -------------------------------------------------------------------------- */
async function fetchMeetingsHistory(searchQuery = "") {
    try {
        let url = `${API_BASE_URL}/meetings`;
        if (searchQuery) url += `?search=${encodeURIComponent(searchQuery)}`;
        
        const res = await fetch(url);
        if (!res.ok) throw new Error("Failed to fetch history");
        const data = await res.json();
        
        allMeetingsHistory = data.meetings || [];
        renderMeetingsTable(allMeetingsHistory);
        renderSideHistoryList(allMeetingsHistory);
        renderRecentActivity(allMeetingsHistory);
    } catch (err) {
        console.error("History fetch error:", err);
    }
}

function renderSideHistoryList(meetings) {
    const list = document.getElementById("sideHistoryList");
    if (!list) return;
    list.innerHTML = "";

    if (!meetings || meetings.length === 0) {
        list.innerHTML = "<p class='muted-p' style='font-size:0.8rem;'>No meetings stored.</p>";
        return;
    }

    meetings.slice(0, 5).forEach(m => {
        const div = document.createElement("div");
        div.className = "history-item-row";
        div.onclick = () => viewMeetingDetails(m.id);

        const dateStr = m.created_at ? new Date(m.created_at).toLocaleDateString([], { month: 'short', day: 'numeric' }) : "Recent";
        const minStr = m.duration_seconds ? `${Math.round(m.duration_seconds / 60)} min` : "Audio";

        div.innerHTML = `
            <div class="item-left">
                <div class="item-wave-icon"><i class="fa-solid fa-waveform"></i></div>
                <div class="item-info">
                    <h4>${m.title}</h4>
                    <span>${dateStr} • ${minStr}</span>
                </div>
            </div>
            <span class="status-pill processed">Processed</span>
        `;
        list.appendChild(div);
    });
}

function renderRecentActivity(meetings) {
    const container = document.getElementById("recentActivityContainer");
    if (!container) return;
    container.innerHTML = "";

    if (!meetings || meetings.length === 0) {
        container.innerHTML = `
            <div class="empty-state-box">
                <i class="fa-regular fa-folder-open empty-icon"></i>
                <h4>No meetings yet</h4>
                <p>Upload your first audio file to get started.</p>
            </div>
        `;
        return;
    }

    meetings.slice(0, 3).forEach(m => {
        const card = document.createElement("div");
        card.style.background = "var(--bg-card-subtle)";
        card.style.border = "1px solid var(--border-color)";
        card.style.padding = "14px 18px";
        card.style.borderRadius = "12px";
        card.style.marginBottom = "10px";
        card.style.cursor = "pointer";
        card.onclick = () => viewMeetingDetails(m.id);

        card.innerHTML = `
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:4px;">
                <h4 style="font-size:0.95rem; font-weight:700;">${m.title}</h4>
                <span class="status-pill processed">Processed</span>
            </div>
            <p style="font-size:0.82rem; color:var(--text-muted);">${m.summary ? m.summary.substring(0, 100) + '...' : 'Meeting transcript summary available.'}</p>
        `;
        container.appendChild(card);
    });
}

function renderMeetingsTable(meetings) {
    const tbody = document.getElementById("meetingHistoryTableBody");
    if (!tbody) return;
    tbody.innerHTML = "";

    if (!meetings || meetings.length === 0) {
        tbody.innerHTML = `<tr><td colspan="6" style="text-align:center; padding:24px;" class="muted-p">No meetings stored in history.</td></tr>`;
        return;
    }

    meetings.forEach(m => {
        const tr = document.createElement("tr");
        const dateStr = m.created_at ? new Date(m.created_at).toLocaleDateString() : "N/A";
        const taskCount = m.action_items ? m.action_items.length : 0;
        const durationStr = `${Math.round(m.duration_seconds || 0)}s`;

        tr.innerHTML = `
            <td><strong>${m.title}</strong></td>
            <td>${dateStr}</td>
            <td>${durationStr}</td>
            <td><span class="tag-badge">${taskCount} tasks</span></td>
            <td><span class="status-pill processed">Processed</span></td>
            <td>
                <button class="btn-secondary-sm" onclick="viewMeetingDetails('${m.id}')">
                    <i class="fa-solid fa-eye"></i> View
                </button>
                <button class="btn-secondary-sm" onclick="deleteMeetingRecord('${m.id}')" style="color:#ef4444;">
                    <i class="fa-solid fa-trash"></i>
                </button>
            </td>
        `;
        tbody.appendChild(tr);
    });
}

async function viewMeetingDetails(meetingId) {
    try {
        const res = await fetch(`${API_BASE_URL}/meetings/${meetingId}`);
        if (!res.ok) throw new Error("Meeting not found");
        const data = await res.json();
        renderMeetingResults(data);
        showView("workbench");
    } catch (err) {
        showToast("Error loading meeting details.", "error");
    }
}

let pendingDeleteMeetingId = null;

function deleteMeetingRecord(meetingId) {
    pendingDeleteMeetingId = meetingId;
    const modal = document.getElementById("confirmDeleteModal");
    if (modal) modal.style.display = "flex";

    const confirmBtn = document.getElementById("confirmDeleteBtn");
    if (confirmBtn) {
        confirmBtn.onclick = () => executeDeleteMeeting(meetingId);
    }
}

function closeDeleteModal() {
    pendingDeleteMeetingId = null;
    const modal = document.getElementById("confirmDeleteModal");
    if (modal) modal.style.display = "none";
}

async function executeDeleteMeeting(meetingId) {
    closeDeleteModal();
    if (!meetingId) return;
    try {
        const res = await fetch(`${API_BASE_URL}/meetings/${meetingId}`, { method: "DELETE" });
        if (!res.ok) throw new Error("Delete failed");
        showToast("Meeting deleted successfully", "info");
        fetchMeetingsHistory();
    } catch (err) {
        showToast("Failed to delete meeting.", "error");
    }
}

function handleGlobalSearch(event) {
    const query = event.target.value.trim();
    fetchMeetingsHistory(query);
}

/* --------------------------------------------------------------------------
   Export Helpers
   -------------------------------------------------------------------------- */
function toggleExportMenu() {
    const menu = document.getElementById("exportMenu");
    if (menu) menu.style.display = menu.style.display === "none" ? "flex" : "none";
}

async function exportCurrentMeeting(format) {
    if (!currentMeetingData || !currentMeetingData.id) {
        showToast("No active meeting loaded for export.", "error");
        return;
    }

    try {
        const url = `${API_BASE_URL}/meetings/${currentMeetingData.id}/export?format=${format}`;
        window.open(url, '_blank');
        toggleExportMenu();
        showToast(`Exporting meeting as ${format.toUpperCase()}...`, "info");
    } catch (err) {
        showToast("Failed to export meeting.", "error");
    }
}

function copyTranscriptText() {
    if (!currentMeetingData || !currentMeetingData.transcript) {
        showToast("No transcript text available to copy.", "error");
        return;
    }

    navigator.clipboard.writeText(currentMeetingData.transcript)
        .then(() => showToast("Full transcript text copied to clipboard!", "success"))
        .catch(() => showToast("Failed to copy text.", "error"));
}

/* --------------------------------------------------------------------------
   RAG Q&A Engine Frontend
   -------------------------------------------------------------------------- */
function setQAQuestion(text) {
    const input = document.getElementById("qaQuestionInput");
    if (input) {
        input.value = text;
        askMeetingQuestion();
    }
}

async function askMeetingQuestion() {
    if (!currentMeetingData || !currentMeetingData.id) {
        showToast("Please select or upload a meeting first.", "error");
        return;
    }

    const input = document.getElementById("qaQuestionInput");
    const question = input ? input.value.trim() : "";

    if (!question) {
        showToast("Please enter a question to ask.", "error");
        return;
    }

    const submitBtn = document.getElementById("qaSubmitBtn");
    const container = document.getElementById("qaResultsContainer");
    const questionDisplayEl = document.getElementById("qaQuestionDisplayText");
    const answerEl = document.getElementById("qaAnswerText");

    submitBtn.disabled = true;
    submitBtn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> Processing...`;

    try {
        const response = await fetch(`${API_BASE_URL}/meetings/${currentMeetingData.id}/qa`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ question: question })
        });

        if (!response.ok) {
            const errData = await response.json();
            throw new Error(errData.detail || "Failed to generate answer.");
        }

        const data = await response.json();
        
        container.style.display = "block";
        if (questionDisplayEl) questionDisplayEl.textContent = question;
        if (answerEl) answerEl.textContent = data.answer;

        showToast("Answer generated successfully!", "success");

    } catch (err) {
        console.error("RAG Q&A error:", err);
        showToast(`Q&A Error: ${err.message}`, "error");
    } finally {
        submitBtn.disabled = false;
        submitBtn.innerHTML = `<i class="fa-solid fa-paper-plane"></i> Ask`;
    }
}

/* --------------------------------------------------------------------------
   Toast Notification System
   -------------------------------------------------------------------------- */
function showToast(message, type = "info") {
    const container = document.getElementById("toastContainer");
    if (!container) return;

    const toast = document.createElement("div");
    toast.className = `toast toast-${type}`;
    toast.textContent = message;

    container.appendChild(toast);

    setTimeout(() => {
        toast.style.opacity = "0";
        setTimeout(() => toast.remove(), 300);
    }, 3500);
}
