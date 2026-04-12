class AssistantChat {
    constructor() {
        this.apiUrl = '/api/chat';
        this.csrfToken = document.querySelector('meta[name="csrf-token"]')?.content || '';
        this.messagesContainer = document.getElementById('chatMessages');
        this.input = document.getElementById('messageInput');
        this.sendButton = document.getElementById('sendButton');
        this.clearHistoryBtn = document.getElementById('clearHistory');
        this.documentsList = document.getElementById('documentsList');
        this.isLoading = false;
        this.markdownParser = new MarkdownParser();
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.loadDocuments();
        this.loadHistory();
    }

    setupEventListeners() {
        this.input.addEventListener('input', () => {
            this.sendButton.disabled = !this.input.value.trim();
            this.autoResizeTextarea();
        });

        this.input.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                if (this.input.value.trim() && !this.isLoading) {
                    this.sendMessage();
                }
            }
        });

        this.sendButton.addEventListener('click', () => {
            if (!this.isLoading) {
                this.sendMessage();
            }
        });

        this.clearHistoryBtn.addEventListener('click', () => {
            this.clearHistory();
        });
    }

    autoResizeTextarea() {
        this.input.style.height = 'auto';
        this.input.style.height = Math.min(this.input.scrollHeight, 150) + 'px';
    }

    addMessage(role, content, isStreaming = false) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message message-${role}`;
        
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
        
        if (isStreaming) {
            messageDiv.setAttribute('data-streaming', 'true');
        }
        
        this.messagesContainer.appendChild(messageDiv);
        this.messagesContainer.scrollTop = this.messagesContainer.scrollHeight;
    }

    updateLastMessage(content) {
        const lastMessage = this.messagesContainer.lastElementChild;
        if (lastMessage && lastMessage.classList.contains('message-assistant')) {
            const contentDiv = lastMessage.querySelector('.message-content');
            if (contentDiv) {
                contentDiv.innerHTML = this.markdownParser.parse(content);
            }
            this.messagesContainer.scrollTop = this.messagesContainer.scrollHeight;
        }
    }

    showTypingIndicator() {
        const indicator = document.createElement('div');
        indicator.className = 'message message-assistant typing-indicator';
        indicator.innerHTML = '<div class="typing-dots"><span>.</span><span>.</span><span>.</span></div>';
        this.messagesContainer.appendChild(indicator);
        this.messagesContainer.scrollTop = this.messagesContainer.scrollHeight;
    }

    removeTypingIndicator() {
        const indicator = this.messagesContainer.querySelector('.typing-indicator');
        if (indicator) {
            indicator.remove();
        }
    }

    async sendMessage() {
        const message = this.input.value.trim();
        if (!message || this.isLoading) return;

        this.addMessage('user', message);
        this.input.value = '';
        this.input.style.height = 'auto';
        this.sendButton.disabled = true;
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
                })
            });

            if (!response.ok) throw new Error('Network error');

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
                            console.error('Parse error:', e);
                        }
                    }
                }
            }
        } catch (error) {
            console.error('Error:', error);
            this.removeTypingIndicator();
            this.addMessage('assistant', 'Извините, произошла ошибка. Попробуйте еще раз.');
        } finally {
            this.isLoading = false;
        }
    }

    async loadHistory() {
        try {
            const response = await fetch(`${this.apiUrl}/history`);
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

    async clearHistory() {
        if (!confirm('Очистить историю чата?')) return;
        try {
            const response = await fetch(`${this.apiUrl}/history`, {
                method: 'DELETE',
                headers: { 'X-CSRF-Token': this.csrfToken }
            });
            if (response.ok) {
                this.messagesContainer.innerHTML = '';
                this.addMessage('assistant', 'История очищена. Чем могу помочь?');
            }
        } catch (error) {
            console.error('Error clearing history:', error);
        }
    }

    async loadDocuments() {
        try {
            const response = await fetch(`${this.apiUrl}/documents`);
            if (response.ok) {
                const data = await response.json();
                if (data.documents && data.documents.length > 0) {
                    this.renderDocuments(data.documents);
                } else {
                    this.documentsList.innerHTML = '<div class="loading">Нет загруженных документов</div>';
                }
            }
        } catch (error) {
            console.error('Error loading documents:', error);
            this.documentsList.innerHTML = '<div class="loading">Ошибка загрузки документов</div>';
        }
    }

    renderDocuments(documents) {
        this.documentsList.innerHTML = '';
        documents.forEach(doc => {
            const docEl = document.createElement('div');
            docEl.className = 'document-item';
            docEl.innerHTML = `
                <div class="document-name">${doc.display_name}</div>
                <div class="document-meta">${doc.chunks} фрагментов • ${Math.round(doc.size / 1024)} KB</div>
            `;
            this.documentsList.appendChild(docEl);
        });
    }
}

document.addEventListener('DOMContentLoaded', () => {
    new AssistantChat();
});