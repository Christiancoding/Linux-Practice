class CLIPlayground {
    constructor() {
        this.commandHistory = [];
        this.historyIndex = -1;
        this.isProcessing = false;
        this.suggestions = [];
        this.currentSuggestionIndex = -1;
        
        this.init();
    }
    
    init() {
        this.bindEvents();
        this.loadAvailableCommands();
        this.focusInput();
        this.addWelcomeMessage();
    }
    
    bindEvents() {
        const input = document.getElementById('cliInput');
        if (!input) return;
        
        // Main input events
        input.addEventListener('keydown', (e) => this.handleKeyDown(e));
        input.addEventListener('input', (e) => this.handleInput(e));
        
        // Terminal click to focus
        const terminal = document.getElementById('cliTerminal');
        if (terminal) {
            terminal.addEventListener('click', () => this.focusInput());
        }
        
        // Global shortcuts
        document.addEventListener('keydown', (e) => {
            if (e.ctrlKey || e.metaKey) {
                switch(e.key) {
                    case 'l':
                        e.preventDefault();
                        this.clearTerminal();
                        break;
                    case 'r':
                        e.preventDefault();
                        this.resetPlayground();
                        break;
                }
            }
        });
    }
    
    handleKeyDown(e) {
        const input = e.target;
        
        switch(e.key) {
            case 'Enter':
                e.preventDefault();
                this.executeCommand();
                break;
                
            case 'ArrowUp':
                e.preventDefault();
                this.navigateHistory('up');
                break;
                
            case 'ArrowDown':
                e.preventDefault();
                this.navigateHistory('down');
                break;
                
            case 'Tab':
                e.preventDefault();
                this.handleTabCompletion();
                break;
                
            case 'Escape':
                e.preventDefault();
                input.value = '';
                this.historyIndex = this.commandHistory.length;
                break;
        }
    }
    
    handleInput(e) {
        // Reset history index when user types
        this.historyIndex = this.commandHistory.length;
    }
    
    handleTabCompletion() {
        const input = document.getElementById('cliInput');
        const currentValue = input.value.trim();
        
        if (!currentValue) return;
        
        const matches = this.suggestions.filter(cmd => 
            cmd.toLowerCase().startsWith(currentValue.toLowerCase())
        );
        
        if (matches.length === 1) {
            input.value = matches[0];
        } else if (matches.length > 1) {
            this.addToTerminal(`Available completions: ${matches.join(', ')}`, 'result');
            this.scrollToBottom();
        }
    }
    
    executeCommand() {
        const input = document.getElementById('cliInput');
        const command = input.value.trim();
        
        if (!command || this.isProcessing) return;
        
        // Add command to display
        this.addToTerminal(`student@linux-study:~/sandbox$ ${command}`, 'command');
        
        // Add to history
        if (command !== this.commandHistory[this.commandHistory.length - 1]) {
            this.commandHistory.push(command);
        }
        this.historyIndex = this.commandHistory.length;
        
        // Clear input
        input.value = '';
        
        // Execute command
        this.processCommand(command);
    }
    
    processCommand(command) {
        this.isProcessing = true;
        this.showLoading(true);
        
        this.callAPI('/api/cli/execute', 'POST', { command: command })
            .then(data => {
                this.handleCommandResult(data);
            })
            .catch(error => {
                this.addToTerminal(`Network error: ${error.message}`, 'error');
            })
            .finally(() => {
                this.showLoading(false);
                this.isProcessing = false;
                this.scrollToBottom();
                this.focusInput();
            });
    }
    
    handleCommandResult(data) {
        if (data.output === 'CLEAR_SCREEN') {
            this.clearTerminal();
        } else {
            if (data.success && data.output) {
                this.addToTerminal(data.output, 'result');
            } else if (!data.success && data.error) {
                this.addToTerminal(data.error, 'error');
            }
        }
    }
    
    addToTerminal(text, type) {
        const terminal = document.getElementById('cliTerminal');
        const inputLine = terminal.querySelector('.cli-input-line');
        
        const output = document.createElement('div');
        output.className = 'cli-output';
        
        // Format output based on type
        const formattedText = this.formatOutput(text, type);
        
        if (type === 'command') {
            output.innerHTML = `<div class="cli-command">${formattedText}</div>`;
        } else if (type === 'error') {
            output.innerHTML = `<div class="cli-error">${formattedText}</div>`;
        } else {
            output.innerHTML = `<div class="cli-result">${formattedText}</div>`;
        }
        
        terminal.insertBefore(output, inputLine);
    }
    
    formatOutput(text, type) {
        // Escape HTML to prevent injection first
        let escaped = text.replace(/</g, '&lt;').replace(/>/g, '&gt;');
        
        // Convert newlines to HTML line breaks
        escaped = escaped.replace(/\n/g, '<br>');
        
        // Basic syntax highlighting for file listings
        if (type === 'result' && text.includes('  ')) {
            // Possible ls output - highlight file extensions
            escaped = escaped.replace(/(\S+\.\w+)/g, '<span style="color: #ffaa00;">$1</span>');
        }
        
        return escaped;
    }
    
    addWelcomeMessage() {
        // Welcome message is already in the HTML template
        this.scrollToBottom();
    }
    
    navigateHistory(direction) {
        const input = document.getElementById('cliInput');
        
        if (direction === 'up' && this.historyIndex > 0) {
            this.historyIndex--;
            input.value = this.commandHistory[this.historyIndex];
        } else if (direction === 'down') {
            if (this.historyIndex < this.commandHistory.length - 1) {
                this.historyIndex++;
                input.value = this.commandHistory[this.historyIndex];
            } else {
                this.historyIndex = this.commandHistory.length;
                input.value = '';
            }
        }
    }
    
    clearTerminal() {
        const terminal = document.getElementById('cliTerminal');
        const outputs = terminal.querySelectorAll('.cli-output');
        outputs.forEach(output => output.remove());
        
        // Add welcome message back
        this.addToTerminal('Terminal cleared.', 'result');
        this.focusInput();
    }
    
    showHistory() {
        this.callAPI('/api/cli/history')
            .then(data => {
                if (data.success) {
                    const content = document.getElementById('historyContent');
                    if (content) {
                        if (data.history.length === 0) {
                            content.innerHTML = '<em>No commands in history</em>';
                        } else {
                            content.innerHTML = data.history.map((cmd, index) => 
                                `<div style="margin: 5px 0; cursor: pointer; padding: 5px; border-radius: 3px;" 
                                      onclick="window.cliPlayground.insertCommand('${cmd.replace(/'/g, "\\'")}')"
                                      onmouseover="this.style.background='#e9ecef'"
                                      onmouseout="this.style.background='transparent'">
                                    ${index + 1}. ${cmd}
                                 </div>`
                            ).join('');
                        }
                        
                        // Show modal if it exists
                        const modal = document.getElementById('historyModal');
                        if (modal && window.bootstrap) {
                            const bsModal = new bootstrap.Modal(modal);
                            bsModal.show();
                        }
                    } else {
                        // Fallback: show history in terminal
                        if (data.history.length === 0) {
                            this.addToTerminal('No commands in history', 'result');
                        } else {
                            this.addToTerminal('Command History:', 'result');
                            data.history.forEach((cmd, index) => {
                                this.addToTerminal(`${index + 1}. ${cmd}`, 'result');
                            });
                        }
                    }
                }
            })
            .catch(error => {
                this.addToTerminal(`Error loading history: ${error.message}`, 'error');
            });
    }
    
    clearHistory() {
        this.callAPI('/api/cli/clear', 'POST')
            .then(data => {
                if (data.success) {
                    this.commandHistory = [];
                    this.historyIndex = -1;
                    const historyContent = document.getElementById('historyContent');
                    if (historyContent) {
                        historyContent.innerHTML = '<em>History cleared</em>';
                    }
                    this.addToTerminal('Command history cleared.', 'result');
                }
            })
            .catch(error => {
                this.addToTerminal(`Error clearing history: ${error.message}`, 'error');
            });
    }
    
    resetPlayground() {
        if (confirm('Reset playground? This will clear the terminal and command history.')) {
            this.clearTerminal();
            this.clearHistory();
            this.addToTerminal('Playground reset. Welcome back!', 'result');
            this.addToTerminal('Type "help" to see available commands.', 'result');
        }
    }
    
    loadAvailableCommands() {
        this.callAPI('/api/cli/commands')
            .then(data => {
                if (data.success) {
                    this.suggestions = data.commands.map(cmd => cmd.command);
                    this.renderCommandGrid(data.commands);
                }
            })
            .catch(error => {
                console.error('Error loading commands:', error);
            });
    }
    
    renderCommandGrid(commands) {
        const grid = document.getElementById('commandGrid');
        if (!grid) return;
        
        grid.innerHTML = commands.map(cmd => `
            <div class="command-item" onclick="window.cliPlayground.insertCommand('${cmd.command}')">
                <div class="command-name">${cmd.command}</div>
                <div class="command-desc">${cmd.description}</div>
            </div>
        `).join('');
    }
    
    insertCommand(command) {
        const input = document.getElementById('cliInput');
        if (input) {
            input.value = command;
            this.focusInput();
        }
    }
    
    executeCommandDirect(command) {
        const input = document.getElementById('cliInput');
        if (input) {
            input.value = command;
            this.executeCommand();
        }
    }
    
    showHelp() {
        this.executeCommandDirect('help');
    }
    
    focusInput() {
        const input = document.getElementById('cliInput');
        if (input) {
            input.focus();
        }
    }
    
    scrollToBottom() {
        const terminal = document.getElementById('cliTerminal');
        if (terminal) {
            terminal.scrollTop = terminal.scrollHeight;
        }
    }
    
    showLoading(show) {
        const indicator = document.getElementById('loadingIndicator');
        if (indicator) {
            indicator.style.display = show ? 'block' : 'none';
        }
    }
    
    async callAPI(url, method = 'GET', data = null) {
        const options = {
            method: method,
            headers: {
                'Content-Type': 'application/json',
            }
        };
        
        if (data) {
            options.body = JSON.stringify(data);
        }
        
        try {
            const response = await fetch(url, options);
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            return await response.json();
        } catch (error) {
            console.error('API call failed:', error);
            throw error;
        }
    }
}

// Global functions for backward compatibility
function clearTerminal() { 
    if (window.cliPlayground) window.cliPlayground.clearTerminal(); 
}

function showHistory() { 
    if (window.cliPlayground) window.cliPlayground.showHistory(); 
}

function showHelp() { 
    if (window.cliPlayground) window.cliPlayground.showHelp(); 
}

function resetPlayground() { 
    if (window.cliPlayground) window.cliPlayground.resetPlayground(); 
}

function clearHistory() { 
    if (window.cliPlayground) window.cliPlayground.clearHistory(); 
}

function insertCommand(cmd) { 
    if (window.cliPlayground) window.cliPlayground.insertCommand(cmd); 
}

// Initialize CLI Playground when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    if (document.getElementById('cliTerminal')) {
        window.cliPlayground = new CLIPlayground();
        console.log('CLI Playground initialized');
    }
});