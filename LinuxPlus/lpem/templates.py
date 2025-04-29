"""Template definitions for the LPEM tool."""

# --- Challenge Template Definition ---
CHALLENGE_TEMPLATE = """# --- Challenge Definition File ---
# See PDF documentation and existing challenges for examples.
# SECURITY WARNING: 'run_command' executes commands via SSH on the target VM.
# Do not load challenges from untrusted sources without understanding the commands.

# Unique identifier for the challenge (e.g., configure-ssh-keys)
id: my-new-challenge-id

# Human-readable name for the challenge
name: "My New Challenge Title"

# Detailed description of the objective for the user (Markdown supported)
description: |
  Provide a clear, step-by-step objective for the learner.
  Explain the desired final state of the system.
  Mention any specific tools or methods they should practice (if applicable).
  * Use lists.
  * Use `code formatting`.
  * **Bold** and _italics_.

# Category for grouping challenges (e.g., Networking, Security, Storage, Scripting)
category: "Storage"

# Difficulty level (e.g., Basic, Intermediate, Advanced) based on Linux+ scope
difficulty: "Intermediate"

# List of relevant Linux concepts or commands involved (for filtering/searching)
concepts:
  - lvm
  - mkfs.xfs
  - mount
  - fstab
#  - systemctl
#  - ssh
#  - grep

# --- XK0-005 Alignment & Metadata ---
# Specific XK0-005 objective codes covered (e.g., "1.3", "2.5")
objective_refs: ["1.3"]

# Estimated time for the learner to complete the challenge (integer)
estimated_time_mins: 15

# Compatible distribution families ("Any", "RHEL-based", "Debian-based")
distro_compatibility: ["Any"]

# Path to the corresponding solution guide (relative to this challenge file)
solution_file: "solutions/my-new-challenge-id.md"

# --- Challenge State & Scoring ---
# Potential score for completing the challenge successfully (before hint costs)
score: 100 # Defaults to 100 if omitted

# Optional: A 'flag' string displayed upon successful completion (for CTF-style use)
# flag: "CTF{LVM_Mastery_Achieved}"

# Optional: Setup steps executed *before* the user interacts with the VM.
# Used to put the VM into the correct starting state for the challenge.
# WARNING: Commands run here execute on the VM via SSH. Use with extreme caution.
#          Prefer declarative steps (ensure_package, ensure_disk) when possible.
setup:
  # - type: run_command
  #   command: "echo 'Setup: Placeholder command executed on VM'"
  #   user_context: root # Optional: 'root' or specific user (requires careful permission handling)
  - type: ensure_package_installed
    package: lvm2 # Ensure the lvm2 package is present
    # manager_type: "apt" # Optional: Force package manager type
    # update_cache: true # Optional: Defaults to true? Check implementation
  # Example setup type from PDF (requires platform implementation)
  # - type: ensure_disk_available
  #   disk_name: /dev/sdx # The tool needs to determine an available disk
  #   size: 500M

# Optional: A command that simulates the user performing the correct action.
# Useful for testing validation logic with the --simulate flag.
# WARNING: Command runs on the VM via SSH.
user_action_simulation: |
  echo 'Simulating LVM creation...' &&
  sudo pvcreate /dev/sdx &&
  sudo vgcreate storage_vg /dev/sdx &&
  sudo lvcreate -L 100M -n data_lv storage_vg &&
  sudo mkfs.xfs /dev/storage_vg/data_lv &&
  sudo mkdir -p /mnt/data &&
  echo '/dev/mapper/storage_vg-data_lv /mnt/data xfs defaults 0 0' | sudo tee -a /etc/fstab &&
  sudo mount /mnt/data

# Required: Validation steps executed *after* the user performs the action.
# Divided into final state (outcome) and process (method) checks per PDF.

# Checks verifying the outcome/final configuration of the system. (Required)
final_state_checks:
  - type: check_lvm_state
    check_type: pv_exists # pv_exists | vg_exists | lv_exists | lv_size
    device: /dev/sdx # Or partition if used (replace sdx with actual device)
    expected_state: true # Default: true
  - type: check_lvm_state
    check_type: vg_exists
    vg_name: storage_vg
  - type: check_lvm_state
    check_type: lv_exists
    vg_name: storage_vg
    lv_name: data_lv
  - type: check_lvm_state
    check_type: lv_size
    vg_name: storage_vg
    lv_name: data_lv
    min_size_mb: 95 # Check size is within a reasonable range
    max_size_mb: 105
    # exact_size_mb: 100 # Alternative: check for exact size
  - type: check_mount_point # Verifies mount command AND fstab correctness after reboot (implicitly)
    mount_point: /mnt/data
    # Use a pattern for the device as mapping can vary slightly
    device_pattern: "/dev/(mapper/)?storage_vg-data_lv" # Regex pattern
    filesystem_type: "xfs"
    # options_contain: ["defaults"] # Optional: Check mount options
  - type: check_file_contains
    path: /etc/fstab
    # Use regex for flexibility with whitespace, ensure whole line match
    matches_regex: "^/dev/(mapper/)?storage_vg-data_lv\\s+/mnt/data\\s+xfs\\s+defaults\\s+[0-9]+\\s+[0-9]+\\s*$"
    expected_state: true

# Optional checks verifying the *method* used or discouraging specific shortcuts.
# These checks are often less reliable than final state checks.
process_validation_checks:
  - type: check_history
    # Example: Check if core LVM commands were likely used
    command_pattern: "(pvcreate.*sdx|vgcreate.*storage_vg|lvcreate.*data_lv)" # Regex pattern
    expected_count: ">=3" # Expect at least one of each relevant command variation
    # disallowed_commands: ["bad_command", "shortcut_tool"] # Optional: List forbidden commands/patterns
    # history_command: "cat ~/.custom_history" # Optional: Override default history source
    notes: "History checks are indicative, not foolproof." # Optional notes for results
  # - type: check_journalctl
  #   # Example: Check if mkfs.xfs was logged by sudo or systemd
  #   syslog_identifier: "sudo" # Check sudo logs
  #   message_pattern: "mkfs\\.xfs.* /dev/mapper/storage_vg-data_lv" # Regex
  #   since: "5 minutes ago" # Time scope for the check
  #   expected_state: true
  # - type: check_audit_log
  #   # Example: Check if lvcreate command was executed (requires auditd rule)
  #   rule_key: "lvm_commands" # Key defined in auditd rules (e.g., -S execve -F path=/usr/sbin/lvcreate -k lvm_commands)
  #   since: "recent"
  #   expected_state: true
  #   notes: "Requires auditd setup with appropriate rules."

# Optional: Hints displayed to the user upon request.
hints:
  - text: "What command initializes a physical disk for LVM use?"
    cost: 0 # Score cost for viewing this hint
  - text: "Remember the sequence: `pvcreate`, `vgcreate`, `lvcreate`."
    cost: 5
  - text: "After creating the LV, what must you do before mounting it? Use `mkfs`."
    cost: 10
  - text: "How do you make mounts persistent across reboots? Edit the `/etc/fstab` file."
    cost: 15

# Optional: A 'flag' string displayed upon successful completion.
# If omitted, a generic success message is shown.
# flag: "CTF{My_Challenge_Completed_Successfully}"
"""