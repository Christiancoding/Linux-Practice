#!/usr/bin/env python3
"""
Database-driven Question Model for Linux+ Study Game

Handles question data loading from database instead of JSON files.
"""

import logging
import random
from typing import List, Tuple, Optional, Dict, Any, Union
from utils.db_connections import get_db_connection, get_db_session
from models.db_models import Question

logger = logging.getLogger(__name__)

class QuestionDatabase:
    """Database-driven question management."""
    
    def __init__(self):
        """Initialize question database manager."""
        self.questions = []
        self.categories = set()
        self.difficulties = set()
        
    def load_questions(self) -> List[Dict[str, Any]]:
        """Load all questions from database."""
        try:
            with get_db_session("questions") as session:
                questions = session.query(Question).all()
                
                question_list = []
                for q in questions:
                    import json
                    # Parse JSON fields if they're strings
                    options = q.options
                    if isinstance(options, str):
                        try:
                            options = json.loads(options)
                        except:
                            options = []
                    
                    # Find correct_index from correct_answer
                    correct_index = 0
                    if options and q.correct_answer:
                        try:
                            correct_index = options.index(q.correct_answer)
                        except ValueError:
                            # If correct_answer is not in options, try to parse as index
                            try:
                                correct_index = int(q.correct_answer)
                            except ValueError:
                                correct_index = 0
                    
                    question_dict = {
                        'id': q.question_id,
                        'category': q.category,
                        'subcategory': q.subcategory,
                        'difficulty': q.difficulty,
                        'text': q.question,
                        'question': q.question,
                        'options': options,
                        'correct_index': correct_index,
                        'correct_answer': q.correct_answer,
                        'explanation': q.explanation,
                        'links': q.links if isinstance(q.links, list) else [],
                        'tags': q.tags if isinstance(q.tags, list) else []
                    }
                    question_list.append(question_dict)
                    self.categories.add(q.category)
                    self.difficulties.add(q.difficulty)
                
                self.questions = question_list
                logger.info(f"Loaded {len(question_list)} questions from database")
                return question_list
                
        except Exception as e:
            logger.error(f"Error loading questions from database: {e}")
            return []
    
    def get_questions_by_category(self, category: str) -> List[Dict[str, Any]]:
        """Get questions filtered by category."""
        if not self.questions:
            self.load_questions()
        
        return [q for q in self.questions if q['category'] == category]
    
    def get_questions_by_difficulty(self, difficulty: str) -> List[Dict[str, Any]]:
        """Get questions filtered by difficulty."""
        if not self.questions:
            self.load_questions()
        
        return [q for q in self.questions if q['difficulty'] == difficulty]
    
    def get_random_questions(self, count: int, category: Optional[str] = None, 
                           difficulty: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get random questions with optional filters."""
        if not self.questions:
            self.load_questions()
        
        filtered_questions = self.questions
        
        if category:
            filtered_questions = [q for q in filtered_questions if q['category'] == category]
        
        if difficulty:
            filtered_questions = [q for q in filtered_questions if q['difficulty'] == difficulty]
        
        if len(filtered_questions) <= count:
            return filtered_questions
        
        return random.sample(filtered_questions, count)
    
    def get_all_categories(self) -> List[str]:
        """Get all available categories."""
        if not self.questions:
            self.load_questions()
        
        return sorted(list(self.categories))
    
    def get_all_difficulties(self) -> List[str]:
        """Get all available difficulties."""
        if not self.questions:
            self.load_questions()
        
        return sorted(list(self.difficulties))
    
    def get_question_by_id(self, question_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific question by ID."""
        if not self.questions:
            self.load_questions()
        
        for q in self.questions:
            if q['id'] == question_id:
                return q
        return None
    
    def get_total_questions_count(self) -> int:
        """Get total number of questions."""
        if not self.questions:
            self.load_questions()
        
        return len(self.questions)

# Global instance for easy access
question_db = QuestionDatabase()