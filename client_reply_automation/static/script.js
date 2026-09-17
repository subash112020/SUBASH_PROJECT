const checkButton = document.getElementById("checkReply");
const startButton = document.getElementById("startMonitor");
const stopButton = document.getElementById("stopMonitor");
const resultBox = document.getElementById("resultBox");
const currentTime = document.getElementById("currentTime");
const monitorState = document.getElementById("monitorState");
const monitorIndicator = document.getElementById("monitorIndicator");
const timezoneLabel = document.getElementById("timezoneLabel");
const mailNotification = document.getElementById("mailNotification");
const notificationDetails = document.getElementById("notificationDetails");
const notificationSummary = document.getElementById("notificationSummary");
const dismissNotification = document.getElementById("dismissNotification");
const enquiryForm = document.getElementById("enquiryForm");
const enquiryResult = document.getElementById("enquiryResult");
const submitEnquiryButton = document.getElementById("submitEnquiry");
let lastNotifiedReplyId = null;

enquiryForm.addEventListener("submit", async event => {
    event.preventDefault();
    submitEnquiryButton.disabled = true;
    submitEnquiryButton.textContent = "Sending...";
    enquiryResult.hidden = false;

    try {
        const formData = new FormData(enquiryForm);
        const response = await fetch("/enquiries", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(Object.fromEntries(formData)),
        });
        const data = await response.json();
        if (!response.ok) throw new Error(data.message || "Unable to process enquiry.");
        enquiryResult.innerHTML = `
            <h2>${escapeHtml(data.status)}</h2>
            <p>${escapeHtml(data.message)}</p>
            <p><strong>Summary:</strong> ${escapeHtml(data.summary)}</p>
            <p><a href="${escapeHtml(data.audio_url)}" target="_blank" rel="noopener">Open generated audio</a></p>
            <audio controls src="${escapeHtml(data.audio_url)}"></audio>
        `;
        enquiryForm.reset();
    } catch (error) {
        enquiryResult.textContent = error.message;
    } finally {
        submitEnquiryButton.disabled = false;
        submitEnquiryButton.textContent = "Send enquiry to Asterisk";
    }
});

function showMailNotification(result) {
    if (!result || !result.new_reply || !result.reply_id || result.reply_id === lastNotifiedReplyId) {
        return;
    }

    lastNotifiedReplyId = result.reply_id;
    notificationDetails.textContent = `${result.sender || "Unknown client"}${result.subject ? ` - ${result.subject}` : ""}`;
    notificationSummary.textContent = result.summary || "No message summary available.";
    mailNotification.hidden = false;

    if ("Notification" in window && Notification.permission === "granted") {
        new Notification("New client email received", {
            body: notificationDetails.textContent,
        });
    }
}

function requestBrowserNotifications() {
    if ("Notification" in window && Notification.permission === "default") {
        Notification.requestPermission();
    }
}

async function refreshStatus() {
    try {
        const response = await fetch("/monitor-status");
        const data = await response.json();
        currentTime.textContent = data.current_time;
        currentTime.dateTime = data.current_time.replace(" ", "T");
        timezoneLabel.textContent = `Server time (${data.timezone})`;
        monitorState.textContent = data.running ? "Monitor running" : "Monitor stopped";
        monitorIndicator.className = `status-dot ${data.running ? "running" : "stopped"}`;
        startButton.disabled = data.running;
        stopButton.disabled = !data.running;
        showMailNotification(data.last_event || data.last_result);
    } catch (error) {
        monitorState.textContent = "Status unavailable";
    }
}

async function changeMonitor(action) {
    const button = action === "start" ? startButton : stopButton;
    button.disabled = true;
    try {
        const response = await fetch(`/monitor/${action}`, { method: "POST" });
        const data = await response.json();
        if (!response.ok) throw new Error(data.message || "Unable to change monitor state.");
        resultBox.textContent = data.message;
        resultBox.hidden = false;
        await refreshStatus();
    } catch (error) {
        resultBox.textContent = error.message;
        resultBox.hidden = false;
    }
}

startButton.addEventListener("click", () => {
    requestBrowserNotifications();
    changeMonitor("start");
});
stopButton.addEventListener("click", () => changeMonitor("stop"));

checkButton.addEventListener("click", async () => {
    requestBrowserNotifications();
    checkButton.disabled = true;
    checkButton.textContent = "Checking Gmail...";

    try {
        const response = await fetch("/check-reply");
        const data = await response.json();
        if (!response.ok) throw new Error(data.message || "Unable to check Gmail.");
        showMailNotification(data);

        resultBox.innerHTML = `
            <h2>${escapeHtml(data.status || "Result")}</h2>
            <p>${escapeHtml(data.message || "No status returned.")}</p>
            ${data.sender ? `<p><strong>Recognized client:</strong> ${escapeHtml(data.sender)}</p>` : ""}
            ${data.subject ? `<p><strong>Subject:</strong> ${escapeHtml(data.subject)}</p>` : ""}
            ${data.audio_url ? `<p><strong>Audio:</strong> <a href="${escapeHtml(data.audio_url)}" target="_blank" rel="noopener">Open audio file</a></p><audio controls src="${escapeHtml(data.audio_url)}"></audio>` : ""}
        `;
        resultBox.hidden = false;
    } catch (error) {
        resultBox.textContent = error.message;
        resultBox.hidden = false;
    } finally {
        checkButton.disabled = false;
        checkButton.textContent = "Check Gmail now";
    }
});

dismissNotification.addEventListener("click", () => {
    mailNotification.hidden = true;
});

refreshStatus();
setInterval(refreshStatus, 1000);

function escapeHtml(value) {
    return String(value).replace(/[&<>'"]/g, character => ({
        "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;",
    }[character]));
}