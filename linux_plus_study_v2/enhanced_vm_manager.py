#!/usr/bin/env python3
"""
Enhanced VM Manager with Windows Support
Handles both Linux and Windows VMs with appropriate connection methods.
"""

import os
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional, Union
import logging

class EnhancedVMManager:
    """VM Manager that supports both Linux and Windows VMs."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Default configurations for different OS types
        self.vm_configs = {
            'linux': {
                'default_user': 'roo',
                'ssh_port': 22,
                'shell': 'bash',
                'commands': {
                    'test': 'echo "test"',
                    'os_info': 'uname -a',
                    'install_ttyd': 'sudo apt update && sudo apt install -y ttyd'
                }
            },
            'windows': {
                'default_user': 'Administrator',  # or configured user
                'ssh_port': 22,
                'shell': 'powershell',
                'rdp_port': 3389,
                'commands': {
                    'test': 'echo "test"',
                    'os_info': 'Get-ComputerInfo | Select-Object WindowsProductName, TotalPhysicalMemory',
                    'enable_ssh': 'Add-WindowsCapability -Online -Name OpenSSH.Server~~~~0.0.1.0; Start-Service sshd'
                }
            }
        }
    
    def detect_vm_os(self, vm_name: str) -> str:
        """
        Detect the operating system of a VM.
        
        Args:
            vm_name: Name of the VM
            
        Returns:
            'linux', 'windows', or 'unknown'
        """
        # Check VM name patterns
        vm_name_lower = vm_name.lower()
        
        if any(keyword in vm_name_lower for keyword in ['win', 'windows', 'w10', 'w11']):
            return 'windows'
        elif any(keyword in vm_name_lower for keyword in ['ubuntu', 'linux', 'centos', 'debian']):
            return 'linux'
        
        # Try to detect via libvirt domain info if available
        try:
            from vm_integration.utils.vm_manager import VMManager
            vm_manager = VMManager()
            domain = vm_manager.find_vm(vm_name)
            
            # Get VM description or metadata
            desc = domain.metadata(0, None, 0)  # Get description
            if desc:
                if 'windows' in desc.lower():
                    return 'windows'
                elif 'linux' in desc.lower():
                    return 'linux'
        except Exception as e:
            self.logger.debug(f"Could not detect OS via libvirt: {e}")
        
        # Default to linux for backward compatibility
        return 'linux'
    
    def get_vm_config(self, vm_name: str) -> Dict[str, Any]:
        """Get configuration for a specific VM based on its OS."""
        os_type = self.detect_vm_os(vm_name)
        return self.vm_configs.get(os_type, self.vm_configs['linux'])
    
    def test_ssh_connection(self, vm_ip: str, vm_name: str) -> Dict[str, Any]:
        """
        Test SSH connection to a VM with OS-appropriate credentials.
        
        Args:
            vm_ip: IP address of the VM
            vm_name: Name of the VM
            
        Returns:
            Dictionary with connection test results
        """
        config = self.get_vm_config(vm_name)
        
        from vm_integration.utils.ssh_manager import SSHManager
        ssh_manager = SSHManager()
        
        # Try different user accounts
        users_to_try = [config['default_user']]
        
        # Add common alternatives based on OS
        if self.detect_vm_os(vm_name) == 'windows':
            users_to_try.extend(['Administrator', 'admin', 'user', 'vagrant'])
        else:
            users_to_try.extend(['root', 'ubuntu', 'vagrant', 'user'])
        
        ssh_key_path = Path.home() / '.ssh' / 'id_ed25519'
        
        for user in users_to_try:
            try:
                result = ssh_manager.run_ssh_command(
                    host=vm_ip,
                    username=user,
                    key_path=ssh_key_path,
                    command=config['commands']['test'],
                    timeout=10,
                    verbose=False
                )
                
                if result.get('exit_status') == 0:
                    return {
                        'success': True,
                        'user': user,
                        'os_type': self.detect_vm_os(vm_name),
                        'message': f'SSH connection successful with user {user}'
                    }
            except Exception as e:
                self.logger.debug(f"SSH test failed for user {user}: {e}")
                continue
        
        return {
            'success': False,
            'error': f'SSH connection failed for all attempted users: {users_to_try}',
            'suggestions': self._get_connection_suggestions(vm_name)
        }
    
    def _get_connection_suggestions(self, vm_name: str) -> list:
        """Get suggestions for connecting to a VM based on its OS."""
        os_type = self.detect_vm_os(vm_name)
        
        if os_type == 'windows':
            return [
                "Enable SSH Server on Windows: Add-WindowsCapability -Online -Name OpenSSH.Server~~~~0.0.1.0",
                "Start SSH service: Start-Service sshd",
                "Check Windows Firewall: Allow port 22",
                "Alternative: Use RDP instead of SSH",
                "Verify user account and credentials"
            ]
        else:
            return [
                "Check if SSH service is running: sudo systemctl status ssh",
                "Verify SSH key is installed: cat ~/.ssh/authorized_keys",
                "Check firewall rules: sudo ufw status",
                "Verify user account exists: id roo"
            ]
    
    def execute_command(self, vm_name: str, vm_ip: str, command: str, user: Optional[str] = None) -> Dict[str, Any]:
        """
        Execute a command on a VM with OS-appropriate handling.
        
        Args:
            vm_name: Name of the VM
            vm_ip: IP address of the VM
            command: Command to execute
            user: Username (if None, will be detected)
            
        Returns:
            Dictionary with execution results
        """
        config = self.get_vm_config(vm_name)
        os_type = self.detect_vm_os(vm_name)
        
        # If user not specified, detect working user
        if not user:
            ssh_test = self.test_ssh_connection(vm_ip, vm_name)
            if not ssh_test['success']:
                return ssh_test
            user = ssh_test['user']
        
        # Adapt command for Windows if necessary
        if os_type == 'windows':
            command = self._adapt_command_for_windows(command)
        
        from vm_integration.utils.ssh_manager import SSHManager
        ssh_manager = SSHManager()
        ssh_key_path = Path.home() / '.ssh' / 'id_ed25519'
        
        # Check if command requires interactive mode
        interactive_commands = ['vim', 'nano', 'htop', 'top', 'man', 'less', 'more', 'vi']
        is_interactive = any(cmd in command.lower() for cmd in interactive_commands)
        
        try:
            if is_interactive and os_type == 'linux':
                # Use interactive SSH for Linux TTY commands
                result = ssh_manager.run_interactive_ssh_command(
                    host=vm_ip,
                    username=user,
                    key_path=ssh_key_path,
                    command=command,
                    timeout=60,
                    verbose=True
                )
            else:
                # Use regular SSH for non-interactive or Windows commands
                result = ssh_manager.run_ssh_command(
                    host=vm_ip,
                    username=user,
                    key_path=ssh_key_path,
                    command=command,
                    timeout=30,
                    verbose=True
                )
            
            success = result.get('error') is None and result.get('exit_status') == 0
            
            return {
                'success': success,
                'output': result.get('stdout', ''),
                'error': result.get('stderr', '') or result.get('error', ''),
                'exit_status': result.get('exit_status', 0),
                'user': user,
                'os_type': os_type
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'suggestions': self._get_connection_suggestions(vm_name)
            }
    
    def _adapt_command_for_windows(self, command: str) -> str:
        """Adapt Linux commands for Windows PowerShell."""
        # Basic command translations
        translations = {
            'ls': 'Get-ChildItem',
            'cat': 'Get-Content',
            'grep': 'Select-String',
            'ps': 'Get-Process',
            'pwd': 'Get-Location',
            'whoami': 'whoami',
            'echo': 'Write-Output',
            'mkdir': 'New-Item -ItemType Directory',
            'rm': 'Remove-Item',
            'cp': 'Copy-Item',
            'mv': 'Move-Item'
        }
        
        # Split command and translate first word
        parts = command.split()
        if parts and parts[0] in translations:
            parts[0] = translations[parts[0]]
            return ' '.join(parts)
        
        return command
    
    def start_ttyd_enhanced(self, vm_name: str, vm_ip: str, port: int = 7682) -> Dict[str, Any]:
        """
        Start ttyd with enhanced OS detection and error handling.
        
        Args:
            vm_name: Name of the VM
            vm_ip: IP address of the VM
            port: Port for ttyd service
            
        Returns:
            Dictionary with operation results
        """
        os_type = self.detect_vm_os(vm_name)
        
        if os_type == 'windows':
            return {
                'success': False,
                'error': 'ttyd is not supported on Windows VMs',
                'suggestion': 'Use RDP or Windows Terminal for Windows VMs',
                'rdp_url': f'rdp://{vm_ip}:3389'
            }
        
        # For Linux VMs, use existing ttyd logic
        return self._start_ttyd_linux(vm_name, vm_ip, port)
    
    def _start_ttyd_linux(self, vm_name: str, vm_ip: str, port: int) -> Dict[str, Any]:
        """Start ttyd on Linux VM (existing logic)."""
        # Test SSH connection first
        ssh_test = self.test_ssh_connection(vm_ip, vm_name)
        if not ssh_test['success']:
            return ssh_test
        
        user = ssh_test['user']
        
        from vm_integration.utils.ssh_manager import SSHManager
        ssh_manager = SSHManager()
        ssh_key_path = Path.home() / '.ssh' / 'id_ed25519'
        
        # Check if ttyd is already running
        check_cmd = f"pgrep -f 'ttyd.*{port}'"
        check_result = ssh_manager.run_ssh_command(
            host=vm_ip,
            username=user,
            key_path=ssh_key_path,
            command=check_cmd,
            timeout=10
        )
        
        if check_result.get('exit_status') == 0:
            return {
                'success': True,
                'message': f'ttyd is already running on port {port}',
                'url': f'http://{vm_ip}:{port}'
            }
        
        # Install and start ttyd
        install_cmd = "which ttyd || (sudo apt update && sudo apt install -y ttyd)"
        install_result = ssh_manager.run_ssh_command(
            host=vm_ip,
            username=user,
            key_path=ssh_key_path,
            command=install_cmd,
            timeout=120
        )
        
        if install_result.get('exit_status') != 0:
            return {
                'success': False,
                'error': f'Failed to install ttyd: {install_result.get("stderr", "Unknown error")}'
            }
        
        # Start ttyd
        ttyd_cmd = f"sudo ttyd -p {port} -W -R bash"
        start_cmd = f"nohup {ttyd_cmd} > /dev/null 2>&1 & echo $!"
        
        start_result = ssh_manager.run_ssh_command(
            host=vm_ip,
            username=user,
            key_path=ssh_key_path,
            command=start_cmd,
            timeout=10
        )
        
        if start_result.get('exit_status') == 0:
            import time
            time.sleep(2)
            
            # Verify ttyd is running
            verify_result = ssh_manager.run_ssh_command(
                host=vm_ip,
                username=user,
                key_path=ssh_key_path,
                command=check_cmd,
                timeout=5
            )
            
            if verify_result.get('exit_status') == 0:
                return {
                    'success': True,
                    'message': f'ttyd started successfully on port {port}',
                    'url': f'http://{vm_ip}:{port}',
                    'pid': start_result.get('stdout', '').strip()
                }
        
        return {
            'success': False,
            'error': 'ttyd failed to start or is not responding'
        }

# Usage example
if __name__ == "__main__":
    vm_manager = EnhancedVMManager()
    
    # Test with your Windows VM
    result = vm_manager.test_ssh_connection("192.168.122.110", "win11")
    print("SSH Test Result:", result)
    
    if not result['success']:
        print("Suggestions:")
        for suggestion in result.get('suggestions', []):
            print(f"  - {suggestion}")
