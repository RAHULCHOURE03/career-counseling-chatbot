const chatLog = document.getElementById("chat-log");
const input = document.getElementById("userInput");

function addMessage(message, className) {
    const element = document.createElement("div");
    element.classList.add(className);
    element.innerText = message;
    chatLog.appendChild(element);
    chatLog.scrollTop = chatLog.scrollHeight;
}

async function sendMessage() {
    const message = input.value.trim();
    if (!message) return;
    addMessage(message, "user-message");
    input.value = "";
    try {
        const response = await fetch("/api/chat", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ message })
        });
        const data = await response.json();
        addMessage(data.answer || data.error || "Error: No response received.", "bot-message");
        if (response.ok) loadHistory();
    } catch (error) {
        console.error("Chat request failed:", error);
        addMessage("Error: Unable to connect to server.", "bot-message");
    }
}

async function loadHistory() {
    const response = await fetch("/api/history");
    if (!response.ok) return;
    const { dates } = await response.json();
    const historyList = document.getElementById("history-list");
    historyList.innerHTML = "";
    dates.forEach((date) => {
        const link = document.createElement("a");
        link.href = `/api/history/${date}`;
        link.textContent = date;
        const item = document.createElement("li");
        item.appendChild(link);
        historyList.appendChild(item);
    });
}

document.getElementById("sendButton").addEventListener("click", sendMessage);
input.addEventListener("keydown", (event) => {
    if (event.key === "Enter") sendMessage();
});

document.getElementById("history-list").addEventListener("click", async (event) => {
    if (event.target.tagName !== "A") return;
    event.preventDefault();
    const response = await fetch(event.target.href);
    if (!response.ok) return;
    const entries = await response.json();
    chatLog.innerHTML = "";
    entries.forEach(({ question, answer }) => {
        addMessage(question, "user-message");
        addMessage(answer, "bot-message");
    });
});

document.addEventListener("DOMContentLoaded", async () => {
    const response = await fetch("/api/me");
    if (response.ok) {
        const user = await response.json();
        document.getElementById("username").textContent = user.name;
        document.getElementById("profile-icon").textContent = user.name.charAt(0).toUpperCase();
    }
    loadHistory();
});

document.getElementById("toggle-sidebar").addEventListener("click", () => document.getElementById("sidebar").classList.toggle("open"));
document.getElementById("close-btn").addEventListener("click", () => document.getElementById("sidebar").classList.remove("open"));
document.getElementById("logout-btn").addEventListener("click", async () => {
    if ((await fetch("/logout", { method: "POST" })).ok) window.location.href = "/login";
});

let isSpeaking = false;
const synth = window.speechSynthesis;
document.getElementById("voiceOutputButton").addEventListener("click", () => {
    const lastBot = chatLog.querySelector(".bot-message:last-child");
    const button = document.getElementById("voiceOutputButton");
    if (!isSpeaking && lastBot) {
        const utterance = new SpeechSynthesisUtterance(lastBot.innerText);
        utterance.lang = /[\u0900-\u097F]/.test(utterance.text) ? "hi-IN" : "en-US";
        utterance.onend = () => { isSpeaking = false; button.innerText = "🔊 Read"; };
        synth.speak(utterance); isSpeaking = true; button.innerText = "⏹ Stop";
    } else { synth.cancel(); isSpeaking = false; button.innerText = "🔊 Read"; }
});

document.getElementById("voiceInputButton").addEventListener("click", () => {
    const button = document.getElementById("voiceInputButton");
    const recognition = new (window.SpeechRecognition || window.webkitSpeechRecognition)();
    recognition.lang = "en-US"; recognition.interimResults = true; button.innerText = "🎤 Listening..."; input.value = "";
    recognition.onresult = (event) => { input.value = event.results[event.results.length - 1][0].transcript.trim(); };
    recognition.onend = recognition.onerror = () => { button.innerText = "🎙 Voice"; };
    recognition.start();
});
