# Linux+ Practice Environment Manager (LPEM)

A CLI tool for managing libvirt VMs and running practice challenges for the CompTIA Linux+ exam (XK0-005).
Uses external snapshots for safe, revertible practice environments.

## Features

- VM lifecycle management using libvirt
- External VM snapshots for consistent practice environments
- SSH command execution and validation
- Challenge definitions in YAML format
- Configurable setup, simulation, and validation steps
- Rich terminal UI with progress indicators and colorful output

## Installation

### Prerequisites

- libvirt with QEMU support
- Python 3.6+
- VM with SSH access configured

### Installation Steps

1. Clone this repository:
   ```bash
   git clone https://github.com/yourusername/lpem.git
   cd lpem
   ```

2. Install the package:
   ```bash
   pip install -e .
   ```

## Usage

### Basic Commands

```bash
# List available VMs
lpem list-available-vms

# List available challenges
lpem list-challenges

# Set up a new user on the VM
lpem setup-user --vm ubuntu24.04-2 --new-user roo

# Run a challenge
lpem run-challenge network-basics --vm ubuntu24.04-2
```

### Creating Challenges

1. Create a challenge template:
   ```bash
   lpem challenge create-template -o challenges/my-challenge.yaml
   ```

2. Edit the template with your custom challenge details

3. Validate your challenge file:
   ```bash
   lpem challenge validate challenges/my-challenge.yaml
   ```

## Challenge File Format

Challenges are defined in YAML files with the following structure:

```yaml
id: my-challenge
name: "My Challenge Title"
description: |
  This is a description of what the user needs to accomplish.
category: "System Administration"
difficulty: "Medium"
score: 100
concepts:
  - ssh
  - systemctl
setup:
  - type: run_command
    command: "echo 'Setup command executed on VM'"
user_action_simulation: "echo 'User action simulation'"
validation:
  - type: run_command
    command: "hostname"
    success_criteria:
      exit_status: 0
  - type: check_service_status
    service: "ssh"
    expected_status: "active"
hints:
  - text: "First hint: Use the ssh command."
    cost: 0
  - text: "Second hint: Try looking at configuration files."
    cost: 10
flag: "CTF{Challenge_Completed}"
```

## Security Notice

The tool executes commands on VMs via SSH. Only use challenge files from trusted sources, and review the commands in the `setup` and `validation` sections before running.

## License

This project is licensed under the MIT License - see the LICENSE file for details.
