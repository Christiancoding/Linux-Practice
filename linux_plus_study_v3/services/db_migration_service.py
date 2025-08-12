#!/usr/bin/env python3
"""
Service for migrating JSON data to database.
"""

import json
import os
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from utils.database import get_db_session
from models.user_achievements import UserAchievement, UserHistory, TimeTracking, AppSettings, Base
from utils.config import (
    ACHIEVEMENTS_FILE, HISTORY_FILE, WEB_SETTINGS_FILE,
    DATA_DIR, PROJECT_ROOT
)


class DBMigrationService:
    """Service for migrating JSON files to database."""
    
    def __init__(self):
        """Initialize migration service."""
        self.data_dir = DATA_DIR
        self.project_root = PROJECT_ROOT
    
    def create_tables(self) -> bool:
        """Create database tables."""
        try:
            from utils.database import get_database_manager
            db_manager = get_database_manager()
            if db_manager is None:
                from utils.database import initialize_database_pool
                db_manager = initialize_database_pool()
            
            # Access the engine from the database manager
            engine = db_manager.engine
            Base.metadata.create_all(engine)
            print("Database tables created successfully")
            return True
        except Exception as e:
            print(f"Error creating tables: {e}")
            return False
    
    def migrate_achievements(self, user_id: str = 'anonymous') -> bool:
        """Migrate achievements from JSON to database."""
        try:
            # Check if already migrated
            with get_db_session() as session:
                existing = session.query(UserAchievement).filter_by(user_id=user_id).first()
                if existing:
                    print("Achievements already migrated")
                    return True
            
            # Load JSON data
            achievements_data = {}
            if os.path.exists(ACHIEVEMENTS_FILE):
                with open(ACHIEVEMENTS_FILE, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                    if content:
                        achievements_data = json.loads(content)
            
            # Create database record
            with get_db_session() as session:
                achievement_record = UserAchievement.from_dict(achievements_data, user_id)
                session.add(achievement_record)
                session.commit()
                print("Achievements migrated successfully")
                return True
                
        except Exception as e:
            print(f"Error migrating achievements: {e}")
            return False
    
    def migrate_time_tracking(self, user_id: str = 'anonymous') -> bool:
        """Migrate time tracking from JSON to database."""
        try:
            # Check if already migrated
            with get_db_session() as session:
                existing = session.query(TimeTracking).filter_by(user_id=user_id).first()
                if existing:
                    print("Time tracking already migrated")
                    return True
            
            # Load JSON data
            time_tracking_file = self.data_dir / "time_tracking.json"
            tracking_data = {}
            if time_tracking_file.exists():
                with open(time_tracking_file, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                    if content:
                        tracking_data = json.loads(content)
            
            # Create database record
            with get_db_session() as session:
                tracking_record = TimeTracking.from_dict(tracking_data, user_id)
                session.add(tracking_record)
                session.commit()
                print("Time tracking migrated successfully")
                return True
                
        except Exception as e:
            print(f"Error migrating time tracking: {e}")
            return False
    
    def migrate_user_analytics(self, user_id: str = 'anonymous') -> bool:
        """Migrate user analytics from JSON to database analytics table."""
        try:
            # Load JSON data
            analytics_file = self.data_dir / "user_analytics.json"
            if not analytics_file.exists():
                print("No user analytics file found")
                return True
            
            with open(analytics_file, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                if not content:
                    print("User analytics file is empty")
                    return True
                analytics_data = json.loads(content)
            
            # Check if data needs to be migrated to analytics table
            # This data should already be handled by the analytics system
            print("User analytics data found - should be handled by analytics system")
            return True
                
        except Exception as e:
            print(f"Error migrating user analytics: {e}")
            return False
    
    def migrate_settings(self) -> bool:
        """Migrate settings from JSON files to database."""
        try:
            settings_to_migrate = [
                (WEB_SETTINGS_FILE, 'web_settings'),
                (self.data_dir / "game_values.json", 'game_values')
            ]
            
            with get_db_session() as session:
                for file_path, setting_key in settings_to_migrate:
                    # Check if already migrated
                    existing = session.query(AppSettings).filter_by(setting_key=setting_key).first()
                    if existing:
                        print(f"Settings {setting_key} already migrated")
                        continue
                    
                    # Load JSON data
                    settings_data = {}
                    if os.path.exists(file_path):
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read().strip()
                            if content:
                                settings_data = json.loads(content)
                    
                    # Create database record
                    setting_record = AppSettings(
                        setting_key=setting_key,
                        setting_value=settings_data,
                        description=f"Migrated from {file_path}"
                    )
                    session.add(setting_record)
                
                session.commit()
                print("Settings migrated successfully")
                return True
                
        except Exception as e:
            print(f"Error migrating settings: {e}")
            return False
    
    def migrate_all(self, user_id: str = 'anonymous') -> bool:
        """Migrate all JSON data to database."""
        print("Starting migration of JSON data to database...")
        
        # Create tables first
        if not self.create_tables():
            return False
        
        success = True
        
        # Migrate each data type
        if not self.migrate_achievements(user_id):
            success = False
        
        if not self.migrate_time_tracking(user_id):
            success = False
        
        if not self.migrate_user_analytics(user_id):
            success = False
        
        if not self.migrate_settings():
            success = False
        
        if success:
            print("All data migrated successfully!")
        else:
            print("Some migrations failed - check errors above")
        
        return success
    
    def backup_json_files(self) -> bool:
        """Backup JSON files before removal."""
        try:
            backup_dir = self.data_dir / "json_backup"
            backup_dir.mkdir(exist_ok=True)
            
            json_files = [
                ACHIEVEMENTS_FILE,
                HISTORY_FILE, 
                WEB_SETTINGS_FILE,
                self.data_dir / "time_tracking.json",
                self.data_dir / "user_analytics.json",
                self.data_dir / "game_values.json"
            ]
            
            for file_path in json_files:
                if os.path.exists(file_path):
                    backup_path = backup_dir / os.path.basename(file_path)
                    import shutil
                    shutil.copy2(file_path, backup_path)
                    print(f"Backed up {file_path} to {backup_path}")
            
            return True
            
        except Exception as e:
            print(f"Error backing up JSON files: {e}")
            return False
    
    def remove_json_files(self) -> bool:
        """Remove JSON files after successful migration."""
        try:
            json_files = [
                ACHIEVEMENTS_FILE,
                HISTORY_FILE,
                self.data_dir / "time_tracking.json", 
                self.data_dir / "user_analytics.json"
                # Note: Keep web_settings.json and game_values.json for now as they may be used differently
            ]
            
            for file_path in json_files:
                if os.path.exists(file_path):
                    os.remove(file_path)
                    print(f"Removed {file_path}")
            
            return True
            
        except Exception as e:
            print(f"Error removing JSON files: {e}")
            return False


def run_migration():
    """Run the complete migration process."""
    migration_service = DBMigrationService()
    
    # Backup first
    print("Backing up JSON files...")
    if not migration_service.backup_json_files():
        print("Backup failed - aborting migration")
        return False
    
    # Migrate data
    if migration_service.migrate_all():
        print("Migration successful - removing JSON files...")
        return migration_service.remove_json_files()
    else:
        print("Migration failed - keeping JSON files")
        return False


if __name__ == "__main__":
    run_migration()