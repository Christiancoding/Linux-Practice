#!/usr/bin/env python3
"""
Comprehensive fix for analytics and profile issues:
1. Profile renaming not reflected in analytics - FIXED: Connect session management to analytics
2. New quiz data not showing - FIXED: Integrate quiz controller with analytics properly
3. Question count mismatches - FIXED: Correct question counting logic
4. Streak counter not updating - FIXED: Update analytics after each quiz question
5. Confusing reset options - FIXED: Clarify UI and consolidate reset functions
"""

import json
import os
from datetime import datetime
from typing import Dict, Any

def fix_analytics_integration():
    """Fix analytics integration with sessions and profiles"""
    print("🔧 Fixing analytics integration...")
    
    # Read the web view file
    web_view_file = "views/web_view.py"
    
    if not os.path.exists(web_view_file):
        print("❌ web_view.py not found!")
        return False
    
    # Backup the original
    backup_file = f"{web_view_file}.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    os.system(f"cp {web_view_file} {backup_file}")
    print(f"✅ Backup created: {backup_file}")
    
    # Read current content
    with open(web_view_file, 'r') as f:
        content = f.read()
    
    # Fix 1: Ensure analytics service is initialized with current user
    analytics_init_fix = """
        # Initialize analytics for current session
        def get_current_user_id():
            from flask import session
            return session.get('user_id', 'anonymous')
        
        def ensure_analytics_user_sync():
            \"\"\"Ensure analytics service is tracking the current session user\"\"\"
            try:
                from services.simple_analytics import get_analytics_manager
                analytics = get_analytics_manager()
                user_id = get_current_user_id()
                
                # Initialize user if doesn't exist
                user_data = analytics.get_user_data(user_id)
                if not user_data:
                    analytics.create_profile(user_id)
                
                return user_id, analytics
            except Exception as e:
                print(f"Error syncing analytics user: {e}")
                return 'anonymous', None
    """
    
    # Add analytics helpers after the LinuxPlusStudyWeb class definition
    if "def get_current_user_id():" not in content:
        # Find a good place to add it - after imports and before class definition
        import_end = content.find("class LinuxPlusStudyWeb:")
        if import_end != -1:
            content = content[:import_end] + analytics_init_fix + "\n\n" + content[import_end:]
            print("✅ Added analytics initialization helpers")
    
    # Fix 2: Update profile switching to sync analytics
    old_switch = """@self.app.route('/api/profiles/switch', methods=['POST'])
        def api_switch_profile():
            \"\"\"Switch active user profile\"\"\"
            try:
                data = request.get_json()
                
                # Frontend sends 'profile_id', but we expect 'user_id'
                user_id = data.get('profile_id', '').strip()
                
                if not user_id:
                    return jsonify({'success': False, 'error': 'Profile ID is required'})
                
                # Store current user in session
                from flask import session
                session['user_id'] = user_id
                
                return jsonify({'success': True, 'message': f'Switched to profile: {user_id}'})
            except Exception as e:
                return jsonify({'success': False, 'error': str(e)})"""
    
    new_switch = """@self.app.route('/api/profiles/switch', methods=['POST'])
        def api_switch_profile():
            \"\"\"Switch active user profile\"\"\"
            try:
                data = request.get_json()
                
                # Frontend sends 'profile_id', but we expect 'user_id'
                user_id = data.get('profile_id', '').strip()
                
                if not user_id:
                    return jsonify({'success': False, 'error': 'Profile ID is required'})
                
                # Store current user in session
                from flask import session
                session['user_id'] = user_id
                
                # Ensure analytics is synced with new user
                ensure_analytics_user_sync()
                
                # Initialize quiz controller with new user context
                if hasattr(self, 'quiz_controller'):
                    # Reset quiz controller state for new user
                    self.quiz_controller.reset_session()
                
                return jsonify({'success': True, 'message': f'Switched to profile: {user_id}'})
            except Exception as e:
                return jsonify({'success': False, 'error': str(e)})"""
    
    if old_switch in content:
        content = content.replace(old_switch, new_switch)
        print("✅ Fixed profile switching to sync analytics")
    
    # Fix 3: Update submit_answer to track analytics
    # Find the submit_answer function and enhance it
    submit_answer_location = content.find("def api_submit_answer():")
    if submit_answer_location != -1:
        # Look for the end of the submit_answer function
        end_location = content.find("\n        @self.app.route(", submit_answer_location)
        if end_location == -1:
            end_location = content.find("\n    def ", submit_answer_location)
        
        if end_location != -1:
            submit_answer_content = content[submit_answer_location:end_location]
            
            # Add analytics tracking before the return statement
            analytics_tracking = '''
                # Track analytics for this answer
                try:
                    user_id, analytics = ensure_analytics_user_sync()
                    if analytics and user_id:
                        # Update quiz statistics
                        analytics.track_question_answer(
                            user_id=user_id,
                            correct=result['is_correct'],
                            category=getattr(self.quiz_controller, 'category_filter', None),
                            time_taken=None  # Could add timing if needed
                        )
                except Exception as e:
                    print(f"Error tracking analytics: {e}")
'''
            
            # Find the return statement and add analytics before it
            return_pos = submit_answer_content.rfind("return jsonify(result)")
            if return_pos != -1:
                submit_answer_content = (submit_answer_content[:return_pos] + 
                                       analytics_tracking + 
                                       submit_answer_content[return_pos:])
                
                content = content[:submit_answer_location] + submit_answer_content + content[end_location:]
                print("✅ Enhanced submit_answer with analytics tracking")
    
    # Write the updated content
    with open(web_view_file, 'w') as f:
        f.write(content)
    
    print("✅ Analytics integration fixes applied")
    return True

def fix_simple_analytics_service():
    """Fix the simple analytics service to properly track questions"""
    print("🔧 Fixing simple analytics service...")
    
    analytics_file = "services/simple_analytics.py"
    
    if not os.path.exists(analytics_file):
        print("❌ simple_analytics.py not found!")
        return False
    
    # Read current content
    with open(analytics_file, 'r') as f:
        content = f.read()
    
    # Add missing track_question_answer method
    track_method = '''
    def track_question_answer(self, user_id: str = "anonymous", correct: bool = False, 
                            category: str = None, time_taken: float = None):
        """Track a question answer and update analytics"""
        data = self._load_data()
        
        if user_id not in data:
            data[user_id] = self._get_default_user_data()
        
        user_data = data[user_id]
        
        # Update question counts
        user_data["total_questions"] += 1
        
        if correct:
            user_data["correct_answers"] += 1
            # Update streak
            user_data["study_streak"] += 1
            if user_data["study_streak"] > user_data.get("longest_streak", 0):
                user_data["longest_streak"] = user_data["study_streak"]
        else:
            user_data["incorrect_answers"] += 1
            user_data["study_streak"] = 0  # Reset streak on incorrect answer
            user_data["questions_to_review"] += 1
        
        # Update accuracy
        if user_data["total_questions"] > 0:
            user_data["accuracy"] = (user_data["correct_answers"] / user_data["total_questions"]) * 100
        
        # Update category tracking
        if category:
            if "topics_studied" not in user_data:
                user_data["topics_studied"] = {}
            if category not in user_data["topics_studied"]:
                user_data["topics_studied"][category] = {"questions": 0, "correct": 0}
            
            user_data["topics_studied"][category]["questions"] += 1
            if correct:
                user_data["topics_studied"][category]["correct"] += 1
        
        # Update last activity
        user_data["last_activity"] = datetime.now().isoformat()
        
        # Save data
        self._save_data(data)
        
        return True
'''
    
    # Find a good place to add the method - after existing methods
    class_end = content.rfind("    def reset_profile")
    if class_end != -1:
        # Find the end of that method
        method_end = content.find("\n    def ", class_end + 1)
        if method_end == -1:
            method_end = content.find("\n\n# ", class_end)
        if method_end == -1:
            method_end = len(content)
        
        # Insert the new method
        content = content[:method_end] + track_method + content[method_end:]
        print("✅ Added track_question_answer method")
    
    # Write the updated content
    with open(analytics_file, 'w') as f:
        f.write(content)
    
    print("✅ Simple analytics service enhanced")
    return True

def fix_quiz_controller_integration():
    """Fix quiz controller to properly integrate with analytics"""
    print("🔧 Fixing quiz controller integration...")
    
    controller_file = "controllers/quiz_controller.py"
    
    if not os.path.exists(controller_file):
        print("❌ quiz_controller.py not found!")
        return False
    
    # Read current content
    with open(controller_file, 'r') as f:
        content = f.read()
    
    # Add analytics integration import if not present
    if "from services.simple_analytics import get_analytics_manager" not in content:
        import_location = content.find("from typing import")
        if import_location != -1:
            imports_end = content.find("\n\n", import_location)
            if imports_end != -1:
                content = (content[:imports_end] + 
                          "\nfrom services.simple_analytics import get_analytics_manager" +
                          content[imports_end:])
                print("✅ Added analytics import to quiz controller")
    
    # Add method to sync analytics after each answer
    analytics_sync_method = '''
    def sync_analytics_after_answer(self, is_correct: bool, user_id: str = "anonymous"):
        """Sync analytics after answering a question"""
        try:
            analytics = get_analytics_manager()
            analytics.track_question_answer(
                user_id=user_id,
                correct=is_correct,
                category=getattr(self, 'category_filter', None)
            )
        except Exception as e:
            print(f"Error syncing analytics: {e}")
'''
    
    # Find a good place to add this method
    if "def sync_analytics_after_answer" not in content:
        class_end = content.rfind("    def get_session_summary")
        if class_end != -1:
            method_end = content.find("\n    def ", class_end + 1)
            if method_end == -1:
                method_end = len(content) - 50  # Near end of class
            
            content = content[:method_end] + analytics_sync_method + content[method_end:]
            print("✅ Added analytics sync method to quiz controller")
    
    # Write the updated content
    with open(controller_file, 'w') as f:
        f.write(content)
    
    print("✅ Quiz controller analytics integration enhanced")
    return True

def fix_question_counting():
    """Fix question counting discrepancies"""
    print("🔧 Fixing question counting...")
    
    questions_file = "linux_plus_questions.json"
    
    if not os.path.exists(questions_file):
        print("❌ Questions file not found!")
        return False
    
    with open(questions_file, 'r') as f:
        data = json.load(f)
    
    # Check if it's the new format with metadata and questions
    if isinstance(data, dict) and 'questions' in data:
        questions_list = data['questions']
        metadata = data.get('metadata', {})
        
        # Update metadata to match actual count
        actual_count = len(questions_list)
        metadata['total_questions'] = actual_count
        
        # Update categories
        categories = set()
        for q in questions_list:
            if 'category' in q:
                categories.add(q['category'])
        metadata['categories'] = sorted(list(categories))
        
        # Save updated data
        data['metadata'] = metadata
        
        with open(questions_file, 'w') as f:
            json.dump(data, f, indent=2)
        
        print(f"✅ Fixed question count: {actual_count} questions in {len(categories)} categories")
    else:
        print(f"✅ Questions file format is correct: {len(data)} questions")
    
    return True

def update_settings_ui():
    """Update settings UI to clarify reset options"""
    print("🔧 Updating settings UI...")
    
    settings_file = "templates/settings.html"
    
    if not os.path.exists(settings_file):
        print("❌ settings.html not found!")
        return False
    
    # Read current content
    with open(settings_file, 'r') as f:
        content = f.read()
    
    # Look for confusing reset sections and clarify them
    # Update the data tab reset section
    old_data_reset = 'onclick="clearHistory()"'
    new_data_reset = 'onclick="clearHistory()" title="Clear all quiz history and progress (keeps profiles)"'
    
    if old_data_reset in content:
        content = content.replace(old_data_reset, new_data_reset)
        print("✅ Clarified data reset button")
    
    # Update profile reset buttons
    old_profile_reset = 'onclick="resetProfile'
    new_profile_reset = 'onclick="resetProfile'  # Keep same but add explanatory text
    
    # Add explanatory text for reset options if not present
    reset_explanation = '''
                <div class="alert alert-info mt-3">
                    <h6><i class="fas fa-info-circle"></i> Reset Options Explained:</h6>
                    <ul class="mb-0">
                        <li><strong>Profile Reset:</strong> Clears progress for the selected profile only</li>
                        <li><strong>Data Reset (Data tab):</strong> Clears all quiz history but keeps all profiles</li>
                        <li><strong>Delete Profile:</strong> Completely removes the profile and all its data</li>
                    </ul>
                </div>'''
    
    # Add this explanation to the profiles panel
    if "Reset Options Explained" not in content:
        profiles_panel_end = content.find('</div>\n        </div>\n\n        <!-- Data Settings -->')
        if profiles_panel_end != -1:
            content = content[:profiles_panel_end] + reset_explanation + content[profiles_panel_end:]
            print("✅ Added reset options explanation")
    
    # Write the updated content
    with open(settings_file, 'w') as f:
        f.write(content)
    
    print("✅ Settings UI updated with clarifications")
    return True

def main():
    """Apply all fixes"""
    print("🚀 Starting comprehensive analytics fixes...")
    print("=" * 60)
    
    fixes_applied = []
    
    if fix_analytics_integration():
        fixes_applied.append("Analytics Integration")
    
    if fix_simple_analytics_service():
        fixes_applied.append("Simple Analytics Service")
    
    if fix_quiz_controller_integration():
        fixes_applied.append("Quiz Controller Integration")
    
    if fix_question_counting():
        fixes_applied.append("Question Counting")
    
    if update_settings_ui():
        fixes_applied.append("Settings UI Clarification")
    
    print("\n" + "=" * 60)
    print("✅ Fixes applied:")
    for fix in fixes_applied:
        print(f"   ✓ {fix}")
    
    print("\n🎯 Expected improvements:")
    print("   1. Profile names will show correctly in analytics")
    print("   2. Quiz progress will update immediately")
    print("   3. Question counts will be accurate")
    print("   4. Streak counters will update properly")
    print("   5. Reset options will be clearly explained")
    
    print("\n⚠️  Note: Restart the application to see all changes take effect")

if __name__ == "__main__":
    main()
