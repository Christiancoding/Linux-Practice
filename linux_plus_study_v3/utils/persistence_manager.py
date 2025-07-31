#!/usr/bin/env python3
"""
Unified Persistence Manager for Linux+ Study System

This module provides a centralized, consistent way to handle all data persistence
operations, ensuring that personal records, settings, achievements, and history
are properly saved and loaded.
"""

import json
import os
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List, Union
import logging
from utils.config import (
    HISTORY_FILE, ACHIEVEMENTS_FILE, WEB_SETTINGS_FILE, 
    DATA_DIR, PROJECT_ROOT
)

class PersistenceManager:
    """
    Centralized persistence manager that handles all data saving and loading
    operations with consistency, error handling, and automatic backups.
    """
    
    def __init__(self):
        """Initialize the persistence manager."""
        self.logger = logging.getLogger(__name__)
        self._lock = threading.RLock()
        
        # File paths
        self.history_file = Path(HISTORY_FILE)
        self.achievements_file = Path(ACHIEVEMENTS_FILE)
        self.settings_file = Path(WEB_SETTINGS_FILE) if WEB_SETTINGS_FILE else Path(PROJECT_ROOT / "web_settings.json")
        
        # Backup directory
        self.backup_dir = Path(DATA_DIR) / "backups"
        self.backup_dir.mkdir(exist_ok=True)
        
        # In-memory cache
        self._cache: Dict[str, Any] = {}
        self._last_save_times: Dict[str, float] = {}
        
        # Auto-save settings
        self.auto_save_interval = 30  # seconds
        self.max_backups = 5
        
        self.logger.info("Persistence Manager initialized")
    
    def _ensure_file_exists(self, file_path: Path, default_content: Dict[str, Any]) -> None:
        """Ensure a file exists with default content if it doesn't."""
        try:
            if not file_path.exists():
                file_path.parent.mkdir(parents=True, exist_ok=True)
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(default_content, f, indent=2)
                self.logger.info(f"Created file with defaults: {file_path}")
        except Exception as e:
            self.logger.error(f"Error ensuring file exists {file_path}: {e}")
    
    def _create_backup(self, file_path: Path) -> Optional[Path]:
        """Create a backup of a file before modifying it."""
        try:
            if not file_path.exists():
                return None
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"{file_path.stem}_backup_{timestamp}{file_path.suffix}"
            backup_path = self.backup_dir / backup_name
            
            # Copy the file
            import shutil
            shutil.copy2(file_path, backup_path)
            
            # Clean up old backups
            self._cleanup_old_backups(file_path.stem)
            
            return backup_path
        except Exception as e:
            self.logger.error(f"Error creating backup for {file_path}: {e}")
            return None
    
    def _cleanup_old_backups(self, file_stem: str) -> None:
        """Remove old backup files, keeping only the most recent ones."""
        try:
            pattern = f"{file_stem}_backup_*"
            backup_files = sorted(
                self.backup_dir.glob(pattern),
                key=lambda x: x.stat().st_mtime,
                reverse=True
            )
            
            # Remove old backups
            for backup_file in backup_files[self.max_backups:]:
                backup_file.unlink()
                self.logger.debug(f"Removed old backup: {backup_file}")
                
        except Exception as e:
            self.logger.error(f"Error cleaning up old backups: {e}")
    
    def _safe_write_json(self, file_path: Path, data: Dict[str, Any]) -> bool:
        """Safely write JSON data to a file with backup and atomic operation."""
        with self._lock:
            try:
                # Create backup
                self._create_backup(file_path)
                
                # Ensure parent directory exists
                file_path.parent.mkdir(parents=True, exist_ok=True)
                
                # Write to temporary file first (atomic operation)
                temp_file = file_path.with_suffix('.tmp')
                with open(temp_file, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2, ensure_ascii=False, default=str)
                
                # Move temp file to actual file (atomic on most filesystems)
                temp_file.replace(file_path)
                
                # Update cache and last save time
                cache_key = str(file_path)
                self._cache[cache_key] = data.copy()
                self._last_save_times[cache_key] = time.time()
                
                self.logger.debug(f"Successfully saved data to {file_path}")
                return True
                
            except Exception as e:
                self.logger.error(f"Error writing to {file_path}: {e}")
                # Try to clean up temp file
                try:
                    temp_file = file_path.with_suffix('.tmp')
                    if temp_file.exists():
                        temp_file.unlink()
                except:
                    pass
                return False
    
    def _safe_read_json(self, file_path: Path, default_content: Dict[str, Any]) -> Dict[str, Any]:
        """Safely read JSON data from a file with fallback to defaults."""
        cache_key = str(file_path)
        
        try:
            # Check cache first
            if cache_key in self._cache:
                return self._cache[cache_key].copy()
            
            # Ensure file exists
            self._ensure_file_exists(file_path, default_content)
            
            # Read file
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Validate and merge with defaults
            merged_data = self._merge_with_defaults(data, default_content)
            
            # Cache the data
            self._cache[cache_key] = merged_data.copy()
            
            return merged_data
            
        except Exception as e:
            self.logger.error(f"Error reading {file_path}: {e}, using defaults")
            return default_content.copy()
    
    def _merge_with_defaults(self, data: Dict[str, Any], defaults: Dict[str, Any]) -> Dict[str, Any]:
        """Merge data with defaults, ensuring all required fields exist."""
        result = defaults.copy()
        
        def deep_merge(target: Dict[str, Any], source: Dict[str, Any]) -> None:
            for key, value in source.items():
                if key in target and isinstance(target[key], dict) and isinstance(value, dict):
                    deep_merge(target[key], value)
                else:
                    target[key] = value
        
        deep_merge(result, data)
        return result
    
    # History Management
    def load_history(self) -> Dict[str, Any]:
        """Load study history data."""
        default_history = {
            "questions": {},
            "categories": {},
            "sessions": [],
            "total_correct": 0,
            "total_attempts": 0,
            "incorrect_review": [],
            "leaderboard": [],
            "settings": {},
            "export_metadata": {},
            "achievements": {}
        }
        return self._safe_read_json(self.history_file, default_history)
    
    def save_history(self, history_data: Dict[str, Any]) -> bool:
        """Save study history data."""
        return self._safe_write_json(self.history_file, history_data)
    
    # Achievements Management
    def load_achievements(self) -> Dict[str, Any]:
        """Load achievements data."""
        default_achievements = {
            "badges": [],
            "points_earned": 0,
            "days_studied": [],
            "questions_answered": 0,
            "streaks_achieved": 0,
            "perfect_sessions": 0,
            "daily_warrior_dates": [],
            "leaderboard": []
        }
        return self._safe_read_json(self.achievements_file, default_achievements)
    
    def save_achievements(self, achievements_data: Dict[str, Any]) -> bool:
        """Save achievements data."""
        # Convert sets to lists for JSON serialization
        processed_data = achievements_data.copy()
        if "days_studied" in processed_data and hasattr(processed_data["days_studied"], '__iter__'):
            if not isinstance(processed_data["days_studied"], list):
                processed_data["days_studied"] = list(processed_data["days_studied"])
        
        return self._safe_write_json(self.achievements_file, processed_data)
    
    # Settings Management
    def load_settings(self) -> Dict[str, Any]:
        """Load application settings."""
        default_settings = {
            "focusMode": False,
            "breakReminder": 10,
            "debugMode": False,
            "pointsPerQuestion": 10,
            "streakBonus": 5,
            "maxStreakBonus": 50,
            "vmDefaults": {
                "memory": 2,
                "memoryUnit": "GB",
                "cpus": 2,
                "disk": 20,
                "diskUnit": "GB",
                "autoDownloadIso": False,
                "autoStart": False,
                "defaultTemplate": "ubuntu-22.04"
            },
            "isoDownloads": {
                "enabled": False,
                "downloadPath": str(Path.home() / "Downloads"),
                "urls": {}
            }
        }
        return self._safe_read_json(self.settings_file, default_settings)
    
    def save_settings(self, settings_data: Dict[str, Any]) -> bool:
        """Save application settings."""
        return self._safe_write_json(self.settings_file, settings_data)
    
    # Unified Save/Load Operations
    def save_all_data(self, history_data: Optional[Dict[str, Any]] = None,
                     achievements_data: Optional[Dict[str, Any]] = None,
                     settings_data: Optional[Dict[str, Any]] = None) -> Dict[str, bool]:
        """Save all data in a single operation."""
        results = {}
        
        with self._lock:
            if history_data is not None:
                results['history'] = self.save_history(history_data)
            
            if achievements_data is not None:
                results['achievements'] = self.save_achievements(achievements_data)
            
            if settings_data is not None:
                results['settings'] = self.save_settings(settings_data)
        
        return results
    
    def load_all_data(self) -> Dict[str, Dict[str, Any]]:
        """Load all data in a single operation."""
        return {
            'history': self.load_history(),
            'achievements': self.load_achievements(),
            'settings': self.load_settings()
        }
    
    # Leaderboard Management (unified across history and achievements)
    def get_leaderboard(self) -> List[Dict[str, Any]]:
        """Get unified leaderboard data."""
        # Try to get from achievements first (primary source)
        achievements = self.load_achievements()
        leaderboard = achievements.get("leaderboard", [])
        
        # If empty, try to get from history (backup)
        if not leaderboard:
            history = self.load_history()
            leaderboard = history.get("leaderboard", [])
        
        return leaderboard
    
    def save_leaderboard(self, leaderboard_data: List[Dict[str, Any]]) -> bool:
        """Save leaderboard data to both achievements and history."""
        success = True
        
        # Save to achievements (primary)
        achievements = self.load_achievements()
        achievements["leaderboard"] = leaderboard_data
        success &= self.save_achievements(achievements)
        
        # Save to history (backup/sync)
        history = self.load_history()
        history["leaderboard"] = leaderboard_data
        success &= self.save_history(history)
        
        return success
    
    # Data Integrity and Maintenance
    def validate_data_integrity(self) -> Dict[str, Any]:
        """Validate the integrity of all data files."""
        results = {
            "valid": True,
            "issues": [],
            "fixes_applied": []
        }
        
        try:
            # Check history file
            history = self.load_history()
            if "leaderboard" not in history:
                history["leaderboard"] = []
                self.save_history(history)
                results["fixes_applied"].append("Added missing leaderboard to history")
            
            # Check achievements file
            achievements = self.load_achievements()
            if "leaderboard" not in achievements:
                achievements["leaderboard"] = []
                self.save_achievements(achievements)
                results["fixes_applied"].append("Added missing leaderboard to achievements")
            
            # Sync leaderboards if they differ
            hist_lb = history.get("leaderboard", [])
            ach_lb = achievements.get("leaderboard", [])
            
            if hist_lb != ach_lb:
                # Use the one with more data or achievements as primary
                primary_lb = ach_lb if len(ach_lb) >= len(hist_lb) else hist_lb
                self.save_leaderboard(primary_lb)
                results["fixes_applied"].append("Synchronized leaderboard data")
            
            # Check settings file
            settings = self.load_settings()
            required_settings = ["pointsPerQuestion", "streakBonus", "maxStreakBonus"]
            for setting in required_settings:
                if setting not in settings:
                    results["issues"].append(f"Missing setting: {setting}")
                    results["valid"] = False
            
        except Exception as e:
            results["valid"] = False
            results["issues"].append(f"Validation error: {e}")
        
        return results
    
    def export_all_data(self, export_path: Optional[Path] = None) -> Path:
        """Export all data to a single JSON file."""
        if export_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            export_path = Path(f"linux_plus_export_{timestamp}.json")
        
        all_data = self.load_all_data()
        all_data["export_metadata"] = {
            "export_date": datetime.now().isoformat(),
            "version": "2.0",
            "source": "PersistenceManager"
        }
        
        with open(export_path, 'w', encoding='utf-8') as f:
            json.dump(all_data, f, indent=2, ensure_ascii=False, default=str)
        
        return export_path
    
    def import_all_data(self, import_path: Path) -> Dict[str, Any]:
        """Import data from a JSON file."""
        try:
            with open(import_path, 'r', encoding='utf-8') as f:
                imported_data = json.load(f)
            
            results = {"success": True, "imported": []}
            
            if "history" in imported_data:
                if self.save_history(imported_data["history"]):
                    results["imported"].append("history")
            
            if "achievements" in imported_data:
                if self.save_achievements(imported_data["achievements"]):
                    results["imported"].append("achievements")
            
            if "settings" in imported_data:
                if self.save_settings(imported_data["settings"]):
                    results["imported"].append("settings")
            
            # Clear cache to force reload
            self._cache.clear()
            
            return results
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def clear_cache(self) -> None:
        """Clear the in-memory cache."""
        with self._lock:
            self._cache.clear()
            self._last_save_times.clear()

# Global instance
_persistence_manager: Optional[PersistenceManager] = None

def get_persistence_manager() -> PersistenceManager:
    """Get the global persistence manager instance."""
    global _persistence_manager
    if _persistence_manager is None:
        _persistence_manager = PersistenceManager()
    return _persistence_manager

def initialize_persistence() -> PersistenceManager:
    """Initialize and validate the persistence system."""
    manager = get_persistence_manager()
    
    # Validate data integrity on startup
    validation_result = manager.validate_data_integrity()
    if validation_result["fixes_applied"]:
        logging.info(f"Applied persistence fixes: {validation_result['fixes_applied']}")
    
    if not validation_result["valid"]:
        logging.warning(f"Data integrity issues found: {validation_result['issues']}")
    
    return manager
