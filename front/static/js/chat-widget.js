class ChatWidget {
    constructor(options = {}) {
        this.apiUrl = options.apiUrl || '/api/chat';
        this.csrfToken = options.csrfToken || document.querySelector('meta[name="csrf-token"]')?.content || '';
        this.position = options.position || 'bottom-right';
        this.theme = options.theme || 'light';
        this.useRag = options.useRag !== false;
        this.container = null;
        this.messages = [];
        this.isOpen = false;
        this.isMinimized = true;
        this.isLoading = false;
        this.sessionId = this.getSessionId();
        this.markdownParser = new MarkdownParser();
        this.init();
    }

    getSessionId() {
        let sessionId = localStorage.getItem('chat_session_id');
        if (!sessionId) {
            sessionId = 'session_' + Math.random().toString(36).substring(2, 15);
            localStorage.setItem('chat_session_id', sessionId);
        }
        return sessionId;
    }

    init() {
        this.createWidget();
        this.loadHistory();
        this.setupEventListeners();
    }

    createWidget() {
        this.container = document.createElement('div');
        this.container.className = `chat-widget chat-${this.position} chat-theme-${this.theme}`;
        this.container.innerHTML = `
            <div class="chat-toggle ${this.isMinimized ? '' : 'hidden'}">
                <button class="chat-toggle-btn" aria-label="Открыть чат">
                    <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
                        <path d="M20 2H4C2.9 2 2 2.9 2 4V22L6 18H20C21.1 18 22 17.1 22 16V4C22 2.9 21.1 2 20 2Z" fill="currentColor"/>
                    </svg>
                </button>
            </div>
            <div class="chat-window ${this.isMinimized ? 'hidden' : ''}">
                <div class="chat-header">
                    <h3>MartFi Ассистент</h3>
                    <div class="chat-header-actions">
                        <button class="chat-minimize-btn" aria-label="Свернуть">
                            <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
                                <path d="M19 13H5V11H19V13Z" fill="currentColor"/>
                            </svg>
                        </button>
                        <button class="chat-close-btn" aria-label="Закрыть">
                            <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
                                <path d="M19 6.41L17.59 5L12 10.59L6.41 5L5 6.41L10.59 12L5 17.59L6.41 19L12 13.41L17.59 19L19 17.59L13.41 12L19 6.41Z" fill="currentColor"/>
                            </svg>
                        </button>
                    </div>
                </div>
                <div class="chat-messages"></div>
                <div class="chat-input-area">
                    <div class="rag-toggle">
                        <label>
                            <input type="checkbox" ${this.useRag ? 'checked' : ''}>
                            Использовать базу знаний
                        </label>
                    </div>
                    <div class="input-wrapper">
                        <textarea class="chat-input" placeholder="Задайте вопрос..."></textarea>
                        <button class="chat-send-btn" disabled>
                            <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
                                <path d="M2 21L23 12L2 3V10L17 12L2 14V21Z" fill="currentColor"/>
                            </svg>
                        </button>
                    </div>
                </div>
            </div>
        `;
        document.body.appendChild(this.container);
    }

    setupEventListeners() {
        const toggleBtn = this.container.querySelector('.chat-toggle-btn');
        const minimizeBtn = this.container.querySelector('.chat-minimize-btn');
        const closeBtn = this.container.querySelector('.chat-close-btn');
        const sendBtn = this.container.querySelector('.chat-send-btn');
        const input = this.container.querySelector('.chat-input');
        const ragCheckbox = this.container.querySelector('.rag-toggle input');

        toggleBtn?.addEventListener('click', () => this.toggle());
        minimizeBtn?.addEventListener('click', () => this.minimize());
        closeBtn?.addEventListener('click', () => this.close());

        input.addEventListener('input', () => {
            sendBtn.disabled = !input.value.trim();
            this.autoResizeTextarea(input);
        });

        input.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                if (input.value.trim()) {
                    this.sendMessage();
                }
            }
        });

        sendBtn.addEventListener('click', () => this.sendMessage());
        ragCheckbox.addEventListener('change', (e) => {
            this.useRag = e.target.checked;
        });
    }

    autoResizeTextarea(textarea) {
        textarea.style.height = 'auto';
        textarea.style.height = Math.min(textarea.scrollHeight, 150) + 'px';
    }

    toggle() {
        this.isMinimized = !this.isMinimized;
        this.updateVisibility();
    }

    minimize() {
        this.isMinimized = true;
        this.updateVisibility();
    }

    close() {
        this.isMinimized = true;
        this.isOpen = false;
        this.updateVisibility();
    }

    updateVisibility() {
        const toggle = this.container.querySelector('.chat-toggle');
        const window = this.container.querySelector('.chat-window');
        if (toggle) toggle.classList.toggle('hidden', !this.isMinimized);
        if (window) window.classList.toggle('hidden', this.isMinimized);
    }

    async sendMessage() {
        const input = this.container.querySelector('.chat-input');
        const message = input.value.trim();
        if (!message || this.isLoading) return;

        this.addMessage('user', message);
        input.value = '';
        input.style.height = 'auto';
        this.container.querySelector('.chat-send-btn').disabled = true;
        this.isLoading = true;
        this.showTypingIndicator();

        try {
            const response = await fetch(`${this.apiUrl}/message/stream`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRF-Token': this.csrfToken
                },
                body: JSON.stringify({
                    message: message,
                    use_rag: this.useRag
                })
            });

            if (!response.ok) throw new Error('Network response was not ok');

            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let assistantMessage = '';

            this.removeTypingIndicator();
            this.addMessage('assistant', '', true);

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                const chunk = decoder.decode(value);
                const lines = chunk.split('\n');

                for (const line of lines) {
                    if (line.startsWith('data: ') && line !== 'data: [DONE]') {
                        try {
                            const data = JSON.parse(line.substring(6));
                            if (data.choices && data.choices[0].delta.content) {
                                assistantMessage += data.choices[0].delta.content;
                                this.updateLastMessage(assistantMessage);
                            }
                        } catch (e) {
                            console.error('Error parsing chunk:', e);
                        }
                    }
                }
            }
        } catch (error) {
            console.error('Error sending message:', error);
            this.removeTypingIndicator();
            this.addMessage('assistant', 'Извините, произошла ошибка. Пожалуйста, попробуйте еще раз.');
        } finally {
            this.isLoading = false;
        }
    }

    addMessage(role, content, isStreaming = false) {
        const messagesContainer = this.container.querySelector('.chat-messages');
        const messageDiv = document.createElement('div');
        messageDiv.className = `message message-${role}`;
        
        if (isStreaming) {
            messageDiv.classList.add('streaming');
            messageDiv.setAttribute('data-streaming', 'true');
        }
        
        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content';
        
        if (role === 'assistant') {
            contentDiv.innerHTML = this.markdownParser.parse(content);
        } else {
            contentDiv.textContent = content;
        }
        
        const timeDiv = document.createElement('div');
        timeDiv.className = 'message-time';
        timeDiv.textContent = new Date().toLocaleTimeString();
        
        messageDiv.appendChild(contentDiv);
        messageDiv.appendChild(timeDiv);
        
        messagesContainer.appendChild(messageDiv);
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
        this.messages.push({ role, content, timestamp: new Date() });
    }

    updateLastMessage(content) {
        const messagesContainer = this.container.querySelector('.chat-messages');
        const lastMessage = messagesContainer.lastElementChild;
        if (lastMessage && lastMessage.classList.contains('message-assistant')) {
            const contentDiv = lastMessage.querySelector('.message-content');
            if (contentDiv) {
                contentDiv.innerHTML = this.markdownParser.parse(content);
            }
            messagesContainer.scrollTop = messagesContainer.scrollHeight;
        }
    }

    showTypingIndicator() {
        const messagesContainer = this.container.querySelector('.chat-messages');
        const indicator = document.createElement('div');
        indicator.className = 'message message-assistant typing-indicator';
        indicator.innerHTML = '<div class="typing-dots"><span>.</span><span>.</span><span>.</span></div>';
        messagesContainer.appendChild(indicator);
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }

    removeTypingIndicator() {
        const indicator = this.container.querySelector('.typing-indicator');
        if (indicator) {
            indicator.remove();
        }
    }

    async loadHistory() {
        try {
            const response = await fetch(`${this.apiUrl}/history?session_id=${this.sessionId}`);
            if (response.ok) {
                const data = await response.json();
                if (data.messages) {
                    data.messages.forEach(msg => {
                        this.addMessage(msg.role, msg.content);
                    });
                }
            }
        } catch (error) {
            console.error('Error loading history:', error);
        }
    }
}

if (typeof module !== 'undefined' && module.exports) {
    module.exports = ChatWidget;
}