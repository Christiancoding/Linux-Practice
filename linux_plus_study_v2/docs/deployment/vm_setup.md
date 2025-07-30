# VM Setup Instructions

## Overview
This project uses virtual machines for hands-on Linux practice. ISO files and VM storage are excluded from Git to prevent large file issues.

## Initial VM Setup

### 1. Create VM Storage Directory
```bash
mkdir -p ~/vm-storage/{isos,vms,snapshots}
```

### 2. Download Ubuntu ISO
Download Ubuntu 22.04 LTS ISO to `~/vm-storage/isos/`:
```bash
cd ~/vm-storage/isos/
wget https://releases.ubuntu.com/22.04/ubuntu-22.04.4-live-server-amd64.iso
```

### 3. VM Configuration
The development configuration includes:
- VM storage paths in `~/vm-storage/`
- Maximum 3 concurrent VMs
- 2GB memory limit per VM
- Practice sessions timeout: 1 hour

## File Structure
```
~/vm-storage/
├── isos/              # ISO files (excluded from Git)
├── vms/               # VM disk images (excluded from Git)
└── snapshots/         # VM snapshots (excluded from Git)
```

## Git Configuration
Large files (.iso, .vmdk, .vdi, .qcow2) are automatically ignored.
See `.gitignore` for complete exclusion list.

## Development Environment
Run the project with:
```bash
python main.py
```

VM features will be available through the web interface.
