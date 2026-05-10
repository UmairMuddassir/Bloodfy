/**
 * Chatbot Integration Script
 * Handles chat interactions with the backend AI chatbot
 */

document.addEventListener('DOMContentLoaded', () => {
    // =============================================================================
    // Chat Elements
    // =============================================================================

    const messagesContainer = document.querySelector('.messages-container');
    const chatInput = document.querySelector('.chat-input');
    const sendButton = document.querySelector('.btn-send');
    const inputArea = document.querySelector('.input-area');

    if (!messagesContainer || !chatInput || !sendButton) return;

    // =============================================================================
    // Send Message Function
    // =============================================================================

    async function sendMessage() {
        const message = chatInput.value.trim();

        if (!message) return;

        // Clear input
        chatInput.value = '';

        // Add user message to UI
        addUserMessage(message);

        // Show typing indicator
        showTypingIndicator();

        // Disable input during processing
        chatInput.disabled = true;
        sendButton.disabled = true;

        try {
            // Call chatbot API
            const result = await API.chatbot.sendQuery(message);

            // Hide typing indicator
            hideTypingIndicator();

            // Add bot response to UI
            if (result.success && result.data) {
                // Backend sends 'message' key
                const botResponse = result.data.message || result.data.response || result.data.answer || 'I understand. How else can I help?';
                addBotMessage(botResponse);
                
                // Show suggestion chips if available
                const suggestions = result.data.suggestions || [];
                if (suggestions.length > 0) {
                    addSuggestionChips(suggestions);
                }
            } else {
                addBotMessage('Sorry, I could not process that. Please try a different question.');
            }

        } catch (error) {
            console.error('Chatbot error:', error);

            // Hide typing indicator
            hideTypingIndicator();

            // Show helpful fallback instead of generic error
            addBotMessage(
                "I'm having trouble connecting to the server right now. 🔄\n\n" +
                "Please make sure the backend server is running, then try again.\n\n" +
                "In the meantime, you can:\n" +
                "• Check the **Emergency** page for urgent needs\n" +
                "• Visit **Blood Stock** for inventory\n" +
                "• Go to **Donors** page for donor info"
            );
        } finally {
            // Re-enable input
            chatInput.disabled = false;
            sendButton.disabled = false;
            chatInput.focus();
        }
    }

    // =============================================================================
    // Add User Message to UI
    // =============================================================================

    function addUserMessage(text) {
        const messageDiv = document.createElement('div');
        messageDiv.className = 'message user';
        messageDiv.textContent = text;

        messagesContainer.appendChild(messageDiv);
        scrollToBottom();
    }

    // =============================================================================
    // Add Bot Message to UI
    // =============================================================================

    function addBotMessage(text) {
        const messageDiv = document.createElement('div');
        messageDiv.className = 'message bot';
        
        // Format: convert \n to <br>, **bold** to <strong>
        let formatted = text
            .replace(/\n/g, '<br>')
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
        
        messageDiv.innerHTML = `
            <div class="avatar"><i class="fas fa-robot"></i></div>
            <div class="bot-text">${formatted}</div>
        `;

        messagesContainer.appendChild(messageDiv);
        scrollToBottom();
    }

    // =============================================================================
    // Suggestion Chips
    // =============================================================================

    function addSuggestionChips(suggestions) {
        const chipsDiv = document.createElement('div');
        chipsDiv.className = 'suggestion-chips';
        chipsDiv.style.cssText = 'display:flex;gap:8px;flex-wrap:wrap;padding:8px 0 8px 50px;';
        
        suggestions.forEach(text => {
            const chip = document.createElement('button');
            chip.textContent = text;
            chip.style.cssText = `
                background:rgba(229,57,53,0.15);
                color:#FF5252;
                border:1px solid rgba(229,57,53,0.3);
                border-radius:20px;
                padding:6px 14px;
                font-size:0.8rem;
                font-family:Poppins,sans-serif;
                cursor:pointer;
                transition:all 0.2s;
                white-space:nowrap;
            `;
            chip.onmouseover = () => { chip.style.background = 'rgba(229,57,53,0.3)'; };
            chip.onmouseout = () => { chip.style.background = 'rgba(229,57,53,0.15)'; };
            chip.onclick = () => {
                chatInput.value = text;
                chipsDiv.remove();
                sendMessage();
            };
            chipsDiv.appendChild(chip);
        });

        messagesContainer.appendChild(chipsDiv);
        scrollToBottom();
    }

    // =============================================================================
    // Typing Indicator
    // =============================================================================

    function showTypingIndicator() {
        // Check if indicator already exists
        if (document.querySelector('.typing-indicator')) {
            return;
        }

        const indicatorDiv = document.createElement('div');
        indicatorDiv.className = 'typing-indicator';
        indicatorDiv.innerHTML = `
            Bloodfy AI is typing
            <div class="dot"></div>
            <div class="dot"></div>
            <div class="dot"></div>
        `;

        messagesContainer.appendChild(indicatorDiv);
        scrollToBottom();
    }

    function hideTypingIndicator() {
        const indicator = document.querySelector('.typing-indicator');
        if (indicator) {
            indicator.remove();
        }
    }

    // =============================================================================
    // Scroll to Bottom
    // =============================================================================

    function scrollToBottom() {
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }

    // =============================================================================
    // Event Listeners
    // =============================================================================

    // Send button click
    sendButton.addEventListener('click', sendMessage);

    // Enter key in input
    chatInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });

    // =============================================================================
    // Suggested Actions (Info Panel)
    // =============================================================================

    const infoCards = document.querySelectorAll('.info-card');
    infoCards.forEach(card => {
        card.addEventListener('click', () => {
            const heading = card.querySelector('h4').textContent;

            // Map headings to queries
            const queryMap = {
                'Find Donors': 'Find donors for O- blood type in Lahore',
                'Verify Donor': 'How do I verify a new donor?',
                'Check Stock': 'What is the current blood stock level?',
                'Emergency Alert': 'How do I send an emergency alert?'
            };

            const query = queryMap[heading] || heading;

            // Set query in input
            chatInput.value = query;
            chatInput.focus();
        });
    });

    // =============================================================================
    // Load Chat History (Optional)
    // =============================================================================

    async function loadChatHistory() {
        // If you want to load previous chat history from backend
        // This would require a chat history endpoint
        // For now, start with a welcome message

        // Check if there are already messages (from HTML)
        const existingMessages = messagesContainer.querySelectorAll('.message');
        if (existingMessages.length === 0) {
            addBotMessage('Hello! I am the Bloodfy AI Assistant. How can I help you with donor management or blood requests today?');
        }
    }

    // Initialize chat
    loadChatHistory();

    // Focus input on load
    chatInput.focus();
});
