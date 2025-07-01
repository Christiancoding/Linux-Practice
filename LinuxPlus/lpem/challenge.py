"""Challenge loading and management functions."""
import re
import yaml
from pathlib import Path
from typing import Dict, List, Any

from .console import console, Table, Panel, Syntax
from .exceptions import ChallengeLoadError
from .config import Config

# Define supported validation types centrally
# Keep this list synchronized with functions in validation.py
SUPPORTED_VALIDATION_TYPES = [
    "run_command", "check_service_status", "check_port_listening",
    "check_file_exists", "check_file_contains", "check_history",
    "check_journalctl", "check_audit_log", "check_lvm_state"
]

# Define supported setup types centrally
SUPPORTED_SETUP_TYPES = [
    "run_command", "ensure_package_installed"
    # Add "copy_file", "ensure_service_status", "ensure_disk_available" etc. when implemented
]

def _validate_steps_list(steps: Any, key_name: str, filename: str, errors: List[str], supported_types: List[str]):
    """Helper function to validate a list of setup or validation steps."""
    if not isinstance(steps, list):
        errors.append(f"'{filename}': '{key_name}' field must be a list.")
        return
    # Allow empty process_validation_checks or setup, but not final_state_checks or validation
    if not steps and key_name not in ['process_validation_checks', 'setup']:
        errors.append(f"'{filename}': '{key_name}' list cannot be empty.")
        return # Return if empty, no steps to validate

    for i, step in enumerate(steps):
        step_label = f"'{filename}' {key_name} step {i+1}"
        if not isinstance(step, dict):
            errors.append(f"{step_label}: Must be a dictionary.")
            continue # Skip further checks on this step if not a dict
        if 'type' not in step:
            errors.append(f"{step_label}: Missing required key 'type'.")
            continue # Cannot validate further without type

        step_type = step.get('type')
        if not isinstance(step_type, str):
             errors.append(f"{step_label}: 'type' must be a string.")
             continue

        if step_type not in supported_types:
            errors.append(f"{step_label}: Unsupported type: '{step_type}'. Supported: {', '.join(supported_types)}")
            continue # Skip specific checks for unsupported type

        # --- Type-specific parameter checks ---
        if key_name in ['validation', 'final_state_checks', 'process_validation_checks']: # Validation step checks
            if step_type == 'run_command':
                 if 'command' not in step: errors.append(f"{step_label}: Missing 'command'.")
                 if 'success_criteria' in step and not isinstance(step['success_criteria'], dict): errors.append(f"{step_label}: 'success_criteria' must be a dictionary.")
                 # Add deeper checks for success_criteria keys/types if desired
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
                 # Add optional checks for owner/group/permissions types if implemented later
            elif step_type == 'check_file_contains':
                 if 'path' not in step: errors.append(f"{step_label}: Missing 'path'.")
                 if 'text' not in step and 'matches_regex' not in step: errors.append(f"{step_label}: Missing 'text' or 'matches_regex'.")
                 if 'text' in step and 'matches_regex' in step: errors.append(f"{step_label}: Cannot have both 'text' and 'matches_regex'.")
                 if 'expected_state' not in step: errors.append(f"{step_label}: Missing 'expected_state'.")
                 elif not isinstance(step['expected_state'], bool): errors.append(f"{step_label}: 'expected_state' must be true or false.")
                 if 'matches_regex' in step:
                     try: re.compile(step['matches_regex'])
                     except re.error as regex_err: errors.append(f"{step_label}: Invalid regex '{step['matches_regex']}': {regex_err}")
            elif step_type == 'check_lvm_state':
                 if 'check_type' not in step: errors.append(f"{step_label}: Missing 'check_type' for check_lvm_state.")
                 # Add more specific checks based on check_type (e.g., require 'device' for 'pv_exists')
                 check_type_lvm = step.get("check_type")
                 if check_type_lvm == "pv_exists" and "device" not in step: errors.append(f"{step_label}: 'pv_exists' check requires 'device'.")
                 elif check_type_lvm == "vg_exists" and "vg_name" not in step: errors.append(f"{step_label}: 'vg_exists' check requires 'vg_name'.")
                 elif check_type_lvm == "lv_exists" and ("vg_name" not in step or "lv_name" not in step): errors.append(f"{step_label}: 'lv_exists' check requires 'vg_name' and 'lv_name'.")
                 elif check_type_lvm == "lv_size" and ("vg_name" not in step or "lv_name" not in step): errors.append(f"{step_label}: 'lv_size' check requires 'vg_name' and 'lv_name'.")
                 elif check_type_lvm == "lv_size" and "min_size_mb" not in step and "max_size_mb" not in step and "exact_size_mb" not in step: errors.append(f"{step_label}: 'lv_size' check requires 'min_size_mb'/'max_size_mb' or 'exact_size_mb'.")
            elif step_type == 'check_history':
                 if 'command_pattern' not in step and 'disallowed_commands' not in step: errors.append(f"{step_label}: 'check_history' requires 'command_pattern' or 'disallowed_commands'.")
            elif step_type == 'check_journalctl':
                 if 'message_pattern' not in step and 'service' not in step and 'syslog_identifier' not in step and 'command_name' not in step: errors.append(f"{step_label}: 'check_journalctl' requires at least one filter (e.g., 'message_pattern', 'service').")
            elif step_type == 'check_audit_log':
                 if 'rule_key' not in step: errors.append(f"{step_label}: 'check_audit_log' requires 'rule_key'.")
            # ... include parameter checks for ALL supported validation types ...

        elif key_name == 'setup': # Setup step checks
             if step_type == 'run_command':
                 if 'command' not in step: errors.append(f"{step_label}: Missing 'command'.")
                 if 'user_context' in step and not isinstance(step['user_context'], str): errors.append(f"{step_label}: 'user_context' must be a string if present.")
             elif step_type == 'ensure_package_installed':
                 if 'package' not in step: errors.append(f"{step_label}: Missing 'package' parameter for ensure_package_installed.")
                 elif not isinstance(step['package'], str): errors.append(f"{step_label}: 'package' must be a string.")
                 if 'manager_type' in step and step['manager_type'] not in ["apt", "dnf", "yum", "zypper"]: errors.append(f"{step_label}: Invalid 'manager_type'. Supported: apt, dnf, yum, zypper.")
                 if 'update_cache' in step and not isinstance(step['update_cache'], bool): errors.append(f"{step_label}: 'update_cache' must be true or false.")
             # ... include parameter checks for ALL supported setup types ...

def validate_challenge_structure(challenge_data: dict, filename: str = "challenge") -> List[str]:
    """Performs structural validation of loaded challenge data against expected schema."""
    errors = []
    # --- Top Level Keys ---
    required_keys = ['id', 'name', 'description'] # Validation keys checked separately below
    # Add new optional keys based on PDF/template
    allowed_keys = ['id', 'name', 'description', 'category', 'difficulty', 'score',
                    'concepts', 'setup', 'user_action_simulation',
                    'validation', 'final_state_checks', 'process_validation_checks', # Added split keys
                    'hints', 'flag',
                    'objective_refs', 'estimated_time_mins', 'distro_compatibility', 'solution_file'] # New PDF fields
    for key in challenge_data:
        if key not in allowed_keys: errors.append(f"'{filename}': Unknown top-level key: '{key}'")
    for key in required_keys:
        if key not in challenge_data: errors.append(f"'{filename}': Missing required top-level key: '{key}'")

    # --- Basic Type Checks (including new fields) ---
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

    # --- NEW Field Validations ---
    if 'objective_refs' in challenge_data and not isinstance(challenge_data['objective_refs'], list): errors.append(f"'{filename}': 'objective_refs' must be a list of strings.")
    elif 'objective_refs' in challenge_data:
         if not all(isinstance(c, str) for c in challenge_data['objective_refs']): errors.append(f"'{filename}': All items in 'objective_refs' must be strings.")

    if 'estimated_time_mins' in challenge_data:
        try:
            time_val = int(challenge_data['estimated_time_mins'])
            if time_val <= 0: errors.append(f"'{filename}': 'estimated_time_mins' must be a positive integer.")
        except (ValueError, TypeError): errors.append(f"'{filename}': 'estimated_time_mins' ('{challenge_data['estimated_time_mins']}') must be an integer.")

    if 'distro_compatibility' in challenge_data and not isinstance(challenge_data['distro_compatibility'], list): errors.append(f"'{filename}': 'distro_compatibility' must be a list of strings.")
    elif 'distro_compatibility' in challenge_data:
         if not all(isinstance(c, str) for c in challenge_data['distro_compatibility']): errors.append(f"'{filename}': All items in 'distro_compatibility' must be strings.")

    if 'solution_file' in challenge_data and not isinstance(challenge_data['solution_file'], str): errors.append(f"'{filename}': 'solution_file' must be a string.")
    # --- END NEW Field Validations ---

    # --- Score Validation ---
    if 'score' in challenge_data:
        try:
             score_val = int(challenge_data['score'])
             if score_val < 0: errors.append(f"'{filename}': 'score' must be a non-negative integer.")
        except (ValueError, TypeError): errors.append(f"'{filename}': 'score' ('{challenge_data['score']}') must be an integer.")

    # --- ID Format Validation ---
    challenge_id = challenge_data.get('id')
    if challenge_id and isinstance(challenge_id, str) and not re.match(r'^[a-zA-Z0-9._-]+$', challenge_id):
        errors.append(f"'{filename}': 'id' field '{challenge_id}' contains invalid characters. Use only letters, numbers, hyphens, underscores, periods.")

    # --- Validation Steps (Revised Logic) ---
    has_validation_key = 'validation' in challenge_data
    has_final_state_key = 'final_state_checks' in challenge_data
    has_process_checks_key = 'process_validation_checks' in challenge_data

    # Check for mutually exclusive use or mandatory presence
    if has_validation_key and (has_final_state_key or has_process_checks_key):
        errors.append(f"'{filename}': Cannot use 'validation' key together with 'final_state_checks' or 'process_validation_checks'. Use one structure or the other.")
    elif not has_validation_key and not has_final_state_key: # Check if primary validation is missing
        # If process_checks exist but final_state does not, it's an error.
        # If neither exist, it's an error.
        if has_process_checks_key:
             errors.append(f"'{filename}': If using 'process_validation_checks', 'final_state_checks' is also required (or use the single 'validation' key).")
        else:
             errors.append(f"'{filename}': Missing validation steps. Must provide 'validation' list OR 'final_state_checks' list.")

    # Validate the structure based on which keys are present
    if has_validation_key:
        _validate_steps_list(challenge_data.get('validation'), 'validation', filename, errors, SUPPORTED_VALIDATION_TYPES)
    else:
        # Validate final_state_checks (required if validation key is absent)
        if has_final_state_key:
            _validate_steps_list(challenge_data.get('final_state_checks'), 'final_state_checks', filename, errors, SUPPORTED_VALIDATION_TYPES)
        # Validate process_validation_checks (optional)
        if has_process_checks_key:
            _validate_steps_list(challenge_data.get('process_validation_checks'), 'process_validation_checks', filename, errors, SUPPORTED_VALIDATION_TYPES)

    # --- Setup Steps ---
    if 'setup' in challenge_data:
        _validate_steps_list(challenge_data.get('setup'), 'setup', filename, errors, SUPPORTED_SETUP_TYPES)

    # --- Hints ---
    if 'hints' in challenge_data:
         if not isinstance(challenge_data['hints'], list): errors.append(f"'{filename}': 'hints' field must be a list if present.")
         else:
             for i, hint in enumerate(challenge_data['hints']):
                 hint_label = f"'{filename}' Hint {i+1}"
                 if not isinstance(hint, dict): errors.append(f"{hint_label}: Must be a dictionary.")
                 elif 'text' not in hint: errors.append(f"{hint_label}: Missing 'text'.")
                 elif not isinstance(hint['text'], str): errors.append(f"{hint_label}: 'text' must be a string.")
                 elif 'cost' in hint:
                     try:
                         cost_val = int(hint['cost'])
                         if cost_val < 0: errors.append(f"{hint_label}: 'cost' must be a non-negative integer.")
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
                # Use safe_load to avoid arbitrary code execution from YAML
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
                from .console import Panel, RICH_AVAILABLE
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
            # Ensure 'hints' exists and cost is int and non-negative
            processed_hints = []
            for hint in challenge_data.get('hints', []):
                if isinstance(hint, dict) and 'text' in hint:
                    hint['cost'] = max(0, int(hint.get('cost', 0))) # Ensure non-negative
                    processed_hints.append(hint)
            challenge_data['hints'] = processed_hints
            # Ensure list fields default to empty list if not present, except distro_compatibility
            challenge_data['setup'] = challenge_data.get('setup', [])
            challenge_data['concepts'] = challenge_data.get('concepts', [])
            challenge_data['objective_refs'] = challenge_data.get('objective_refs', [])
            # Default 'distro_compatibility' to ["Any"] as per PDF example suggestion
            challenge_data['distro_compatibility'] = challenge_data.get('distro_compatibility', ['Any'])
            # Ensure validation lists exist, even if empty (for process checks)
            if 'validation' not in challenge_data:
                 challenge_data['final_state_checks'] = challenge_data.get('final_state_checks', [])
                 challenge_data['process_validation_checks'] = challenge_data.get('process_validation_checks', [])


            if challenge_id in challenges:
                 console.print(f"  :warning: Duplicate challenge ID '[bold yellow]{challenge_id}[/]' found in '[cyan]{yaml_file.name}[/cyan]'. Overwriting previous definition.", style="yellow")

            challenges[challenge_id] = challenge_data
            loaded_count += 1

        except yaml.YAMLError as e:
            console.print(f"  [red]:x: Error parsing YAML file '[cyan]{yaml_file.name}[/cyan]': {e}[/]", style="red")
            skipped_count += 1
        except FileNotFoundError:
             # This case should ideally not happen if glob works correctly, but good to handle
             console.print(f"  [red]:x: File '{yaml_file.name}' not found during loading attempt.[/]", style="red")
             skipped_count += 1
        except Exception as e:
            # Catch other potential errors during loading/processing
            console.print(f"  [red]:x: An unexpected error occurred loading '{yaml_file.name}': {e}[/]", style="red")
            from .console import RICH_AVAILABLE
            import traceback
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