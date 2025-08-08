#!/usr/bin/env python3
"""
Challenge Runner Controller

Executes practice challenges on virtual machines with comprehensive
error handling and progress tracking functionality.
"""

import sys
import logging
import time
from typing import Dict, Any, Optional
from pathlib import Path

# Ensure Python 3 compatibility
if sys.version_info < (3, 8):
    print("This script requires Python 3.8+. Please upgrade.")
    sys.exit(1)

class ChallengeRunner:
    """Advanced challenge execution and management system."""
    
    def __init__(self):
        """Initialize challenge runner with proper logging infrastructure."""
        self._setup_logging()
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    def _setup_logging(self) -> None:
        """Configure comprehensive logging infrastructure."""
        try:
            logging.basicConfig(
                level=logging.INFO,
                format='%(asctime)s - %(name)s - %(levelname)s: %(message)s',
                handlers=[
                    logging.StreamHandler(),
                    logging.FileHandler('challenge_runner.log', mode='a')
                ]
            )
        except PermissionError:
            # Fallback to console-only logging if file access fails
            logging.basicConfig(
                level=logging.INFO,
                format='%(asctime)s - %(name)s - %(levelname)s: %(message)s',
                handlers=[logging.StreamHandler()]
            )
    
    def run_challenge(self, challenge_path: Path, vm_name: str, 
                     libvirt_uri: str = "qemu:///system") -> Dict[str, Any]:
        """
        Execute a practice challenge on specified virtual machine.
        
        Args:
            challenge_path: Path to challenge YAML file
            vm_name: Target virtual machine name
            libvirt_uri: Libvirt connection URI
            
        Returns:
            Dict containing execution results and status information
        """
        try:
            self.logger.info(f"Starting challenge execution: {challenge_path.name} on VM: {vm_name}")
            
            # Validate challenge file exists
            if not challenge_path.exists():
                error_msg = f"Challenge file not found: {challenge_path}"
                self.logger.error(error_msg)
                return {
                    'success': False,
                    'error': error_msg,
                    'execution_time': 0
                }
            
            # Load and validate challenge configuration
            challenge_config = self._load_challenge_config(challenge_path)
            if not challenge_config:
                return {
                    'success': False,
                    'error': "Failed to load challenge configuration",
                    'execution_time': 0
                }
            
            # Execute challenge steps
            start_time = time.time()
            execution_result = self._execute_challenge_steps(
                challenge_config, vm_name, libvirt_uri
            )
            execution_time = time.time() - start_time
            
            self.logger.info(f"Challenge execution completed in {execution_time:.2f}s")
            
            return {
                'success': execution_result['success'],
                'message': execution_result.get('message', 'Challenge execution completed'),
                'execution_time': execution_time,
                'steps_completed': execution_result.get('steps_completed', 0),
                'total_steps': execution_result.get('total_steps', 0)
            }
            
        except Exception as e:
            error_msg = f"Challenge execution failed: {e}"
            self.logger.error(error_msg, exc_info=True)
            return {
                'success': False,
                'error': error_msg,
                'execution_time': 0
            }
    
    def _load_challenge_config(self, challenge_path: Path) -> Optional[Dict[str, Any]]:
        """Load and validate challenge configuration from YAML file."""
        try:
            import yaml
            
            with open(challenge_path, 'r', encoding='utf-8') as file:
                config = yaml.safe_load(file)
            
            # Basic validation
            required_fields = ['name', 'description', 'steps']
            for field in required_fields:
                if field not in config:
                    self.logger.error(f"Missing required field in challenge: {field}")
                    return None
            
            return config
            
        except ImportError:
            self.logger.error("PyYAML not installed. Install with: pip install pyyaml")
            return None
        except Exception as e:
            self.logger.error(f"Error loading challenge config: {e}")
            return None
    
    def _execute_challenge_steps(self, config: Dict[str, Any], vm_name: str, 
                                libvirt_uri: str) -> Dict[str, Any]:
        """Execute individual challenge steps with progress tracking."""
        try:
            steps = config.get('steps', [])
            total_steps = len(steps)
            completed_steps = 0
            
            self.logger.info(f"Executing {total_steps} challenge steps")
            
            for i, step in enumerate(steps, 1):
                try:
                    self.logger.info(f"Executing step {i}/{total_steps}: {step.get('name', 'Unnamed step')}")
                    
                    # Simulate step execution (replace with actual implementation)
                    time.sleep(0.5)  # Simulate processing time
                    completed_steps += 1
                    
                except Exception as step_error:
                    self.logger.error(f"Step {i} failed: {step_error}")
                    return {
                        'success': False,
                        'message': f"Challenge failed at step {i}: {step_error}",
                        'steps_completed': completed_steps,
                        'total_steps': total_steps
                    }
            
            return {
                'success': True,
                'message': f"Challenge completed successfully ({completed_steps}/{total_steps} steps)",
                'steps_completed': completed_steps,
                'total_steps': total_steps
            }
            
        except Exception as e:
            self.logger.error(f"Error executing challenge steps: {e}")
            return {
                'success': False,
                'message': f"Challenge execution error: {e}",
                'steps_completed': 0,
                'total_steps': 0
            }