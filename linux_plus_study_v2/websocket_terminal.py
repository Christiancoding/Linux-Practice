#!/usr/bin/env python3
"""
WebSocket Terminal Handler for real-time interactive terminal sessions.
Provides full vim/nano support through proper PTY allocation.
"""

import asyncio
import json
import logging
import os
import pty
import subprocess
import termios
import websockets
from pathlib import Path
from threading import Thread
import struct
import fcntl

logger = logging.getLogger(__name__)

class WebSocketTerminal:
    """WebSocket-based terminal that supports full interactive programs."""
    
    def __init__(self, vm_ip: str, vm_user: str, ssh_key_path: Path):
        self.vm_ip = vm_ip
        self.vm_user = vm_user
        self.ssh_key_path = ssh_key_path
        self.process = None
        self.master_fd = None
        self.websocket = None
        
    async def handle_websocket(self, websocket, path):
        """Handle WebSocket connection for terminal session."""
        self.websocket = websocket
        logger.info(f"WebSocket terminal connected: {path}")
        
        try:
            # Start SSH session with PTY
            await self.start_ssh_session()
            
            # Handle WebSocket messages
            async for message in websocket:
                data = json.loads(message)
                if data['type'] == 'input':
                    await self.send_input(data['data'])
                elif data['type'] == 'resize':
                    await self.resize_terminal(data['rows'], data['cols'])
                    
        except websockets.exceptions.ConnectionClosed:
            logger.info("WebSocket connection closed")
        except Exception as e:
            logger.error(f"WebSocket error: {e}")
        finally:
            await self.cleanup()
    
    async def start_ssh_session(self):
        """Start SSH session with proper PTY allocation."""
        try:
            # Create pseudo-terminal
            self.master_fd, slave_fd = pty.openpty()
            
            # SSH command with PTY allocation
            ssh_cmd = [
                'ssh',
                '-i', str(self.ssh_key_path),
                '-o', 'StrictHostKeyChecking=no',
                '-o', 'UserKnownHostsFile=/dev/null',
                '-o', 'LogLevel=quiet',
                '-t',  # Force TTY allocation
                f'{self.vm_user}@{self.vm_ip}'
            ]
            
            # Start SSH process
            self.process = subprocess.Popen(
                ssh_cmd,
                stdin=slave_fd,
                stdout=slave_fd,
                stderr=slave_fd,
                preexec_fn=os.setsid
            )
            
            # Close slave fd in parent process
            os.close(slave_fd)
            
            # Start reading from master fd
            asyncio.create_task(self.read_output())
            
            logger.info(f"SSH session started to {self.vm_user}@{self.vm_ip}")
            
        except Exception as e:
            logger.error(f"Failed to start SSH session: {e}")
            raise
    
    async def read_output(self):
        """Read output from SSH session and send to WebSocket."""
        loop = asyncio.get_event_loop()
        
        while self.process and self.process.poll() is None:
            try:
                # Read from master fd (non-blocking)
                output = await loop.run_in_executor(
                    None, self._read_nonblocking, self.master_fd, 1024
                )
                
                if output:
                    # Send output to WebSocket
                    if self.websocket:
                        await self.websocket.send(json.dumps({
                            'type': 'output',
                            'data': output.decode('utf-8', errors='replace')
                        }))
                else:
                    # No data available, small delay
                    await asyncio.sleep(0.01)
                    
            except Exception as e:
                logger.error(f"Error reading output: {e}")
                break
    
    def _read_nonblocking(self, fd, size):
        """Read from file descriptor in non-blocking mode."""
        try:
            # Set non-blocking mode
            flags = fcntl.fcntl(fd, fcntl.F_GETFL)
            fcntl.fcntl(fd, fcntl.F_SETFL, flags | os.O_NONBLOCK)
            
            return os.read(fd, size)
        except OSError:
            return b''
    
    async def send_input(self, data):
        """Send input to SSH session."""
        if self.master_fd:
            try:
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(
                    None, os.write, self.master_fd, data.encode('utf-8')
                )
            except Exception as e:
                logger.error(f"Error sending input: {e}")
    
    async def resize_terminal(self, rows, cols):
        """Resize the terminal window."""
        if self.master_fd:
            try:
                # Set terminal size
                winsize = struct.pack('HHHH', rows, cols, 0, 0)
                fcntl.ioctl(self.master_fd, termios.TIOCSWINSZ, winsize)
                logger.debug(f"Terminal resized to {rows}x{cols}")
            except Exception as e:
                logger.error(f"Error resizing terminal: {e}")
    
    async def cleanup(self):
        """Clean up resources."""
        if self.process:
            try:
                self.process.terminate()
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
            except Exception as e:
                logger.error(f"Error terminating process: {e}")
        
        if self.master_fd:
            try:
                os.close(self.master_fd)
            except Exception as e:
                logger.error(f"Error closing master fd: {e}")

# WebSocket server setup
async def terminal_handler(websocket, path):
    """WebSocket handler for terminal connections."""
    try:
        # Extract VM name from path
        vm_name = path.split('/')[-1] if '/' in path else 'ubuntu-practice'
        
        # SSH connection details
        vm_ip = "192.168.122.182"  # Update with actual VM IP
        vm_user = "roo"
        ssh_key_path = Path.home() / '.ssh' / 'id_ed25519'
        
        # Create terminal instance
        terminal = WebSocketTerminal(vm_ip, vm_user, ssh_key_path)
        
        # Handle WebSocket connection
        await terminal.handle_websocket(websocket, path)
        
    except Exception as e:
        logger.error(f"Terminal handler error: {e}")

def start_websocket_server(host='localhost', port=8765):
    """Start WebSocket server for terminal connections."""
    logger.info(f"Starting WebSocket terminal server on {host}:{port}")
    
    return websockets.serve(terminal_handler, host, port)

if __name__ == '__main__':
    # Example usage
    logging.basicConfig(level=logging.INFO)
    
    # Start WebSocket server
    start_server = start_websocket_server()
    
    loop = asyncio.get_event_loop()
    loop.run_until_complete(start_server)
    loop.run_forever()
