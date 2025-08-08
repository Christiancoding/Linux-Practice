#!/usr/bin/env python3
"""
Reset user analytics to clean state for testing
"""

import json
from typing import Dict, List, Union

# Reset user analytics to clean state
clean_analytics: Dict[str, Dict[str, Union[int, float, List[str]]]] = {
    "anonymous": {
        "total_questions": 0,
        "correct_answers": 0,
        "incorrect_answers": 0,
        "accuracy": 0.0,
        "total_study_time": 0,
        "total_sessions": 0,
        "study_streak": 0,
        "current_streak": 0,
        "longest_streak": 0,
        "questions_to_review": 0,
        "level": 1,
        "xp": 0,
        "achievements": []
    }
}

with open('data/user_analytics.json', 'w') as f:
    json.dump(clean_analytics, f, indent=2)

print("User analytics reset to clean state.")
print("You can now test the quiz with fresh session data.")
