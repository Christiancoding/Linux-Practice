#!/usr/bin/env python3
"""
Challenge Management Module

Comprehensive challenge loading, validation, and execution system for Linux+ 
practice environments with YAML-based challenge definitions.
"""

import re
import logging
from pathlib import Path
from typing import Dict, List, Any, Tuple, Union

# Third-party imports
try:
    import yaml
except ImportError:
    raise ImportError("PyYAML is required. Install with: pip install pyyaml")

# Local imports
from .console_helper import console, RICH_AVAILABLE
from rich.console import Console  # type: ignore

console: "Console"  # type: ignore
from .exceptions import (
    PracticeToolError,
    ChallengeLoadError
)
from .config import config
from .ssh_manager import run_ssh_command, SSHCommandError

# Set up module logger
logger = logging.getLogger(__name__)

if RICH_AVAILABLE:
    from rich.panel import Panel
    from rich.table import Table
    from rich.markdown import Markdown
    from rich.prompt import Confirm


class ChallengeManager:
    """
    Advanced challenge management system with comprehensive validation,
    loading, execution, and scoring capabilities.
    """
    
    def __init__(self):
        """Initialize the challenge manager."""
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self._loaded_challenges: Dict[str, Dict[str, Any]] = {}

        self._challenge_template = self._get_challenge_template()
    
    def _get_challenge_template(self) -> str:
        """Get the default challenge template for new challenges."""
        return """# --- Challenge Definition File ---
# See documentation or existing challenges for examples.
# SECURITY WARNING: 'run_command' executes commands via SSH on the target VM.
# Do not load challenges from untrusted sources without understanding the commands.

# Unique identifier for the challenge (e.g., configure-ssh-keys)
id: my-new-challenge

# Human-readable name for the challenge
name: "My New Challenge Title"

# Detailed description of the objective for the user (Markdown supported)
description: |
  Explain what the user needs to accomplish here.
  * Use lists.
  * Use `code`.
  * **Bold** and _italics_.

# Category for grouping challenges (e.g., Networking, Security, File Management)
category: "Uncategorized"

# Difficulty level (e.g., Easy, Medium, Hard, Expert)
difficulty: "Medium"

# Potential score for completing the challenge successfully (before hint costs)
score: 100

# List of relevant Linux concepts or commands involved
concepts:
  - example-concept
  - example-command

# Optional: Setup steps executed *before* the user interacts with the VM.
# Used to put the VM into the correct starting state for the challenge.
# WARNING: Commands run here execute on the VM via SSH. Use with extreme caution.
setup:
  - type: run_command
    command: "echo 'Challenge setup complete'"

# Validation steps to check if the challenge was completed successfully
validation:
  - type: run_command
    command: "test -f /tmp/example"
    expected_exit_code: 0
    description: "Check if example file exists"

# Optional: Hints to help users (with score penalties)
hints:
  - text: "This is your first hint"
    cost: 10
  - text: "This is a more detailed hint"
    cost: 20
"""
    
    # --- Challenge Structure Validation ---
    
    def validate_challenge_structure(self, challenge_data: Dict[str, Any], filename: str = "challenge") -> List[str]:
        """
        Validate the structure and content of a challenge definition.
        
        Args:
            challenge_data: The parsed challenge YAML data
            filename: The filename for error reporting
            
        Returns:
            List[str]: List of validation errors (empty if valid)
        """
        # --- NORMALIZATION: Handle alternative field naming conventions ---
        normalized_data = dict(challenge_data)
        errors: List[str] = []
        # Handle alternative field naming conventions for backward compatibility
        normalized_data = dict(challenge_data)
        if 'challenge_id' in normalized_data and 'id' not in normalized_data:
            normalized_data['id'] = normalized_data['challenge_id']
        if 'title' in normalized_data and 'name' not in normalized_data:
            normalized_data['name'] = normalized_data['title']

        # Handle nested validation structure
        if 'validation' in normalized_data:
            validation = normalized_data['validation']
            if isinstance(validation, dict):
                # Handle nested validation structure like final_state_checks
                if 'final_state_checks' in validation:
                    normalized_data['validation'] = validation['final_state_checks']
                elif 'process_validation_checks' in validation:
                    normalized_data['validation'] = validation['process_validation_checks']
                else:
                    # Convert any nested dict to a list of its values
                    validation_steps = []
                    for key, value in validation.items():
                        if isinstance(value, list):
                            validation_steps.extend(value)
                    if validation_steps:
                        normalized_data['validation'] = validation_steps

        # Use normalized_data for the rest of the validation instead of challenge_data
        
        # --- Required Fields ---
        required_fields: Dict[str, type] = {
            'id': str,
            'name': str, 
            'description': str,
            'validation': list
        }
        
        for field, expected_type in required_fields.items():
            expected_type: type  # type: ignore
            if field not in challenge_data:
                errors.append(f"'{filename}': Missing required field '{field}'")
            elif not isinstance(challenge_data[field], expected_type):
                errors.append(f"'{filename}': Field '{field}' must be of type {getattr(expected_type, '__name__', str(expected_type))}")
        
        # --- Optional Fields with Type Validation ---
        optional_fields: Dict[str, Union[type, Tuple[type, ...]]] = {
            'category': str,
            'difficulty': str,
            'score': (int, str),  # Allow string for conversion
            'concepts': list,
            'setup': list,
            'hints': list
        }
        
        for field, expected_type in optional_fields.items():
            expected_type: type | tuple[type, ...]  # type: ignore
            if field in challenge_data:
                value = challenge_data[field]
                if isinstance(expected_type, tuple):
                    # Multiple allowed types
                    if not any(isinstance(value, t) for t in expected_type):
                        type_names = " or ".join([t.__name__ for t in expected_type if hasattr(t, "__name__")])
                        errors.append(f"'{filename}': Field '{field}' must be of type {type_names}")
                else:
                    if not isinstance(value, expected_type):
                        errors.append(f"'{filename}': Field '{field}' must be of type {expected_type.__name__}")
        
        # --- ID Validation ---
        if 'id' in challenge_data and isinstance(challenge_data['id'], str):
            if not re.match(r'^[a-zA-Z0-9_-]+$', challenge_data['id']):
                errors.append(f"'{filename}': ID must contain only alphanumeric characters, hyphens, and underscores")
        
        # --- Score Validation ---
        if 'score' in challenge_data:
            try:
                score_val = int(challenge_data['score'])
                if score_val < 0:
                    errors.append(f"'{filename}': Score must be non-negative")
            except (ValueError, TypeError):
                errors.append(f"'{filename}': Score must be a valid integer")
        
        # --- Validation Steps ---
        if 'validation' in challenge_data and isinstance(challenge_data['validation'], list):
            if not challenge_data['validation']:
                errors.append(f"'{filename}': 'validation' cannot be empty")
            else:
                for i, step in enumerate(challenge_data['validation']):  # type: ignore[var-annotated]
                    step_label = f"'{filename}' Validation step {i+1}"
                    if not isinstance(step, dict):
                        errors.append(f"{step_label}: Must be a dictionary")
                    elif 'type' not in step:
                        errors.append(f"{step_label}: Missing 'type'")
                    else:
                        # Type-specific validation
                        step_typed: Dict[str, Any] = step  # type: ignore
                        step_type = step_typed.get('type')
                        if step_type == 'run_command':
                            if 'command' not in step:
                                errors.append(f"{step_label}: Missing 'command'")
                        elif step_type == 'ensure_group_exists':
                            if 'group' not in step:
                                errors.append(f"{step_label}: Missing 'group'")
                        elif step_type == 'ensure_user_exists':
                            if 'user' not in step:
                                errors.append(f"{step_label}: Missing 'user'")
                            if 'expected_exit_code' in step:
                                try:
                                    if step['expected_exit_code'] is None or not isinstance(step['expected_exit_code'], (int, str)):
                                        raise ValueError
                                    int(step['expected_exit_code']);
                                except (ValueError, TypeError):
                                    errors.append(f"{step_label}: 'expected_exit_code' must be an integer")
                        elif step_type == 'check_service_status':
                            if 'service' not in step:
                                errors.append(f"{step_label}: Missing 'service'")
                            if 'expected_status' in step:
                                valid_statuses = ['active', 'inactive', 'failed', 'enabled', 'disabled']
                                if step['expected_status'] not in valid_statuses:
                                    errors.append(f"{step_label}: 'expected_status' must be one of {valid_statuses}")
                        elif step_type == 'check_user_group':
                            check_type = step.get('check_type')
                            if not check_type:
                                errors.append(f"{step_label}: Missing 'check_type'")
                            elif check_type in ['user_exists', 'user_primary_group', 'user_in_group', 'user_shell']:
                                if 'username' not in step:
                                    errors.append(f"{step_label}: Missing 'username'")
                                if check_type in ['user_primary_group', 'user_in_group'] and 'group' not in step:
                                    errors.append(f"{step_label}: Missing 'group'")
                                if check_type == 'user_shell' and 'shell' not in step:
                                    errors.append(f"{step_label}: Missing 'shell'")
                        elif step_type == 'check_command':
                            if 'command' not in step:
                                errors.append(f"{step_label}: Missing 'command'")
                        elif step_type == 'check_history':
                            if 'command_pattern' not in step:
                                errors.append(f"{step_label}: Missing 'command_pattern'")
                        elif step_type == 'check_port_listening':
                            if 'port' not in step:
                                errors.append(f"{step_label}: Missing 'port'")
                            else:
                                try:
                                    port_value = step['port']
                                    if isinstance(port_value, (int, str)):
                                        port = int(str(port_value))
                                        if not (1 <= port <= 65535):
                                            errors.append(f"{step_label}: Port must be between 1 and 65535")
                                    else:
                                        errors.append(f"{step_label}: Port must be a valid integer")
                                except (ValueError, TypeError):
                                    errors.append(f"{step_label}: Port must be a valid integer")
                        elif step_type == 'check_file_exists':
                            if 'path' not in step:
                                errors.append(f"{step_label}: Missing 'path'")
                        elif step_type == 'check_file_contains':
                            if 'path' not in step:
                                errors.append(f"{step_label}: Missing 'path'")
                            if 'text' not in step and 'matches_regex' not in step:
                                errors.append(f"{step_label}: Missing 'text' or 'matches_regex'")
                            if 'text' in step and 'matches_regex' in step:
                                errors.append(f"{step_label}: Cannot have both 'text' and 'matches_regex'")
                            if 'matches_regex' in step:
                                regex_value: str = step['matches_regex']
                                if not isinstance(regex_value, str):
                                    errors.append(f"{step_label}: 'matches_regex' must be a string")
                                else:
                                    try:
                                        re.compile(regex_value)
                                    except re.error as regex_err:
                                        errors.append(f"{step_label}: Invalid regex '{regex_value}': {regex_err}")
                        else:
                            errors.append(f"{step_label}: Unsupported validation type: '{step_type}'")
        
        # --- Setup Steps ---
        if 'setup' in challenge_data and isinstance(challenge_data['setup'], list):
            setup_steps: List[Dict[str, Any]] = challenge_data['setup']  # type: ignore
            for i, step in enumerate(setup_steps):
                step_label = f"'{filename}' Setup step {i+1}"
                if 'type' not in step:
                    errors.append(f"{step_label}: Missing 'type'")
                else:
                    step_type = step.get('type')
                    if step_type == 'run_command':
                        if 'command' not in step:
                            errors.append(f"{step_label}: Missing 'command'")
                    else:
                        errors.append(f"{step_label}: Unsupported setup type: '{step_type}'")
        
        # --- Hints ---
        if 'hints' in challenge_data and isinstance(challenge_data['hints'], list):
            for i, hint in enumerate(challenge_data.get('hints', [])):
                hint_label = f"'{filename}' Hint {i+1}"
                if not isinstance(hint, dict):
                    errors.append(f"{hint_label}: Must be a dictionary")
                elif 'text' not in hint:
                    errors.append(f"{hint_label}: Missing 'text'")
                elif 'cost' in hint:
                    try:
                        cost_val = hint.get('cost', 0)  # `hint` is now explicitly typed
                        cost = int(cost_val) if isinstance(cost_val, (int, str)) and str(cost_val).isdigit() else 0
                    except (ValueError, TypeError):
                        cost = 0
                    if cost < 0:
                        errors.append(f"{hint_label}: Cost must be non-negative")
        
        return errors
    
    # --- Challenge Loading ---
    
    def load_challenges_from_dir(self, challenges_dir: Path) -> Dict[str, Dict[str, Any]]:
        """
        Load challenge definitions from YAML files in a directory.
        
        Args:
            challenges_dir: Path to directory containing challenge YAML files
            
        Returns:
            Dict[str, Dict[str, Any]]: Dictionary mapping challenge IDs to challenge data
            
        Raises:
            ChallengeLoadError: If directory doesn't exist or other loading errors
        """
        challenges: Dict[str, Dict[str, Any]] = {}
        
        if not challenges_dir.is_dir():
            raise ChallengeLoadError(f"Challenges directory not found: '{challenges_dir}'")
        
        console.print(f"\n:books: Loading challenges from: [blue underline]{challenges_dir.resolve()}[/]")
        
        # Find all YAML files
        yaml_files = sorted(list(challenges_dir.glob('*.yaml')) + list(challenges_dir.glob('*.yml')))
        
        if not yaml_files:
            console.print(f"  [yellow]:warning: No challenge YAML files (*.yaml, *.yml) found in '{challenges_dir}'.[/]", style="yellow")
            return challenges
        
        loaded_count = 0
        skipped_count = 0
        
        for yaml_file in yaml_files:
            try:
                # Load YAML content
                with open(yaml_file, 'r', encoding='utf-8') as f:
                    challenge_data = yaml.safe_load(f)
                
                if not isinstance(challenge_data, dict):
                    console.print(f"  :warning: Skipping '[cyan]{yaml_file.name}[/cyan]': Content is not a valid YAML dictionary (root object).", style="yellow")
                    skipped_count += 1
                    continue
                
                # Validate structure before processing
                validation_errors = self.validate_challenge_structure(challenge_data, yaml_file.name)
                if validation_errors:
                    error_panel_content = "\n".join([f"- {e}" for e in validation_errors])
                    if RICH_AVAILABLE:
                        console.print(Panel(
                            error_panel_content, 
                            title=f"[bold red]Validation Errors in '{yaml_file.name}'[/]", 
                            border_style="red", 
                            expand=False
                        ))
                    else:
                        console.print(f"--- Validation Errors in '{yaml_file.name}' ---")
                        console.print(error_panel_content)
                        console.print(f"--- End Errors ---")
                    skipped_count += 1
                    continue
                
                challenge_id = challenge_data['id']
                
                # Apply defaults and type conversions after validation
                challenge_data['score'] = int(challenge_data.get('score', config.challenge.DEFAULT_CHALLENGE_SCORE))
                
                # Process hints
                processed_hints = []
                for hint in challenge_data.get('hints', []):
                    if isinstance(hint, dict) and 'text' in hint:
                        hint['cost'] = int(hint.get('cost', 0))
                        processed_hints.append(hint)
                challenge_data['hints'] = processed_hints
                
                # Ensure required lists exist
                challenge_data['setup'] = challenge_data.get('setup', [])
                challenge_data['concepts'] = challenge_data.get('concepts', [])
                
                # Check for duplicate IDs
                if challenge_id in challenges:
                    console.print(f"  :warning: Duplicate challenge ID '[bold yellow]{challenge_id}[/]' found in '[cyan]{yaml_file.name}[/cyan]'. Overwriting previous definition.", style="yellow")
                
                challenges[challenge_id] = challenge_data
                loaded_count += 1
                self.logger.debug(f"Loaded challenge: {challenge_id} from {yaml_file.name}")
                
            except yaml.YAMLError as e:
                console.print(f"  [red]:x: Error parsing YAML file '[cyan]{yaml_file.name}[/cyan]': {e}[/]", style="red")
                skipped_count += 1
                self.logger.error(f"YAML parsing error in {yaml_file.name}: {e}")
            except FileNotFoundError:
                console.print(f"  [red]:x: File '{yaml_file.name}' suddenly not found during loading.[/]", style="red")
                skipped_count += 1
            except Exception as e:
                console.print(f"  [red]:x: Unexpected error loading '[cyan]{yaml_file.name}[/cyan]': {e}[/]", style="red")
                skipped_count += 1
                self.logger.error(f"Unexpected error loading {yaml_file.name}: {e}", exc_info=True)
        
        # Summary
        total_files = loaded_count + skipped_count
        if RICH_AVAILABLE:
            summary_table = Table.grid(padding=(0, 2))
            summary_table.add_column(style="bold")
            summary_table.add_column()
            summary_table.add_row("Files Found:", str(total_files))
            summary_table.add_row("Loaded:", f"[green]{loaded_count}[/]")
            summary_table.add_row("Skipped:", f"[red]{skipped_count}[/]" if skipped_count > 0 else "0")
            console.print(Panel(summary_table, title="Loading Summary", border_style="blue"))
        else:
            console.print(f"Loading Summary: {loaded_count} loaded, {skipped_count} skipped")
        
        self._loaded_challenges = challenges
        return challenges
    
    # --- Challenge Display and Management ---
    
    def list_challenges(self, challenges: Dict[str, Dict[str, Any]]) -> None:
        """
        Display a formatted list of available challenges.
        
        Args:
            challenges: Dictionary of challenge data
        """
        if not challenges:
            if RICH_AVAILABLE:
                console.print(Panel("[dim]No challenges available.[/]", title="Available Challenges", border_style="dim"))
            else:
                console.print("No challenges available.")
            return
        
        if RICH_AVAILABLE:
            table = Table(title="Available Practice Challenges", show_header=True, header_style="bold blue")
            table.add_column("ID", style="cyan", width=20)
            table.add_column("Name", style="white", width=30)
            table.add_column("Category", style="yellow", width=15)
            table.add_column("Difficulty", style="magenta", width=12)
            table.add_column("Score", style="green", width=8)
            table.add_column("Concepts", style="dim", width=25)
            
            for challenge_id, challenge in sorted(challenges.items()):
                concepts_str = ", ".join(challenge.get('concepts', [])[:3])
                if len(challenge.get('concepts', [])) > 3:
                    concepts_str += "..."
                
                table.add_row(
                    challenge_id,
                    challenge.get('name', 'N/A'),
                    challenge.get('category', 'N/A'),
                    challenge.get('difficulty', 'N/A'),
                    str(challenge.get('score', 0)),
                    concepts_str or "[dim]None[/]"
                )
            
            console.print(table)
        else:
            # Fallback table format
            console.print("\nAvailable Practice Challenges:")
            console.print("-" * 80)
            for challenge_id, challenge in sorted(challenges.items()):
                console.print(f"{challenge_id:20} | {challenge.get('name', 'N/A'):25} | {challenge.get('difficulty', 'N/A'):10} | {challenge.get('score', 0):>3}")
            console.print("-" * 80)
    
    def display_challenge_details(self, challenge: Dict[str, Any], challenge_id: str) -> None:
        """
        Display detailed information about a specific challenge.
        
        Args:
            challenge: The challenge data dictionary
            challenge_id: The challenge identifier
        """
        if RICH_AVAILABLE:
            # Create detailed challenge information display
            info_table = Table.grid(padding=(0, 2))
            info_table.add_column(style="bold")
            info_table.add_column()
            
            info_table.add_row("Challenge ID:", f"[cyan]{challenge_id}[/]")
            info_table.add_row("Name:", f"[white]{challenge.get('name', 'N/A')}[/]")
            info_table.add_row("Category:", f"[yellow]{challenge.get('category', 'N/A')}[/]")
            info_table.add_row("Difficulty:", f"[magenta]{challenge.get('difficulty', 'N/A')}[/]")
            info_table.add_row("Max Score:", f"[green]{challenge.get('score', 0)}[/]")
            
            if challenge.get('concepts'):
                concepts_str = ", ".join(challenge['concepts'])
                info_table.add_row("Concepts:", f"[dim]{concepts_str}[/]")
            
            console.print(Panel(info_table, title="Challenge Information", border_style="blue"))
            
            # Display description
            description = challenge.get('description', 'No description provided.')
            description_content = Markdown(description) if RICH_AVAILABLE else description
            console.print(Panel(description_content, title="Objective", border_style="cyan"))
        else:
            # Fallback display
            console.print(f"Challenge ID: {challenge_id}")
            console.print(f"Name: {challenge.get('name', 'N/A')}")
            console.print(f"Category: {challenge.get('category', 'N/A')}")
            console.print(f"Difficulty: {challenge.get('difficulty', 'N/A')}")
            console.print(f"Max Score: {challenge.get('score', 0)}")
            if challenge.get('concepts'):
                console.print(f"Concepts: {', '.join(challenge['concepts'])}")
            console.print("\n--- Objective ---")
            console.print(challenge.get('description', 'No description provided.'))
            console.print("--- End Objective ---")
    
    # --- Challenge Execution ---
    
    def execute_setup_steps(self, challenge: Dict[str, Any], challenge_id: str, 
                           vm_ip: str, ssh_user: str, ssh_key_path: Path, 
                           verbose: bool = False) -> None:
        """
        Execute challenge setup steps on the target VM.
        
        Args:
            challenge: The challenge data dictionary
            challenge_id: The challenge identifier  
            vm_ip: Target VM IP address
            ssh_user: SSH username
            ssh_key_path: Path to SSH private key
            verbose: Enable verbose output
            
        Raises:
            PracticeToolError: If setup fails
        """
        setup_steps = challenge.get("setup", [])
        if not setup_steps:
            self.logger.debug(f"No setup steps for challenge {challenge_id}")
            return
        
        console.rule("[bold]Challenge Setup[/]", style="blue")
        
        for i, step in enumerate(setup_steps):
            step_type = step.get("type")
            setup_title = f"Setup Step {i+1}: [bold cyan]{step_type}[/]"
            
            if step_type == "run_command":
                command = step.get("command")
                if not command:
                    raise ChallengeLoadError(f"Setup step {i+1} (run_command) in challenge '{challenge_id}' is missing 'command'.")
                
                panel_content = f"Executing: `{command}`"
                if RICH_AVAILABLE:
                    console.print(Panel(panel_content, title=setup_title, border_style="magenta", expand=False))
                else:
                    console.print(f"--- {setup_title} ---\n{panel_content}\n------")
                
                if verbose:
                    console.print("[yellow]Running setup command (Ensure challenge source is trusted!)[/]", style="yellow")
                
                try:
                    setup_result = run_ssh_command(vm_ip, ssh_user, ssh_key_path, command, verbose=False)
                except SSHCommandError as e:
                    raise PracticeToolError(f"Challenge setup failed: Error executing command '{command}': {e}") from e
                
                if verbose:
                    from .ssh_manager import format_ssh_output
                    console.print(format_ssh_output(setup_result, command))
                
                # Check for command failure
                exec_error = setup_result.get('error')
                exit_status = setup_result.get('exit_status', -1)
                if exec_error or exit_status != 0:
                    details = exec_error or f"Exited with status {exit_status}"
                    raise PracticeToolError(f"Challenge setup failed: Command '{command}' did not succeed ({details}). Aborting.")
                
                console.print(f"[green]:heavy_check_mark: Setup command successful.[/]")
            else:
                self.logger.warning(f"Unsupported setup step type: {step_type}")
                console.print(f"[yellow]:warning: Unsupported setup step type: {step_type}[/]", style="yellow")
    
    def manage_hints(self, challenge: Dict[str, Any], current_score: int) -> Tuple[int, int, int]:
        """
        Manage the hint system for a challenge.
        
        Args:
            challenge: The challenge data dictionary
            current_score: Current challenge score
            
        Returns:
            Tuple[int, int, int]: (updated_score, hints_used_count, total_hint_cost)
        """
        available_hints = challenge.get("hints", [])
        if not available_hints:
            return current_score, 0, 0
        
        console.print("\n")  # Spacer before hint prompt
        remaining_hints = list(available_hints)  # Copy to modify
        hints_used_count = 0
        total_hint_cost = 0
        base_score = challenge.get('score', 100)
        
        while remaining_hints:
            hint_prompt = f":bulb: Show hint? ({len(remaining_hints)} remaining, Current Score: {current_score})"
            show_hint = Confirm.ask(hint_prompt, default=False)
            
            if show_hint:
                hint_data = remaining_hints.pop(0)  # Get and remove first hint
                hint_text = hint_data.get('text', '[i]No text[/]')
                hint_cost = hint_data.get('cost', 0)
                
                hint_panel_content = Markdown(hint_text) if RICH_AVAILABLE else hint_text
                hint_title = f"Hint #{hints_used_count + 1} (Cost: {hint_cost})"
                
                if RICH_AVAILABLE:
                    console.print(Panel(hint_panel_content, title=hint_title, border_style="yellow", expand=False))
                else:
                    console.print(f"--- {hint_title} ---\n{hint_panel_content}\n------")
                
                hints_used_count += 1
                total_hint_cost += hint_cost
                current_score = max(0, base_score - total_hint_cost)  # Recalculate from base score
                console.print(f"  -> [bold]Current Score Potential:[/bold] [blue]{current_score}[/]")
            else:
                console.print("[dim]Skipping remaining hints.[/]")
                break
        
        if not remaining_hints:
            console.print("[dim]All hints shown.[/]")
        
        return current_score, hints_used_count, total_hint_cost
    
    def display_challenge_results(self, challenge: Dict[str, Any], challenge_id: str,
                                challenge_passed: bool, final_score: int, 
                                hints_used_count: int, total_hint_cost: int) -> None:
        """
        Display the final results of a challenge attempt.
        
        Args:
            challenge: The challenge data dictionary
            challenge_id: The challenge identifier
            challenge_passed: Whether the challenge was completed successfully
            final_score: The final score achieved
            hints_used_count: Number of hints used
            total_hint_cost: Total cost of hints used
        """
        console.rule("[bold]Challenge Results[/]", style="magenta")
        
        result_panel_title = "[bold green]Success![/]" if challenge_passed else "[bold red]Failure[/]"
        result_panel_style = "green" if challenge_passed else "red"
        
        if RICH_AVAILABLE:
            result_table = Table.grid(padding=(0, 2))
            result_table.add_column(style="bold")
            result_table.add_column()
            
            result_table.add_row("Challenge:", f"[cyan]{challenge.get('name', challenge_id)}[/cyan]")
            result_table.add_row("Hints Used:", f"{hints_used_count} ([dim]Cost: {total_hint_cost}[/])")
            
            if challenge_passed:
                final_score_text = f"[bold green]{final_score}[/] / {challenge.get('score', 0)}"
                result_table.add_row("Status:", "[bold green]:trophy: PASSED![/]")
            else:
                final_score_text = f"[bold red]{final_score}[/] / {challenge.get('score', 0)}"
                result_table.add_row("Status:", "[bold red]:x: FAILED[/]")
            
            result_table.add_row("Final Score:", final_score_text)
            
            console.print(Panel(result_table, title=result_panel_title, border_style=result_panel_style))
        else:
            # Fallback display
            status = "PASSED" if challenge_passed else "FAILED"
            console.print(f"Challenge: {challenge.get('name', challenge_id)}")
            console.print(f"Status: {status}")
            console.print(f"Hints Used: {hints_used_count} (Cost: {total_hint_cost})")
            console.print(f"Final Score: {final_score} / {challenge.get('score', 0)}")
    
    def create_challenge_template(self, output_path: Path) -> None:
        """
        Create a new challenge template file.
        
        Args:
            output_path: Path where the template should be created
            
        Raises:
            PracticeToolError: If template creation fails
        """
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(self._challenge_template)
            
            console.print(f"[green]:heavy_check_mark: Challenge template created: [blue underline]{output_path}[/][/]")
            self.logger.info(f"Created challenge template: {output_path}")
            
        except PermissionError:
            raise PracticeToolError(f"Permission denied creating template: {output_path}")
        except Exception as e:
            raise PracticeToolError(f"Error creating challenge template: {e}")


# Convenience functions for backward compatibility with ww.py
def validate_challenge_structure(challenge_data: Dict[str, Any], filename: str = "challenge") -> List[str]:
    """Backward compatibility function for challenge structure validation."""
    manager = ChallengeManager()
    return manager.validate_challenge_structure(challenge_data, filename)

def load_challenges_from_dir(challenges_dir: Path) -> Dict[str, Dict[str, Any]]:
    """Backward compatibility function for loading challenges from directory."""
    manager = ChallengeManager()
    return manager.load_challenges_from_dir(challenges_dir)

def list_challenges(challenges: Dict[str, Dict[str, Any]]) -> None:
    """Backward compatibility function for listing challenges."""
    manager = ChallengeManager()
    return manager.list_challenges(challenges)

def display_challenge_details(challenge: Dict[str, Any], challenge_id: str) -> None:
    """Backward compatibility function for displaying challenge details."""
    manager = ChallengeManager()
    return manager.display_challenge_details(challenge, challenge_id)

def execute_setup_steps(challenge: Dict[str, Any], challenge_id: str, 
                       vm_ip: str, ssh_user: str, ssh_key_path: Path, 
                       verbose: bool = False) -> None:
    """Backward compatibility function for executing setup steps."""
    manager = ChallengeManager()
    return manager.execute_setup_steps(challenge, challenge_id, vm_ip, ssh_user, ssh_key_path, verbose)

def manage_hints(challenge: Dict[str, Any], current_score: int) -> Tuple[int, int, int]:
    """Backward compatibility function for hint management."""
    manager = ChallengeManager()
    return manager.manage_hints(challenge, current_score)

def create_challenge_template(output_path: Path) -> None:
    """Backward compatibility function for creating challenge templates."""
    manager = ChallengeManager()
    return manager.create_challenge_template(output_path)


# Export all public components
__all__ = [
    'ChallengeManager',
    'validate_challenge_structure',
    'load_challenges_from_dir',
    'list_challenges',
    'display_challenge_details', 
    'execute_setup_steps',
    'manage_hints',
    'create_challenge_template'
]