#!/usr/bin/env python3
"""
Populate Analytics Database with Demo Data

Creates realistic analytics data for testing the dashboard.
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta
import random
import uuid

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from models.analytics import Analytics
from utils.database import initialize_database_pool
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_demo_analytics():
    """Create demo analytics data."""
    try:
        # Initialize database
        db_manager = initialize_database_pool()
        
        with db_manager.get_session() as session:
            # Create a demo user
            demo_user_id = "demo_user_001"
            
            # Topics for Linux+ certification
            topics = [
                "File Management", "System Administration", "Network Configuration",
                "Security", "Shell Scripting", "Process Management", 
                "Package Management", "Text Processing", "System Monitoring",
                "User Management", "Permissions", "Storage Management"
            ]
            
            # Activity types
            activities = ["quiz", "practice", "study", "vm_lab"]
            
            logger.info("Creating demo analytics data...")
            
            # Create sessions for the last 30 days
            today = datetime.now()
            total_sessions = 0
            
            for days_ago in range(30):
                session_date = today - timedelta(days=days_ago)
                
                # Skip some days to make it realistic (not studying every day)
                if random.random() < 0.3:  # 30% chance to skip a day
                    continue
                
                # Create 1-3 sessions per day
                sessions_per_day = random.randint(1, 3)
                
                for _ in range(sessions_per_day):
                    session_id = str(uuid.uuid4())
                    activity_type = random.choice(activities)
                    topic = random.choice(topics)
                    
                    # Simulate session timing
                    session_start = session_date.replace(
                        hour=random.randint(9, 22),
                        minute=random.randint(0, 59),
                        second=random.randint(0, 59)
                    )
                    
                    # Session duration (5-45 minutes)
                    duration_minutes = random.randint(5, 45)
                    session_duration = duration_minutes * 60
                    session_end = session_start + timedelta(seconds=session_duration)
                    
                    # Quiz/practice specific data
                    accuracy = 0.0  # Default accuracy
                    if activity_type in ['quiz', 'practice']:
                        questions_attempted = random.randint(5, 20)
                        # Accuracy improves over time (learning effect)
                        base_accuracy = 0.6 + (0.3 * (30 - days_ago) / 30)  # 60% to 90%
                        accuracy = min(0.95, max(0.4, base_accuracy + random.uniform(-0.15, 0.15)))
                        questions_correct = int(questions_attempted * accuracy)
                        questions_incorrect = questions_attempted - questions_correct
                        time_per_question = session_duration / questions_attempted
                    else:
                        questions_attempted = 0
                        questions_correct = 0
                        questions_incorrect = 0
                        time_per_question = None
                    
                    # VM commands for vm_lab sessions
                    vm_commands = random.randint(10, 50) if activity_type == 'vm_lab' else 0
                    
                    # Create analytics record
                    analytics = Analytics(
                        user_id=demo_user_id,
                        session_id=session_id,
                        session_start=session_start,
                        session_end=session_end,
                        session_duration=session_duration,
                        activity_type=activity_type,
                        topic_area=topic,
                        difficulty_level=random.choice(['beginner', 'intermediate', 'advanced']),
                        questions_attempted=questions_attempted,
                        questions_correct=questions_correct,
                        questions_incorrect=questions_incorrect,
                        accuracy_percentage=accuracy * 100 if activity_type in ['quiz', 'practice'] else None,
                        completion_percentage=random.uniform(0.8, 1.0) * 100,
                        time_per_question=time_per_question,
                        content_pages_viewed=random.randint(0, 5) if activity_type == 'study' else 0,
                        time_on_content=session_duration if activity_type == 'study' else 0,
                        practice_commands_executed=random.randint(0, 20) if activity_type == 'practice' else 0,
                        vm_sessions_started=1 if activity_type == 'vm_lab' else 0,
                        cli_playground_usage=1 if activity_type == 'practice' else 0,
                        vm_commands_executed=vm_commands,
                        help_requests=random.randint(0, 3),
                        hint_usage=random.randint(0, 5),
                        active_learning_time=session_duration * random.uniform(0.7, 0.95)
                    )
                    
                    session.add(analytics)
                    total_sessions += 1
            
            # Also create some anonymous sessions (what currently exists)
            for days_ago in range(7):
                session_date = today - timedelta(days=days_ago)
                
                for _ in range(random.randint(1, 3)):
                    session_id = str(uuid.uuid4())
                    activity_type = random.choice(['study', 'quiz'])
                    
                    session_start = session_date.replace(
                        hour=random.randint(9, 22),
                        minute=random.randint(0, 59)
                    )
                    
                    session_duration = random.randint(300, 1800)  # 5-30 minutes
                    
                    analytics = Analytics(
                        user_id=None,  # Anonymous
                        session_id=session_id,
                        session_start=session_start,
                        session_duration=session_duration,
                        activity_type=activity_type,
                        questions_attempted=random.randint(0, 15) if activity_type == 'quiz' else 0,
                        questions_correct=random.randint(0, 12) if activity_type == 'quiz' else 0
                    )
                    
                    session.add(analytics)
                    total_sessions += 1
            
            session.commit()
            logger.info(f"✅ Created {total_sessions} demo analytics sessions")
            logger.info(f"   Demo user ID: {demo_user_id}")
            logger.info(f"   Date range: {today - timedelta(days=30)} to {today}")
            
    except Exception as e:
        logger.error(f"Error creating demo analytics: {e}")
        return False
    
    return True

def main():
    """Main entry point."""
    print("🎯 Creating Demo Analytics Data")
    print("=" * 50)
    
    if create_demo_analytics():
        print("✅ Demo analytics data created successfully!")
        print("\nNow you can:")
        print("  • View realistic analytics in the dashboard")
        print("  • Test the refresh functionality")
        print("  • See actual performance trends")
    else:
        print("❌ Failed to create demo analytics data")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
