/* ==========================================================================
   Reticla AI Meeting Assistant - Frontend Application JavaScript
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
   API Health & Status
   -------------------------------------------------------------------------- */
async function checkApiHealth() {
    try {
        const res = await fetch(`${API_BASE_URL}/health`);
        if (!res.ok) throw new Error("Health check failed");
        const data = await res.json();
        
        const statusText = document.getElementById("statusText");
        const maxMb = data.max_file_size_mb || 40;
        
        if (data.gemini_configured) {
            statusText.textContent = `Engine: Google Gemini AI (Max ${maxMb}MB)`;
        } else if (data.groq_configured) {
            statusText.textContent = `Engine: Groq AI (Max ${maxMb}MB)`;
        } else {
            statusText.textContent = `Engine: HuggingFace / Local ASR (Max ${maxMb}MB)`;
        }
    } catch (err) {
        console.warn("API Health warning:", err);
        document.getElementById("statusText").textContent = "Engine: HuggingFace / Speech Engine (Max 40MB)";
    }
}

/* --------------------------------------------------------------------------
   Drag and Drop & File Selection
   -------------------------------------------------------------------------- */
function setupDragAndDrop() {
    const dropzone = document.getElementById("dropzone");
    if (!dropzone) return;

    ["dragenter", "dragover", "dragleave", "drop"].forEach(eventName => {
        dropzone.addEventListener(eventName, preventDefaults, false);
    });

    function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }

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
    const allowedExts = [".mp3", ".wav", ".m4a", ".ogg", ".flac", ".webm", ".aac"];
    const fileExt = file.name.substring(file.name.lastIndexOf(".")).toLowerCase();

    if (!allowedExts.includes(fileExt)) {
        showToast(`Invalid file format '${fileExt}'. Allowed: ${allowedExts.join(", ")}`, "error");
        return;
    }

    const maxSize = 40 * 1024 * 1024; // Up to 40MB
    if (file.size > maxSize) {
        showToast(`File size (${(file.size / (1024 * 1024)).toFixed(1)} MB) exceeds 40MB maximum limit.`, "error");
        return;
    }

    currentSelectedFile = file;
    const fileMb = (file.size / (1024 * 1024)).toFixed(2);
    
    document.getElementById("selectedFileName").textContent = file.name;
    document.getElementById("selectedFileSize").textContent = `${fileMb} MB`;

    const largeFileBadge = document.getElementById("largeFileBadge");
    if (file.size > 15 * 1024 * 1024) {
        largeFileBadge.style.display = "inline-block";
    } else {
        largeFileBadge.style.display = "none";
    }
    
    document.getElementById("dropzone").style.display = "none";
    document.getElementById("selectedFileCard").style.display = "flex";
    
    const suggestedTitle = file.name.substring(0, file.name.lastIndexOf(".")).replace(/[-_]/g, " ");
    document.getElementById("meetingTitleInput").value = suggestedTitle.charAt(0).toUpperCase() + suggestedTitle.slice(1);
}

function clearSelectedFile() {
    currentSelectedFile = null;
    document.getElementById("audioFileInput").value = "";
    document.getElementById("dropzone").style.display = "block";
    document.getElementById("selectedFileCard").style.display = "none";
    document.getElementById("largeFileBadge").style.display = "none";
}

/* --------------------------------------------------------------------------
   Audio Processing Stepper - 2-Pass Pipeline Flow
   -------------------------------------------------------------------------- */
async function uploadAndProcessAudio() {
    if (!currentSelectedFile) {
        showToast("Please select an audio file first.", "error");
        return;
    }

    const titleInput = document.getElementById("meetingTitleInput").value.trim();
    const formData = new FormData();
    formData.append("file", currentSelectedFile);
    if (titleInput) {
        formData.append("title", titleInput);
    }

    const fileSizeMb = (currentSelectedFile.size / (1024 * 1024)).toFixed(1);
    const isLarge = currentSelectedFile.size > 15 * 1024 * 1024;

    document.getElementById("selectedFileCard").style.display = "none";
    const stepper = document.getElementById("processingStepper");
    stepper.style.display = "flex";

    // 2-Pass Pipeline visual updates
    updateStepUI(20, `Pass 1: Ingesting audio file (${fileSizeMb} MB)...`, "stepPass1", "Reading complete audio track...");

    setTimeout(() => {
        updateStepUI(
            50,
            `Pass 1: Extracting 100% full content spoken in audio...`,
            "stepVerify",
            "Running Speech-to-Text ASR model to get full verbatim transcript..."
        );
    }, 1200);

    setTimeout(() => {
        updateStepUI(
            80,
            `Pass 2: Processing extracted transcript through LLM...`,
            "stepPass2",
            "Generating executive summary, key decisions, and action items strictly from the transcript..."
        );
    }, 2800);

    try {
        const response = await fetch(`${API_BASE_URL}/meetings/upload`, {
            method: "POST",
            body: formData
        });

        if (!response.ok) {
            const errData = await response.json();
            throw new Error(errData.detail || "Failed to process meeting audio.");
        }

        const meetingData = await response.json();
        updateStepUI(100, "Pass 1 & Pass 2 Complete!", "stepDone", "100% audio content transcribed and summarized!");

        setTimeout(() => {
            stepper.style.display = "none";
            showToast("Meeting transcribed and summarized successfully!", "success");
            renderMeetingResults(meetingData);
            clearSelectedFile();
            fetchMeetingsHistory();
            scrollToSection("upload");
        }, 600);

    } catch (err) {
        console.error("Processing error:", err);
        stepper.style.display = "none";
        document.getElementById("selectedFileCard").style.display = "flex";
        showToast(`Processing Error: ${err.message}`, "error");
    }
}

function updateStepUI(percent, statusText, activeStepId, detailText = "") {
    document.getElementById("progressFill").style.width = `${percent}%`;
    document.getElementById("stepperStatusText").textContent = statusText;
    document.getElementById("chunkingDetailText").textContent = detailText;
    
    ["stepPass1", "stepVerify", "stepPass2", "stepDone"].forEach(id => {
        const el = document.getElementById(id);
        if (el) el.classList.remove("active");
    });
    if (activeStepId) {
        const el = document.getElementById(activeStepId);
        if (el) el.classList.add("active");
    }
}

/* --------------------------------------------------------------------------
   Render Meeting Results
   -------------------------------------------------------------------------- */
function renderMeetingResults(data) {
    currentMeetingData = data;
    document.getElementById("resultsView").style.display = "flex";

    // Header & Player
    document.getElementById("resTitle").textContent = data.title;
    document.getElementById("resAsrTag").textContent = `ASR: ${data.asr_provider_used || 'Auto'}`;
    document.getElementById("resLlmTag").textContent = `LLM: ${data.llm_provider_used || 'Auto'}`;
    document.getElementById("resDate").textContent = data.created_at ? new Date(data.created_at).toLocaleString() : "Just now";

    const player = document.getElementById("meetingAudioPlayer");
    player.src = data.audio_path;

    // Overview Tab
    document.getElementById("resSummaryText").textContent = data.summary || "No summary available.";
    
    const topicsList = document.getElementById("resTopicsList");
    topicsList.innerHTML = "";
    if (data.topics && data.topics.length > 0) {
        data.topics.forEach(t => {
            const item = document.createElement("div");
            item.className = "topic-item";
            item.innerHTML = `<h4>${t.topic}</h4><p>${t.summary}</p>`;
            topicsList.appendChild(item);
        });
    } else {
        topicsList.innerHTML = "<p class='muted-text'>No sub-topics categorized.</p>";
    }

    // Decisions Tab
    const decisionsList = document.getElementById("resDecisionsList");
    decisionsList.innerHTML = "";
    const decisions = data.key_decisions || [];
    document.getElementById("decisionsCount").textContent = decisions.length;
    if (decisions.length > 0) {
        decisions.forEach(d => {
            const li = document.createElement("li");
            li.innerHTML = `<i class="fa-solid fa-circle-check"></i> <span>${d}</span>`;
            decisionsList.appendChild(li);
        });
    } else {
        decisionsList.innerHTML = "<p class='muted-text'>No key decisions recorded.</p>";
    }

    // Action Items Tab
    const actionsList = document.getElementById("resActionItemsList");
    actionsList.innerHTML = "";
    const actions = data.action_items || [];
    document.getElementById("actionsCount").textContent = actions.length;
    
    if (actions.length > 0) {
        actions.forEach(act => {
            const isDone = act.status === "Done";
            const row = document.createElement("div");
            row.className = `action-item-row ${isDone ? 'done' : ''}`;
            row.innerHTML = `
                <div class="task-left">
                    <input type="checkbox" class="task-checkbox" ${isDone ? 'checked' : ''} onchange="toggleActionItem('${data.id}', '${act.id}', this.checked)">
                    <span class="task-desc">${act.task}</span>
                </div>
                <div class="task-meta">
                    <span class="badge-assignee"><i class="fa-regular fa-user"></i> ${act.assignee || 'Unassigned'}</span>
                    <span class="badge-priority">${act.priority || 'Medium'}</span>
                </div>
            `;
            actionsList.appendChild(row);
        });
    } else {
        actionsList.innerHTML = "<p class='muted-text'>No action items assigned.</p>";
    }

    // Transcript Tab
    const transcriptBody = document.getElementById("resTranscriptBody");
    transcriptBody.innerHTML = "";
    if (data.transcript_segments && data.transcript_segments.length > 0) {
        data.transcript_segments.forEach(seg => {
            const minutes = Math.floor(seg.start / 60).toString().padStart(2, '0');
            const seconds = Math.floor(seg.start % 60).toString().padStart(2, '0');
            const timeStr = `[${minutes}:${seconds}]`;
            
            const line = document.createElement("div");
            line.style.marginBottom = "8px";
            line.innerHTML = `<span class="timestamp-link" onclick="seekAudio(${seg.start})">${timeStr}</span> ${seg.text}`;
            transcriptBody.appendChild(line);
        });
    } else if (data.transcript) {
        transcriptBody.textContent = data.transcript;
    } else {
        transcriptBody.textContent = "No transcript recorded.";
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
        if (!response.ok) throw new Error("Failed to update action item state");
        showToast(`Task status updated to ${newStatus}`, "info");
    } catch (err) {
        console.error("Action item toggle error:", err);
        showToast("Could not update task status.", "error");
    }
}

/* --------------------------------------------------------------------------
   Tabs Navigation
   -------------------------------------------------------------------------- */
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
   Meeting History Archive
   -------------------------------------------------------------------------- */
async function fetchMeetingsHistory(searchQuery = "") {
    try {
        let url = `${API_BASE_URL}/meetings`;
        if (searchQuery) url += `?search=${encodeURIComponent(searchQuery)}`;
        
        const res = await fetch(url);
        if (!res.ok) throw new Error("Failed to fetch meetings history");
        const data = await res.json();
        
        allMeetingsHistory = data.meetings || [];
        renderMeetingsTable(allMeetingsHistory);
    } catch (err) {
        console.error("History fetch error:", err);
    }
}

function renderMeetingsTable(meetings) {
    const tbody = document.getElementById("meetingHistoryTableBody");
    tbody.innerHTML = "";

    if (!meetings || meetings.length === 0) {
        tbody.innerHTML = `<tr><td colspan="6" class="text-center py-4 muted-text">No meetings stored in history.</td></tr>`;
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
            <td><span class="badge-priority">${taskCount} tasks</span></td>
            <td><span class="meta-tag">${m.asr_provider_used || 'ASR'}</span></td>
            <td>
                <button class="btn btn-pill btn-secondary btn-sm" onclick="viewMeetingDetails('${m.id}')">
                    <i class="fa-solid fa-eye"></i> View
                </button>
                <button class="btn btn-pill btn-secondary btn-sm" onclick="deleteMeetingRecord('${m.id}')" style="color:#FF6B4A">
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
        scrollToSection("upload");
    } catch (err) {
        showToast("Error loading meeting details.", "error");
    }
}

async function deleteMeetingRecord(meetingId) {
    if (!confirm("Are you sure you want to delete this meeting recording and summary?")) return;
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
   Export & Copy Helpers
   -------------------------------------------------------------------------- */
function toggleExportMenu() {
    const menu = document.getElementById("exportMenu");
    menu.style.display = menu.style.display === "none" ? "flex" : "none";
}

function exportCurrentMeeting(format) {
    if (!currentMeetingData) return;
    window.open(`${API_BASE_URL}/meetings/${currentMeetingData.id}/export?format=${format}`, "_blank");
    document.getElementById("exportMenu").style.display = "none";
}

function copyCurrentSummary() {
    if (!currentMeetingData || !currentMeetingData.summary) {
        showToast("No active summary to copy.", "error");
        return;
    }
    navigator.clipboard.writeText(currentMeetingData.summary);
    showToast("Executive summary copied to clipboard!", "success");
}

function copyTranscriptText() {
    if (!currentMeetingData || !currentMeetingData.transcript) return;
    navigator.clipboard.writeText(currentMeetingData.transcript);
    showToast("Full transcript copied to clipboard!", "success");
}

function scrollToSection(id) {
    const el = document.getElementById(id);
    if (el) el.scrollIntoView({ behavior: "smooth" });
}

/* --------------------------------------------------------------------------
   RAG Transcript Q&A Helper Functions
   -------------------------------------------------------------------------- */
function setQAQuestion(questionText) {
    const input = document.getElementById("qaQuestionInput");
    if (input) {
        input.value = questionText;
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
    const hintEl = document.getElementById("qaProviderHint");

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
        if (hintEl) hintEl.textContent = "RAG AI Engine";

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
   Toast Notifications
   -------------------------------------------------------------------------- */
function showToast(message, type = "info") {
    const container = document.getElementById("toastContainer");
    const toast = document.createElement("div");
    toast.className = "toast";
    
    let icon = "fa-circle-info";
    if (type === "success") icon = "fa-circle-check";
    if (type === "error") icon = "fa-circle-exclamation";
    
    toast.innerHTML = `<i class="fa-solid ${icon}"></i> <span>${message}</span>`;
    container.appendChild(toast);
    
    setTimeout(() => {
        toast.remove();
    }, 4000);
}
