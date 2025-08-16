/**
 * XTerm.js Web Terminal Integration
 * Provides a full terminal emulator in the browser that can handle vim, nano, etc.
 */

class WebTerminal {
    constructor(containerId) {
        this.container = document.getElementById(containerId);
        this.terminal = null;
        this.fitAddon = null;
        this.socket = null;
        this.vmName = null;
        
        this.init();
    }
    
    async init() {
        // Check if xterm.js is available
        if (typeof Terminal === 'undefined') {
            await this.loadXTermLibrary();
        }
        
        // Create terminal instance
        this.terminal = new Terminal({
            cursorBlink: true,
            theme: {
                background: '#000000',
                foreground: '#ffffff',
                cursor: '#ffffff',
                selection: '#3949ab'
            },
            fontSize: 14,
            fontFamily: 'Consolas, Monaco, "Courier New", monospace',
            rows: 24,
            cols: 80
        });
        
        // Add fit addon for responsive sizing
        this.fitAddon = new FitAddon.FitAddon();
        this.terminal.loadAddon(this.fitAddon);
        
        // Mount terminal to DOM
        this.terminal.open(this.container);
        this.fitAddon.fit();
        
        // Handle terminal input
        this.terminal.onData(data => {
            if (this.socket && this.socket.readyState === WebSocket.OPEN) {
                this.socket.send(JSON.stringify({
                    type: 'input',
                    data: data
                }));
            }
        });
        
        // Handle window resize
        window.addEventListener('resize', () => {
            this.fitAddon.fit();
        });
        
        this.terminal.writeln('🌐 Web Terminal Ready - Use connectToVM() to start');
    }
    
    async loadXTermLibrary() {
        return new Promise((resolve, reject) => {
            // Load XTerm.js CSS
            const css = document.createElement('link');
            css.rel = 'stylesheet';
            css.href = 'https://cdn.jsdelivr.net/npm/xterm@5.3.0/css/xterm.css';
            document.head.appendChild(css);
            
            // Load XTerm.js library
            const script1 = document.createElement('script');
            script1.src = 'https://cdn.jsdelivr.net/npm/xterm@5.3.0/lib/xterm.js';
            script1.onload = () => {
                // Load FitAddon
                const script2 = document.createElement('script');
                script2.src = 'https://cdn.jsdelivr.net/npm/xterm-addon-fit@0.8.0/lib/xterm-addon-fit.js';
                script2.onload = resolve;
                script2.onerror = reject;
                document.head.appendChild(script2);
            };
            script1.onerror = reject;
            document.head.appendChild(script1);
        });
    }
    
    connectToVM(vmName) {
        this.vmName = vmName;
        
        // Create WebSocket connection for real-time terminal
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws/terminal/${vmName}`;
        
        this.socket = new WebSocket(wsUrl);
        
        this.socket.onopen = () => {
            this.terminal.clear();
            this.terminal.writeln(`🔗 Connected to VM: ${vmName}`);
            this.terminal.writeln('💡 You can now use vim, nano, htop, and other interactive programs!');
            this.terminal.write('\r\n$ ');
        };
        
        this.socket.onmessage = (event) => {
            const message = JSON.parse(event.data);
            if (message.type === 'output') {
                this.terminal.write(message.data);
            }
        };
        
        this.socket.onclose = () => {
            this.terminal.writeln('\r\n🔌 Connection closed');
        };
        
        this.socket.onerror = (error) => {
            this.terminal.writeln(`\r\n❌ Connection error: ${error.message}`);
        };
    }
    
    disconnect() {
        if (this.socket) {
            this.socket.close();
            this.socket = null;
        }
        this.terminal.writeln('\r\n📡 Disconnected from VM');
    }
    
    resize() {
        if (this.fitAddon) {
            this.fitAddon.fit();
        }
    }
}
