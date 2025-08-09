#!/usr/bin/env python3
"""
Populate Analytics with Demo Data for Dashboard Testing

This script creates realistic demo data in the analytics database
to properly showcase the analytics dashboard functionality.
"""

import sys
import os
from datetime import datetime, timedelta
from typing import List, Dict, Any
import random

# Add project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils.database import get_database_manager
from models.analytics import Analytics

def create_demo_analytics_data():
    """Create comprehensive demo analytics data."""
    print("🔧 Creating demo analytics data...")
    
    # Initialize database manager
    try:
        from utils.database import DatabasePoolManager
        db_manager = DatabasePoolManager(db_type="sqlite", enable_pooling=False)
        
        if not db_manager or not db_manager.session_factory:
            print("❌ Database manager not available")
            return False
    except Exception as e:
        print(f"❌ Failed to initialize database: {e}")
        return False
    
    session = db_manager.session_factory()
    try:
        # Clear existing demo data first
        session.query(Analytics).filter(Analytics.user_id == 'demo_user_001').delete()
        session.commit()
        
        # Create demo user data over the past 30 days
        base_date = datetime.now() - timedelta(days=30)
        
        # Demo topics and their relative difficulty (affects accuracy)
        topics = {
            'File Management': 0.85,
            'System Administration': 0.78,
            'Network Configuration': 0.72,
            'Security': 0.88,
            'Shell Scripting': 0.74,
            'Process Management': 0.82,
            'Package Management': 0.79,
            'Text Processing': 0.81
        }
        
        analytics_records = []
        total_sessions = 0
        
        # Generate realistic study pattern (not every day, but regular)
        for day in range(30):
            current_date = base_date + timedelta(days=day)
            
            # Skip some days randomly (realistic usage pattern)
            if random.random() < 0.3:  # 30% chance to skip a day
                continue
            
            # Generate 1-3 sessions per active day
            sessions_today = random.randint(1, 3)
            
            for session_num in range(sessions_today):
                session_start = current_date.replace(
                    hour=random.randint(8, 22),
                    minute=random.randint(0, 59),
                    second=random.randint(0, 59)
                )
                
                # Vary session length (3-15 minutes)
                session_duration = random.randint(180, 900)
                
                # Generate quiz session
                questions_in_session = random.randint(5, 12)
                
                # Select random topics for this session
                session_topics = random.sample(list(topics.keys()), min(3, len(topics)))
                
                for topic in session_topics:
                    # Questions per topic in this session
                    topic_questions = random.randint(2, 4)
                    base_accuracy = topics[topic]
                    
                    # Add some random variation to accuracy (±10%)
                    session_accuracy = base_accuracy + random.uniform(-0.1, 0.1)
                    session_accuracy = max(0.5, min(0.95, session_accuracy))  # Keep realistic bounds
                    
                    questions_correct = int(topic_questions * session_accuracy)
                    
                    # Create analytics record for this topic session
                    analytics_record = Analytics(
                        user_id='demo_user_001',
                        session_id=f'demo_session_{total_sessions}_{topic.replace(" ", "_").lower()}',
                        session_start=session_start,
                        session_end=session_start + timedelta(seconds=session_duration),
                        activity_type='quiz',
                        topic_area=topic,
                        questions_attempted=topic_questions,
                        questions_correct=questions_correct,
                        session_duration=session_duration // len(session_topics),  # Divide duration among topics
                        accuracy_percentage=session_accuracy,
                        created_at=session_start,
                        updated_at=session_start,
                        # Additional metadata
                        device_type='desktop',
                        browser_info='Mozilla/5.0 (Linux) Demo Analytics Generator',
                        custom_metrics={
                            'quiz_mode': 'standard',
                            'difficulty_level': 'mixed',
                            'session_type': 'practice'
                        }
                    )
                    
                    analytics_records.append(analytics_record)
                
                total_sessions += 1
        
        # Add some VM practice sessions
        for _ in range(15):
            vm_date = base_date + timedelta(days=random.randint(0, 29))
            vm_session_start = vm_date.replace(
                hour=random.randint(9, 21),
                minute=random.randint(0, 59)
            )
            
            vm_commands = random.randint(8, 25)
            vm_duration = random.randint(300, 1800)  # 5-30 minutes
            
            vm_record = Analytics(
                user_id='demo_user_001',
                session_id=f'demo_vm_session_{random.randint(1000, 9999)}',
                session_start=vm_session_start,
                session_end=vm_session_start + timedelta(seconds=vm_duration),
                activity_type='vm_lab',
                vm_commands_executed=vm_commands,
                session_duration=vm_duration,
                created_at=vm_session_start,
                updated_at=vm_session_start,
                device_type='desktop',
                browser_info='Mozilla/5.0 (Linux) VM Practice Session',
                custom_metrics={
                    'vm_type': 'ubuntu',
                    'practice_type': 'hands_on',
                    'commands_successful': int(vm_commands * 0.85)
                }
            )
            analytics_records.append(vm_record)
        
        # Add some study/reading sessions
        for _ in range(8):
            study_date = base_date + timedelta(days=random.randint(0, 29))
            study_start = study_date.replace(
                hour=random.randint(10, 20),
                minute=random.randint(0, 59)
            )
            
            study_duration = random.randint(600, 2400)  # 10-40 minutes
            
            study_record = Analytics(
                user_id='demo_user_001',
                session_id=f'demo_study_session_{random.randint(1000, 9999)}',
                session_start=study_start,
                session_end=study_start + timedelta(seconds=study_duration),
                activity_type='study',
                session_duration=study_duration,
                created_at=study_start,
                updated_at=study_start,
                device_type='desktop',
                browser_info='Mozilla/5.0 (Linux) Study Session',
                custom_metrics={
                    'content_type': 'documentation',
                    'study_focus': random.choice(['concepts', 'commands', 'troubleshooting'])
                }
            )
            analytics_records.append(study_record)
        
        # Batch insert all records
        session.add_all(analytics_records)
        session.commit()
        
        print(f"✅ Created {len(analytics_records)} demo analytics records")
        print(f"📊 Demo user: demo_user_001")
        print(f"📈 Total quiz sessions: {total_sessions}")
        print(f"🖥️  VM practice sessions: 15")
        print(f"📚 Study sessions: 8")
        
        # Show summary stats
        total_questions = sum(r.questions_attempted or 0 for r in analytics_records)
        total_correct = sum(r.questions_correct or 0 for r in analytics_records)
        overall_accuracy = (total_correct / total_questions * 100) if total_questions > 0 else 0
        
        print(f"\n📋 Summary Statistics:")
        print(f"   Total Questions: {total_questions}")
        print(f"   Total Correct: {total_correct}")
        print(f"   Overall Accuracy: {overall_accuracy:.1f}%")
        print(f"   Total Study Time: {sum(r.session_duration or 0 for r in analytics_records) / 3600:.1f} hours")
        
        return True
        
    except Exception as e:
        print(f"❌ Error creating demo data: {e}")
        session.rollback()
        return False
    finally:
        session.close()

def verify_demo_data():
    """Verify the demo data was created correctly."""
    print("\n🔍 Verifying demo data...")
    
    try:
        from utils.database import DatabasePoolManager
        db_manager = DatabasePoolManager(db_type="sqlite", enable_pooling=False)
        
        if not db_manager or not db_manager.session_factory:
            print("❌ Database manager not available")
            return False
    except Exception as e:
        print(f"❌ Failed to initialize database: {e}")
        return False
    
    session = db_manager.session_factory()
    try:
        # Query demo user data
        demo_records = session.query(Analytics).filter(Analytics.user_id == 'demo_user_001').all()
        
        if not demo_records:
            print("❌ No demo records found")
            return False
        
        # Calculate summary stats
        total_questions = sum(r.questions_attempted or 0 for r in demo_records)
        total_correct = sum(r.questions_correct or 0 for r in demo_records)
        total_duration = sum(r.session_duration or 0 for r in demo_records)
        vm_commands = sum(r.vm_commands_executed or 0 for r in demo_records)
        
        # Count by activity type
        activity_counts = {}
        for record in demo_records:
            activity_type = record.activity_type or 'unknown'
            activity_counts[activity_type] = activity_counts.get(activity_type, 0) + 1
        
        print(f"✅ Found {len(demo_records)} demo records")
        print(f"📊 Questions: {total_questions} ({total_correct} correct)")
        print(f"⏱️  Total time: {total_duration / 3600:.1f} hours")
        print(f"💻 VM commands: {vm_commands}")
        print(f"📈 Activities: {activity_counts}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error verifying demo data: {e}")
        return False
    finally:
        session.close()

def main():
    """Main execution function."""
    print("🎯 Analytics Demo Data Population Tool")
    print("=" * 50)
    
    success = create_demo_analytics_data()
    if success:
        verify_demo_data()
        print("\n🎉 Demo analytics data creation completed successfully!")
        print("   The analytics dashboard should now show proper data.")
    else:
        print("\n❌ Failed to create demo analytics data")
        sys.exit(1)

if __name__ == "__main__":
    main()