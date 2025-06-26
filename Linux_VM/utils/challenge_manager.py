# --- Part 1: Standard Library Imports ---
import json
import os
import re
import shlex
import socket
import stat  # For checking file permissions
import sys
import time
import traceback
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
# --- Part 12: Challenge Loading & Validation Functions ---
def validate_challenge_structure(challenge_data: dict, filename: str = "challenge") -> List[str]:
    """Performs structural validation of loaded challenge data against expected schema."""
    errors = []
    # --- Top Level Keys ---
    required_keys = ['id', 'name', 'description', 'validation']
    allowed_keys = ['id', 'name', 'description', 'category', 'difficulty', 'score',
                    'concepts', 'setup', 'user_action_simulation', 'validation', 'hints', 'flag']
    for key in challenge_data:
        if key not in allowed_keys: errors.append(f"'{filename}': Unknown top-level key: '{key}'")
    for key in required_keys:
        if key not in challenge_data: errors.append(f"'{filename}': Missing required top-level key: '{key}'")

    # --- Basic Type Checks ---
    if 'id' in challenge_data and not isinstance(challenge_data['id'], str): errors.append(f"'{filename}': 'id' must be a string.")
    if 'name' in challenge_data and not isinstance(challenge_data['name'], str): errors.append(f"'{filename}': 'name' must be a string.")
    if 'description' in challenge_data and not isinstance(challenge_data['description'], str): errors.append(f"'{filename}': 'description' must be a string.")
    if 'category' in challenge_data and not isinstance(challenge_data['category'], str): errors.append(f"'{filename}': 'category' must be a string.")
    if 'difficulty' in challenge_data and not isinstance(challenge_data['difficulty'], str): errors.append(f"'{filename}': 'difficulty' must be a string.")
    if 'user_action_simulation' in challenge_data and not isinstance(challenge_data['user_action_simulation'], str): errors.append(f"'{filename}': 'user_action_simulation' must be a string.")
    if 'flag' in challenge_data and not isinstance(challenge_data['flag'], str): errors.append(f"'{filename}': 'flag' must be a string.")
    if 'concepts' in challenge_data and not isinstance(challenge_data['concepts'], list): errors.append(f"'{filename}': 'concepts' must be a list of strings.")
    elif 'concepts' in challenge_data:
        if not all(isinstance(c, str) for c in challenge_data['concepts']): errors.append(f"'{filename}': All items in 'concepts' must be strings.")

    # --- Score Validation ---
    if 'score' in challenge_data:
        try: int(challenge_data['score'])
        except (ValueError, TypeError): errors.append(f"'{filename}': 'score' ('{challenge_data['score']}') must be an integer.")

    # --- ID Format Validation ---
    challenge_id = challenge_data.get('id')
    if challenge_id and isinstance(challenge_id, str) and not re.match(r'^[a-zA-Z0-9._-]+$', challenge_id):
        errors.append(f"'{filename}': 'id' field '{challenge_id}' contains invalid characters. Use only letters, numbers, hyphens, underscores, periods.")

    # --- Validation Steps ---
    if 'validation' not in challenge_data: pass # Error already added
    elif not isinstance(challenge_data['validation'], list): errors.append(f"'{filename}': 'validation' field must be a list.")
    elif not challenge_data['validation']: errors.append(f"'{filename}': 'validation' list cannot be empty.")
    else:
        for i, step in enumerate(challenge_data['validation']):
            step_label = f"'{filename}' Validation step {i+1}"
            if not isinstance(step, dict): errors.append(f"{step_label}: Must be a dictionary.")
            elif 'type' not in step: errors.append(f"{step_label}: Missing 'type'.")
            else: # Type-specific checks
                step_type = step.get('type')
                if step_type == 'run_command':
                     if 'command' not in step: errors.append(f"{step_label}: Missing 'command'.")
                     if 'success_criteria' in step and not isinstance(step['success_criteria'], dict): errors.append(f"{step_label}: 'success_criteria' must be a dictionary.")
                elif step_type == 'check_service_status':
                     if 'service' not in step: errors.append(f"{step_label}: Missing 'service'.")
                     if 'expected_status' not in step: errors.append(f"{step_label}: Missing 'expected_status'.")
                     elif step['expected_status'] not in ["active", "inactive", "failed"]: errors.append(f"{step_label}: Invalid 'expected_status': {step['expected_status']}. Must be 'active', 'inactive', or 'failed'.")
                     if 'check_enabled' in step and not isinstance(step['check_enabled'], bool): errors.append(f"{step_label}: 'check_enabled' must be true or false.")
                elif step_type == 'check_port_listening':
                     if 'port' not in step: errors.append(f"{step_label}: Missing 'port'.")
                     try: int(step.get('port', 'x'))
                     except (ValueError, TypeError): errors.append(f"{step_label}: 'port' must be an integer.")
                     if 'protocol' in step and step['protocol'] not in ["tcp", "udp"]: errors.append(f"{step_label}: Invalid 'protocol': {step['protocol']}. Must be 'tcp' or 'udp'.")
                     if 'expected_state' not in step: errors.append(f"{step_label}: Missing 'expected_state'.")
                     elif not isinstance(step['expected_state'], bool): errors.append(f"{step_label}: 'expected_state' must be true or false.")
                elif step_type == 'check_file_exists':
                     if 'path' not in step: errors.append(f"{step_label}: Missing 'path'.")
                     if 'expected_state' not in step: errors.append(f"{step_label}: Missing 'expected_state'.")
                     elif not isinstance(step['expected_state'], bool): errors.append(f"{step_label}: 'expected_state' must be true or false.")
                     if 'file_type' in step and step['file_type'] not in ["any", "file", "directory"]: errors.append(f"{step_label}: Invalid 'file_type': {step['file_type']}. Must be 'any', 'file', or 'directory'.")
                     # Add optional checks for owner/group/permissions if implemented later
                elif step_type == 'check_file_contains':
                     if 'path' not in step: errors.append(f"{step_label}: Missing 'path'.")
                     if 'text' not in step and 'matches_regex' not in step: errors.append(f"{step_label}: Missing 'text' or 'matches_regex'.")
                     if 'text' in step and 'matches_regex' in step: errors.append(f"{step_label}: Cannot have both 'text' and 'matches_regex'.")
                     if 'expected_state' not in step: errors.append(f"{step_label}: Missing 'expected_state'.")
                     elif not isinstance(step['expected_state'], bool): errors.append(f"{step_label}: 'expected_state' must be true or false.")
                     if 'matches_regex' in step:
                         try: re.compile(step['matches_regex'])
                         except re.error as regex_err: errors.append(f"{step_label}: Invalid regex '{step['matches_regex']}': {regex_err}")
                else: errors.append(f"{step_label}: Unsupported validation type: '{step_type}'")

    # --- Setup Steps ---
    if 'setup' in challenge_data:
        if not isinstance(challenge_data['setup'], list): errors.append(f"'{filename}': 'setup' field must be a list if present.")
        else:
             for i, step in enumerate(challenge_data['setup']):
                 step_label = f"'{filename}' Setup step {i+1}"
                 if not isinstance(step, dict): errors.append(f"{step_label}: Must be a dictionary.")
                 elif 'type' not in step: errors.append(f"{step_label}: Missing 'type'.")
                 else: # Type-specific checks for setup
                     step_type = step.get('type')
                     if step_type == 'run_command':
                          if 'command' not in step: errors.append(f"{step_label}: Missing 'command'.")
                     # Add checks for 'copy_file', 'ensure_service_status' etc. if implemented
                     # elif step_type == 'copy_file': ...
                     else: errors.append(f"{step_label}: Unsupported setup type: '{step_type}'")

    # --- Hints ---
    if 'hints' in challenge_data:
         if not isinstance(challenge_data['hints'], list): errors.append(f"'{filename}': 'hints' field must be a list if present.")
         else:
             for i, hint in enumerate(challenge_data['hints']):
                 hint_label = f"'{filename}' Hint {i+1}"
                 if not isinstance(hint, dict): errors.append(f"{hint_label}: Must be a dictionary.")
                 elif 'text' not in hint: errors.append(f"{hint_label}: Missing 'text'.")
                 elif 'cost' in hint:
                     try: int(hint['cost'])
                     except (ValueError, TypeError): errors.append(f"{hint_label}: 'cost' ('{hint['cost']}') must be an integer.")

    return errors

def load_challenges_from_dir(challenges_dir: Path) -> Dict[str, Dict]:
    """Loads challenge definitions from YAML files in a directory, performing validation."""
    challenges: Dict[str, Dict] = {}
    if not challenges_dir.is_dir():
        raise ChallengeLoadError(f"Challenges directory not found: '{challenges_dir}'")

    console.print(f"\n:books: Loading challenges from: [blue underline]{challenges_dir.resolve()}[/]")
    yaml_files = sorted(list(challenges_dir.glob('*.yaml')) + list(challenges_dir.glob('*.yml')))

    if not yaml_files:
        console.print(f"  [yellow]:warning: No challenge YAML files (*.yaml, *.yml) found in '{challenges_dir}'.[/]", style="yellow")
        return challenges

    loaded_count = 0
    skipped_count = 0
    for yaml_file in yaml_files:
        try:
            with open(yaml_file, 'r', encoding='utf-8') as f:
                challenge_data = yaml.safe_load(f)

            if not isinstance(challenge_data, dict):
                 console.print(f"  :warning: Skipping '[cyan]{yaml_file.name}[/cyan]': Content is not a valid YAML dictionary (root object).", style="yellow")
                 skipped_count += 1
                 continue

            # Validate structure before processing
            validation_errors = validate_challenge_structure(challenge_data, yaml_file.name)
            if validation_errors:
                # Use Panel for better formatting if Rich is available
                error_panel_content = "\n".join([f"- {e}" for e in validation_errors])
                if RICH_AVAILABLE:
                    console.print(Panel(error_panel_content, title=f"[bold red]Validation Errors in '{yaml_file.name}'[/]", border_style="red", expand=False))
                else:
                    console.print(f"--- Validation Errors in '{yaml_file.name}' ---")
                    console.print(error_panel_content)
                    console.print(f"--- End Errors ---")
                skipped_count += 1
                continue # Skip loading invalid challenges

            challenge_id = challenge_data['id'] # Already validated existence and type

            # Apply defaults and type conversions *after* validation
            challenge_data['score'] = int(challenge_data.get('score', Config.DEFAULT_CHALLENGE_SCORE))
            # Ensure 'hints' exists and cost is int
            processed_hints = []
            for hint in challenge_data.get('hints', []):
                if isinstance(hint, dict) and 'text' in hint:
                    hint['cost'] = int(hint.get('cost', 0))
                    processed_hints.append(hint)
            challenge_data['hints'] = processed_hints
            # Ensure 'setup' is a list
            challenge_data['setup'] = challenge_data.get('setup', [])
            # Ensure 'concepts' is a list
            challenge_data['concepts'] = challenge_data.get('concepts', [])

            if challenge_id in challenges:
                 console.print(f"  :warning: Duplicate challenge ID '[bold yellow]{challenge_id}[/]' found in '[cyan]{yaml_file.name}[/cyan]'. Overwriting previous definition.", style="yellow")

            challenges[challenge_id] = challenge_data
            loaded_count += 1

        except yaml.YAMLError as e:
            console.print(f"  [red]:x: Error parsing YAML file '[cyan]{yaml_file.name}[/cyan]': {e}[/]", style="red")
            skipped_count += 1
        except FileNotFoundError:
             console.print(f"  [red]:x: File '{yaml_file.name}' suddenly not found during loading.[/]", style="red")
             skipped_count += 1
        except Exception as e:
            console.print(f"  [red]:x: An unexpected error occurred loading '{yaml_file.name}': {e}[/]", style="red")
            if RICH_AVAILABLE: console.print_exception(show_locals=False)
            else: traceback.print_exc()
            skipped_count += 1

    # --- Summary ---
    summary = f"Load complete: [green]{loaded_count} challenges loaded[/]"
    if skipped_count > 0:
         summary += f", [yellow]{skipped_count} skipped due to errors[/]."
    else:
         summary += "."
    console.print(summary)
    if skipped_count > 0:
         console.print("[yellow]Please review the errors in the skipped challenge files.[/]", style="yellow")

    return challenges

# --- Part 13: Challenge Validation Step Execution Logic ---
def format_ssh_output(result_dict: Dict[str, Any], command_str: str) -> Any:
    """Formats SSH command results using Rich Panel."""
    max_cmd_len = 60
    display_cmd = command_str if len(command_str) <= max_cmd_len else command_str[:max_cmd_len-3] + "..."
    title = f"[bold]SSH Result[/] [dim]({display_cmd})[/]"

    content = ""
    exit_status = result_dict.get('exit_status', -1)
    exec_error = result_dict.get('error') # Specific execution error (timeout, auth fail, etc.)

    # Determine style based on exit status AND execution error
    if exec_error:
        status_text = f"[red]Execution Error[/]"
        border_style = "red"
    elif exit_status == 0:
        status_text = f"[green]{exit_status}[/]"
        border_style = "green"
    else:
        status_text = f"[red]{exit_status}[/]"
        border_style = "red"

    content += f"[b]Exit Status:[/b] {status_text}\n"
    if exec_error:
         content += f"[b]Error:[/b] [red]{exec_error}[/]\n"


    stdout = result_dict.get('stdout', '')
    stderr = result_dict.get('stderr', '')

    # Truncate long output for display
    max_lines = 10
    max_line_len = 100 # Prevent super long lines messing up panel width
    def truncate_output(output: str) -> str:
        lines = output.splitlines()
        truncated_lines = []
        for line in lines[:max_lines]:
             truncated_lines.append(line[:max_line_len] + ('[dim]...[/]' if len(line) > max_line_len else ''))
        display = "\n".join(truncated_lines)
        if len(lines) > max_lines:
            display += f"\n[dim]... ({len(lines) - max_lines} more lines)[/]"
        return display

    if stdout:
        content += f"\n[b]STDOUT:[/]\n---\n{truncate_output(stdout)}\n---"
    else:
        content += "\n[b]STDOUT:[/b] [i dim](empty)[/]"

    if stderr:
        content += f"\n\n[b]STDERR:[/]\n---\n{truncate_output(stderr)}\n---"
    else:
         content += "\n\n[b]STDERR:[/b] [i dim](empty)[/]"

    # Use Panel if Rich available, otherwise basic string format
    if RICH_AVAILABLE:
        return Panel(Text(content, no_wrap=False), title=title, border_style=border_style, expand=False)
    else:
        return f"--- {title} ---\n{content}\n--- End {title} ---"


def _validate_run_command(step_data: dict, vm_ip: str, ssh_user: str, ssh_key: Path, verbose: bool) -> bool:
    """Validates a 'run_command' step. Returns True on success, raises ChallengeValidationError on failure."""
    command = step_data.get("command")
    if not command: raise ChallengeValidationError(["Missing 'command' in run_command step."])

    criteria = step_data.get("success_criteria", {"exit_status": Config.EXIT_CODE_ACTIVE}) # Default criteria = exit 0

    # Run the command via SSH
    try:
        val_result = run_ssh_command(vm_ip, ssh_user, ssh_key, command, verbose=False)
    except SSHCommandError as e:
        # If SSH itself fails (connection, auth), validation fails
        raise ChallengeValidationError([f"SSH execution failed: {e}"]) from e

    if verbose: console.print(format_ssh_output(val_result, command))

    # Check for SSH command execution errors (e.g., timeout *during* command run)
    if val_result.get('error'):
         raise ChallengeValidationError([f"Command execution error: {val_result['error']}"])

    # Validate based on success_criteria
    step_reasons = []
    actual_status = val_result.get('exit_status', -1)
    actual_stdout = val_result.get('stdout', '')
    actual_stderr = val_result.get('stderr', '')

    # 1. Exit Status Check
    expected_status = criteria.get("exit_status")
    if expected_status is not None and actual_status != expected_status:
        step_reasons.append(f"Expected exit status {expected_status}, but got {actual_status}.")

    # 2. STDOUT Checks
    stdout_equals = criteria.get("stdout_equals")
    if stdout_equals is not None and actual_stdout != stdout_equals:
        step_reasons.append(f"stdout did not exactly match expected value.") # Avoid printing potentially large value

    stdout_contains = criteria.get("stdout_contains")
    if stdout_contains is not None and stdout_contains not in actual_stdout:
         step_reasons.append(f"stdout did not contain expected text.") # Avoid printing

    stdout_regex = criteria.get("stdout_matches_regex")
    if stdout_regex is not None:
        try:
            if not re.search(stdout_regex, actual_stdout, re.MULTILINE):
                step_reasons.append(f"stdout did not match regex '{stdout_regex}'.")
        except re.error as regex_err:
            # This should be caught by challenge validation, but handle defensively
            raise ChallengeValidationError([f"Invalid regex in challenge definition '{stdout_regex}': {regex_err}"])

    # 3. STDERR Checks
    stderr_empty = criteria.get("stderr_empty", False)
    if stderr_empty and actual_stderr:
        step_reasons.append(f"Expected stderr to be empty, but it was not.")

    stderr_contains = criteria.get("stderr_contains")
    if stderr_contains is not None and stderr_contains not in actual_stderr:
        step_reasons.append(f"stderr did not contain expected text.") # Avoid printing

    if step_reasons: raise ChallengeValidationError(step_reasons)
    return True # All criteria met


def _validate_check_service_status(step_data: dict, vm_ip: str, ssh_user: str, ssh_key: Path, verbose: bool) -> bool:
    """Validates a 'check_service_status' step."""
    service_name = step_data.get("service")
    expected_status = step_data.get("expected_status") # required, validated in schema
    check_enabled = step_data.get("check_enabled", False) # Optional bool

    if not service_name or not expected_status: # Should be caught by schema validation
        raise ChallengeValidationError(["Invalid check_service_status step: Missing 'service' or 'expected_status'."])

    step_reasons = []

    # Check Active State using systemctl is-active
    cmd_active = f"systemctl is-active --quiet {shlex.quote(service_name)}"
    try:
        result_active = run_ssh_command(vm_ip, ssh_user, ssh_key, cmd_active, verbose=False)
    except SSHCommandError as e: raise ChallengeValidationError([f"SSH execution failed for active check: {e}"])

    if verbose: console.print(format_ssh_output(result_active, f"systemctl is-active {service_name}"))
    if result_active.get('error'): raise ChallengeValidationError([f"Active check command error: {result_active['error']}"])

    actual_status_code = result_active.get('exit_status', -1)
    actual_status_str = "unknown"
    if actual_status_code == Config.EXIT_CODE_ACTIVE: actual_status_str = "active"
    elif actual_status_code == Config.EXIT_CODE_INACTIVE: actual_status_str = "inactive"
    elif actual_status_code >= Config.EXIT_CODE_FAILED_BASE: actual_status_str = "failed" # Treat other non-zero as failed/not-found

    if actual_status_str != expected_status:
        step_reasons.append(f"Expected service status '{expected_status}', but was '{actual_status_str}'.")

    # Check Enabled State (only if active check passed OR if active check failed but we still need to check enabled)
    if check_enabled:
        cmd_enabled = f"systemctl is-enabled --quiet {shlex.quote(service_name)}"
        try:
            result_enabled = run_ssh_command(vm_ip, ssh_user, ssh_key, cmd_enabled, verbose=False)
        except SSHCommandError as e: raise ChallengeValidationError([f"SSH execution failed for enabled check: {e}"])

        if verbose: console.print(format_ssh_output(result_enabled, f"systemctl is-enabled {service_name}"))
        if result_enabled.get('error'): raise ChallengeValidationError([f"Enabled check command error: {result_enabled['error']}"])

        is_enabled_code = result_enabled.get('exit_status', -1)
        is_enabled = (is_enabled_code == Config.EXIT_CODE_ENABLED)

        if not is_enabled:
            step_reasons.append(f"Expected service to be enabled, but 'systemctl is-enabled' reported it is not (exit code {is_enabled_code}).")

    if step_reasons: raise ChallengeValidationError(step_reasons)
    return True


def _validate_check_port_listening(step_data: dict, vm_ip: str, ssh_user: str, ssh_key: Path, verbose: bool) -> bool:
    """Validates a 'check_port_listening' step."""
    port = step_data.get("port") # required, validated int in schema
    protocol = step_data.get("protocol", "tcp").lower() # default tcp
    expected_state = step_data.get("expected_state") # required bool

    if port is None or expected_state is None: # Should be caught by schema
        raise ChallengeValidationError(["Invalid check_port_listening step: Missing 'port' or 'expected_state'."])

    # Use ss command: -n (numeric), -l (listening), -p (processes), -t (tcp) / -u (udp)
    proto_flag = "t" if protocol == "tcp" else "u"
    # Robust check using awk: checks LISTEN state AND correct port in local address field (handles IPv4/IPv6)
    awk_filter = f'$1 == "LISTEN" && ($4 ~ /[:.][*]?{port}$/ || $4 ~ /\\[[:*]\\]:{port}$/) {{ found=1; exit }} END {{ exit !found }}'
    # Need to escape awk script for shell inside SSH command
    cmd = f"ss -nl{proto_flag}p | awk '{awk_filter}'"

    try:
        result = run_ssh_command(vm_ip, ssh_user, ssh_key, cmd, verbose=False)
    except SSHCommandError as e: raise ChallengeValidationError([f"SSH execution failed for port check: {e}"])

    if verbose: console.print(format_ssh_output(result, f"ss -nl{proto_flag}p | awk '...'"))
    if result.get('error'): raise ChallengeValidationError([f"Port check command error: {result['error']}"])

    # awk exits 0 if found (found=1 -> exit 0), 1 if not found (exit !found -> exit 1)
    is_listening = (result.get('exit_status') == 0)

    if is_listening != expected_state:
        state_str = "listening" if is_listening else "not listening"
        expected_str = "be listening" if expected_state else "not be listening"
        raise ChallengeValidationError([f"Expected port {protocol}/{port} to {expected_str}, but it was {state_str}."])
    return True


def _validate_check_file_exists(step_data: dict, vm_ip: str, ssh_user: str, ssh_key: Path, verbose: bool) -> bool:
    """Validates a 'check_file_exists' step."""
    file_path = step_data.get("path") # required string
    expected_state = step_data.get("expected_state") # required bool
    file_type = step_data.get("file_type", "any").lower() # default any

    if not file_path or expected_state is None: # Should be caught by schema
        raise ChallengeValidationError(["Invalid check_file_exists step: Missing 'path' or 'expected_state'."])

    test_flag_map = {"any": "-e", "file": "-f", "directory": "-d"}
    test_flag = test_flag_map[file_type]
    quoted_path = shlex.quote(file_path)
    cmd = f"test {test_flag} {quoted_path}"

    try:
        result = run_ssh_command(vm_ip, ssh_user, ssh_key, cmd, verbose=False)
    except SSHCommandError as e: raise ChallengeValidationError([f"SSH execution failed for file check: {e}"])

    if verbose: console.print(format_ssh_output(result, f"test {test_flag} ..."))
    if result.get('error'): raise ChallengeValidationError([f"File check command error: {result['error']}"])

    # test command exits 0 if condition is true, 1 otherwise
    exists_and_matches_type = (result.get('exit_status') == 0)

    if exists_and_matches_type != expected_state:
        type_desc = f"a {file_type}" if file_type != "any" else "present"
        state_str = f"exists and is {type_desc}" if exists_and_matches_type else f"does not exist or is not {type_desc}"
        expected_str = f"exist and be {type_desc}" if expected_state else f"not exist or not be {type_desc}"
        raise ChallengeValidationError([f"Path '{file_path}' {state_str}, but expected to {expected_str}."])

    # Optional: Add checks for owner/group/permissions here if specified in step_data
    # Need to use 'stat' command and parse output. E.g.:
    # owner = step_data.get("owner")
    # if owner and exists_and_matches_type: ... run stat command ... check owner ... add reason if mismatch

    return True

def _validate_check_file_contains(step_data: dict, vm_ip: str, ssh_user: str, ssh_key: Path, verbose: bool) -> bool:
    """Validates a 'check_file_contains' step."""
    file_path = step_data.get("path") # required string
    expected_text = step_data.get("text")
    expected_regex = step_data.get("matches_regex")
    expected_state = step_data.get("expected_state") # required bool

    if not file_path or expected_state is None or (expected_text is None and expected_regex is None):
        raise ChallengeValidationError(["Invalid check_file_contains step: Missing 'path', 'expected_state', or ('text'/'matches_regex')."])

    quoted_path = shlex.quote(file_path)

    # First, check if file exists and is readable (important for expected_state=False)
    cmd_check = f"test -r {quoted_path}"
    try:
        result_check = run_ssh_command(vm_ip, ssh_user, ssh_key, cmd_check, verbose=False)
        if result_check.get('error'): raise ChallengeValidationError([f"Readability check command error: {result_check['error']}"])
        file_is_readable = (result_check.get('exit_status') == 0)
    except SSHCommandError as e: raise ChallengeValidationError([f"SSH execution failed for readability check: {e}"])

    if not file_is_readable:
        if expected_state is True: # Expected content, but file not readable/found
            raise ChallengeValidationError([f"File '{file_path}' not found or is not readable."])
        else: # Expected NO content, and file not readable/found = Success
            return True # Correctly does not contain the text

    # File exists and is readable, now check content using grep
    grep_opts = "-q" # Quiet mode (exit status only)
    pattern = ""
    search_desc = ""
    if expected_text is not None:
        grep_opts += "F" # Fixed string
        pattern = expected_text
        search_desc = f"text '{expected_text[:30]}{'...' if len(expected_text)>30 else ''}'"
    elif expected_regex is not None:
        grep_opts += "E" # Extended regex
        pattern = expected_regex
        search_desc = f"regex '{expected_regex[:30]}{'...' if len(expected_regex)>30 else ''}'"

    # Use -- to handle patterns starting with '-'
    cmd_grep = f"grep {grep_opts} -- {shlex.quote(pattern)} {quoted_path}"

    try:
        result_grep = run_ssh_command(vm_ip, ssh_user, ssh_key, cmd_grep, verbose=False)
    except SSHCommandError as e: raise ChallengeValidationError([f"SSH execution failed for grep check: {e}"])

    if verbose: console.print(format_ssh_output(result_grep, f"grep {grep_opts} ..."))
    if result_grep.get('error'): raise ChallengeValidationError([f"Grep command execution error: {result_grep['error']}"])

    # grep exit status: 0=found, 1=not found, >1=error
    grep_exit_status = result_grep.get('exit_status', -1)
    found = (grep_exit_status == 0)
    grep_error = (grep_exit_status > 1)

    if grep_error:
        # This indicates an issue like file disappearing or permissions problem during grep
        raise ChallengeValidationError([f"Error running grep on '{file_path}' (exit status {grep_exit_status}). File might have changed, or permissions issue."])

    if found != expected_state:
        state_str = "found" if found else "not found"
        expected_str = "be found" if expected_state else "not be found"
        raise ChallengeValidationError([f"Expected {search_desc} to {expected_str} in '{file_path}', but it was {state_str}."])
    return True


def execute_validation_step(step_num: int, step_data: dict, vm_ip: str, ssh_user: str, ssh_key: Path, verbose: bool):
    """Executes a single validation step, raising ChallengeValidationError on failure."""
    step_type = step_data.get("type")
    step_title = f"Step {step_num}: [bold cyan]{step_type}[/]"

    validation_functions = {
        "run_command": _validate_run_command,
        "check_service_status": _validate_check_service_status,
        "check_port_listening": _validate_check_port_listening,
        "check_file_exists": _validate_check_file_exists,
        "check_file_contains": _validate_check_file_contains,
    }

    validator_func = validation_functions.get(step_type)
    if not validator_func:
        raise ChallengeValidationError([f"Unsupported validation step type: '{step_type}'"])

    try:
        # Call the appropriate validation function
        # It returns True on success or raises ChallengeValidationError on failure
        validator_func(step_data, vm_ip, ssh_user, ssh_key, verbose)

        # If no exception was raised, the step passed
        success_panel_content = "[green]:heavy_check_mark: Passed[/]"
        if RICH_AVAILABLE:
            console.print(Panel(success_panel_content, title=step_title, border_style="green", expand=False))
        else:
            console.print(f"--- {step_title}: Passed ---")

    except ChallengeValidationError as e:
        # Format and print the failure reason panel
        reason_text = "\n".join([f"- {r}" for r in e.reasons])
        failure_panel_content = f"[bold red]:x: Failed[/]\n{reason_text}"
        if RICH_AVAILABLE:
            console.print(Panel(failure_panel_content, title=step_title, border_style="red", expand=False))
        else:
            console.print(f"--- {step_title}: FAILED ---")
            console.print(reason_text)
            console.print(f"--- End Failure ---")
        raise e # Re-raise to signal failure to the main workflow
    except Exception as ex: # Catch unexpected errors during validation logic itself
         reason = f"Unexpected Error during validation logic: {ex}"
         failure_panel_content = f"[bold red]:x: Failed[/]\n{reason}"
         if RICH_AVAILABLE:
            console.print(Panel(failure_panel_content, title=step_title, border_style="red", expand=False))
            console.print_exception(show_locals=False)
         else:
             console.print(f"--- {step_title}: FAILED ---")
             console.print(reason)
             traceback.print_exc()
             console.print(f"--- End Failure ---")
         # Wrap unexpected error in ChallengeValidationError for consistent handling
         raise ChallengeValidationError([reason]) from ex