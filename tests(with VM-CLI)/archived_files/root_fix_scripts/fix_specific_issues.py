#!/usr/bin/env python3
"""
Fix specific issues in the submit_answer API and complete analytics integration
"""

import os
import re

def fix_submit_answer_function():
    """Fix the submit_answer function that has syntax errors"""
    print("🔧 Fixing submit_answer function...")
    
    web_view_file = "views/web_view.py"
    
    if not os.path.exists(web_view_file):
        print("❌ web_view.py not found!")
        return False
    
    # Read current content
    with open(web_view_file, 'r') as f:
        content = f.read()
    
    # Find the problematic submit_answer function
    start_pattern = r'@self\.app\.route\(\'/api/submit_answer\', methods=\[\'POST\'\]\)\s*def api_submit_answer\(\):'
    end_pattern = r'\n\s*# Store reference to the route function'
    
    start_match = re.search(start_pattern, content)
    end_match = re.search(end_pattern, content[start_match.end():] if start_match else content)
    
    if start_match and end_match:
        # Replace the broken function with a clean version
        function_start = start_match.start()
        function_end = start_match.end() + end_match.start()
        
        new_function = '''@self.app.route('/api/submit_answer', methods=['POST'])
        def api_submit_answer():
            try:
                data = cast(AnswerSubmissionData, request.get_json() or {})
                user_answer_index: Optional[int] = data.get('answer_index')
                
                # Validate session and question state
                if not self.quiz_controller.quiz_active:
                    return jsonify({'error': 'No active quiz session'})
                
                # Get current question from controller
                current_question = self.quiz_controller.get_current_question()
                if current_question is None:
                    return jsonify({'error': 'No current question available'})
                
                question_data = current_question['question_data']
                question_index = current_question['original_index']
                
                result = self.quiz_controller.submit_answer(
                    question_data, 
                    user_answer_index, 
                    question_index
                )
                
                # Track analytics for this answer
                try:
                    user_id, analytics = ensure_analytics_user_sync()
                    if analytics and user_id:
                        # Update quiz statistics
                        analytics.track_question_answer(
                            user_id=user_id,
                            correct=result.get('is_correct', False),
                            category=getattr(self.quiz_controller, 'category_filter', None),
                            time_taken=None  # Could add timing if needed
                        )
                except Exception as e:
                    print(f"Error tracking analytics: {e}")
                
                # Clear current question cache after processing
                self.quiz_controller.clear_current_question_cache()
                
                return jsonify(result)
                
            except Exception as e:
                print(f"Error in submit_answer: {e}")
                return jsonify({'error': str(e)})
        
        # Store reference to the route function'''
        
        content = content[:function_start] + new_function + content[function_end:]
        
        # Write the updated content
        with open(web_view_file, 'w') as f:
            f.write(content)
        
        print("✅ Fixed submit_answer function")
        return True
    
    else:
        print("❌ Could not find submit_answer function to fix")
        return False

def ensure_analytics_methods_exist():
    """Ensure analytics methods exist in the simple analytics service"""
    print("🔧 Ensuring analytics methods exist...")
    
    analytics_file = "services/simple_analytics.py"
    
    if not os.path.exists(analytics_file):
        print("❌ simple_analytics.py not found!")
        return False
    
    # Read current content
    with open(analytics_file, 'r') as f:
        content = f.read()
    
    # Check if update_quiz_results method exists
    if "def update_quiz_results" not in content:
        # Add the method
        update_quiz_method = '''
    def update_quiz_results(self, user_id: str = "anonymous", is_correct: bool = False, 
                           topic: str = None, difficulty: str = None):
        """Update quiz results - compatibility method for existing code"""
        return self.track_question_answer(user_id, is_correct, topic)
'''
        
        # Find a good place to add it - after track_question_answer
        if "def track_question_answer" in content:
            # Find the end of that method
            method_start = content.find("def track_question_answer")
            method_end = content.find("\n    def ", method_start + 1)
            if method_end == -1:
                method_end = len(content)
            
            content = content[:method_end] + update_quiz_method + content[method_end:]
            print("✅ Added update_quiz_results compatibility method")
        else:
            # Add at the end of the class
            class_end = content.rfind("        return True")
            if class_end != -1:
                content = content[:class_end + 20] + update_quiz_method + content[class_end + 20:]
                print("✅ Added update_quiz_results method at end of class")
    
    # Write the updated content
    with open(analytics_file, 'w') as f:
        f.write(content)
    
    return True

def fix_question_display_count():
    """Fix question display counts in the frontend"""
    print("🔧 Fixing question display counts...")
    
    # Update quiz.html to show proper question counts
    quiz_template = "templates/quiz.html"
    
    if not os.path.exists(quiz_template):
        print("❌ quiz.html not found!")
        return False
    
    with open(quiz_template, 'r') as f:
        content = f.read()
    
    # Look for question counter updates and fix them
    # Fix the question counter display
    old_counter = "document.getElementById('question-counter').textContent = counterText;"
    new_counter = '''document.getElementById('question-counter').textContent = counterText;
            
            // Update badge if it exists
            const badgeElement = document.getElementById('question-counter-badge');
            if (badgeElement) {
                badgeElement.textContent = data.question_number || 1;
            }'''
    
    if old_counter in content:
        content = content.replace(old_counter, new_counter)
        print("✅ Fixed question counter display")
    
    # Write updated content
    with open(quiz_template, 'w') as f:
        f.write(content)
    
    return True

def add_streak_counter_fix():
    """Fix streak counter not updating"""
    print("🔧 Fixing streak counter updates...")
    
    quiz_template = "templates/quiz.html"
    
    if not os.path.exists(quiz_template):
        print("❌ quiz.html not found!")
        return False
    
    with open(quiz_template, 'r') as f:
        content = f.read()
    
    # Look for streak display updates
    if "quizState.streak = data.streak" in content:
        # Find this line and add badge update after it
        old_streak = "quizState.streak = data.streak || 0;"
        new_streak = '''quizState.streak = data.streak || 0;
            
            // Update streak badge
            const streakBadge = document.querySelector('.streak-badge, #streak-counter');
            if (streakBadge) {
                streakBadge.textContent = quizState.streak;
            }'''
        
        if old_streak in content:
            content = content.replace(old_streak, new_streak)
            print("✅ Added streak counter update")
    
    # Write updated content
    with open(quiz_template, 'w') as f:
        f.write(content)
    
    return True

def main():
    """Apply all specific fixes"""
    print("🚀 Applying specific analytics fixes...")
    print("=" * 50)
    
    fixes = [
        ("Submit Answer Function", fix_submit_answer_function),
        ("Analytics Methods", ensure_analytics_methods_exist),
        ("Question Count Display", fix_question_display_count),
        ("Streak Counter", add_streak_counter_fix)
    ]
    
    for fix_name, fix_func in fixes:
        try:
            if fix_func():
                print(f"✅ {fix_name}: SUCCESS")
            else:
                print(f"❌ {fix_name}: FAILED")
        except Exception as e:
            print(f"❌ {fix_name}: ERROR - {e}")
    
    print("\n" + "=" * 50)
    print("🎯 Fixes completed! Restart the application to see changes.")

if __name__ == "__main__":
    main()
