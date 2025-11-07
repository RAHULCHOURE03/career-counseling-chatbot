// Add event listeners to send button and input field
document.getElementById("sendButton").addEventListener("click", sendMessage);
document.getElementById("userInput").addEventListener("keydown", function (event) {
    if (event.key === "Enter") {
        sendMessage();
    }
});

// Voice Input (Speech Recognition) with Real-Time Display
document.getElementById("voiceInputButton").addEventListener("click", function () {
    let button = document.getElementById("voiceInputButton");
    let userInput = document.getElementById("userInput");
    let recognition = new (window.SpeechRecognition || window.webkitSpeechRecognition)();
    recognition.lang = "en-US";
    recognition.interimResults = true;

    // Change button text to indicate listening
    button.innerText = "🎤 Listening...";

    // Clear input field before starting
    userInput.value = "";

    recognition.onresult = function (event) {
        let transcript = event.results[event.results.length - 1][0].transcript;
        userInput.value = transcript.trim();
    };

    recognition.onspeechend = function () {
        recognition.stop();
        button.innerText = "🎙 Voice";
    };

    recognition.onerror = function () {
        button.innerText = "🎙 Voice";
    };

    recognition.start();
});

// Voice Output (Text-to-Speech) with Toggle
let isSpeaking = false;
let synth = window.speechSynthesis;
let utterance = null;

document.getElementById("voiceOutputButton").addEventListener("click", function () {
    let chatLog = document.getElementById("chat-log");
    let lastBotMessage = chatLog.querySelector(".bot-message:last-child");
    let button = document.getElementById("voiceOutputButton");

    if (!isSpeaking && lastBotMessage) {
        let messageText = lastBotMessage.innerText;
        
         // Remove unwanted characters (e.g., diamonds, emojis)
         messageText = messageText.replace(/[^\u0000-\u007F\u0900-\u097F\s.,?!]/g, "").trim();

         // Detect language
         const hindiRegex = /[\u0900-\u097F]/;
         const lang = hindiRegex.test(messageText) ? "hi-IN" : "en-US";
 
         utterance = new SpeechSynthesisUtterance(messageText);
         utterance.lang = lang;
         utterance.rate = 1;
 
         // 🧠 Try setting a preferred Hindi-compatible voice if available
         let voices = synth.getVoices();
         if (lang === "hi-IN") {
             let hindiVoice = voices.find(v => v.lang === "hi-IN" || v.name.includes("Hindi"));
             if (hindiVoice) utterance.voice = hindiVoice;
         }

        utterance.onend = function () {
            isSpeaking = false;
            button.innerText = "🔊 Read";
        };

        synth.speak(utterance);
        isSpeaking = true;
        button.innerText = "⏹ Stop";
    } else {
        synth.cancel();
        isSpeaking = false;
        button.innerText = "🔊 Read";
    }
});

let userEmail = null; // Global variable to store user email

// Fetch user details separately on page load
document.addEventListener("DOMContentLoaded", function () {
    fetch(`/get-user`)
        .then(response => response.json())
        .then(user => {
            if (user.name) {
                document.getElementById("username").textContent = user.name;
                document.getElementById("profile-icon").textContent = user.name.charAt(0).toUpperCase();
            }

            if (user.email) {
                userEmail = user.email; // ✅ Store email globally
                console.log("Fetched Email:", userEmail);
            }
        })
        .catch(error => console.error("Error fetching user data:", error));
});

// Function to send the message to the backend and display responses
function sendMessage() {
    let userMessage = document.getElementById("userInput").value.trim();


    if (userMessage === "") return; // Skip if input is empty

    // Add user's message to the chat log
    addMessageToChatLog(userMessage, "user-message");

    // Clear the input field
    document.getElementById("userInput").value = "";

    // Send user's message to the Flask backend and get a response
    fetch(`http://127.0.0.1:5000/home/${encodeURIComponent(userMessage)}`)
        .then(response => response.json())
        .then(data => {
            if (data.top && data.top.res) {
                let botResponse = data.top.res;
                addMessageToChatLog(botResponse, "bot-message");

                // ✅ Store chatbot history after getting a response
                console.log("Storing History:", { user_email: userEmail, userMessage, botResponse });
                storeSearchHistory(userEmail, userMessage, botResponse);
            } else {
                addMessageToChatLog("Error: No response received.", "bot-message");
            }
        })
        .catch(error => {
            console.error('Error:', error);
            addMessageToChatLog("Error: Unable to connect to server.", "bot-message");
        });
}

// Function to add messages to the chat log
function addMessageToChatLog(message, className) {
    let chatLog = document.getElementById("chat-log");

    if (!chatLog) {
        console.error("Error: chat-log element not found.");
        return;
    }

    let messageDiv = document.createElement("div");
    messageDiv.classList.add(className);
    messageDiv.innerText = message;

    chatLog.appendChild(messageDiv);
    chatLog.scrollTop = chatLog.scrollHeight;
}

// ✅ Function to store chatbot history in Flask backend
function storeSearchHistory(userEmail, question, answer) {
    console.log("Storing History:", { user_email: userEmail, question, answer });  // ✅ Log before sending

    fetch('/store-search', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            user_email: userEmail,
            question: question,
            answer: answer
        })
    })
        .then(response => response.json())
        .then(data => console.log("History Saved:", data))
        .catch(error => console.error("Error saving history:", error));
}


document.addEventListener("DOMContentLoaded", function () {
    let username = null; // Declare a variable to store the user's email

    // Fetch user details from the backend
    fetch(`/get-user`)
        .then(response => response.json())
        .then(user => {
            if (user.name) {
                document.getElementById("username").textContent = user.name;  // Show full name
                document.getElementById("profile-icon").textContent = user.name.charAt(0).toUpperCase(); // Show first letter
            }

            if (user.email) {
                userEmail = user.email; // Store user email correctly
                console.log("Fetched email:", userEmail);

                // Now fetch search history only after getting the correct email
                console.log("fetching history");
                setTimeout(() => {
                    fetch(`/get-history?user_email=${userEmail}`)
                        .then(response => response.json())
                        .then(history => {
                            console.log("Full history response:", history); // Log full response

                            if (!history || Object.keys(history).length === 0) {
                                console.error("No history found for this user.");
                                return;
                            }

                            let historyList = document.getElementById("history-list");
                            historyList.innerHTML = "";

                            Object.keys(history).forEach(date => {
                                console.log("Processing date:", date, "Data:", history[date]);


                                let listItem = document.createElement("li");
                                let link = document.createElement("a");
                                link.href = `/history/${userEmail}/${date}`;
                                link.textContent = date;
                                listItem.appendChild(link);
                                historyList.appendChild(listItem);
                            });
                        })
                        .catch(error => console.error("Error fetching history:", error));
                }, 1000);
            }
        })
        .catch(error => console.error("Error fetching user data:", error));

    // Sidebar Toggle
    const sidebar = document.getElementById("sidebar");
    document.getElementById("toggle-sidebar").addEventListener("click", function () {
        sidebar.classList.toggle("open");
    });

    document.getElementById("close-btn").addEventListener("click", function () {
        sidebar.classList.remove("open");
    });

    // Chatbot Search & Store History
    document.getElementById("sendButton").addEventListener("click", function () {
        let question = document.getElementById("userInput").value;

        if (!username) {
            console.error("User email is not available yet.");
            return;
        }

        fetch("/chatbot", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ question, user_email: username })
        })
            .then(response => response.json())
            .then(data => {
                document.getElementById("chat-log").innerHTML += `<div class="bot-message">${data.answer}</div>`;

                // Store search in history
                fetch("/store-search", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ question, answer: data.answer, user_email: username })
                });
            });
    });
});

document.getElementById("history-list").addEventListener("click", function(event) {
    if (event.target.tagName === "A") {
        event.preventDefault();  // Stop default link action

        let historyUrl = event.target.href;

        fetch(historyUrl)
            .then(response => response.json())
            .then(historyData => {
                console.log("History Data:", historyData);

                // Print history to chatbot UI
                historyData.forEach(entry => {
                    appendToChatbot(entry.question, "user");  // User's past queries
                    appendToChatbot(entry.answer, "bot");  // Corresponding bot responses
                });
            })
            .catch(error => console.error("Error fetching chat history:", error));
    }
});

// Function to append messages to chatbot UI
function appendToChatbot(text, sender) {
    let chatContainer = document.getElementById("chat-log");
    let messageDiv = document.createElement("div");
    messageDiv.className = sender === "user" ? "user-message" : "bot-message";
    messageDiv.textContent = text;
    chatContainer.appendChild(messageDiv);
}

document.getElementById("logout-btn").addEventListener("click", function () {
    fetch("/logout", { method: "POST" })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                window.location.href = "/login"; // Redirect to login page
            }
        })
        .catch(error => console.error("Error logging out:", error));
});
