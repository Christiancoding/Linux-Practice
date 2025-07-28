# Full Terminal with Automatic ttyd Integration

## Overview

The full terminal functionality now automatically starts `ttyd` on the VM when you press the "Full Terminal" button. This provides a web-based terminal that supports all interactive programs like vim, nano, htop, etc.

## How it Works

1. **Select a VM**: Choose a virtual machine from the VM playground
2. **Click "Full Terminal"**: Press the Full Terminal button
3. **Automatic Setup**: The system will:
   - Check if ttyd is already running on the VM
   - Install ttyd if not present (`sudo apt install -y ttyd`)
   - Start ttyd with the command: `sudo ttyd -p 7682 -W -R bash`
   - Open a new window with the terminal interface

## Command Executed

When you press the Full Terminal button, the system automatically runs:

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

- **Full Interactive Support**: Works with vim, nano, htop, man pages, etc.
- **Automatic Installation**: ttyd is installed automatically if needed
- **Smart Detection**: Checks if ttyd is already running to avoid conflicts
- **Dynamic URLs**: Terminal URL is generated based on actual VM IP
- **Error Handling**: Clear error messages if something goes wrong

## API Endpoint

The functionality is provided through a new API endpoint:

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

**Response (Success):**
```json
{
    "success": true,
    "message": "ttyd started successfully on port 7682",
    "url": "http://192.168.122.182:7682",
    "pid": "12345"
}
```

**Response (Error):**
```json
{
    "success": false,
    "error": "Failed to start ttyd: [error details]"
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
