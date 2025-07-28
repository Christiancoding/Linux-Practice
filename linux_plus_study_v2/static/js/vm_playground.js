class VMPlayground {
    constructor() {
        this.selectedVM = null;
        this.commandHistory = [];
        this.historyIndex = -1;
        this.isProcessing = false;
        this.connectionStatus = 'disconnected';
        
        this.init();
    }
    
    init() {
        this.bindEvents();
        this.refreshVMs();
        this.updateConnectionIndicator();
    }
    
    bindEvents() {
        const input = document.getElementById('terminalInput');
        if (input) {
            input.addEventListener('keydown', (e) => this.handleKeyDown(e));
            input.addEventListener('input', (e) => this.handleInput(e));
        }
        
        // Button event bindings
        const startBtn = document.getElementById('startBtn');
        const stopBtn = document.getElementById('stopBtn');
        const restartBtn = document.getElementById('restartBtn');
        const clearBtn = document.getElementById('clearBtn');
        const snapshotBtn = document.getElementById('snapshotBtn');
        const refreshVMsBtn = document.getElementById('refreshVMsBtn');
        const createVMBtn = document.getElementById('createVMBtn');
        const closeDetailsBtn = document.getElementById('closeDetailsBtn');
        
        if (startBtn) startBtn.addEventListener('click', () => this.startVM());
        if (stopBtn) stopBtn.addEventListener('click', () => this.stopVM());
        if (restartBtn) restartBtn.addEventListener('click', () => this.restartVM());
        if (clearBtn) clearBtn.addEventListener('click', () => this.clearTerminal());
        if (snapshotBtn) snapshotBtn.addEventListener('click', () => this.showSnapshots());
        if (refreshVMsBtn) refreshVMsBtn.addEventListener('click', () => this.refreshVMs());
        if (createVMBtn) createVMBtn.addEventListener('click', () => this.showCreateVM());
        if (closeDetailsBtn) closeDetailsBtn.addEventListener('click', () => this.hideDetails());
        
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
            if (event.target.classList.contains('modal-overlay')) {
                event.target.style.display = 'none';
            }
        };
        
        // Challenge category tabs
        document.addEventListener('click', (e) => {
            if (e.target.classList.contains('category-tab')) {
                this.switchChallengeCategory(e.target.dataset.category);
            }
        });
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
        } else if (e.key === 'Tab') {
            e.preventDefault();
            this.handleTabCompletion();
        }
    }
    
    handleInput(e) {
        const input = e.target.value;
        this.showCommandSuggestions(input);
    }
    
    showCommandSuggestions(input) {
        const suggestions = document.getElementById('inputSuggestions');
        if (!suggestions) return;
        
        const commonCommands = [
            'ls', 'cd', 'pwd', 'mkdir', 'rmdir', 'rm', 'cp', 'mv', 'cat', 'less', 'more',
            'grep', 'find', 'which', 'whereis', 'man', 'info', 'help', 'history',
            'ps', 'top', 'htop', 'kill', 'killall', 'jobs', 'bg', 'fg', 'nohup',
            'chmod', 'chown', 'chgrp', 'umask', 'su', 'sudo', 'passwd',
            'df', 'du', 'free', 'uptime', 'uname', 'whoami', 'who', 'w', 'last',
            'tar', 'gzip', 'gunzip', 'zip', 'unzip', 'wget', 'curl', 'ssh', 'scp'
        ];
        
        const matches = commonCommands.filter(cmd => 
            cmd.toLowerCase().startsWith(input.toLowerCase().trim()) && input.trim()
        );
        
        if (matches.length > 0 && input.trim()) {
            suggestions.innerHTML = matches.slice(0, 5).map(cmd => 
                `<div class="suggestion" onclick="vmPlayground.selectSuggestion('${cmd}')">${cmd}</div>`
            ).join('');
            suggestions.style.display = 'block';
        } else {
            suggestions.style.display = 'none';
        }
    }
    
    selectSuggestion(command) {
        const input = document.getElementById('terminalInput');
        input.value = command + ' ';
        input.focus();
        document.getElementById('inputSuggestions').style.display = 'none';
    }
    
    handleTabCompletion() {
        const input = document.getElementById('terminalInput');
        const value = input.value;
        const words = value.split(' ');
        const lastWord = words[words.length - 1];
        
        // Simple tab completion for common commands
        const commands = ['ls', 'cd', 'cat', 'mkdir', 'rmdir', 'rm', 'cp', 'mv'];
        const matches = commands.filter(cmd => cmd.startsWith(lastWord));
        
        if (matches.length === 1) {
            words[words.length - 1] = matches[0];
            input.value = words.join(' ') + ' ';
        }
    }
    
    async refreshVMs() {
        const vmListContainer = document.getElementById('vmList');
        
        // Show loading state
        vmListContainer.innerHTML = `
            <div class="loading-state">
                <div class="modern-spinner"></div>
                <p>Discovering virtual machines...</p>
            </div>
        `;
        
        try {
            const response = await fetch('/api/vm/list');
            const data = await response.json();
            
            if (data.success) {
                this.renderVMList(data.vms);
                this.updateStats(data.vms);
            } else {
                this.showError(data.error);
            }
        } catch (error) {
            this.showError(`Network error: ${error.message}`);
        }
    }
    
    showError(errorMessage) {
        const vmListContainer = document.getElementById('vmList');
        vmListContainer.innerHTML = `
            <div class="error-state">
                <div class="error-icon">⚠️</div>
                <div class="error-title">Connection Error</div>
                <div class="error-message">${errorMessage}</div>
                <button class="btn-panel refresh" onclick="vmPlayground.refreshVMs()">
                    <i class="fas fa-sync-alt"></i>
                    <span>Retry</span>
                </button>
            </div>
        `;
    }
    
    renderVMList(vms) {
        const container = document.getElementById('vmList');
        
        if (vms.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <div class="empty-icon">🖥️</div>
                    <div class="empty-title">No Virtual Machines</div>
                    <div class="empty-message">Create your first VM to get started</div>
                    <button class="btn-panel create" onclick="vmPlayground.showCreateVM()">
                        <i class="fas fa-plus"></i>
                        <span>Create VM</span>
                    </button>
                </div>
            `;
            return;
        }
        
        container.innerHTML = vms.map(vm => `
            <div class="vm-card ${vm.name === this.selectedVM ? 'active' : ''}" 
                 data-vm-name="${vm.name}" 
                 onclick="vmPlayground.selectVM('${vm.name}')">
                <div class="vm-card-header">
                    <div class="vm-name">${vm.name}</div>
                    <span class="vm-status-badge ${vm.status}">${vm.status}</span>
                </div>
                <div class="vm-card-body">
                    <div class="vm-info-row">
                        <span>IP Address:</span>
                        <span>${vm.ip || 'Not assigned'}</span>
                    </div>
                    ${vm.id ? `
                    <div class="vm-info-row">
                        <span>ID:</span>
                        <span>${vm.id}</span>
                    </div>
                    ` : ''}
                    ${vm.memory ? `
                    <div class="vm-info-row">
                        <span>Memory:</span>
                        <span>${vm.memory}</span>
                    </div>
                    ` : ''}
                </div>
                ${vm.error ? `<div class="error-text">${vm.error}</div>` : ''}
                <div class="vm-card-actions">
                    <button class="btn-vm-action details" onclick="event.stopPropagation(); vmPlayground.showVMDetails('${vm.name}')">
                        <i class="fas fa-info-circle"></i>
                    </button>
                    <button class="btn-vm-action ${vm.status === 'running' ? 'stop' : 'start'}" 
                            onclick="event.stopPropagation(); vmPlayground.${vm.status === 'running' ? 'stopVM' : 'startVM'}('${vm.name}')">
                        <i class="fas fa-${vm.status === 'running' ? 'stop' : 'play'}"></i>
                    </button>
                </div>
            </div>
        `).join('');
    }
    
    updateStats(vms) {
        const runningCount = vms.filter(vm => vm.status === 'running').length;
        const stoppedCount = vms.filter(vm => vm.status === 'stopped').length;
        const errorCount = vms.filter(vm => vm.status === 'error').length;
        const totalCount = vms.length;
        
        const runningElement = document.getElementById('running-vms');
        const stoppedElement = document.getElementById('stopped-vms');
        const errorElement = document.getElementById('error-vms');
        const totalElement = document.getElementById('total-vms');
        
        if (runningElement) runningElement.textContent = runningCount;
        if (stoppedElement) stoppedElement.textContent = stoppedCount;
        if (errorElement) errorElement.textContent = errorCount;
        if (totalElement) totalElement.textContent = totalCount;
    }
    
    selectVM(vmName) {
        // Update selection
        document.querySelectorAll('.vm-card').forEach(item => {
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
        this.connectionStatus = 'connected';
        this.updateConnectionIndicator();
        
        // Enable input
        const input = document.getElementById('terminalInput');
        if (input) {
            input.disabled = false;
            input.focus();
        }
    }
    
    updatePrompt() {
        const prompt = document.getElementById('terminalPrompt');
        if (prompt) {
            if (this.selectedVM) {
                prompt.textContent = `${this.selectedVM}:~$`;
            } else {
                prompt.textContent = 'vm@playground:~$';
            }
        }
    }
    
    updateControls() {
        const startBtn = document.getElementById('startBtn');
        const stopBtn = document.getElementById('stopBtn');
        const restartBtn = document.getElementById('restartBtn');
        
        const hasSelection = !!this.selectedVM;
        
        if (startBtn) startBtn.disabled = !hasSelection;
        if (stopBtn) stopBtn.disabled = !hasSelection;
        if (restartBtn) restartBtn.disabled = !hasSelection;
    }
    
    updateConnectionIndicator() {
        const indicator = document.getElementById('connectionIndicator');
        if (indicator) {
            const dot = indicator.querySelector('.indicator-dot');
            const text = indicator.querySelector('span');
            
            if (this.connectionStatus === 'connected') {
                dot.className = 'indicator-dot connected';
                text.textContent = `Connected to ${this.selectedVM}`;
            } else {
                dot.className = 'indicator-dot disconnected';
                text.textContent = 'Disconnected';
            }
        }
    }
    
    async startVM(vmName = null) {
        const targetVM = vmName || this.selectedVM;
        if (!targetVM) return;
        
        try {
            this.addToTerminal(`Starting VM: ${targetVM}...`, 'info');
            
            const response = await fetch('/api/vm/start', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ vm_name: targetVM })
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
    
    async stopVM(vmName = null) {
        const targetVM = vmName || this.selectedVM;
        if (!targetVM) return;
        
        try {
            this.addToTerminal(`Stopping VM: ${targetVM}...`, 'info');
            
            const response = await fetch('/api/vm/stop', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ vm_name: targetVM })
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.addToTerminal(data.message, 'success');
                this.refreshVMs();
                
                // Update connection status if stopping selected VM
                if (targetVM === this.selectedVM) {
                    this.connectionStatus = 'disconnected';
                    this.updateConnectionIndicator();
                }
            } else {
                this.addToTerminal(`Error: ${data.error}`, 'error');
            }
        } catch (error) {
            this.addToTerminal(`Error stopping VM: ${error.message}`, 'error');
        }
    }
    
    async restartVM() {
        if (!this.selectedVM) return;
        
        try {
            this.addToTerminal(`Restarting VM: ${this.selectedVM}...`, 'info');
            await this.stopVM();
            // Wait a moment before starting
            setTimeout(() => this.startVM(), 2000);
        } catch (error) {
            this.addToTerminal(`Error restarting VM: ${error.message}`, 'error');
        }
    }
    
    // VM Creation Modal
    showCreateVM() {
        const modalHTML = `
            <div class="modal-overlay" id="createVMModal">
                <div class="modal-content create-vm-modal">
                    <div class="modal-header">
                        <h3><i class="fas fa-plus-circle"></i> Create New Virtual Machine</h3>
                        <button class="btn-close" onclick="vmPlayground.hideCreateVM()">
                            <i class="fas fa-times"></i>
                        </button>
                    </div>
                    <div class="modal-body">
                        <form id="createVMForm" onsubmit="vmPlayground.handleCreateVM(event)">
                            <div class="form-group">
                                <label for="vmName">VM Name *</label>
                                <input type="text" id="vmName" name="vmName" required 
                                       placeholder="e.g., ubuntu-practice" 
                                       pattern="[a-zA-Z0-9-_]+" 
                                       title="Only alphanumeric characters, hyphens, and underscores allowed">
                            </div>
                            
                            <div class="form-group">
                                <label for="vmTemplate">Template</label>
                                <select id="vmTemplate" name="vmTemplate">
                                    <option value="ubuntu-20.04">Ubuntu 20.04 LTS</option>
                                    <option value="ubuntu-22.04">Ubuntu 22.04 LTS</option>
                                    <option value="centos-8">CentOS 8</option>
                                    <option value="fedora-37">Fedora 37</option>
                                    <option value="debian-11">Debian 11</option>
                                </select>
                            </div>
                            
                            <div class="form-row">
                                <div class="form-group">
                                    <label for="vmMemory">Memory (GB)</label>
                                    <select id="vmMemory" name="vmMemory">
                                        <option value="1">1 GB</option>
                                        <option value="2" selected>2 GB</option>
                                        <option value="4">4 GB</option>
                                        <option value="8">8 GB</option>
                                    </select>
                                </div>
                                
                                <div class="form-group">
                                    <label for="vmCpus">CPU Cores</label>
                                    <select id="vmCpus" name="vmCpus">
                                        <option value="1" selected>1 Core</option>
                                        <option value="2">2 Cores</option>
                                        <option value="4">4 Cores</option>
                                    </select>
                                </div>
                            </div>
                            
                            <div class="form-group">
                                <label for="vmDisk">Disk Size (GB)</label>
                                <select id="vmDisk" name="vmDisk">
                                    <option value="10">10 GB</option>
                                    <option value="20" selected>20 GB</option>
                                    <option value="40">40 GB</option>
                                    <option value="80">80 GB</option>
                                </select>
                            </div>
                            
                            <div class="form-group">
                                <label>
                                    <input type="checkbox" id="autoStart" name="autoStart">
                                    Start VM after creation
                                </label>
                            </div>
                            
                            <div class="form-actions">
                                <button type="button" class="btn-secondary" onclick="vmPlayground.hideCreateVM()">
                                    Cancel
                                </button>
                                <button type="submit" class="btn-primary">
                                    <i class="fas fa-plus"></i>
                                    Create VM
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            </div>
        `;
        
        // Remove existing modal if present
        const existingModal = document.getElementById('createVMModal');
        if (existingModal) {
            existingModal.remove();
        }
        
        // Add modal to DOM
        document.body.insertAdjacentHTML('beforeend', modalHTML);
        
        // Show modal
        document.getElementById('createVMModal').style.display = 'flex';
        
        // Focus on name input
        document.getElementById('vmName').focus();
    }
    
    hideCreateVM() {
        const modal = document.getElementById('createVMModal');
        if (modal) {
            modal.style.display = 'none';
            setTimeout(() => modal.remove(), 300);
        }
    }
    
    async handleCreateVM(event) {
        event.preventDefault();
        
        const formData = new FormData(event.target);
        const vmData = {
            name: formData.get('vmName'),
            template: formData.get('vmTemplate'),
            memory: formData.get('vmMemory'),
            cpus: formData.get('vmCpus'),
            disk: formData.get('vmDisk'),
            auto_start: formData.get('autoStart') === 'on'
        };
        
        try {
            this.addToTerminal(`Creating VM: ${vmData.name}...`, 'info');
            
            const response = await fetch('/api/vm/create', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(vmData)
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.addToTerminal(data.message, 'success');
                this.hideCreateVM();
                this.refreshVMs();
            } else {
                this.addToTerminal(`Error creating VM: ${data.error}`, 'error');
            }
        } catch (error) {
            this.addToTerminal(`Error creating VM: ${error.message}`, 'error');
        }
    }
    
    // VM Details Panel
    async showVMDetails(vmName) {
        try {
            const response = await fetch(`/api/vm/details?vm_name=${vmName}`);
            const data = await response.json();
            
            if (data.success) {
                const detailsPanel = document.getElementById('vmDetailsPanel');
                
                document.getElementById('detail-name').textContent = data.vm.name;
                document.getElementById('detail-status').textContent = data.vm.status;
                document.getElementById('detail-status').className = `status-badge ${data.vm.status}`;
                document.getElementById('detail-ip').textContent = data.vm.ip || 'Not assigned';
                document.getElementById('detail-memory').textContent = data.vm.memory || 'Unknown';
                document.getElementById('detail-cpu').textContent = data.vm.cpu || 'Unknown';
                
                detailsPanel.style.display = 'block';
            } else {
                this.addToTerminal(`Error loading VM details: ${data.error}`, 'error');
            }
        } catch (error) {
            this.addToTerminal(`Error loading VM details: ${error.message}`, 'error');
        }
    }
    
    hideDetails() {
        const detailsPanel = document.getElementById('vmDetailsPanel');
        if (detailsPanel) {
            detailsPanel.style.display = 'none';
        }
    }
    
    // Snapshots Management
    async showSnapshots() {
        if (!this.selectedVM) {
            this.addToTerminal('Please select a VM first', 'error');
            return;
        }
        
        const modalHTML = `
            <div class="modal-overlay" id="snapshotsModal">
                <div class="modal-content snapshots-modal">
                    <div class="modal-header">
                        <h3><i class="fas fa-camera"></i> VM Snapshots - ${this.selectedVM}</h3>
                        <button class="btn-close" onclick="vmPlayground.hideSnapshots()">
                            <i class="fas fa-times"></i>
                        </button>
                    </div>
                    <div class="modal-body">
                        <div class="snapshot-actions">
                            <div class="form-group">
                                <input type="text" id="snapshotName" placeholder="Enter snapshot name..." 
                                       onkeypress="if(event.key==='Enter') vmPlayground.createSnapshot()">
                                <button class="btn-primary" onclick="vmPlayground.createSnapshot()">
                                    <i class="fas fa-camera"></i>
                                    Create Snapshot
                                </button>
                            </div>
                        </div>
                        <div class="snapshots-list" id="snapshotsList">
                            <div class="loading-state">
                                <div class="modern-spinner"></div>
                                <p>Loading snapshots...</p>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        // Remove existing modal if present
        const existingModal = document.getElementById('snapshotsModal');
        if (existingModal) {
            existingModal.remove();
        }
        
        // Add modal to DOM
        document.body.insertAdjacentHTML('beforeend', modalHTML);
        
        // Show modal
        document.getElementById('snapshotsModal').style.display = 'flex';
        
        // Load snapshots
        this.loadSnapshots();
    }
    
    hideSnapshots() {
        const modal = document.getElementById('snapshotsModal');
        if (modal) {
            modal.style.display = 'none';
            setTimeout(() => modal.remove(), 300);
        }
    }
    
    async loadSnapshots() {
        try {
            const response = await fetch(`/api/vm/snapshots?vm_name=${this.selectedVM}`);
            const data = await response.json();
            
            if (data.success) {
                this.renderSnapshots(data.snapshots);
            } else {
                document.getElementById('snapshotsList').innerHTML = `
                    <div class="error-state">Error loading snapshots: ${data.error}</div>
                `;
            }
        } catch (error) {
            document.getElementById('snapshotsList').innerHTML = `
                <div class="error-state">Network error: ${error.message}</div>
            `;
        }
    }
    
    renderSnapshots(snapshots) {
        const container = document.getElementById('snapshotsList');
        
        if (snapshots.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <div class="empty-icon">📸</div>
                    <div class="empty-title">No Snapshots</div>
                    <div class="empty-message">Create your first snapshot to save VM state</div>
                </div>
            `;
            return;
        }
        
        container.innerHTML = snapshots.map(snapshot => `
            <div class="snapshot-item">
                <div class="snapshot-info">
                    <div class="snapshot-name">${snapshot.name}</div>
                    <div class="snapshot-date">${snapshot.creation_time || 'Unknown date'}</div>
                    ${snapshot.current ? '<span class="badge current-badge">Current</span>' : ''}
                </div>
                <div class="snapshot-actions">
                    <button class="btn-snapshot restore" onclick="vmPlayground.restoreSnapshot('${snapshot.name}')">
                        <i class="fas fa-undo"></i>
                        Restore
                    </button>
                    <button class="btn-snapshot delete" onclick="vmPlayground.deleteSnapshot('${snapshot.name}')">
                        <i class="fas fa-trash"></i>
                        Delete
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
                this.loadSnapshots();
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
                this.hideSnapshots();
                this.refreshVMs();
            } else {
                this.addToTerminal(`Error: ${data.error}`, 'error');
            }
        } catch (error) {
            this.addToTerminal(`Error restoring snapshot: ${error.message}`, 'error');
        }
    }
    
    async deleteSnapshot(snapshotName) {
        if (!confirm(`Are you sure you want to delete snapshot ${snapshotName}?`)) {
            return;
        }
        
        try {
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
                this.loadSnapshots();
            } else {
                this.addToTerminal(`Error: ${data.error}`, 'error');
            }
        } catch (error) {
            this.addToTerminal(`Error deleting snapshot: ${error.message}`, 'error');
        }
    }
    
    // Challenge System
    async showChallenges() {
        const modalHTML = `
            <div class="modal-overlay" id="challengeModal">
                <div class="modal-content challenge-modal">
                    <div class="modal-header">
                        <h3><i class="fas fa-trophy"></i> VM Challenges</h3>
                        <button class="btn-close" onclick="vmPlayground.hideChallenges()">
                            <i class="fas fa-times"></i>
                        </button>
                    </div>
                    <div class="modal-body">
                        <div class="challenge-categories">
                            <div class="category-tab active" data-category="basic">Basic</div>
                            <div class="category-tab" data-category="intermediate">Intermediate</div>
                            <div class="category-tab" data-category="advanced">Advanced</div>
                        </div>
                        <div class="challenge-list" id="challengeList">
                            <div class="loading-state">
                                <div class="modern-spinner"></div>
                                <p>Loading challenges...</p>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        // Remove existing modal if present
        const existingModal = document.getElementById('challengeModal');
        if (existingModal) {
            existingModal.remove();
        }
        
        // Add modal to DOM
        document.body.insertAdjacentHTML('beforeend', modalHTML);
        
        // Show modal
        document.getElementById('challengeModal').style.display = 'flex';
        
        // Load challenges
        this.loadChallenges('basic');
    }
    
    hideChallenges() {
        const modal = document.getElementById('challengeModal');
        if (modal) {
            modal.style.display = 'none';
            setTimeout(() => modal.remove(), 300);
        }
    }
    
    switchChallengeCategory(category) {
        // Update active tab
        document.querySelectorAll('.category-tab').forEach(tab => {
            tab.classList.toggle('active', tab.dataset.category === category);
        });
        
        // Load challenges for category
        this.loadChallenges(category);
    }
    
    async loadChallenges(category) {
        try {
            const response = await fetch(`/api/vm/challenges?category=${category}`);
            const data = await response.json();
            
            if (data.success) {
                this.renderChallenges(data.challenges);
            } else {
                document.getElementById('challengeList').innerHTML = `
                    <div class="error-state">Error loading challenges: ${data.error}</div>
                `;
            }
        } catch (error) {
            document.getElementById('challengeList').innerHTML = `
                <div class="error-state">Network error: ${error.message}</div>
            `;
        }
    }
    
    renderChallenges(challenges) {
        const container = document.getElementById('challengeList');
        
        if (challenges.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <div class="empty-icon">🎯</div>
                    <div class="empty-title">No Challenges Available</div>
                    <div class="empty-message">Check back later for new challenges</div>
                </div>
            `;
            return;
        }
        
        container.innerHTML = challenges.map(challenge => `
            <div class="challenge-item">
                <div class="challenge-header">
                    <div class="challenge-title">${challenge.title}</div>
                    <div class="challenge-difficulty ${challenge.difficulty.toLowerCase()}">${challenge.difficulty}</div>
                </div>
                <div class="challenge-description">${challenge.description}</div>
                <div class="challenge-stats">
                    <span class="stat-item">
                        <i class="fas fa-clock"></i>
                        ${challenge.estimated_time || '10'} mins
                    </span>
                    <span class="stat-item">
                        <i class="fas fa-star"></i>
                        ${challenge.score || '50'} points
                    </span>
                </div>
                <div class="challenge-actions">
                    <button class="btn-challenge start" onclick="vmPlayground.startChallenge('${challenge.id}')">
                        <i class="fas fa-play"></i>
                        Start Challenge
                    </button>
                </div>
            </div>
        `).join('');
    }
    
    async startChallenge(challengeId) {
        if (!this.selectedVM) {
            alert('Please select a VM first');
            return;
        }
        
        try {
            this.addToTerminal(`Starting challenge: ${challengeId}`, 'info');
            
            const response = await fetch('/api/vm/start_challenge', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ 
                    challenge_id: challengeId,
                    vm_name: this.selectedVM
                })
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.addToTerminal(data.message || 'Challenge started successfully', 'success');
                this.hideChallenges();
            } else {
                this.addToTerminal(`Error: ${data.error}`, 'error');
            }
        } catch (error) {
            this.addToTerminal(`Error starting challenge: ${error.message}`, 'error');
        }
    }
    
    // Terminal functionality
    navigateHistory(direction) {
        const input = document.getElementById('terminalInput');
        if (!input) return;
        
        if (direction === 'up' && this.historyIndex < this.commandHistory.length - 1) {
            this.historyIndex++;
            input.value = this.commandHistory[this.commandHistory.length - 1 - this.historyIndex];
        } else if (direction === 'down' && this.historyIndex > -1) {
            this.historyIndex--;
            if (this.historyIndex === -1) {
                input.value = '';
            } else {
                input.value = this.commandHistory[this.commandHistory.length - 1 - this.historyIndex];
            }
        }
    }
    
    async executeCommand() {
        const input = document.getElementById('terminalInput');
        if (!input || this.isProcessing) return;
        
        const command = input.value.trim();
        if (!command) return;
        
        // Add to history
        this.commandHistory.push(command);
        this.historyIndex = -1;
        
        // Clear input
        input.value = '';
        
        // Show command in terminal
        this.addToTerminal(`${this.selectedVM || 'vm'}:~$ ${command}`, 'command');
        
        // Process command
        this.isProcessing = true;
        
        try {
            if (command.toLowerCase() === 'help') {
                this.showHelp();
            } else if (command.toLowerCase() === 'clear') {
                this.clearTerminal();
            } else if (this.selectedVM) {
                await this.sendCommand(command);
            } else {
                this.addToTerminal('Please select a VM first', 'error');
            }
        } catch (error) {
            this.addToTerminal(`Error: ${error.message}`, 'error');
        } finally {
            this.isProcessing = false;
        }
    }
    
    async sendCommand(command) {
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
                this.addToTerminal(`Command failed: ${data.error}`, 'error');
            }
        } catch (error) {
            this.addToTerminal(`Network error: ${error.message}`, 'error');
        }
    }
    
    showHelp() {
        const helpText = `
Available Commands:
  help              - Show this help message
  clear             - Clear terminal output
  ls [path]         - List directory contents
  cd [path]         - Change directory
  pwd               - Show current directory
  cat [file]        - Display file contents
  mkdir [dir]       - Create directory
  rmdir [dir]       - Remove empty directory
  rm [file]         - Remove file
  cp [src] [dest]   - Copy file or directory
  mv [src] [dest]   - Move/rename file or directory
  chmod [mode] [file] - Change file permissions
  ps                - Show running processes
  top               - Show system processes
  df                - Show disk usage
  free              - Show memory usage
  uname -a          - Show system information

VM Controls:
  Use the buttons above for VM management (Start, Stop, Restart, Snapshots)
        `;
        this.addToTerminal(helpText, 'help');
    }
    
    addToTerminal(text, type = 'output') {
        const output = document.getElementById('terminalOutput');
        if (!output) return;
        
        const timestamp = new Date().toLocaleTimeString();
        const line = document.createElement('div');
        line.className = `terminal-line ${type}`;
        
        if (type === 'command') {
            line.innerHTML = `<span class="timestamp">[${timestamp}]</span> ${text}`;
        } else {
            line.innerHTML = `<span class="timestamp">[${timestamp}]</span> <span class="line-content">${text}</span>`;
        }
        
        output.appendChild(line);
        output.scrollTop = output.scrollHeight;
    }
    
    clearTerminal() {
        const output = document.getElementById('terminalOutput');
        if (output) {
            output.innerHTML = `
                <div class="welcome-message">
                    <div class="ascii-art">
                        <pre>
╔═══════════════════════════════════════════════════════════════╗
║                    VM Management Terminal                     ║
║                                                               ║
║  Select a virtual machine from the sidebar to get started.   ║
║  Use 'help' for available commands.                          ║
╚═══════════════════════════════════════════════════════════════╝
                        </pre>
                    </div>
                </div>
            `;
        }
    }
}

// Self-initializing when DOM loads and script is ready
(function() {
    function initializeVMPlayground() {
        if (typeof VMPlayground !== 'undefined' && document.readyState === 'complete') {
            window.vmPlayground = new VMPlayground();
            console.log('VM Playground initialized successfully');
        } else {
            // Retry after a short delay
            setTimeout(initializeVMPlayground, 50);
        }
    }

    // Start initialization when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initializeVMPlayground);
    } else {
        initializeVMPlayground();
    }
})();

// Export for module systems
if (typeof module !== 'undefined' && module.exports) {
    module.exports = VMPlayground;
}