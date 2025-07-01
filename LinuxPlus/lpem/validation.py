"""Challenge validation functions."""

import re
import shlex
from pathlib import Path
from typing import Dict, Any, Optional

# Ensure necessary imports are present
from .console import console, Panel, RICH_AVAILABLE # Added RICH_AVAILABLE check
from .config import Config
from .exceptions import ChallengeValidationError, PracticeToolError, SSHCommandError # Added SSHCommandError
from .network import run_ssh_command, format_ssh_output


# --- New Validation Function ---
def _validate_check_history(step_data: dict, vm_ip: str, ssh_user: str, ssh_key: Path, verbose: bool) -> bool:
    """
    Validates shell history based on patterns or disallowed commands.
    NOTE: This method is inherently unreliable and easily bypassed. Use with caution.
    Returns True on success, raises ChallengeValidationError on failure.
    """
    command_pattern = step_data.get("command_pattern") # Regex pattern to search for
    disallowed_commands = step_data.get("disallowed_commands", []) # List of forbidden command strings/patterns
    history_command = step_data.get("history_command", "cat ~/.bash_history 2>/dev/null || history 2>/dev/null") # Command to get history, adaptable
    expected_count = step_data.get("expected_count") # Optional: Check for specific count ">0", "==1", ">=2" etc.

    if not command_pattern and not disallowed_commands:
        raise ChallengeValidationError(["check_history step requires 'command_pattern' or 'disallowed_commands'."])
    if expected_count and not command_pattern:
         raise ChallengeValidationError(["check_history step requires 'command_pattern' when 'expected_count' is specified."])


    note = "[Note: History checks are indicative only and easily bypassed]"

    try:
        if verbose:
            console.print(f"[dim]Executing history retrieval command: `{history_command}`[/]")
        hist_result = run_ssh_command(vm_ip, ssh_user, ssh_key, history_command, verbose=False) # Keep verbose false for run_ssh itself

        # Check for SSH execution errors first
        if hist_result.get('error'):
            raise ChallengeValidationError([f"Failed to retrieve command history: {hist_result['error']}", note])

        # Display formatted output if verbose is enabled for the validation step
        if verbose:
            console.print(format_ssh_output(hist_result, history_command))

        history_content = hist_result.get('stdout', '')
        if not history_content and hist_result.get('exit_status', -1) != 0:
             # If command failed AND produced no output, history might be unavailable
             console.print(f"[yellow]Warning:[/yellow] History command failed (Exit: {hist_result.get('exit_status')}) and produced no output.", style="yellow")
             # Depending on strictness, could raise error here, or allow checks below to fail
             # For now, let checks below handle empty content

        step_reasons = []

        # 1. Check for Required Command Pattern
        if command_pattern:
            try:
                matches = re.findall(command_pattern, history_content, re.MULTILINE)
                actual_count = len(matches)

                # Check against expected_count if provided
                count_check_passed = True
                if expected_count:
                    if isinstance(expected_count, int): # e.g., expected_count: 1
                        if actual_count != expected_count:
                            count_check_passed = False
                            step_reasons.append(f"Expected exactly {expected_count} match(es) for pattern '{command_pattern}', but found {actual_count}.")
                    elif isinstance(expected_count, str): # e.g., expected_count: ">0", ">=1", "<5"
                        match = re.match(r'([><=]+)\s*(\d+)', expected_count)
                        if match:
                            op = match.group(1)
                            num = int(match.group(2))
                            if op == ">" and not actual_count > num: count_check_passed = False
                            elif op == ">=" and not actual_count >= num: count_check_passed = False
                            elif op == "<" and not actual_count < num: count_check_passed = False
                            elif op == "<=" and not actual_count <= num: count_check_passed = False
                            elif op == "==" and not actual_count == num: count_check_passed = False
                            elif op == "!=" and not actual_count != num: count_check_passed = False
                            else:
                                 # Invalid operator, treat as error in challenge definition? Or ignore?
                                 console.print(f"[yellow]Warning:[/yellow] Invalid operator in expected_count: '{expected_count}'. Ignoring count check.", style="yellow")
                        else:
                             console.print(f"[yellow]Warning:[/yellow] Invalid format for expected_count: '{expected_count}'. Ignoring count check.", style="yellow")

                        if not count_check_passed and f"Expected count '{expected_count}'" not in " ".join(step_reasons): # Avoid duplicate reason prefix
                             step_reasons.append(f"Expected count '{expected_count}' for pattern '{command_pattern}', but found {actual_count}.")

                    else: # Invalid type for expected_count
                         console.print(f"[yellow]Warning:[/yellow] Invalid type for expected_count: '{type(expected_count)}'. Ignoring count check.", style="yellow")

                # If no count specified, default is simply > 0 matches needed
                elif actual_count == 0:
                     step_reasons.append(f"Expected command pattern '{command_pattern}' not found in history.")

            except re.error as regex_err:
                raise ChallengeValidationError([f"Invalid regex in command_pattern '{command_pattern}': {regex_err}", note])

        # 2. Check for Disallowed Commands
        if disallowed_commands:
            for disallowed_pattern in disallowed_commands:
                try:
                    # Check if the disallowed pattern exists in the history
                    if re.search(disallowed_pattern, history_content, re.MULTILINE):
                        step_reasons.append(f"Disallowed command pattern '{disallowed_pattern}' found in history.")
                except re.error as regex_err:
                    # Treat error in disallowed pattern as validation failure
                     step_reasons.append(f"Invalid regex in disallowed_commands '{disallowed_pattern}': {regex_err}")


        if step_reasons: raise ChallengeValidationError(step_reasons + [note])
        return True # All history checks passed

    except SSHCommandError as e: # Catch errors from run_ssh_command itself
        raise ChallengeValidationError([f"SSH execution failed during history check: {e}", note])
    except ChallengeValidationError: # Re-raise if already validation error
        raise
    except Exception as e: # Catch unexpected errors during check logic
        raise ChallengeValidationError([f"Unexpected error during history check logic: {e}", note])
    
def _validate_check_journalctl(step_data: dict, vm_ip: str, ssh_user: str, ssh_key: Path, verbose: bool) -> bool:
    """
    Validates systemd journal entries based on specified filters.
    Returns True on success, raises ChallengeValidationError on failure.
    """
    # --- Parameters for journalctl query ---
    # Basic filters:
    service_unit = step_data.get("service") # e.g., "sshd" or "nginx.service"
    syslog_identifier = step_data.get("syslog_identifier") # e.g., "sudo" or "my_app"
    command_name = step_data.get("command_name") # e.g., "useradd" (checks _COMM field)
    message_pattern = step_data.get("message_pattern") # Regex pattern to grep for in messages

    # Time constraints (important to scope the search):
    # Use relative time like "5 minutes ago", "1 hour ago"
    # Or potentially pass challenge start time for absolute timestamp "--since @timestamp"
    since = step_data.get("since", "10 minutes ago") # Default to recent history

    # Expected outcome:
    expected_state = step_data.get("expected_state", True) # Default: Expect entries to exist

    # --- Build journalctl command ---
    cmd_parts = ["journalctl", "--no-pager"] # Base command

    if since:
        # Ensure 'since' value is quoted if it contains spaces
        cmd_parts.extend(["--since", since])

    # Add filters
    if service_unit:
        cmd_parts.extend(["-u", service_unit])
    if syslog_identifier:
        # Matches SYSLOG_IDENTIFIER= field
        cmd_parts.append(f"SYSLOG_IDENTIFIER={syslog_identifier}")
    if command_name:
        # Matches _COMM= field (command name without path)
        cmd_parts.append(f"_COMM={command_name}")

    # Add grep for message pattern if specified
    grep_cmd = ""
    if message_pattern:
        # Use grep -E for extended regex, -q for quiet (exit status only)
        # Pipe journalctl output to grep
        try:
            re.compile(message_pattern) # Validate regex pattern
        except re.error as regex_err:
            raise ChallengeValidationError([f"Invalid regex in message_pattern '{message_pattern}': {regex_err}"])
        # Need to carefully quote the pattern for the shell
        grep_cmd = f" | grep -Eq -- {shlex.quote(message_pattern)}"
    else:
        # If no message pattern, just check if journalctl finds *any* entries matching filters
        # Check exit status of journalctl directly if it found lines
        # Add --quiet to journalctl to make it exit 0 if entries found, 1 otherwise
        cmd_parts.append("--quiet")

    # Combine parts, ensuring proper quoting only where needed (shlex.quote handles spaces)
    # Handles cases like --since "10 minutes ago" correctly
    journal_cmd = " ".join(shlex.quote(part) if any(c in part for c in [' ', '"', "'"]) and not part.startswith(('-', '=')) else part for part in cmd_parts)
    full_cmd = journal_cmd + grep_cmd

    note = "[Note: Journal checks depend on service logging and journald configuration]"

    try:
        if verbose:
            console.print(f"[dim]Executing journal check command: `{full_cmd}`[/]")

        result = run_ssh_command(vm_ip, ssh_user, ssh_key, full_cmd, verbose=False)

        # Check for SSH execution errors first
        if result.get('error'):
            raise ChallengeValidationError([f"Failed to execute journal check command: {result['error']}", note])

        # Display formatted output if verbose is enabled for the validation step
        if verbose:
            console.print(format_ssh_output(result, full_cmd))

        # Determine if entries were found based on exit status
        # grep -q exits 0 if found, 1 if not found, >1 on error
        # journalctl --quiet exits 0 if found, 1 if not found
        exit_status = result.get('exit_status', -1)
        found_entries = (exit_status == 0)
        command_error = (exit_status > 1 and message_pattern) or (exit_status < 0) # Grep error or SSH error

        if command_error:
             stderr_info = result.get('stderr', '')
             raise ChallengeValidationError([f"Error running journal/grep command (Exit: {exit_status}). STDERR: {stderr_info}", note])


        # Compare actual state with expected state
        if found_entries != expected_state:
            filter_desc = []
            if service_unit: filter_desc.append(f"service='{service_unit}'")
            if syslog_identifier: filter_desc.append(f"identifier='{syslog_identifier}'")
            if command_name: filter_desc.append(f"command='{command_name}'")
            if message_pattern: filter_desc.append(f"message matching '{message_pattern}'")
            filter_str = ", ".join(filter_desc) if filter_desc else "any relevant entries"

            state_str = "found" if found_entries else "not found"
            expected_str = "exist" if expected_state else "not exist"
            step_reasons = [f"Expected journal entries for {filter_str} (since '{since}') to {expected_str}, but they were {state_str}.", note]
            raise ChallengeValidationError(step_reasons)

        return True # Validation passed

    except SSHCommandError as e:
        raise ChallengeValidationError([f"SSH execution failed during journal check: {e}", note])
    except ChallengeValidationError: # Re-raise if already validation error
        raise
    except Exception as e: # Catch unexpected errors
        raise ChallengeValidationError([f"Unexpected error during journal check logic: {e}", note])

def _validate_check_audit_log(step_data: dict, vm_ip: str, ssh_user: str, ssh_key: Path, verbose: bool) -> bool:
    """
    Validates auditd log entries based on a rule key.
    NOTE: Requires auditd to be installed, running, and configured with appropriate rules on the VM.
    Returns True on success, raises ChallengeValidationError on failure.
    """
    rule_key = step_data.get("rule_key") # The '-k keyname' used in auditd rules
    # Optional: Add other ausearch filters like '--comm', '--uid', '--syscall' if needed
    since = step_data.get("since", "recent") # Use 'recent', 'today', 'yesterday', or specific time/date
    expected_state = step_data.get("expected_state", True) # Default: Expect entries to exist

    if not rule_key:
        raise ChallengeValidationError(["check_audit_log step requires 'rule_key'."])

    # Construct ausearch command.
    # --input-logs: Necessary if running shortly after event, ensures logs are flushed/read.
    # -k key: Filter by rule key.
    # --start time: Scope the search (e.g., 'recent', 'today').
    # -i: Interpret numeric values into text (e.g., UIDs). Helpful for debugging but not needed for -q.
    # We need to check the exit status, so run without -q first if verbose, then with -q.
    # Command for checking existence (quiet):
    audit_cmd_quiet_parts = ["ausearch", "--input-logs", "-k", rule_key, "--start", since, "-c"] # Using -c for count > 0 check

    # Combine parts, ensuring proper quoting
    audit_cmd_quiet = " ".join(shlex.quote(part) for part in audit_cmd_quiet_parts)

    note = "[Note: Audit log checks depend on auditd service running and correctly configured rules]"

    try:
        if verbose:
            # For verbose mode, run *without* -c first to see entries
            verbose_cmd_parts = ["ausearch", "--input-logs", "-k", rule_key, "--start", since, "-i"]
            verbose_cmd = " ".join(shlex.quote(part) for part in verbose_cmd_parts)
            console.print(f"[dim]Executing verbose audit check command: `{verbose_cmd}`[/]")
            verbose_result = run_ssh_command(vm_ip, ssh_user, ssh_key, verbose_cmd, verbose=False)
            console.print(format_ssh_output(verbose_result, verbose_cmd)) # Show potential entries
            # Then run the count command for the actual check
            console.print(f"[dim]Executing audit check command (count): `{audit_cmd_quiet}`[/]")


        result = run_ssh_command(vm_ip, ssh_user, ssh_key, audit_cmd_quiet, verbose=False) # Always run count check

        # Check for SSH execution errors first
        if result.get('error'):
            raise ChallengeValidationError([f"Failed to execute audit check command: {result['error']}", note])

        # Display count command output if verbose (usually just a number or empty)
        if verbose:
             console.print(format_ssh_output(result, audit_cmd_quiet))


        # Determine if entries were found based on output count
        # ausearch -c outputs a number (count). We expect > 0 if entries exist.
        exit_status = result.get('exit_status', -1)
        stdout = result.get('stdout', '').strip()
        found_entries = False
        command_error = (exit_status != 0) # Any non-zero exit is likely an ausearch error

        if not command_error:
            try:
                 count = int(stdout)
                 if count > 0:
                      found_entries = True
            except (ValueError, TypeError):
                 # If output is not an integer, ausearch likely failed or had no results in a way that didn't change exit code (unlikely but possible)
                 command_error = True

        if command_error:
             stderr_info = result.get('stderr', '')
             raise ChallengeValidationError([f"Error running ausearch command (Exit: {exit_status}). Check auditd status/config. STDOUT: '{stdout}' STDERR: {stderr_info}", note])

        # Compare actual state with expected state
        if found_entries != expected_state:
            state_str = "found" if found_entries else "not found"
            expected_str = "exist" if expected_state else "not exist"
            step_reasons = [f"Expected audit log entries for key '{rule_key}' (since '{since}') to {expected_str}, but they were {state_str}.", note]
            # Optionally add stderr if it contains useful info about why search failed
            stderr_info = result.get('stderr', '').strip()
            if stderr_info:
                 step_reasons.append(f"ausearch STDERR: {stderr_info}")
            raise ChallengeValidationError(step_reasons)

        return True # Validation passed

    except SSHCommandError as e:
        raise ChallengeValidationError([f"SSH execution failed during audit log check: {e}", note])
    except ChallengeValidationError: # Re-raise if already validation error
        raise
    except Exception as e: # Catch unexpected errors
        raise ChallengeValidationError([f"Unexpected error during audit log check logic: {e}", note])

def _validate_check_process(step_data: dict, vm_ip: str, ssh_user: str, ssh_key: Path, verbose: bool) -> bool:
    """
    Validates if a process is running/not running based on its name.
    Optionally checks for the existence of a PID file.
    Returns True on success, raises ChallengeValidationError on failure.
    """
    # --- Parameters for process check ---
    process_name = step_data.get("process_name") # e.g., "sshd", "nginx"
    expected_state = step_data.get("expected_state") # True (running) / False (not running)
    pid_file = step_data.get("pid_file") # Optional: Path to PID file to check existence

    if process_name is None or expected_state is None:
        raise ChallengeValidationError(["check_process step requires 'process_name' and 'expected_state'."])
    if not isinstance(process_name, str) or not process_name:
         raise ChallengeValidationError(["check_process 'process_name' must be a non-empty string."])
    if not isinstance(expected_state, bool):
         raise ChallengeValidationError(["check_process 'expected_state' must be true or false."])
    if pid_file and not isinstance(pid_file, str):
         raise ChallengeValidationError(["check_process 'pid_file' must be a string if provided."])


    # --- Build pgrep command ---
    # Use pgrep: -x for exact match. It exits 0 if found, 1 if not found.
    cmd_pgrep = f"pgrep -x -- {shlex.quote(process_name)}"

    note = "[Note: Process checks rely on pgrep utility on the VM]"
    step_reasons = []

    try:
        # 1. Check Process Running State
        if verbose:
            console.print(f"[dim]Executing process check command: `{cmd_pgrep}`[/]")
        result_pgrep = run_ssh_command(vm_ip, ssh_user, ssh_key, cmd_pgrep, verbose=False)

        if result_pgrep.get('error'):
            raise ChallengeValidationError([f"Failed to execute pgrep command: {result_pgrep['error']}", note])

        if verbose:
            console.print(format_ssh_output(result_pgrep, cmd_pgrep))

        exit_status = result_pgrep.get('exit_status', -1)
        process_is_running = (exit_status == 0) # pgrep exits 0 if found
        pgrep_error = (exit_status > 1) # pgrep exit code 1 means "not found", >1 means error

        if pgrep_error:
             stderr_info = result_pgrep.get('stderr', '')
             step_reasons.append(f"Error running pgrep for '{process_name}' (Exit: {exit_status}). STDERR: {stderr_info}")
             # Cannot reliably determine running state if pgrep failed, so raise error
             raise ChallengeValidationError(step_reasons + [note])

        # Compare actual running state with expected state
        if process_is_running != expected_state:
            state_str = "running" if process_is_running else "not running"
            expected_str = "be running" if expected_state else "not be running"
            step_reasons.append(f"Expected process '{process_name}' to {expected_str}, but it was {state_str}.")
            # If the state check fails, raise immediately
            raise ChallengeValidationError(step_reasons + [note])

        # 2. Optionally Check PID File Existence (only if primary state check passed)
        if pid_file:
             cmd_pid_check = f"test -f {shlex.quote(pid_file)}"
             if verbose:
                  console.print(f"[dim]Checking PID file existence: `{cmd_pid_check}`[/]")

             result_pid = run_ssh_command(vm_ip, ssh_user, ssh_key, cmd_pid_check, verbose=False)

             if result_pid.get('error'):
                  raise ChallengeValidationError([f"Failed to check PID file '{pid_file}': {result_pid['error']}", note])

             if verbose:
                   console.print(format_ssh_output(result_pid, cmd_pid_check))

             pid_file_exists = (result_pid.get('exit_status') == 0) # test -f exits 0 if file exists

             # Usually, if checking a PID file, you expect it to exist *if* the process should be running
             # And expect it *not* to exist if the process should *not* be running
             # Modify this logic if a different expectation is needed
             if pid_file_exists != expected_state:
                  pid_state_str = "exists" if pid_file_exists else "does not exist"
                  pid_expected_str = "exist" if expected_state else "not exist"
                  step_reasons.append(f"Expected PID file '{pid_file}' to {pid_expected_str} (matching expected process state), but it {pid_state_str}.")
                  raise ChallengeValidationError(step_reasons + [note])
             # If we reach here, PID file state matches expected process state
             if verbose:
                 console.print(f"[dim]PID file '{pid_file}' state consistent with expected process state.[/]")


        # If we reach here without raising an error, all checks passed
        return True

    except SSHCommandError as e:
        # Catch SSH errors during either command execution
        raise ChallengeValidationError([f"SSH execution failed during process check: {e}", note])
    except ChallengeValidationError:
        # Re-raise specific validation failures
        raise
    except Exception as e: # Catch unexpected errors
        raise ChallengeValidationError([f"Unexpected error during process check logic: {e}", note])
    
# --- Existing Validation Functions ---
def _validate_run_command(step_data: dict, vm_ip: str, ssh_user: str, ssh_key: Path, verbose: bool) -> bool:
    # ... (existing implementation) ...
    command = step_data.get("command")
    if not command: raise ChallengeValidationError(["Missing 'command' in run_command step."])

    criteria = step_data.get("success_criteria", {"exit_status": Config.EXIT_CODE_ACTIVE}) # Default criteria = exit 0

    try:
        val_result = run_ssh_command(vm_ip, ssh_user, ssh_key, command, verbose=False)
    except SSHCommandError as e: # Make sure to catch SSHCommandError here too
        raise ChallengeValidationError([f"SSH execution failed for command check: {e}"])
    except Exception as e:
        raise ChallengeValidationError([f"Unexpected error running command '{command}': {e}"])

    if verbose: console.print(format_ssh_output(val_result, command))

    if val_result.get('error'):
         raise ChallengeValidationError([f"Command execution error: {val_result['error']}"])

    step_reasons = []
    actual_status = val_result.get('exit_status', -1)
    actual_stdout = val_result.get('stdout', '')
    actual_stderr = val_result.get('stderr', '')

    # 1. Exit Status Check
    expected_status = criteria.get("exit_status")
    if expected_status is not None:
        try:
             expected_status_int = int(expected_status)
             if actual_status != expected_status_int:
                 step_reasons.append(f"Expected exit status {expected_status_int}, but got {actual_status}.")
        except (ValueError, TypeError):
             raise ChallengeValidationError([f"Invalid non-integer 'exit_status' in success_criteria: {expected_status}"])


    # 2. STDOUT Checks
    stdout_equals = criteria.get("stdout_equals")
    if stdout_equals is not None and actual_stdout != stdout_equals:
        # Avoid printing potentially large/sensitive values in error message by default
        step_reasons.append(f"stdout did not exactly match expected value.")
        if verbose: # Optionally show diff if verbose
             # You could add a diff library here if needed, or just show actual vs expected
             step_reasons.append(f"  Expected: '{stdout_equals}'")
             step_reasons.append(f"  Actual:   '{actual_stdout}'")


    stdout_contains = criteria.get("stdout_contains")
    if stdout_contains is not None and stdout_contains not in actual_stdout:
         step_reasons.append(f"stdout did not contain expected text: '{stdout_contains}'")

    stdout_matches_regex = criteria.get("stdout_matches_regex")
    if stdout_matches_regex is not None:
        try:
            if not re.search(stdout_matches_regex, actual_stdout, re.MULTILINE):
                step_reasons.append(f"stdout did not match regex '{stdout_matches_regex}'.")
        except re.error as regex_err:
            raise ChallengeValidationError([f"Invalid regex in challenge definition '{stdout_matches_regex}': {regex_err}"])

    # 3. STDERR Checks
    stderr_empty = criteria.get("stderr_empty", False) # Default is False, allow stderr
    if stderr_empty and actual_stderr:
        step_reasons.append(f"Expected stderr to be empty, but it was not.")
        if verbose:
             step_reasons.append(f"  Actual STDERR: '{actual_stderr}'")


    stderr_contains = criteria.get("stderr_contains")
    if stderr_contains is not None and stderr_contains not in actual_stderr:
        step_reasons.append(f"stderr did not contain expected text: '{stderr_contains}'")

    # 4. Explicitly check for *no* stdout/stderr if requested
    stdout_empty = criteria.get("stdout_empty", False)
    if stdout_empty and actual_stdout:
        step_reasons.append(f"Expected stdout to be empty, but it was not.")
        if verbose:
             step_reasons.append(f"  Actual STDOUT: '{actual_stdout}'")

    if step_reasons: raise ChallengeValidationError(step_reasons)
    return True

def _validate_check_service_status(step_data: dict, vm_ip: str, ssh_user: str, ssh_key: Path, verbose: bool) -> bool:
    # ... (existing implementation) ...
    service_name = step_data.get("service")
    expected_status = step_data.get("expected_status")
    check_enabled = step_data.get("check_enabled") # Allow None, False, True

    if not service_name or not expected_status:
        raise ChallengeValidationError(["Invalid check_service_status step: Missing 'service' or 'expected_status'."])
    if expected_status not in ["active", "inactive", "failed"]:
         raise ChallengeValidationError([f"Invalid 'expected_status' value: {expected_status}. Must be 'active', 'inactive', or 'failed'."])


    step_reasons = []

    # Check Active State
    cmd_active = f"systemctl is-active --quiet {shlex.quote(service_name)}"
    try:
        result_active = run_ssh_command(vm_ip, ssh_user, ssh_key, cmd_active, verbose=False)
    except SSHCommandError as e:
        raise ChallengeValidationError([f"SSH execution failed for active check: {e}"])
    except Exception as e:
        raise ChallengeValidationError([f"Unexpected error during active check for '{service_name}': {e}"])


    if verbose: console.print(format_ssh_output(result_active, cmd_active))
    if result_active.get('error'):
        raise ChallengeValidationError([f"Active check command error: {result_active['error']}"])

    actual_status_code = result_active.get('exit_status', -1)
    # Map exit code to string status expected in YAML
    actual_status_str = "unknown"
    if actual_status_code == Config.EXIT_CODE_ACTIVE: actual_status_str = "active"
    # systemd's is-active returns 3 for inactive state.
    elif actual_status_code == Config.EXIT_CODE_INACTIVE: actual_status_str = "inactive"
    # Treat other non-zero as likely failed/error state, map to 'failed' for simplicity
    elif actual_status_code != 0: actual_status_str = "failed"

    if actual_status_str != expected_status:
        step_reasons.append(f"Expected service status '{expected_status}', but was '{actual_status_str}' (is-active exit code: {actual_status_code}).")

    # Check Enabled State (only if requested via check_enabled: true or false)
    if check_enabled is not None: # Only run if check_enabled is explicitly true or false
        cmd_enabled = f"systemctl is-enabled --quiet {shlex.quote(service_name)}"
        try:
            result_enabled = run_ssh_command(vm_ip, ssh_user, ssh_key, cmd_enabled, verbose=False)
        except SSHCommandError as e:
            raise ChallengeValidationError([f"SSH execution failed for enabled check: {e}"])
        except Exception as e:
             raise ChallengeValidationError([f"Unexpected error during enabled check for '{service_name}': {e}"])


        if verbose: console.print(format_ssh_output(result_enabled, cmd_enabled))
        if result_enabled.get('error'):
            raise ChallengeValidationError([f"Enabled check command error: {result_enabled['error']}"])

        is_enabled_code = result_enabled.get('exit_status', -1)
        # is-enabled: 0 = enabled, 1 = disabled/static/masked etc.
        # Map code to boolean
        actual_enabled_bool = (is_enabled_code == Config.EXIT_CODE_ENABLED)

        if actual_enabled_bool != check_enabled:
            expected_enable_str = "enabled" if check_enabled else "not enabled"
            actual_enable_str = "enabled" if actual_enabled_bool else "not enabled"
            step_reasons.append(f"Expected service to be {expected_enable_str}, but it was {actual_enable_str} (is-enabled exit code: {is_enabled_code}).")

    if step_reasons: raise ChallengeValidationError(step_reasons)
    return True

def _validate_check_port_listening(step_data: dict, vm_ip: str, ssh_user: str, ssh_key: Path, verbose: bool) -> bool:
    # ... (existing implementation - seems robust) ...
    port = step_data.get("port")
    protocol = step_data.get("protocol", "tcp").lower()
    expected_state = step_data.get("expected_state")
    address = step_data.get("address") # Optional: Specific address to check (e.g., '127.0.0.1', '0.0.0.0')


    if port is None or expected_state is None:
        raise ChallengeValidationError(["Invalid check_port_listening step: Missing 'port' or 'expected_state'."])
    if protocol not in ["tcp", "udp"]:
         raise ChallengeValidationError([f"Invalid protocol '{protocol}'. Must be 'tcp' or 'udp'."])
    try:
         port_int = int(port)
         if not 0 < port_int < 65536: raise ValueError("Port out of range")
    except (ValueError, TypeError):
         raise ChallengeValidationError([f"Invalid port number: {port}. Must be an integer between 1 and 65535."])


    # Use ss command: -n (numeric), -l (listening), p (processes), t (tcp) / u (udp)
    proto_flag = "t" if protocol == "tcp" else "u"
    # Refined awk filter:
    # - Checks state is LISTEN
    # - Checks correct port number (handles IPv4 *:port, addr:port and IPv6 [::]:port, [addr]:port)
    # - Optionally filters by specific local address if 'address' is provided
    awk_script = f"""
    BEGIN {{ found=0 }}
    $1 == "LISTEN" {{
        split($4, parts, ":");
        port_in_addr = parts[length(parts)]; # Get last part after ':' which should be port
        # Handle IPv6 bracket notation for address matching
        addr_part = $4;
        sub(/:[^:]+$/, "", addr_part); # Remove :port part to get address
        gsub(/\[|\]/, "", addr_part); # Remove brackets for IPv6 matching

        # Basic port check first
        if (port_in_addr == "{port}") {{
            # Check address if specified
            addr_match = 1; # Assume match if no address specified
            if ("{address}" != "") {{
                 # Check if addr_part matches specified address or wildcard *
                 if !(addr_part == "{address}" || addr_part == "*" || addr_part == "::" || addr_part == "0.0.0.0") {{
                     addr_match = 0;
                 }}
            }}
            if (addr_match) {{
                 found=1;
                 exit; # Exit awk early if match found
            }}
        }}
    }}
    END {{ exit !found }}
    """
    # Remove newlines and escape single quotes for shell execution
    awk_oneline = " ".join(awk_script.splitlines()).strip().replace("'", "'\\''")
    cmd = f"ss -nl{proto_flag}p | awk '{awk_oneline}'"


    try:
        if verbose:
            console.print(f"[dim]Executing port check command: `{cmd}`[/]")
        result = run_ssh_command(vm_ip, ssh_user, ssh_key, cmd, verbose=False)
    except SSHCommandError as e:
        raise ChallengeValidationError([f"SSH execution failed for port check: {e}"])
    except Exception as e:
        raise ChallengeValidationError([f"Unexpected error during port check execution: {e}"])


    if verbose: console.print(format_ssh_output(result, f"ss/awk check for {protocol}/{port}"))
    if result.get('error'):
        raise ChallengeValidationError([f"Port check command error: {result['error']}"])

    # awk exits 0 if found, 1 if not found
    is_listening = (result.get('exit_status') == 0)

    if is_listening != expected_state:
        state_str = "listening" if is_listening else "not listening"
        expected_str = "be listening" if expected_state else "not be listening"
        addr_str = f" on address {address}" if address else ""
        raise ChallengeValidationError([f"Expected port {protocol}/{port}{addr_str} to {expected_str}, but it was {state_str}."])
    return True

def _validate_check_file_exists(step_data: dict, vm_ip: str, ssh_user: str, ssh_key: Path, verbose: bool) -> bool:
    # ... (existing implementation seems okay, maybe add owner/group/perm checks later) ...
    file_path = step_data.get("path")
    expected_state = step_data.get("expected_state")
    file_type = step_data.get("file_type", "any").lower() # any, file, directory
    owner = step_data.get("owner") # Optional string (user name or uid)
    group = step_data.get("group") # Optional string (group name or gid)
    permissions = step_data.get("permissions") # Optional string (octal like "0644")

    if not file_path or expected_state is None:
        raise ChallengeValidationError(["Invalid check_file_exists step: Missing 'path' or 'expected_state'."])
    if file_type not in ["any", "file", "directory"]:
         raise ChallengeValidationError([f"Invalid 'file_type' value: {file_type}. Must be 'any', 'file', or 'directory'."])
    if permissions and not re.match(r"^[0-7]{3,4}$", str(permissions)): # Basic check for 3 or 4 octal digits
         raise ChallengeValidationError([f"Invalid 'permissions' format: {permissions}. Must be octal string e.g., '0644'."])


    test_flag_map = {"any": "-e", "file": "-f", "directory": "-d"}
    test_flag = test_flag_map[file_type]
    quoted_path = shlex.quote(file_path)
    cmd_exists = f"test {test_flag} {quoted_path}"

    try:
        result_exists = run_ssh_command(vm_ip, ssh_user, ssh_key, cmd_exists, verbose=False)
    except SSHCommandError as e:
        raise ChallengeValidationError([f"SSH execution failed for file existence check: {e}"])
    except Exception as e:
        raise ChallengeValidationError([f"Unexpected error during file existence check: {e}"])


    if verbose: console.print(format_ssh_output(result_exists, cmd_exists))
    if result_exists.get('error'):
        raise ChallengeValidationError([f"File existence check command error: {result_exists['error']}"])

    # test command exits 0 if condition is true, 1 otherwise
    exists_and_matches_type = (result_exists.get('exit_status') == 0)

    step_reasons = []
    if exists_and_matches_type != expected_state:
        type_desc = f"a {file_type}" if file_type != "any" else "present"
        state_str = f"exists and is {type_desc}" if exists_and_matches_type else f"does not exist or is not {type_desc}"
        expected_str = f"exist and be {type_desc}" if expected_state else f"not exist or not be {type_desc}"
        step_reasons.append(f"Path '{file_path}' {state_str}, but expected to {expected_str}.")
        # If existence check failed, no point checking owner/group/perms
        raise ChallengeValidationError(step_reasons)

    # --- Owner/Group/Permission Checks (only if file exists as expected) ---
    if exists_and_matches_type and (owner or group or permissions):
         # Use stat command for reliable checks
         # %U = user name, %u = uid, %G = group name, %g = gid, %a = octal perms
         stat_format = "%U:%u:%G:%g:%a"
         cmd_stat = f"stat --format='{stat_format}' {quoted_path}"
         try:
             result_stat = run_ssh_command(vm_ip, ssh_user, ssh_key, cmd_stat, verbose=False)
             if verbose: console.print(format_ssh_output(result_stat, cmd_stat))

             if result_stat.get('error'):
                 raise ChallengeValidationError([f"Stat command execution error: {result_stat['error']}"])
             if result_stat.get('exit_status', -1) != 0:
                  raise ChallengeValidationError([f"Stat command failed (Exit: {result_stat.get('exit_status')}) for path '{file_path}'."])

             stat_output = result_stat.get('stdout', '').strip()
             parts = stat_output.split(':')
             if len(parts) == 5:
                 actual_owner_name, actual_owner_uid, actual_group_name, actual_group_gid, actual_perms_octal = parts

                 # Check Owner
                 if owner and not (owner == actual_owner_name or owner == actual_owner_uid):
                      step_reasons.append(f"Expected owner '{owner}', but found '{actual_owner_name}' (UID: {actual_owner_uid}).")
                 # Check Group
                 if group and not (group == actual_group_name or group == actual_group_gid):
                      step_reasons.append(f"Expected group '{group}', but found '{actual_group_name}' (GID: {actual_group_gid}).")
                 # Check Permissions (compare last 3 or 4 digits depending on input format)
                 if permissions:
                      # Normalize actual permissions (sometimes stat includes leading 0 for FS type)
                      actual_perms_normalized = actual_perms_octal.lstrip('0')
                      # Normalize expected permissions
                      expected_perms_str = str(permissions).lstrip('0')
                      if len(expected_perms_str) == 3: # e.g. 644
                          if actual_perms_normalized[-3:] != expected_perms_str:
                              step_reasons.append(f"Expected permissions '{permissions}', but found '{actual_perms_octal}'.")
                      elif len(expected_perms_str) == 4: # e.g. 0755 or 4755 (sticky/suid/sgid)
                           if actual_perms_normalized != expected_perms_str:
                                step_reasons.append(f"Expected permissions '{permissions}', but found '{actual_perms_octal}'.")
                      else: # Should be caught by earlier regex, but defensive check
                            step_reasons.append(f"Invalid expected permissions format '{permissions}' during comparison.")


             else:
                 step_reasons.append(f"Unexpected output format from stat command: {stat_output}")

         except SSHCommandError as e:
             step_reasons.append(f"SSH execution failed for stat check: {e}")
         except Exception as e:
             step_reasons.append(f"Unexpected error during stat check: {e}")

    if step_reasons: raise ChallengeValidationError(step_reasons)
    return True

def _validate_check_file_contains(step_data: dict, vm_ip: str, ssh_user: str, ssh_key: Path, verbose: bool) -> bool:
    # ... (existing implementation seems okay) ...
    file_path = step_data.get("path")
    expected_text = step_data.get("text")
    expected_regex = step_data.get("matches_regex")
    expected_state = step_data.get("expected_state")

    if not file_path or expected_state is None or (expected_text is None and expected_regex is None):
        raise ChallengeValidationError(["Invalid check_file_contains step: Missing 'path', 'expected_state', or ('text'/'matches_regex')."])
    if expected_text is not None and expected_regex is not None:
         raise ChallengeValidationError(["Invalid check_file_contains step: Cannot have both 'text' and 'matches_regex'."])


    quoted_path = shlex.quote(file_path)

    # Check readability first (especially important for expected_state=False)
    # Use 'test -r' which checks read permission for the executing user
    cmd_check = f"test -r {quoted_path}"
    try:
        result_check = run_ssh_command(vm_ip, ssh_user, ssh_key, cmd_check, verbose=False)
        if verbose: console.print(format_ssh_output(result_check, cmd_check))
        if result_check.get('error'):
            raise ChallengeValidationError([f"Readability check command error: {result_check['error']}"])
        file_is_readable = (result_check.get('exit_status') == 0)
    except SSHCommandError as e:
        raise ChallengeValidationError([f"SSH execution failed for readability check: {e}"])
    except Exception as e:
        raise ChallengeValidationError([f"Unexpected error during readability check: {e}"])


    if not file_is_readable:
        if expected_state is True: # Expected content, but file not readable/found
            raise ChallengeValidationError([f"File '{file_path}' not found or is not readable by user '{ssh_user}'."])
        else: # Expected NO content, and file not readable/found = Success for this check
            return True # Correctly does not contain the text as file isn't readable/present

    # File exists and is readable, now check content using grep
    grep_opts = ["-q"] # Quiet mode (exit status only)
    pattern = ""
    search_desc = ""
    if expected_text is not None:
        grep_opts.append("-F") # Fixed string
        pattern = expected_text
        search_desc = f"text '{expected_text[:30]}{'...' if len(expected_text)>30 else ''}'"
    elif expected_regex is not None:
        grep_opts.append("-E") # Extended regex
        pattern = expected_regex
        search_desc = f"regex '{expected_regex[:30]}{'...' if len(expected_regex)>30 else ''}'"
        try:
            re.compile(pattern) # Pre-validate regex syntax
        except re.error as regex_err:
             raise ChallengeValidationError([f"Invalid regex pattern '{pattern}' in check_file_contains step: {regex_err}"])


    # Use list for command parts to handle pattern quoting robustly
    cmd_grep_parts = ["grep"] + grep_opts + ["--", pattern, quoted_path]
    cmd_grep_str = " ".join(shlex.quote(part) for part in cmd_grep_parts) # For display/logging


    try:
        # Execute using the list form if run_ssh_command supports it, otherwise join carefully
        # Assuming run_ssh_command takes a string for now:
        cmd_to_run = cmd_grep_str
        if verbose:
            console.print(f"[dim]Executing content check command: `{cmd_to_run}`[/]")
        result_grep = run_ssh_command(vm_ip, ssh_user, ssh_key, cmd_to_run, verbose=False)

    except SSHCommandError as e:
        raise ChallengeValidationError([f"SSH execution failed for grep check: {e}"])
    except Exception as e:
        raise ChallengeValidationError([f"Unexpected error during grep check execution: {e}"])


    if verbose: console.print(format_ssh_output(result_grep, cmd_grep_str))
    if result_grep.get('error'):
        raise ChallengeValidationError([f"Grep command execution error: {result_grep['error']}"])

    # grep exit status: 0=found, 1=not found, >1=error
    grep_exit_status = result_grep.get('exit_status', -1)
    found = (grep_exit_status == 0)
    grep_error = (grep_exit_status > 1)

    if grep_error:
        stderr_info = result_grep.get('stderr', '')
        raise ChallengeValidationError([f"Error running grep on '{file_path}' (exit status {grep_exit_status}). File might have changed, or permissions issue. STDERR: {stderr_info}"])

    if found != expected_state:
        state_str = "found" if found else "not found"
        expected_str = "be found" if expected_state else "not be found"
        raise ChallengeValidationError([f"Expected {search_desc} to {expected_str} in '{file_path}', but it was {state_str}."])
    return True
def _validate_check_lvm_state(step_data: dict, vm_ip: str, ssh_user: str, ssh_key: Path, verbose: bool) -> bool:
    """
    Validates LVM state (PVs, VGs, LVs) based on specified criteria.
    Returns True on success, raises ChallengeValidationError on failure.
    """
    check_type = step_data.get("check_type")
    expected_state = step_data.get("expected_state", True) # Default: expect existence/match
    step_reasons = []
    note = "[Note: LVM checks require lvm2 package installed on the VM]"

    if not check_type:
        raise ChallengeValidationError(["'check_lvm_state' step requires 'check_type'."])

    cmd = ""
    check_desc = ""

    try:
        # --- Build Command Based on Check Type ---
        if check_type == "pv_exists":
            device = step_data.get("device")
            if not device: raise ChallengeValidationError(["'pv_exists' check requires 'device'."])
            quoted_device = shlex.quote(device)
            cmd = f"pvs --noheadings -o pv_name {quoted_device}"
            check_desc = f"PV existence for device '{device}'"
        elif check_type == "vg_exists":
            vg_name = step_data.get("vg_name")
            if not vg_name: raise ChallengeValidationError(["'vg_exists' check requires 'vg_name'."])
            quoted_vg = shlex.quote(vg_name)
            cmd = f"vgs --noheadings -o vg_name {quoted_vg}"
            check_desc = f"VG existence for VG '{vg_name}'"
        elif check_type == "lv_exists":
            vg_name = step_data.get("vg_name")
            lv_name = step_data.get("lv_name")
            if not vg_name or not lv_name: raise ChallengeValidationError(["'lv_exists' check requires 'vg_name' and 'lv_name'."])
            quoted_vg = shlex.quote(vg_name)
            quoted_lv = shlex.quote(lv_name)
            lv_path = f"{quoted_vg}/{quoted_lv}" # LVM path format
            cmd = f"lvs --noheadings -o lv_name {lv_path}"
            check_desc = f"LV existence for LV '{lv_path}'"
        elif check_type == "lv_size":
            vg_name = step_data.get("vg_name")
            lv_name = step_data.get("lv_name")
            min_size_mb = step_data.get("min_size_mb")
            max_size_mb = step_data.get("max_size_mb")
            exact_size_mb = step_data.get("exact_size_mb") # Optional alternative

            if not vg_name or not lv_name: raise ChallengeValidationError(["'lv_size' check requires 'vg_name' and 'lv_name'."])
            if min_size_mb is None and max_size_mb is None and exact_size_mb is None:
                raise ChallengeValidationError(["'lv_size' check requires 'min_size_mb'/'max_size_mb' or 'exact_size_mb'."])

            quoted_vg = shlex.quote(vg_name)
            quoted_lv = shlex.quote(lv_name)
            lv_path = f"{quoted_vg}/{quoted_lv}"
            # Get size in megabytes using --units m
            cmd = f"lvs --noheadings --units m -o lv_size {lv_path}"
            size_desc = []
            if exact_size_mb is not None: size_desc.append(f"exactly {exact_size_mb}MB")
            if min_size_mb is not None: size_desc.append(f">= {min_size_mb}MB")
            if max_size_mb is not None: size_desc.append(f"<= {max_size_mb}MB")
            check_desc = f"LV size for '{lv_path}' (expected {' and '.join(size_desc)})"
        else:
            raise ChallengeValidationError([f"Unsupported 'check_type' for check_lvm_state: '{check_type}'"])

        # --- Execute Command ---
        if verbose:
            console.print(f"[dim]Executing LVM check command: `{cmd}`[/]")
        result = run_ssh_command(vm_ip, ssh_user, ssh_key, cmd, verbose=False)

        if result.get('error'):
            raise ChallengeValidationError([f"LVM check command execution error: {result['error']}", note])
        if verbose:
            console.print(format_ssh_output(result, f"LVM Check: {check_type}"))

        # --- Process Results ---
        exit_status = result.get('exit_status', -1)
        stdout = result.get('stdout', '').strip()
        stderr = result.get('stderr', '').strip() # Check stderr for LVM tool errors

        # Generic LVM command errors (often exit 5 for "not found")
        if exit_status != 0:
             # Treat non-zero exit as "not found" or failed for existence checks
             if check_type in ["pv_exists", "vg_exists", "lv_exists"]:
                 component_found = False
             # For size check, non-zero means LV likely doesn't exist
             elif check_type == "lv_size":
                 step_reasons.append(f"Could not retrieve size for LV '{lv_path}'. Does it exist? LVM tool exit code: {exit_status}. STDERR: {stderr}")
                 raise ChallengeValidationError(step_reasons + [note])
             else: # Should not happen if check_type is validated above
                 step_reasons.append(f"LVM command failed with exit code {exit_status}. STDERR: {stderr}")
                 raise ChallengeValidationError(step_reasons + [note])
        else:
            # Exit code 0 generally means found for existence checks
            if check_type in ["pv_exists", "vg_exists", "lv_exists"]:
                 component_found = True
            # For size check, need to parse the output
            elif check_type == "lv_size":
                 try:
                     # Output is like " 100.00m", remove unit and whitespace
                     size_str = stdout.lower().replace('m', '').strip()
                     actual_size_mb = float(size_str)

                     # Perform size comparisons
                     size_ok = True
                     if exact_size_mb is not None and abs(actual_size_mb - float(exact_size_mb)) > 0.1: # Allow small float tolerance
                          size_ok = False
                          step_reasons.append(f"Expected LV size exactly {exact_size_mb}MB, but found {actual_size_mb:.2f}MB.")
                     else: # Check min/max if exact not specified or matched
                         if min_size_mb is not None and actual_size_mb < float(min_size_mb):
                             size_ok = False
                             step_reasons.append(f"LV size {actual_size_mb:.2f}MB is less than minimum requirement ({min_size_mb}MB).")
                         if max_size_mb is not None and actual_size_mb > float(max_size_mb):
                             size_ok = False
                             step_reasons.append(f"LV size {actual_size_mb:.2f}MB is greater than maximum requirement ({max_size_mb}MB).")

                     if not size_ok:
                          raise ChallengeValidationError(step_reasons + [note])
                     # If size is okay, validation passes for this type
                     return True # Size check successful

                 except (ValueError, TypeError) as parse_err:
                      step_reasons.append(f"Could not parse LVM size output '{stdout}': {parse_err}")
                      raise ChallengeValidationError(step_reasons + [note])

        # --- Final check for existence types ---
        if check_type in ["pv_exists", "vg_exists", "lv_exists"]:
            if component_found != expected_state:
                state_str = "found" if component_found else "not found"
                expected_str = "exist" if expected_state else "not exist"
                step_reasons.append(f"Expected {check_desc} to {expected_str}, but it was {state_str}.")
                if exit_status != 0: # Add stderr if LVM command failed
                     step_reasons.append(f"LVM tool exit code: {exit_status}. STDERR: {stderr}")
                raise ChallengeValidationError(step_reasons + [note])
            # If state matches expected, validation passes
            return True

    except SSHCommandError as e:
        raise ChallengeValidationError([f"SSH execution failed during LVM check: {e}", note])
    except ChallengeValidationError: # Re-raise known validation errors
        raise
    except Exception as e: # Catch unexpected errors
        raise ChallengeValidationError([f"Unexpected error during LVM check logic: {e}", note])


# --- Main Execution Function ---
def execute_validation_step(step_num: int, step_data: dict, vm_ip: str, ssh_user: str, ssh_key: Path, verbose: bool):
    """Executes a single validation step, raising ChallengeValidationError on failure."""
    step_type = step_data.get("type")
    step_title = f"Step {step_num}: [bold cyan]{step_type}[/]"

    # Map step type to validation function
    validation_functions = {
        "run_command": _validate_run_command,
        "check_service_status": _validate_check_service_status,
        "check_port_listening": _validate_check_port_listening,
        "check_file_exists": _validate_check_file_exists,
        "check_file_contains": _validate_check_file_contains,
        "check_history": _validate_check_history,           # <-- ADDED
        "check_journalctl": _validate_check_journalctl,     # <-- ADDED
        "check_audit_log": _validate_check_audit_log,       # <-- ADDED
        "check_lvm_state": _validate_check_lvm_state,       # <-- Ensure this exists
    }

    validator_func = validation_functions.get(step_type)
    if not validator_func:
        # Provide more context in the error message
        raise ChallengeValidationError([f"Unsupported validation step type: '{step_type}' in step {step_num}"])

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
         reason = f"Unexpected Error during validation logic for step type '{step_type}': {ex}"
         failure_panel_content = f"[bold red]:x: Failed[/]\n{reason}"
         if RICH_AVAILABLE:
            console.print(Panel(failure_panel_content, title=step_title, border_style="red", expand=False))
            # Optionally include traceback for unexpected errors
            # console.print_exception(show_locals=False)
         else:
             console.print(f"--- {step_title}: FAILED ---")
             console.print(reason)
             import traceback
             traceback.print_exc()
             console.print(f"--- End Failure ---")
         # Wrap unexpected error in ChallengeValidationError for consistent handling
         raise ChallengeValidationError([reason]) from ex