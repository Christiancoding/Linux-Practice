@echo off
REM Windows 11 SSH Setup Script
REM Run this in PowerShell as Administrator

echo Installing OpenSSH Server...
powershell -Command "Add-WindowsCapability -Online -Name OpenSSH.Server~~~~0.0.1.0"

echo Starting SSH service...
powershell -Command "Start-Service sshd"

echo Setting SSH to start automatically...
powershell -Command "Set-Service -Name sshd -StartupType 'Automatic'"

echo Configuring Windows Firewall...
powershell -Command "New-NetFirewallRule -Name sshd -DisplayName 'OpenSSH Server (sshd)' -Enabled True -Direction Inbound -Protocol TCP -Action Allow -LocalPort 22"

echo Creating SSH user account...
set /p username="Enter username for SSH access (default: sshuser): "
if "%username%"=="" set username=sshuser
set /p password="Enter password for SSH user: "
net user %username% %password% /add
net localgroup administrators %username% /add

echo SSH setup complete!
echo You can now connect using: ssh %username%@192.168.122.110
pause
