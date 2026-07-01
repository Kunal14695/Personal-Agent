// Application state
let sessionId = localStorage.getItem("assistant_session_id") || null;
let pendingApprovalCalls = null;

// DOM Elements
const chatMessages = document.getElementById("chat-messages");
const chatForm = document.getElementById("chat-form");
const chatInput = document.getElementById("chat-input");
const sendBtn = document.getElementById("send-btn");
const modelBadge = document.getElementById("model-badge");
const modeBadge = document.getElementById("mode-badge");

const approvalOverlay = document.getElementById("approval-overlay");
const approvalDrawer = document.getElementById("approval-drawer");
const pendingActionsList = document.getElementById("pending-actions-list");
const btnApproveAll = document.getElementById("btn-approve-all");
const btnRejectAll = document.getElementById("btn-reject-all");

// Fetch API Status on load
async function fetchStatus() {
    try {
        const res = await fetch("/api/status");
        const data = await res.json();
        
        // Updatebadges
        modelBadge.textContent = data.model;
        if (data.demo_mode) {
            modeBadge.textContent = "Demo Mode (Mock)";
            modeBadge.classList.add("demo");
        } else {
            modeBadge.textContent = "Live Mode";
            modeBadge.classList.remove("demo");
        }
    } catch (e) {
        console.error("Failed to fetch server status:", e);
    }
}

// Append message bubble to chat
function appendMessage(sender, text, isSystem = false) {
    const messageDiv = document.createElement("div");
    messageDiv.classList.add("message");
    
    if (isSystem) {
        messageDiv.classList.add("system-msg");
    } else {
        messageDiv.classList.add(sender === "user" ? "user" : "agent");
    }
    
    const contentDiv = document.createElement("div");
    contentDiv.classList.add("message-content");
    
    const textP = document.createElement("p");
    textP.textContent = text;
    
    contentDiv.appendChild(textP);
    messageDiv.appendChild(contentDiv);
    chatMessages.appendChild(messageDiv);
    
    // Auto-scroll
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

// Render typing indicator
function showTypingIndicator() {
    const indicatorDiv = document.createElement("div");
    indicatorDiv.classList.add("message", "agent", "typing-msg");
    indicatorDiv.id = "typing-indicator";
    
    const contentDiv = document.createElement("div");
    contentDiv.classList.add("message-content");
    
    const indicator = document.createElement("div");
    indicator.classList.add("typing-indicator");
    
    for (let i = 0; i < 3; i++) {
        const dot = document.createElement("div");
        dot.classList.add("typing-dot");
        indicator.appendChild(dot);
    }
    
    contentDiv.appendChild(indicator);
    indicatorDiv.appendChild(contentDiv);
    chatMessages.appendChild(indicatorDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

function hideTypingIndicator() {
    const indicator = document.getElementById("typing-indicator");
    if (indicator) {
        indicator.remove();
    }
}

// Show/Hide Approval Drawer
function showApprovalDrawer(pendingCalls) {
    pendingApprovalCalls = pendingCalls;
    pendingActionsList.innerHTML = "";
    
    pendingCalls.forEach(call => {
        const card = document.createElement("div");
        card.classList.add("action-card");
        
        let headerText = call.name.replace(/_/g, ' ');
        headerText = headerText.charAt(0).toUpperCase() + headerText.slice(1);
        
        let argsHtml = "";
        for (const [key, val] of Object.entries(call.args)) {
            if (val !== null && val !== "") {
                argsHtml += `
                    <div class="arg-row">
                        <span class="arg-name">${key}:</span>
                        <span class="arg-value">${val}</span>
                    </div>
                `;
            }
        }
        
        card.innerHTML = `
            <div class="action-card-header">
                <span class="action-title">⚡ ${headerText}</span>
            </div>
            <div class="action-args">
                ${argsHtml || '<div class="arg-row"><span class="arg-name">Parameters:</span><span class="arg-value">None</span></div>'}
            </div>
        `;
        pendingActionsList.appendChild(card);
    });
    
    approvalOverlay.style.display = "flex";
    setTimeout(() => {
        approvalDrawer.classList.add("active");
    }, 10);
}

function hideApprovalDrawer() {
    approvalDrawer.classList.remove("active");
    setTimeout(() => {
        approvalOverlay.style.display = "none";
    }, 300);
}

// Submit user message
async function handleSendMessage(message) {
    if (!message) return;
    
    appendMessage("user", message);
    chatInput.value = "";
    showTypingIndicator();
    
    try {
        const res = await fetch("/api/chat", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                message: message,
                session_id: sessionId
            })
        });
        
        if (!res.ok) {
            const err = await res.json();
            throw new Error(err.detail || "Server error");
        }
        
        const data = await res.json();
        
        // Save session id
        if (data.session_id) {
            sessionId = data.session_id;
            localStorage.setItem("assistant_session_id", sessionId);
        }
        
        hideTypingIndicator();
        
        if (data.status === "requires_approval") {
            showApprovalDrawer(data.pending_calls);
        } else if (data.status === "success") {
            appendMessage("agent", data.response);
        }
        
    } catch (e) {
        hideTypingIndicator();
        appendMessage("agent", `❌ Error: ${e.message}`);
    }
}

// Handle approvals
async function submitApproval(approved) {
    if (!pendingApprovalCalls || !sessionId) return;
    
    hideApprovalDrawer();
    showTypingIndicator();
    
    const decisions = pendingApprovalCalls.map(call => ({
        name: call.name,
        approved: approved
    }));
    
    try {
        const res = await fetch("/api/approve", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                session_id: sessionId,
                decisions: decisions
            })
        });
        
        if (!res.ok) {
            const err = await res.json();
            throw new Error(err.detail || "Server error");
        }
        
        const data = await res.json();
        hideTypingIndicator();
        
        if (data.status === "requires_approval") {
            showApprovalDrawer(data.pending_calls);
        } else if (data.status === "success") {
            appendMessage("agent", data.response);
        }
    } catch (e) {
        hideTypingIndicator();
        appendMessage("agent", `❌ Approval Execution Error: ${e.message}`);
    }
}

// Event Listeners
chatForm.addEventListener("submit", (e) => {
    e.preventDefault();
    const msg = chatInput.value.trim();
    handleSendMessage(msg);
});

btnApproveAll.addEventListener("click", () => submitApproval(true));
btnRejectAll.addEventListener("click", () => submitApproval(false));

// Initialize
fetchStatus();
