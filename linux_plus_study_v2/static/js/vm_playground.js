class VMPlayground {
    constructor() {
        this.selectedVM = null;
        this.commandHistory = [];
        this.historyIndex = -1;
        this.isProcessing = false;
        
        this.init();
    }
    
    init() {
        this.bindEvents();
        this.refreshVMs();
    }
    
    bindEvents() {
        const input = document.getElementById('terminalInput');
        if (input) {
            input.addEventListener('keydown', (e) => this.handleKeyDown(e));
        }
        
        // Global shortcuts
        document.addEventListener('keydown', (e) => {
            if (e.ctrlKey || e.metaKey) {
                switch(e.key) {
                    case 'l':
                        e.preventDefault();
                        this.clearTerminal();
                        break;
                }
            }
        });
        
        // Modal close on outside click
        window.onclick = (event) => {
            if (event.target.classList.contains('modal')) {
                event.target.style.display = 'none';
            }
        };
    }
    
    handleKeyDown(e) {
        if (e.key === 'Enter') {
            e.preventDefault();
            this.executeCommand();
        } else if (e.key === 'ArrowUp') {
            e.preventDefault();
            this.navigateHistory('up');
        } else if (e.key === 'ArrowDown') {
            e.preventDefault();
            this.navigateHistory('down');
        }
    }
    
    async refreshVMs() {
        const vmListContainer = document.getElementById('vmList');
        
        // Show loading state
        vmListContainer.innerHTML = `
            <div class="text-center" style="padding: 20px;">
                <div class="spinner-border" role="status"></div>
                <div style="margin-top: 10px; color: #6b7280;">Loading VMs...</div>
            </div>
        `;
        
        try {
            const response = await fetch('/api/vm/list');
            const data = await response.json();
            
            if (data.success) {
                this.renderVMList(data.vms);
            } else {
                this.showError(data.error);
            }
        } catch (error) {
            this.showError(`Network error: ${error.message}`);
        }
    }

    // Add this new method to show errors in the VM list
    showError(errorMessage) {
        const vmListContainer = document.getElementById('vmList');
        vmListContainer.innerHTML = `
            <div class="error-message">
                <strong>Error:</strong> ${errorMessage}
            </div>
            <button class="btn-vm refresh" onclick="vmPlayground.refreshVMs()" style="margin-top: 10px;">
                🔄 Retry
            </button>
        `;
    }
    
    renderVMList(vms) {
        const container = document.getElementById('vmList');
        
        if (vms.length === 0) {
            container.innerHTML = '<div class="text-muted">No VMs found</div>';
            return;
        }
        
        // Enhanced VM rendering with more details
        container.innerHTML = vms.map(vm => `
            <div class="vm-list-item ${vm.name === this.selectedVM ? 'active' : ''}" 
                 data-vm-name="${vm.name}" 
                 onclick="vmPlayground.selectVM('${vm.name}')">
                <div class="d-flex justify-content-between align-items-center">
                    <div>
                        <div class="fw-bold">${vm.name}</div>
                        <div class="text-muted small">${vm.ip || 'No IP'}</div>
                        ${vm.id ? `<div class="text-muted small">ID: ${vm.id}</div>` : ''}
                    </div>
                    <span class="vm-status ${vm.status}">${vm.status}</span>
                </div>
                ${vm.error ? `<div class="error-text small">${vm.error}</div>` : ''}
            </div>
        `).join('');
    }
    
    selectVM(vmName) {
        // Update selection
        document.querySelectorAll('.vm-list-item').forEach(item => {
            item.classList.remove('active');
        });
        
        const selectedItem = document.querySelector(`[data-vm-name="${vmName}"]`);
        if (selectedItem) {
            selectedItem.classList.add('active');
        }
        
        this.selectedVM = vmName;
        this.updatePrompt();
        this.updateControls();
        this.addToTerminal(`Selected VM: ${vmName}`, 'info');
        
        // Enable input
        document.getElementById('terminalInput').disabled = false;
        document.getElementById('terminalInput').focus();
    }
    
    updatePrompt() {
        const prompt = document.getElementById('terminalPrompt');
        if (this.selectedVM) {
            prompt.textContent = `${this.selectedVM}:~$`;
        } else {
            prompt.textContent = 'vm@playground:~$';
        }
    }
    
    updateControls() {
        const startBtn = document.getElementById('startBtn');
        const stopBtn = document.getElementById('stopBtn');
        
        if (this.selectedVM) {
            startBtn.disabled = false;
            stopBtn.disabled = false;
        } else {
            startBtn.disabled = true;
            stopBtn.disabled = true;
        }
    }
    
    async startVM() {
        if (!this.selectedVM) return;
        
        try {
            this.addToTerminal(`Starting VM: ${this.selectedVM}...`, 'info');
            
            const response = await fetch('/api/vm/start', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ vm_name: this.selectedVM })
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.addToTerminal(data.message, 'success');
                this.refreshVMs();
            } else {
                this.addToTerminal(`Error: ${data.error}`, 'error');
            }
        } catch (error) {
            this.addToTerminal(`Error starting VM: ${error.message}`, 'error');
        }
    }
    
    async stopVM() {
        if (!this.selectedVM) return;
        
        try {
            this.addToTerminal(`Stopping VM: ${this.selectedVM}...`, 'info');
            
            const response = await fetch('/api/vm/stop', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ vm_name: this.selectedVM })
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.addToTerminal(data.message, 'success');
                this.refreshVMs();
            } else {
                this.addToTerminal(`Error: ${data.error}`, 'error');
            }
        } catch (error) {
            this.addToTerminal(`Error stopping VM: ${error.message}`, 'error');
        }
    }
    
    async executeCommand() {
        if (!this.selectedVM) {
            this.addToTerminal('Please select a VM first', 'error');
            return;
        }
        
        const input = document.getElementById('terminalInput');
        const command = input.value.trim();
        
        if (!command) return;
        
        // Add to history
        this.commandHistory.push(command);
        this.historyIndex = this.commandHistory.length;
        
        // Show command in terminal
        this.addToTerminal(`${this.selectedVM}:~$ ${command}`, 'command');
        
        // Clear input
        input.value = '';
        input.disabled = true;
        
        try {
            const response = await fetch('/api/vm/execute', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ 
                    vm_name: this.selectedVM, 
                    command: command 
                })
            });
            
            const data = await response.json();
            
            if (data.success) {
                if (data.output) {
                    this.addToTerminal(data.output, 'output');
                }
                if (data.error) {
                    this.addToTerminal(data.error, 'error');
                }
            } else {
                this.addToTerminal(`Error: ${data.error}`, 'error');
            }
        } catch (error) {
            this.addToTerminal(`Error executing command: ${error.message}`, 'error');
        } finally {
            input.disabled = false;
            input.focus();
        }
    }
    async showChallenges() {
    if (!this.selectedVM) {
        this.addToTerminal('Please select a VM first', 'error');
        return;
    }
    
    try {
        const response = await fetch('/api/vm/challenges');
        const data = await response.json();
        
        if (data.success) {
            this.renderChallenges(data.challenges);
            document.getElementById('challengesModal').style.display = 'block';
        } else {
            this.addToTerminal(`Error loading challenges: ${data.error}`, 'error');
        }
    } catch (error) {
        this.addToTerminal(`Error loading challenges: ${error.message}`, 'error');
    }
}

    renderChallenges(challenges) {
        const container = document.getElementById('challengesList');
        
        if (challenges.length === 0) {
            container.innerHTML = '<div class="text-muted">No challenges found</div>';
            return;
        }
        
        container.innerHTML = challenges.map(challenge => `
            <div class="challenge-item">
                <div class="fw-bold">${challenge.name}</div>
                <div class="challenge-meta">
                    File: ${challenge.filename} | Size: ${(challenge.size / 1024).toFixed(1)} KB
                </div>
                <div class="action-buttons">
                    <button class="btn-run" onclick="vmPlayground.runChallenge('${challenge.name}')">
                        🚀 Run Challenge
                    </button>
                </div>
            </div>
        `).join('');
    }

    async runChallenge(challengeName) {
        if (!this.selectedVM) {
            this.addToTerminal('Please select a VM first', 'error');
            return;
        }
        
        try {
            this.addToTerminal(`Running challenge: ${challengeName} on VM: ${this.selectedVM}`, 'info');
            
            const response = await fetch('/api/vm/run_challenge', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ 
                    vm_name: this.selectedVM,
                    challenge_name: challengeName
                })
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.addToTerminal(data.message, 'success');
                if (data.snapshot_created) {
                    this.addToTerminal(`Safety snapshot created: ${data.snapshot_created}`, 'info');
                }
                this.closeModal('challengesModal');
            } else {
                this.addToTerminal(`Error: ${data.error}`, 'error');
            }
        } catch (error) {
            this.addToTerminal(`Error running challenge: ${error.message}`, 'error');
        }
    }

    async showSnapshots() {
        if (!this.selectedVM) {
            this.addToTerminal('Please select a VM first', 'error');
            return;
        }
        
        try {
            const response = await fetch(`/api/vm/snapshots?vm_name=${this.selectedVM}`);
            const data = await response.json();
            
            if (data.success) {
                this.renderSnapshots(data.snapshots);
                document.getElementById('snapshotsModal').style.display = 'block';
            } else {
                this.addToTerminal(`Error loading snapshots: ${data.error}`, 'error');
            }
        } catch (error) {
            this.addToTerminal(`Error loading snapshots: ${error.message}`, 'error');
        }
    }

    renderSnapshots(snapshots) {
        const container = document.getElementById('snapshotsList');
        
        if (snapshots.length === 0) {
            container.innerHTML = '<div class="text-muted">No snapshots found</div>';
            return;
        }
        
        container.innerHTML = snapshots.map(snapshot => `
            <div class="snapshot-item">
                <div class="fw-bold">${snapshot.name}</div>
                <div class="snapshot-meta">
                    ${snapshot.current ? '<span class="badge bg-success">Current</span>' : ''}
                </div>
                <div class="action-buttons">
                    <button class="btn-restore" onclick="vmPlayground.restoreSnapshot('${snapshot.name}')">
                        🔄 Restore
                    </button>
                    <button class="btn-delete" onclick="vmPlayground.deleteSnapshot('${snapshot.name}')">
                        🗑️ Delete
                    </button>
                </div>
            </div>
        `).join('');
    }

    async createSnapshot() {
        if (!this.selectedVM) {
            this.addToTerminal('Please select a VM first', 'error');
            return;
        }
        
        const snapshotName = document.getElementById('snapshotName').value.trim();
        if (!snapshotName) {
            alert('Please enter a snapshot name');
            return;
        }
        
        try {
            this.addToTerminal(`Creating snapshot: ${snapshotName}`, 'info');
            
            const response = await fetch('/api/vm/create_snapshot', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ 
                    vm_name: this.selectedVM,
                    snapshot_name: snapshotName
                })
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.addToTerminal(data.message, 'success');
                document.getElementById('snapshotName').value = '';
                this.showSnapshots(); // Refresh the list
            } else {
                this.addToTerminal(`Error: ${data.error}`, 'error');
            }
        } catch (error) {
            this.addToTerminal(`Error creating snapshot: ${error.message}`, 'error');
        }
    }

    async restoreSnapshot(snapshotName) {
        if (!this.selectedVM) {
            this.addToTerminal('Please select a VM first', 'error');
            return;
        }
        
        if (!confirm(`Are you sure you want to restore VM ${this.selectedVM} from snapshot ${snapshotName}?`)) {
            return;
        }
        
        try {
            this.addToTerminal(`Restoring from snapshot: ${snapshotName}`, 'info');
            
            const response = await fetch('/api/vm/restore_snapshot', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ 
                    vm_name: this.selectedVM,
                    snapshot_name: snapshotName
                })
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.addToTerminal(data.message, 'success');
                this.closeModal('snapshotsModal');
                this.refreshVMs();
            } else {
                this.addToTerminal(`Error: ${data.error}`, 'error');
            }
        } catch (error) {
            this.addToTerminal(`Error restoring snapshot: ${error.message}`, 'error');
        }
    }

    async deleteSnapshot(snapshotName) {
        if (!this.selectedVM) {
            this.addToTerminal('Please select a VM first', 'error');
            return;
        }
        
        if (!confirm(`Are you sure you want to delete snapshot ${snapshotName}?`)) {
            return;
        }
        
        try {
            this.addToTerminal(`Deleting snapshot: ${snapshotName}`, 'info');
            
            const response = await fetch('/api/vm/delete_snapshot', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ 
                    vm_name: this.selectedVM,
                    snapshot_name: snapshotName
                })
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.addToTerminal(data.message, 'success');
                this.showSnapshots(); // Refresh the list
            } else {
                this.addToTerminal(`Error: ${data.error}`, 'error');
            }
        } catch (error) {
            this.addToTerminal(`Error deleting snapshot: ${error.message}`, 'error');
        }
    }

    closeModal(modalId) {
        document.getElementById(modalId).style.display = 'none';
    }

    navigateHistory(direction) {
        const input = document.getElementById('terminalInput');
        
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
    
    addToTerminal(text, type = 'output') {
        const terminal = document.getElementById('terminalOutput');
        const output = document.createElement('div');
        
        let color = '#ffffff';
        switch (type) {
            case 'command':
                color = '#00ff00';
                break;
            case 'error':
                color = '#ff4444';
                break;
            case 'info':
                color = '#4da6ff';
                break;
            case 'success':
                color = '#44ff44';
                break;
        }
        
        output.style.color = color;
        output.textContent = text;
        terminal.appendChild(output);
        
        // Auto-scroll
        terminal.scrollTop = terminal.scrollHeight;
    }
    
    clearTerminal() {
        const terminal = document.getElementById('terminalOutput');
        terminal.innerHTML = `
            <div style="color: #00ff00;">Terminal cleared.</div>
            <div style="color: #ffff00;">Selected VM: ${this.selectedVM || 'None'}</div>
        `;
    }
}
// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    window.vmPlayground = new VMPlayground();
});
