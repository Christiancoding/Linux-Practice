# Full Terminal with Automatic ttyd Integration

## Overview

The full terminal functionality now automatically starts `ttyd` on **Linux VMs** when you press the "Full Terminal" button. This provides a web-based terminal that supports all interactive programs like vim, nano, htop, etc.

**Note: Windows VMs require different setup and are not directly supported by ttyd.**

## How it Works

### For Linux VMs:
1. **Select a Linux VM**: Choose a Linux virtual machine from the VM playground
2. **Click "Full Terminal"**: Press the Full Terminal button
3. **Automatic Setup**: The system will:
   - Detect that it's a Linux VM
   - Check if ttyd is already running on the VM
   - Install ttyd if not present (`sudo apt install -y ttyd`)
   - Start ttyd with the command: `sudo ttyd -p 7682 -W -R bash`
   - Open a new window with the terminal interface

### For Windows VMs:
1. **Select a Windows VM**: Choose a Windows virtual machine from the VM playground
2. **Click "Full Terminal"**: Press the Full Terminal button
3. **Helpful Error Message**: The system will:
   - Detect that it's a Windows VM
   - Display instructions for enabling SSH on Windows
   - Provide RDP connection details as an alternative
   - Show step-by-step SSH setup commands

## Command Executed (Linux Only)

When you press the Full Terminal button on a Linux VM, the system automatically runs:

```bash
sudo ttyd -p 7682 -W -R bash
```

### Command Breakdown:
- `sudo`: Run with administrator privileges
- `ttyd`: Web-based terminal sharing tool
- `-p 7682`: Listen on port 7682
- `-W`: Allow write access to the terminal
- `-R`: Reconnect automatically on disconnect
- `bash`: Start a bash shell

## Features

### Linux VMs:
- **Full Interactive Support**: Works with vim, nano, htop, man pages, etc.
- **Automatic Installation**: ttyd is installed automatically if needed
- **Smart Detection**: Checks if ttyd is already running to avoid conflicts
- **Dynamic URLs**: Terminal URL is generated based on actual VM IP
- **Multi-User Support**: Tries different SSH users (roo, root, ubuntu, vagrant, user)
- **Error Handling**: Clear error messages if something goes wrong

### Windows VMs:
- **OS Detection**: Automatically detects Windows VMs by name
- **SSH Setup Instructions**: Provides step-by-step SSH enablement guide
- **RDP Alternative**: Offers Remote Desktop as alternative access method
- **PowerShell Commands**: Shows exact commands to run on Windows

## API Endpoint

The functionality is provided through enhanced API endpoints:

### Execute Commands
```
POST /api/vm/execute
```

**Request Body:**
```json
{
    "vm_name": "ubuntu-practice",  // or "win11"
    "command": "ls -la"
}
```

**Response (Linux Success):**
```json
{
    "success": true,
    "output": "total 48\ndrwxr-xr-x 7 roo roo 4096 Jul 28 15:30 .\n...",
    "error": "",
    "exit_status": 0,
    "username": "roo"
}
```

**Response (Windows Detection):**
```json
{
    "success": false,
    "error": "Windows VMs require SSH to be enabled first",
    "suggestions": [
        "Enable SSH: Add-WindowsCapability -Online -Name OpenSSH.Server~~~~0.0.1.0",
        "Start SSH service: Start-Service sshd",
        "Allow firewall: New-NetFirewallRule -Name sshd -DisplayName \"OpenSSH Server\" -Enabled True -Direction Inbound -Protocol TCP -Action Allow -LocalPort 22",
        "Alternative: Use RDP at rdp://192.168.122.110:3389"
    ],
    "rdp_url": "rdp://192.168.122.110:3389"
}
```

### Start ttyd
```
POST /api/vm/start_ttyd
```

**Request Body:**
```json
{
    "vm_name": "ubuntu-practice",
    "port": 7682
}
```

**Response (Linux Success):**
```json
{
    "success": true,
    "message": "ttyd started successfully on port 7682",
    "url": "http://192.168.122.182:7682",
    "pid": "12345",
    "username": "roo"
}
```

**Response (Windows Detection):**
```json
{
    "success": false,
    "error": "ttyd is not supported on Windows VMs",
    "suggestions": [
        "Windows VMs require different remote access methods",
        "Enable SSH first with: Add-WindowsCapability -Online -Name OpenSSH.Server~~~~0.0.1.0",
        "Or use Remote Desktop Protocol (RDP)",
        "RDP URL: rdp://192.168.122.110:3389"
    ],
    "rdp_url": "rdp://192.168.122.110:3389",
    "ssh_setup_commands": [
        "Add-WindowsCapability -Online -Name OpenSSH.Server~~~~0.0.1.0",
        "Start-Service sshd",
        "Set-Service -Name sshd -StartupType \"Automatic\"",
        "New-NetFirewallRule -Name sshd -DisplayName \"OpenSSH Server\" -Enabled True -Direction Inbound -Protocol TCP -Action Allow -LocalPort 22"
    ]
}
```

## Testing

Run the test script to verify functionality:

```bash
python3 test_ttyd_integration.py
```

This will:
1. Test basic VM connectivity
2. Test the ttyd startup API
3. Verify terminal accessibility
4. Test Windows VM detection

## Windows VM Setup

### Enable SSH on Windows 11/10

1. **Open PowerShell as Administrator** on your Windows VM
2. **Install OpenSSH Server**:
   ```powershell
   Add-WindowsCapability -Online -Name OpenSSH.Server~~~~0.0.1.0
   ```

3. **Start SSH Service**:
   ```powershell
   Start-Service sshd
   Set-Service -Name sshd -StartupType 'Automatic'
   ```

4. **Configure Firewall**:
   ```powershell
   New-NetFirewallRule -Name sshd -DisplayName 'OpenSSH Server' -Enabled True -Direction Inbound -Protocol TCP -Action Allow -LocalPort 22
   ```

5. **Create SSH User** (optional):
   ```powershell
   net user sshuser MyPassword123! /add
   net localgroup administrators sshuser /add
   ```

### Alternative: Use RDP

For Windows VMs, you can use Remote Desktop instead:

```bash
# Install RDP client (if not already installed)
sudo apt install remmina

# Connect to Windows VM
remmina -c rdp://192.168.122.110:3389
```

## Troubleshooting

### Common Issues:

#### Linux VMs:
1. **VM not selected**: Select a VM before clicking Full Terminal
2. **VM not running**: Start the VM first
3. **SSH connectivity**: Ensure SSH keys are properly configured
4. **Port conflicts**: ttyd uses port 7682 by default
5. **User permissions**: System tries multiple users automatically

#### Windows VMs:
1. **SSH not enabled**: Follow Windows SSH setup instructions
2. **Firewall blocking**: Ensure Windows Firewall allows SSH (port 22)
3. **User authentication**: Create proper SSH user account
4. **RDP alternative**: Use RDP if SSH setup is complex

### Manual Testing:

#### Linux VMs:
1. Open http://localhost:5000/vm_playground
2. Select a Linux VM from the sidebar
3. Click the "Full Terminal" button
4. Check terminal output for status messages
5. New window should open with working terminal

#### Windows VMs:
1. Open http://localhost:5000/vm_playground
2. Select a Windows VM from the sidebar
3. Click the "Full Terminal" button
4. Follow SSH setup instructions or use RDP link

## Files Modified

- `views/web_view.py`: Enhanced `/api/vm/execute` and `/api/vm/start_ttyd` endpoints with OS detection
- `templates/vm_playground.html`: Updated `openFullTerminal()` function
- `templates/full_terminal.html`: Dynamic URL loading and status updates
- `enhanced_vm_manager.py`: New enhanced VM manager with Windows support
- `windows_ssh_setup.bat`: Windows SSH setup script

## Security Notes

### Linux VMs:
- ttyd runs with sudo privileges for full system access
- Terminal sessions are web-accessible on the VM's IP
- Only use on trusted networks/VMs
- Sessions are not encrypted (use VPN if needed)

### Windows VMs:
- SSH setup requires administrator privileges
- RDP connections should use strong passwords
- Consider using SSH keys instead of passwords
- Firewall rules should be configured carefully

## Troubleshooting

### Common Issues:

1. **VM not selected**: Select a VM before clicking Full Terminal
2. **VM not running**: Start the VM first
3. **SSH connectivity**: Ensure SSH keys are properly configured
4. **Port conflicts**: ttyd uses port 7682 by default
5. **Popup blocked**: Allow popups for the site

### Manual Testing:

1. Open http://localhost:5000/vm_playground
2. Select a VM from the sidebar
3. Click the "Full Terminal" button
4. Check terminal output for status messages
5. New window should open with working terminal

## Files Modified

- `views/web_view.py`: Added `/api/vm/start_ttyd` endpoint
- `templates/vm_playground.html`: Updated `openFullTerminal()` function
- `templates/full_terminal.html`: Dynamic URL loading and status updates

## Security Notes

- ttyd runs with sudo privileges for full system access
- Terminal sessions are web-accessible on the VM's IP
- Only use on trusted networks/VMs
- Sessions are not encrypted (use VPN if needed)
