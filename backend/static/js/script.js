const chatBox = document.getElementById("chatBox");
const chatForm = document.getElementById("chatForm");
const userInput = document.getElementById("userInput");
const uploadForm = document.getElementById("uploadForm");
const pdfFile = document.getElementById("pdfFile");
const fileLabel = document.getElementById("fileLabel");
const uploadStatus = document.getElementById("uploadStatus");

const loadDocsBtn = document.getElementById("loadDocsBtn");
const docsList = document.getElementById("docsList");
const loadDbBtn = document.getElementById("loadDbBtn");
const dbViewBox = document.getElementById("dbViewBox");

const API_BASE = "/api";

// Update filename display when file is selected
pdfFile.addEventListener("change", (e) => {
    if (e.target.files.length > 0) {
        fileLabel.querySelector("span").textContent = e.target.files[0].name;
    }
});

// Upload Form Handler
uploadForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    if (!pdfFile.files[0]) return;

    const formData = new FormData();
    formData.append("file", pdfFile.files[0]);
    uploadStatus.textContent = "Uploading and indexing PDF...";
    uploadStatus.style.color = "var(--primary)";

    try {
        const res = await fetch(`${API_BASE}/upload`, { method: "POST", body: formData });
        const data = await res.json();
        if (res.ok) {
            uploadStatus.textContent = data.message;
            uploadStatus.style.color = "#10b981";
            pdfFile.value = "";
            fileLabel.querySelector("span").textContent = "Choose PDF or drag here";
            loadDocuments(); 
        } else {
            uploadStatus.textContent = `Error: ${data.error}`;
            uploadStatus.style.color = "#ef4444";
        }
    } catch (err) {
        uploadStatus.textContent = "Upload failed. Network error.";
        uploadStatus.style.color = "#ef4444";
    }
});

// Chat Form Handler
chatForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const question = userInput.value.trim();
    if (!question) return;

    appendMessage(question, "user-message");
    userInput.value = "";

    // Add temporary loading message indicator
    const loadingId = appendLoadingMessage();

    try {
        const res = await fetch(`${API_BASE}/chat`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ question })
        });
        const data = await res.json();
        
        // Remove loading indicator
        document.getElementById(loadingId)?.remove();

        if (res.ok) {
            appendBotMessage(data.answer, data.route, data.sources);
        } else {
            appendMessage(`Error: ${data.error}`, "bot-message");
        }
    } catch (err) {
        document.getElementById(loadingId)?.remove();
        appendMessage("Failed to reach server.", "bot-message");
    }
});

// Load Documentation List with Delete Option
async function loadDocuments() {
    try {
        const res = await fetch(`${API_BASE}/documents`);
        const data = await res.json();
        docsList.innerHTML = "";
        
        // Extract the array from the database response object
        const documents = data.documents || data;

        if (Array.isArray(documents) && documents.length > 0) {
            documents.forEach(doc => {
                const li = document.createElement("li");
                li.className = "doc-item-row";
                li.innerHTML = `
                    <div class="doc-info-text">
                        <span class="doc-name"><i class="fa-solid fa-file-pdf" style="color: #ef4444; margin-right: 6px;"></i>${doc.filename}</span> 
                        <span class="doc-chunks">${doc.chunks_count || doc.chunks || 0} chunks</span>
                    </div>
                    <button class="delete-doc-btn" onclick="deleteDocument('${doc._id}')" title="Delete Document">
                        <i class="fa-solid fa-trash-can"></i>
                    </button>
                `;
                docsList.appendChild(li);
            });
        } else {
            docsList.innerHTML = "<li class='empty-item'>No documents uploaded yet.</li>";
        }
    } catch (err) {
        console.error("Failed to load documents:", err);
        docsList.innerHTML = "<li class='empty-item'>Failed to load documents.</li>";
    }
}
// Delete Document Handler
async function deleteDocument(docId) {
    if (!confirm("Are you sure you want to delete this document?")) return;

    try {
        const res = await fetch(`${API_BASE}/documents/${docId}`, { 
            method: "DELETE" 
        });
        const data = await res.json();
        
        if (res.ok) {
            loadDocuments(); // Refresh the list after successful deletion
        } else {
            alert(`Error deleting document: ${data.error || "Unknown error"}`);
        }
    } catch (err) {
        alert("Failed to delete document. Network error.");
    }
}
// Load Database Summary
if (loadDbBtn) {
    loadDbBtn.addEventListener("click", async () => {
        dbViewBox.innerHTML = "<p class='empty-text'>Loading DB summary...</p>";
        try {
            const res = await fetch(`${API_BASE}/database`);
            const data = await res.json();
            dbViewBox.innerHTML = "";
            if (data.database && Object.keys(data.database).length > 0) {
                for (const [coll, info] of Object.entries(data.database)) {
                    const div = document.createElement("div");
                    div.style.marginBottom = "8px";
                    div.innerHTML = `<strong>${coll}</strong> (${info.count} items)<br><code style="font-size: 0.75rem; color: #64748b;">${JSON.stringify(info.records).slice(0, 80)}...</code>`;
                    dbViewBox.appendChild(div);
                }
            } else {
                dbViewBox.innerHTML = "<p class='empty-text'>No collections found.</p>";
            }
        } catch (err) {
            dbViewBox.innerHTML = "<p class='empty-text'>Failed to load DB records.</p>";
        }
    });
}

function appendMessage(text, className) {
    const div = document.createElement("div");
    div.className = `message ${className}`;
    div.textContent = text;
    chatBox.appendChild(div);
    chatBox.scrollTop = chatBox.scrollHeight;
}

function appendLoadingMessage() {
    const id = "loading-" + Date.now();
    const div = document.createElement("div");
    div.id = id;
    div.className = "message bot-message";
    div.innerHTML = `<p><i class="fa-solid fa-spinner fa-spin" style="margin-right: 8px;"></i> Thinking...</p>`;
    chatBox.appendChild(div);
    chatBox.scrollTop = chatBox.scrollHeight;
    return id;
}

function appendBotMessage(text, route, sources) {
    const div = document.createElement("div");
    div.className = "message bot-message";
    
    let html = `<span class="route-badge">${route || 'chat'}</span><p>${text}</p>`;
    if (sources && sources.length > 0) {
        html += `<div class="sources-box"><i class="fa-solid fa-book-bookmark"></i> <strong>Sources:</strong> ${sources.join(", ")}</div>`;
    }
    div.innerHTML = html;
    chatBox.appendChild(div);
    chatBox.scrollTop = chatBox.scrollHeight;
}

// Initial load on startup
loadDocuments();