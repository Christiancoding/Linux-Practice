#!/usr/bin/env python3
"""
Game Value Configuration System for Linux+ Study Game.
Centralizes all hardcoded display values, thresholds, and game mechanics.
"""
from typing import Dict, Any, Optional
from pathlib import Path
import json
from dataclasses import dataclass, asdict, field

@dataclass
class ScoringSettings:
    """Scoring system configuration."""
    points_per_correct: int = 10
    points_per_incorrect: int = 0
    hint_penalty: int = 5
    speed_bonus: int = 5
    streak_bonus: int = 5
    max_streak_bonus: int = 50
    streak_bonus_threshold: int = 3
    streak_bonus_multiplier: float = 2.0
    perfect_quiz_bonus: int = 25
    daily_challenge_bonus: int = 50
    default_challenge_score: int = 100
    achievement_point_threshold: int = 500
    achievement_question_threshold: int = 100

@dataclass
class StreakSettings:
    """Streak system configuration."""
    daily_streak_threshold: int = 3
    weekly_streak_threshold: int = 7
    streak_display_threshold: int = 3
    default_streak_value: int = 0
    
@dataclass
class QuizSettings:
    """Quiz mechanics configuration."""
    default_question_count: int = 10
    max_question_count: int = 50
    min_question_count: int = 1
    quick_fire_count: int = 5
    time_per_question: int = 30
    strike_limit: int = 3
    survival_mode_strikes: int = 3
    timed_challenge_seconds: int = 30

@dataclass
class AccuracySettings:
    """Accuracy display and thresholds."""
    excellent_threshold: int = 90
    good_threshold: int = 75
    average_threshold: int = 50
    passing_percentage: int = 70
    perfect_score_percentage: int = 100

@dataclass
class LevelSettings:
    """Level and XP system configuration."""
    default_level: int = 0
    default_xp: int = 0
    legendary_achievement_xp: int = 100
    easter_egg_bonus_xp: int = 100

@dataclass
class DisplaySettings:
    """Display value defaults and fallbacks."""
    default_questions_display: int = 0
    default_score_display: int = 0
    default_percentage_display: int = 0
    activity_level_low: float = 0.2
    activity_level_medium: float = 0.4
    activity_level_high: float = 0.6
    activity_level_max: float = 0.8

@dataclass
class TimeSettings:
    """Time-based configuration."""
    file_cleanup_days: int = 30
    stats_week_days: int = 7
    stats_month_days: int = 30
    calendar_year_days: int = 365
    dashboard_calendar_days: int = 35
    session_timeout_hours: int = 1
    break_reminder_minutes: int = 10

@dataclass
class LeaderboardSettings:
    """Leaderboard and achievement configuration."""
    max_entries: int = 100
    top_sessions_limit: int = 10
    achievement_progress_display: str = "8/20 achievements"

@dataclass
class GameValueSettings:
    """Complete game value configuration."""
    scoring: ScoringSettings = field(default_factory=ScoringSettings)
    streaks: StreakSettings = field(default_factory=StreakSettings)
    quiz: QuizSettings = field(default_factory=QuizSettings)
    accuracy: AccuracySettings = field(default_factory=AccuracySettings)
    levels: LevelSettings = field(default_factory=LevelSettings)
    display: DisplaySettings = field(default_factory=DisplaySettings)
    time: TimeSettings = field(default_factory=TimeSettings)
    leaderboard: LeaderboardSettings = field(default_factory=LeaderboardSettings)

class GameValueManager:
    """Manages game value configuration with persistence."""
    
    def __init__(self, config_file: Optional[Path] = None):
        self.config_file = config_file or Path("data/game_values.json")
        self._settings = self._load_settings()
    
    def _load_settings(self) -> GameValueSettings:
        """Load settings from file or create defaults."""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    data = json.load(f)
                return self._dict_to_settings(data)
            except (json.JSONDecodeError, KeyError, TypeError) as e:
                print(f"Error loading game values config: {e}. Using defaults.")
        
        return GameValueSettings()
    
    def _dict_to_settings(self, data: Dict[str, Any]) -> GameValueSettings:
        """Convert dictionary to GameValueSettings."""
        settings = GameValueSettings()
        
        if 'scoring' in data:
            settings.scoring = ScoringSettings(**data['scoring'])
        if 'streaks' in data:
            settings.streaks = StreakSettings(**data['streaks'])
        if 'quiz' in data:
            settings.quiz = QuizSettings(**data['quiz'])
        if 'accuracy' in data:
            settings.accuracy = AccuracySettings(**data['accuracy'])
        if 'levels' in data:
            settings.levels = LevelSettings(**data['levels'])
        if 'display' in data:
            settings.display = DisplaySettings(**data['display'])
        if 'time' in data:
            settings.time = TimeSettings(**data['time'])
        if 'leaderboard' in data:
            settings.leaderboard = LeaderboardSettings(**data['leaderboard'])
            
        return settings
    
    def save_settings(self) -> bool:
        """Save current settings to file."""
        try:
            self.config_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_file, 'w') as f:
                json.dump(asdict(self._settings), f, indent=2)
            return True
        except Exception as e:
            print(f"Error saving game values config: {e}")
            return False
    
    def get_settings(self) -> GameValueSettings:
        """Get current settings."""
        return self._settings
    
    def update_settings(self, **kwargs: Any) -> bool:
        """Update settings with new values."""
        try:
            for category, values in kwargs.items():
                if hasattr(self._settings, category) and isinstance(values, dict):
                    category_obj = getattr(self._settings, category)
                    for key, value in values.items():
                        if hasattr(category_obj, key):
                            setattr(category_obj, key, value)
            return self.save_settings()
        except Exception as e:
            print(f"Error updating game values: {e}")
            return False
    
    def reset_to_defaults(self) -> bool:
        """Reset all settings to defaults."""
        self._settings = GameValueSettings()
        return self.save_settings()
    
    def get_value(self, category: str, key: str, default: Any = None) -> Any:
        """Get a specific value from the configuration."""
        try:
            category_obj = getattr(self._settings, category)
            return getattr(category_obj, key, default)
        except AttributeError:
            return default
    
    def get_scoring_config(self) -> Dict[str, Any]:
        """Get scoring configuration as dictionary for templates."""
        return asdict(self._settings.scoring)
    
    def get_all_config(self) -> Dict[str, Any]:
        """Get all configuration as dictionary for templates."""
        return asdict(self._settings)

# Global instance
_game_value_manager = None

def get_game_value_manager() -> GameValueManager:
    """Get the global game value manager instance."""
    global _game_value_manager
    if _game_value_manager is None:
        _game_value_manager = GameValueManager()
    return _game_value_manager

def get_game_value(category: str, key: str, default: Any = None) -> Any:
    """Convenience function to get a game value."""
    return get_game_value_manager().get_value(category, key, default)

# Template helper functions for backward compatibility
def get_points_per_correct() -> int:
    """Get points per correct answer."""
    return get_game_value('scoring', 'points_per_correct', 10)

def get_streak_bonus() -> int:
    """Get streak bonus points."""
    return get_game_value('scoring', 'streak_bonus', 5)

def get_hint_penalty() -> int:
    """Get hint penalty points."""
    return get_game_value('scoring', 'hint_penalty', 5)

def get_default_question_count() -> int:
    """Get default number of questions."""
    return get_game_value('quiz', 'default_question_count', 10)

def get_streak_threshold() -> int:
    """Get streak bonus threshold."""
    return get_game_value('scoring', 'streak_bonus_threshold', 3)
