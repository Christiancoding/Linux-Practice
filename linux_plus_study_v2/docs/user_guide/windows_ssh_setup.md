# Windows 11 VM SSH Setup Guide

## Problem
The system is trying to SSH to your Windows 11 VM using Linux credentials (`roo@192.168.122.110`), but Windows doesn't have SSH enabled by default.

## Solution: Enable SSH Server on Windows 11

### Method 1: Via PowerShell (Recommended)
1. **Open PowerShell as Administrator** on your Windows 11 VM
2. **Install OpenSSH Server**:
   ```powershell
   # Check if OpenSSH is available
   Get-WindowsCapability -Online | Where-Object Name -like 'OpenSSH*'
   
   # Install OpenSSH Server
   Add-WindowsCapability -Online -Name OpenSSH.Server~~~~0.0.1.0
   ```

3. **Start and Enable SSH Service**:
   ```powershell
   # Start the service
   Start-Service sshd
   
   # Set it to start automatically
   Set-Service -Name sshd -StartupType 'Automatic'
   
   # Verify the service is running
   Get-Service sshd
   ```

4. **Configure Windows Firewall**:
   ```powershell
   # Allow SSH through Windows Firewall
   New-NetFirewallRule -Name sshd -DisplayName 'OpenSSH Server (sshd)' -Enabled True -Direction Inbound -Protocol TCP -Action Allow -LocalPort 22
   ```

### Method 2: Via Settings GUI
1. Open **Settings** → **Apps** → **Optional Features**
2. Click **Add an optional feature**
3. Find and install **OpenSSH Server**
4. Open **Services** (`services.msc`)
5. Find **OpenSSH SSH Server**
6. Set startup type to **Automatic** and start the service

## User Account Setup

### Create SSH User Account
1. **Create a new user** (or use existing):
   ```powershell
   # Create new user
   net user sshuser MyPassword123! /add
   
   # Add to Administrators group (optional)
   net localgroup administrators sshuser /add
   ```

### SSH Key Authentication (Optional but Recommended)
1. **On your Linux host**, copy your public key to Windows:
   ```bash
   # Copy your public key
   cat ~/.ssh/id_ed25519.pub
   ```

2. **On Windows VM**, create SSH directory and authorized_keys:
   ```powershell
   # Create SSH directory
   mkdir C:\Users\[USERNAME]\.ssh
   
   # Create authorized_keys file and paste your public key
   notepad C:\Users\[USERNAME]\.ssh\authorized_keys
   ```

3. **Set proper permissions**:
   ```powershell
   # Set permissions for SSH directory
   icacls C:\Users\[USERNAME]\.ssh /inheritance:r
   icacls C:\Users\[USERNAME]\.ssh /grant [USERNAME]:F
   icacls C:\Users\[USERNAME]\.ssh /grant SYSTEM:F
   ```

## Testing SSH Connection

### From Linux Host:
```bash
# Test SSH connection (replace with your Windows username)
ssh [USERNAME]@192.168.122.110

# Test with specific key
ssh -i ~/.ssh/id_ed25519 [USERNAME]@192.168.122.110
```

## Code Configuration Changes

Update the VM configuration to use Windows credentials:

1. **Username**: Change from `roo` to your Windows username (e.g., `Administrator`, `sshuser`)
2. **Authentication**: Ensure SSH key is properly configured or use password authentication
3. **Commands**: Adjust commands for Windows PowerShell/CMD instead of bash

## Alternative: Use Remote Desktop Instead

If SSH setup is complex, consider using Windows Remote Desktop:

1. **Enable RDP on Windows VM**:
   ```powershell
   # Enable Remote Desktop
   Set-ItemProperty -Path 'HKLM:\System\CurrentControlSet\Control\Terminal Server' -name "fDenyTSConnections" -value 0
   
   # Enable Remote Desktop through firewall
   Enable-NetFirewallRule -DisplayGroup "Remote Desktop"
   ```

2. **Connect via RDP client** on your Linux host:
   ```bash
   # Install RDP client if not available
   sudo apt install remmina
   
   # Connect to Windows VM
   remmina -c rdp://192.168.122.110
   ```

## Next Steps

1. **Choose your preferred method** (SSH or RDP)
2. **Configure Windows VM** according to the chosen method
3. **Test connectivity** from your Linux host
4. **Update application code** if using SSH with different credentials

## Troubleshooting

### Common Issues:
- **Connection Refused**: SSH service not running
- **Permission Denied**: Wrong username/password or key not configured
- **Timeout**: Windows Firewall blocking port 22
- **Authentication Failed**: SSH key permissions or format issues

### Verification Commands:
```powershell
# Check SSH service status
Get-Service sshd

# Check firewall rules
Get-NetFirewallRule -DisplayName "*ssh*"

# Check SSH configuration
Get-Content C:\ProgramData\ssh\sshd_config
```
