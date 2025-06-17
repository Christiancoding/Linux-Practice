#!/usr/bin/env python3
"""
CLI View for the Linux+ Study Game using terminal interface.
"""

import os
import sys
import time
import json
from datetime import datetime

from utils.config import (
    COLOR_QUESTION, COLOR_OPTIONS, COLOR_OPTION_NUM, COLOR_CATEGORY,
    COLOR_CORRECT, COLOR_INCORRECT, COLOR_EXPLANATION, COLOR_PROMPT,
    COLOR_HEADER, COLOR_SUBHEADER, COLOR_STATS_LABEL, COLOR_STATS_VALUE,
    COLOR_STATS_ACC_GOOD, COLOR_STATS_ACC_AVG, COLOR_STATS_ACC_BAD,
    COLOR_BORDER, COLOR_INPUT, COLOR_ERROR, COLOR_WARNING, COLOR_INFO,
    COLOR_WELCOME_BORDER, COLOR_WELCOME_TEXT, COLOR_WELCOME_TITLE,
    COLOR_RESET, C, QUIZ_MODE_STANDARD, QUIZ_MODE_VERIFY,
    QUICK_FIRE_QUESTIONS, QUICK_FIRE_TIME_LIMIT, MINI_QUIZ_QUESTIONS
)


# --- CLI Helper Functions ---
def cli_print_separator(char='-', length=60, color=COLOR_BORDER):
    """Prints a colored separator line."""
    print(f"{color}{char * length}{COLOR_RESET}")

def cli_print_welcome():
    """Prints the welcome message."""
    print(f"{COLOR_WELCOME_BORDER}{'=' * 60}{COLOR_RESET}")
    print(f"{COLOR_WELCOME_TITLE}Welcome to the Linux+ Study Game!{COLOR_RESET}")
    print(f"{COLOR_WELCOME_TEXT}Prepare for your Linux+ certification with fun quizzes and gamification!{COLOR_RESET}")
    print(f"{COLOR_WELCOME_BORDER}{'=' * 60}{COLOR_RESET}\n")
    print(f"{COLOR_INFO}Type 'help' for a list of commands.{COLOR_RESET}") 

def cli_print_error(message):
    """Prints an error message in red."""
    print(f"{COLOR_ERROR}Error: {message}{COLOR_RESET}")

def cli_print_info(message):
    """Prints an informational message in cyan."""
    print(f"{COLOR_INFO}{message}{COLOR_RESET}")

def cli_print_warning(message):
    """Prints a warning message in bold yellow."""
    print(f"{COLOR_WARNING}Warning: {message}{COLOR_RESET}")

def cli_print_header(text, char='=', length=60, color=COLOR_HEADER):
    """Prints a centered header with separators."""
    text_str = str(text)
    padding = (length - len(text_str) - 2) // 2
    if padding < 0: padding = 0
    print(f"{color}{char * padding} {text_str} {char * (length - len(text_str) - 2 - padding)}{COLOR_RESET}")

def cli_print_box(lines, title="", width=60, border_color=COLOR_BORDER, title_color=COLOR_HEADER, text_color=COLOR_WELCOME_TEXT):
    """Prints text within a colored box."""
    border = f"{border_color}{'=' * width}{COLOR_RESET}"
    print(border)
    if title:
        padding = (width - len(title) - 4) // 2
        if padding < 0: padding = 0
        print(f"{border_color}* { ' ' * padding }{title_color}{title}{border_color}{ ' ' * (width - len(title) - 4 - padding)} *{COLOR_RESET}")
        print(border)

    for line in lines:
        # Basic way to estimate length without color codes
        line_len_no_color = 0
        in_escape = False
        for char in line:
            if char == '\x1b':
                in_escape = True
            elif in_escape and char.isalpha():
                in_escape = False
            elif not in_escape:
                line_len_no_color += 1

        padding_right = width - line_len_no_color - 4
        if padding_right < 0: padding_right = 0
        print(f"{border_color}* {text_color}{line}{' ' * padding_right}{border_color} *{COLOR_RESET}")
    print(border)

class LinuxPlusStudyCLI:
    """Handles the Command-Line Interface for the study game."""
    
    def __init__(self, game_logic):
        self.game_logic = game_logic
        self.current_streak = 0

    def clear_screen(self):
        """Clear the terminal screen."""
        os.system('cls' if os.name == 'nt' else 'clear')

    def display_welcome_message(self):
        """Displays the initial welcome screen for the CLI."""
        self.clear_screen()
        title = "LINUX+ STUDY GAME"
        welcome_lines = [
            "",
            "Welcome to the CompTIA Linux+ Study Game!",
            "",
            "Test your knowledge with multiple-choice questions.",
            "Choose between:",
            f"  - {COLOR_OPTIONS}Standard Quiz{COLOR_WELCOME_TEXT} (Immediate feedback)",
            f"  - {COLOR_OPTIONS}Verify Knowledge{COLOR_WELCOME_TEXT} (Feedback at the end)",
            "",
            "Track your progress with statistics and review incorrect answers.",
            ""
        ]
        cli_print_box(welcome_lines, title=title, width=60, border_color=COLOR_WELCOME_BORDER, title_color=COLOR_WELCOME_TITLE, text_color=COLOR_WELCOME_TEXT)
        try:
            input(f"{COLOR_PROMPT}Press Enter to continue...{COLOR_RESET}")
        except (EOFError, KeyboardInterrupt):
            print(f"\n{COLOR_WARNING} Exiting... {COLOR_RESET}")
            self.game_logic.save_history()
            sys.exit(0)

    def main_menu(self):
        """Display the main menu and handle user choices for CLI."""
        while True:
            self.clear_screen()
            cli_print_header("MAIN MENU", char='*', length=60)
            print(f"  {COLOR_OPTION_NUM}1.{COLOR_RESET} {COLOR_OPTIONS}Start Quiz (Standard){COLOR_RESET}")
            print(f"  {COLOR_OPTION_NUM}2.{COLOR_RESET} {COLOR_OPTIONS}Quiz by Category (Standard){COLOR_RESET}")
            print(f"  {COLOR_OPTION_NUM}3.{COLOR_RESET} {COLOR_OPTIONS}Verify Knowledge (Category/All){COLOR_RESET}")
            print(f"  {COLOR_OPTION_NUM}4.{COLOR_RESET} {COLOR_OPTIONS}⚡ Quick Fire Mode (5 questions, 3 min){COLOR_RESET}")
            print(f"  {COLOR_OPTION_NUM}5.{COLOR_RESET} {COLOR_OPTIONS}🗓️ Daily Challenge{COLOR_RESET}")
            print(f"  {COLOR_OPTION_NUM}6.{COLOR_RESET} {COLOR_OPTIONS}⚡ Mini Quiz (3 questions){COLOR_RESET}")
            print(f"  {COLOR_OPTION_NUM}7.{COLOR_RESET} {COLOR_OPTIONS}📊 Random Pop Quiz (1 question){COLOR_RESET}")
            print(f"  {COLOR_OPTION_NUM}8.{COLOR_RESET} {COLOR_OPTIONS}Review Incorrect Answers{COLOR_RESET}")
            print(f"  {COLOR_OPTION_NUM}9.{COLOR_RESET} {COLOR_OPTIONS}View Statistics{COLOR_RESET}")
            print(f"  {COLOR_OPTION_NUM}10.{COLOR_RESET} {COLOR_OPTIONS}🏆 Show Achievements & Leaderboard{COLOR_RESET}")
            print(f"  {COLOR_OPTION_NUM}11.{COLOR_RESET} {COLOR_OPTIONS}Export Study Data (History){COLOR_RESET}")
            print(f"  {COLOR_OPTION_NUM}12.{COLOR_RESET} {COLOR_OPTIONS}Export Questions & Answers (MD){COLOR_RESET}")
            print(f"  {COLOR_OPTION_NUM}13.{COLOR_RESET} {COLOR_OPTIONS}Export Questions & Answers (JSON){COLOR_RESET}")
            print(f"  {COLOR_OPTION_NUM}14.{COLOR_RESET} {COLOR_OPTIONS}Exit{COLOR_RESET}")
            print(f"  {COLOR_OPTION_NUM}15.{COLOR_RESET} {COLOR_WARNING}Clear All Statistics{COLOR_RESET}")
            cli_print_separator(color=COLOR_BORDER)

            choice = ''
            try:
                choice = input(f"{COLOR_PROMPT}Enter your choice: {COLOR_INPUT}")
                print(COLOR_RESET, end='')
            except (EOFError, KeyboardInterrupt):
                print(f"\n{COLOR_WARNING} Exiting... {COLOR_RESET}")
                choice = '14'

            if choice == '1':
                self.run_quiz(category_filter=None, mode=QUIZ_MODE_STANDARD)
            elif choice == '2':
                selected_category = self.select_category()
                if selected_category != 'b':
                    self.run_quiz(category_filter=selected_category, mode=QUIZ_MODE_STANDARD)
            elif choice == '3':
                selected_category = self.select_category()
                if selected_category != 'b':
                    self.run_quiz(category_filter=selected_category, mode=QUIZ_MODE_VERIFY)
            elif choice == '4':
                self.run_quiz(category_filter=None, mode="quick_fire")
            elif choice == '5':
                self._handle_daily_challenge()
            elif choice == '6':
                self.run_quiz(category_filter=None, mode="mini_quiz")
            elif choice == '7':
                self._handle_pop_quiz()
            elif choice == '8':
                self.review_incorrect_answers()
            elif choice == '9':
                self.show_stats()
            elif choice == '10':
                self.show_achievements_and_leaderboard()
            elif choice == '11':
                self.export_study_data()
            elif choice == '12':
                self.export_questions_answers_md()
            elif choice == '13':
                self.export_questions_answers_json()
            elif choice == '14':
                print(f"\n{COLOR_INFO}Saving progress and quitting. Goodbye!{COLOR_RESET}")
                self.game_logic.save_history()
                self.game_logic.save_achievements()
                sys.exit()
            elif choice == '15':
                self.clear_stats()

    def display_question(self, question_data, question_num=None, total_questions=None):
        """Display the question and options with enhanced CLI formatting."""
        if len(question_data) < 5:
            cli_print_error("Invalid question data format.")
            return
        question_text, options, _, category, _ = question_data
        cli_print_separator(char='~', color=COLOR_CATEGORY)
        header_info = f"Category: {COLOR_OPTIONS}{category}{COLOR_RESET}"
        if question_num is not None and total_questions is not None:
            header_info += f"{COLOR_CATEGORY}  |  Question: {COLOR_STATS_VALUE}{question_num}{COLOR_CATEGORY} / {COLOR_STATS_VALUE}{total_questions}{COLOR_RESET}"
        print(f"{COLOR_CATEGORY}{header_info}{COLOR_RESET}")
        cli_print_separator(char='~', color=COLOR_CATEGORY)

        print(f"\n{COLOR_QUESTION}Q: {question_text}{COLOR_RESET}\n")
        cli_print_separator(length=40, color=COLOR_BORDER + C["dim"])
        for i, option in enumerate(options):
            print(f"  {COLOR_OPTION_NUM}{i + 1}.{COLOR_RESET} {COLOR_OPTIONS}{option}{COLOR_RESET}")
        cli_print_separator(length=40, color=COLOR_BORDER + C["dim"])
        print()

    def get_user_answer(self, num_options):
        """Get and validate user input for CLI with better prompting."""
        while True:
            try:
                prompt = (f"{COLOR_PROMPT}Your choice ({COLOR_OPTION_NUM}1-{num_options}{COLOR_PROMPT}), "
                          f"'{COLOR_INFO}s{COLOR_PROMPT}' to skip, "
                          f"'{COLOR_INFO}q{COLOR_PROMPT}' to quit session: {COLOR_INPUT}")
                answer = input(prompt).lower().strip()
                print(COLOR_RESET, end='')
                if answer == 'q': return 'q'
                if answer == 's': return 's'
                choice = int(answer)
                if 1 <= choice <= num_options:
                    return choice - 1
                else:
                    cli_print_info(f"Invalid choice. Please enter a number between 1 and {num_options}.")
            except ValueError:
                cli_print_info("Invalid input. Please enter a number, 's', or 'q'.")
            except EOFError:
                cli_print_error("Input interrupted. Exiting session.")
                return 'q'
            except KeyboardInterrupt:
                print(f"\n{COLOR_WARNING} Session interrupted by user. Quitting session. {COLOR_RESET}")
                return 'q'

    def show_feedback(self, question_data, user_answer_index, original_index):
        """Show feedback based on the user's answer with enhanced CLI formatting."""
        if len(question_data) < 5:
            cli_print_error("Invalid question data format for feedback.")
            return
        _, options, correct_answer_index, category, explanation = question_data
        
        if original_index < 0 or original_index >= len(self.game_logic.questions):
            cli_print_error("Invalid original index for feedback.")
            original_question_text = "Unknown Question"
        else:
            original_question_text = self.game_logic.questions[original_index][0]

        is_correct = (user_answer_index == correct_answer_index)

        print()
        if is_correct:
            print(f"{COLOR_CORRECT}>>> Correct! \U0001F389 <<<{COLOR_RESET}")
            self.game_logic.score += 1
            self.current_streak += 1
        else:
            self.current_streak = 0
            if 0 <= correct_answer_index < len(options) and 0 <= user_answer_index < len(options):
                correct_option_text = options[correct_answer_index]
                user_option_text = options[user_answer_index]
                print(f"{COLOR_INCORRECT}>>> Incorrect! \U0001F61E <<<")
                print(f"{COLOR_INCORRECT}    Your answer:      {COLOR_OPTION_NUM}{user_answer_index + 1}.{COLOR_RESET} {COLOR_OPTIONS}{user_option_text}{COLOR_RESET}")
                print(f"{COLOR_CORRECT}    Correct answer was: {COLOR_OPTION_NUM}{correct_answer_index + 1}.{COLOR_RESET} {COLOR_OPTIONS}{correct_option_text}{COLOR_RESET}")
                if explanation:
                    print(f"\n{C['bold']}Explanation:{COLOR_RESET}")
                    explanation_lines = explanation.split('\n')
                    for line in explanation_lines:
                        print(f"  {COLOR_EXPLANATION}{line}{COLOR_RESET}")
            else:
                cli_print_error("Error displaying feedback: Invalid answer index.")

        # Update history
        self.game_logic.update_history(original_question_text, category, is_correct)
        self.game_logic.total_questions_session += 1
        
        # Update points and check achievements
        if is_correct:
            points_earned = self.game_logic.POINTS_PER_CORRECT
            if self.current_streak >= self.game_logic.STREAK_BONUS_THRESHOLD:
                points_earned = int(points_earned * self.game_logic.STREAK_BONUS_MULTIPLIER)
                print(f"{COLOR_CORRECT}Streak bonus! +{points_earned} points{COLOR_RESET}")
            else:
                print(f"{COLOR_CORRECT}+{points_earned} points{COLOR_RESET}")
        else:
            points_earned = self.game_logic.POINTS_PER_INCORRECT
            print(f"{COLOR_INCORRECT}{points_earned} points{COLOR_RESET}")
        
        self.game_logic.update_points(points_earned)
        
        # Check for achievements
        new_badges = self.game_logic.check_achievements(is_correct, self.current_streak)
        
        if new_badges:
            print(f"\n{COLOR_CORRECT}🎉 New Achievement(s) Unlocked!{COLOR_RESET}")
            for badge in new_badges:
                print(f"  {self.game_logic.get_achievement_description(badge)}")
        
        # Update quick fire progress if active
        if self.game_logic.quick_fire_active:
            self.game_logic.quick_fire_questions_answered += 1
            remaining = QUICK_FIRE_QUESTIONS - self.game_logic.quick_fire_questions_answered
            elapsed = time.time() - self.game_logic.quick_fire_start_time
            time_left = QUICK_FIRE_TIME_LIMIT - elapsed
            print(f"\n{COLOR_INFO}Quick Fire: {remaining} questions left, {time_left:.0f}s remaining{COLOR_RESET}")
        
        print()
        try:
            input(f"{COLOR_PROMPT}Press Enter to continue...{COLOR_RESET}")
        except EOFError:
            cli_print_error("Input interrupted. Continuing...")
        except KeyboardInterrupt:
            print(f"\n{COLOR_WARNING} Interrupted. Continuing... {COLOR_RESET}")

    def select_category(self):
        """Allow the user to select a category to focus on, using enhanced CLI."""
        self.clear_screen()
        cli_print_header("Select a Category")
        sorted_categories = sorted(list(self.game_logic.categories))
        if not sorted_categories:
            cli_print_error("No categories found!")
            time.sleep(2)
            return None

        print(f"\n{COLOR_OPTIONS}Available Categories:{COLOR_RESET}")
        print(f"  {COLOR_OPTION_NUM}0.{COLOR_RESET} {COLOR_OPTIONS}All Categories{COLOR_RESET}")
        for i, category in enumerate(sorted_categories):
            print(f"  {COLOR_OPTION_NUM}{i + 1}.{COLOR_RESET} {COLOR_OPTIONS}{category}{COLOR_RESET}")
        print()

        while True:
            try:
                prompt = f"{COLOR_PROMPT}Enter category number ({COLOR_OPTION_NUM}0-{len(sorted_categories)}{COLOR_PROMPT}), or '{COLOR_INFO}b{COLOR_PROMPT}' to go back: {COLOR_INPUT}"
                choice = input(prompt).lower().strip()
                print(COLOR_RESET, end='')
                if choice == 'b': return 'b'
                num_choice = int(choice)
                if num_choice == 0: return None
                elif 1 <= num_choice <= len(sorted_categories):
                    return sorted_categories[num_choice - 1]
                else:
                    cli_print_info("Invalid choice.")
            except ValueError:
                cli_print_info("Invalid input. Please enter a number or 'b'.")
            except EOFError:
                cli_print_error("Input interrupted. Returning to main menu.")
                return 'b'
            except KeyboardInterrupt:
                print(f"\n{COLOR_WARNING} Interrupted. Returning to main menu. {COLOR_RESET}")
                return 'b'

    def _handle_daily_challenge(self):
        """Handle daily challenge from CLI menu."""
        self.clear_screen()
        cli_print_header("🗓️ Daily Challenge")
        
        today_iso = datetime.now().date().isoformat()
        if self.game_logic.last_daily_challenge_date == today_iso and self.game_logic.daily_challenge_completed:
            cli_print_info("You've already completed today's daily challenge! Come back tomorrow.")
            time.sleep(2)
            return

        daily_q_data, daily_q_idx = self.game_logic.get_daily_challenge_question()

        if daily_q_data:
            # Reset session specific vars for this single question
            original_score = self.game_logic.score
            original_total_session = self.game_logic.total_questions_session
            original_session_points = self.game_logic.session_points

            self.game_logic.score = 0
            self.game_logic.total_questions_session = 0
            self.game_logic.answered_indices_session = [daily_q_idx]
            self.game_logic.session_points = 0

            self.display_question(daily_q_data, question_num=1, total_questions=1)
            user_answer = self.get_user_answer(len(daily_q_data[1]))

            if user_answer not in ['q', 's'] and isinstance(user_answer, int):
                self.show_feedback(daily_q_data, user_answer, daily_q_idx)
                
                if self.game_logic.score > 0:
                    self.game_logic.daily_challenge_completed = True
                    self.game_logic.last_daily_challenge_date = today_iso
                    
                    self.game_logic.achievements.setdefault("daily_warrior_dates", [])
                    if isinstance(self.game_logic.achievements["daily_warrior_dates"], set):
                        self.game_logic.achievements["daily_warrior_dates"] = list(self.game_logic.achievements["daily_warrior_dates"])

                    if today_iso not in self.game_logic.achievements["daily_warrior_dates"]:
                        self.game_logic.achievements["daily_warrior_dates"].append(today_iso)
                    
                    if "daily_warrior" not in self.game_logic.achievements["badges"] and len(self.game_logic.achievements["daily_warrior_dates"]) >= 1:
                        self.game_logic.achievements["badges"].append("daily_warrior")
                        print(f"\n{COLOR_CORRECT}{self.game_logic.get_achievement_description('daily_warrior')}{COLOR_RESET}")
                
                self.game_logic.save_achievements()
            
            self.game_logic.save_history()

            if user_answer in ['q', 's']:
                try:
                    input(f"\n{COLOR_PROMPT}Press Enter to return to the main menu...{COLOR_RESET}")
                except (EOFError, KeyboardInterrupt):
                    print(f"\n{COLOR_WARNING} Returning to menu... {COLOR_RESET}")
        else:
            cli_print_info("Today's daily challenge is currently unavailable.")
            time.sleep(2)

    def _handle_pop_quiz(self):
        """Handle random pop quiz from CLI menu."""
        question_data, original_index = self.game_logic.select_question(None)
        if question_data:
            print(f"\n{COLOR_HEADER}📊 Random Pop Quiz{COLOR_RESET}")
            self.display_question(question_data, question_num=1, total_questions=1)
            user_answer = self.get_user_answer(len(question_data[1]))
            if user_answer not in ['q', 's'] and isinstance(user_answer, int):
                self.show_feedback(question_data, user_answer, original_index)
        else:
            print(f"{COLOR_WARNING}No questions available for pop quiz.{COLOR_RESET}")
            time.sleep(2)

    def run_quiz(self, category_filter=None, mode=QUIZ_MODE_STANDARD):
        """Run the main quiz loop for the CLI with enhanced display and modes."""
        self.game_logic.score = 0
        self.game_logic.total_questions_session = 0
        self.game_logic.answered_indices_session = []
        self.game_logic.verify_session_answers = []
        self.game_logic.session_points = 0
        self.current_streak = 0

        quiz_title = "Quiz Mode"
        if mode == QUIZ_MODE_VERIFY:
            quiz_title = "Verify Knowledge Mode"
            self.clear_screen()
            cli_print_header("VERIFY YOUR KNOWLEDGE", char='*', length=60, color=COLOR_HEADER)
            verify_intro = [
                "",
                "This mode will test your knowledge and verify your answers.",
                "You won't be told if you're right or wrong until the end.",
                "",
                "Ready?",
            ]
            cli_print_box(verify_intro, width=60, border_color=COLOR_BORDER, text_color=COLOR_INFO)
            try:
                input(f"{COLOR_PROMPT}Press Enter to start...{COLOR_RESET}")
            except (EOFError, KeyboardInterrupt):
                print(f"\n{COLOR_WARNING} Quiz cancelled. Returning to menu. {COLOR_RESET}")
                return

        # Determine total questions for display
        max_available_for_filter = 0
        if category_filter is None:
            max_available_for_filter = len(self.game_logic.questions)
        else:
            max_available_for_filter = sum(1 for q in self.game_logic.questions if len(q) > 3 and q[3] == category_filter)

        total_questions_for_display_label = 0
        questions_to_ask_this_session = 0 

        if mode == "quick_fire":
            self.game_logic.start_quick_fire_mode()
            total_questions_for_display_label = QUICK_FIRE_QUESTIONS
            questions_to_ask_this_session = QUICK_FIRE_QUESTIONS
            quiz_title = "⚡ Quick Fire Mode"
        elif mode == "mini_quiz":
            total_questions_for_display_label = min(MINI_QUIZ_QUESTIONS, max_available_for_filter)
            questions_to_ask_this_session = total_questions_for_display_label
            quiz_title = "⚡ Mini Quiz"
        elif category_filter is None:
            total_questions_for_display_label = max_available_for_filter
            questions_to_ask_this_session = max_available_for_filter
        else:
            total_questions_for_display_label = max_available_for_filter
            questions_to_ask_this_session = max_available_for_filter

        if max_available_for_filter == 0:
            print(f"{COLOR_WARNING}Warning: No questions found for the selected filter: {category_filter or 'All Categories'}. Returning to menu.{COLOR_RESET}")
            time.sleep(3)
            self.game_logic.save_history()
            return

        if questions_to_ask_this_session == 0 and mode in ["mini_quiz", "quick_fire"]:
            print(f"{COLOR_WARNING}Warning: Not enough questions available for {quiz_title}. Returning to menu.{COLOR_RESET}")
            time.sleep(3)
            if mode == "quick_fire": self.game_logic.quick_fire_active = False
            return

        question_count = 0
        
        # Main quiz loop
        while True:
            if mode == "quick_fire":
                if not self.game_logic.check_quick_fire_status():
                    break
            elif mode == "mini_quiz":
                if self.game_logic.total_questions_session >= questions_to_ask_this_session:
                    break

            self.clear_screen()
            category_display = category_filter if category_filter else "All Categories"
            session_header = f"{quiz_title}: {category_display}"
            cli_print_header(session_header)

            if mode == QUIZ_MODE_STANDARD or mode == "mini_quiz" or mode == "quick_fire":
                print(f"{COLOR_STATS_LABEL}Session Score: {COLOR_STATS_VALUE}{self.game_logic.score} / {self.game_logic.total_questions_session}{COLOR_RESET}")
                if mode == "quick_fire" and self.game_logic.quick_fire_active:
                    elapsed = time.time() - self.game_logic.quick_fire_start_time
                    time_left = QUICK_FIRE_TIME_LIMIT - elapsed
                    print(f"{COLOR_INFO}Time Left: {time_left:.0f}s{COLOR_RESET}")
                print()
            else:
                print(f"{COLOR_STATS_LABEL}Questions Answered: {COLOR_STATS_VALUE}{self.game_logic.total_questions_session}{COLOR_RESET}\n")

            question_data, original_index = self.game_logic.select_question(category_filter)

            if question_data is None:
                cli_print_info("No more new questions available in this filter for this session. Ending session.")
                time.sleep(3)
                break 

            question_count += 1
            self.display_question(question_data, question_num=question_count, total_questions=total_questions_for_display_label)

            user_answer = self.get_user_answer(len(question_data[1])) 

            if user_answer == 'q':
                cli_print_info("Quitting quiz session.")
                if mode == "quick_fire": self.game_logic.end_quick_fire_mode(time_up=True)
                break 
            elif user_answer == 's':
                cli_print_info("Skipping question...")
                if mode == "quick_fire":
                    self.game_logic.quick_fire_questions_answered +=1
                try:
                    input(f"\n{COLOR_PROMPT}Press Enter to continue...{COLOR_RESET}")
                except (EOFError, KeyboardInterrupt):
                    print(f"\n{COLOR_WARNING} Interrupted. Continuing... {COLOR_RESET}")
                continue 

            # Process Answer
            if len(question_data) < 5: 
                cli_print_error("Invalid question data during processing. Skipping.")
                continue
            
            _, _, correct_answer_index, q_category, _ = question_data
            if original_index < 0 or original_index >= len(self.game_logic.questions):
                original_question_text = "Error: Unknown Question Text" 
            else:
                original_question_text = self.game_logic.questions[original_index][0] 

            is_correct = (user_answer == correct_answer_index)

            if mode == QUIZ_MODE_STANDARD or mode == "quick_fire" or mode == "mini_quiz":
                self.show_feedback(question_data, user_answer, original_index)
            elif mode == QUIZ_MODE_VERIFY:
                self.game_logic.verify_session_answers.append((question_data, user_answer, is_correct))
                self.game_logic.total_questions_session += 1
                if is_correct: self.game_logic.score +=1
                self.game_logic.update_history(original_question_text, q_category, is_correct)
                
                points_earned = self.game_logic.POINTS_PER_CORRECT if is_correct else self.game_logic.POINTS_PER_INCORRECT
                self.game_logic.update_points(points_earned)
                self.game_logic.check_achievements(is_correct, getattr(self, 'current_streak', 0))

                cli_print_info("Answer recorded. Next question...")
                time.sleep(1) 
        
        # End of Session
        if mode == "quick_fire" and not self.game_logic.quick_fire_active:
            pass  # Messages handled by _end_quick_fire_mode
        elif mode == "mini_quiz":
            print(f"\n{COLOR_HEADER}Mini Quiz session finished.{COLOR_RESET}")
            if self.game_logic.total_questions_session > 0:
                accuracy = (self.game_logic.score / self.game_logic.total_questions_session * 100)
                acc_color = COLOR_STATS_ACC_GOOD if accuracy >= 75 else (COLOR_STATS_ACC_AVG if accuracy >= 50 else COLOR_STATS_ACC_BAD)
                print(f"{COLOR_STATS_LABEL}Your final score for this session: {COLOR_STATS_VALUE}{self.game_logic.score} / {self.game_logic.total_questions_session}{COLOR_RESET} ({acc_color}{accuracy:.1f}%{COLOR_RESET})")
            else:
                print(f"{COLOR_STATS_LABEL}No questions were answered in this session.{COLOR_RESET}")
        elif mode == QUIZ_MODE_STANDARD:
            print(f"\n{COLOR_HEADER}Quiz session finished.{COLOR_RESET}")
            if self.game_logic.total_questions_session > 0:
                accuracy = (self.game_logic.score / self.game_logic.total_questions_session * 100)
                acc_color = COLOR_STATS_ACC_GOOD if accuracy >= 75 else (COLOR_STATS_ACC_AVG if accuracy >= 50 else COLOR_STATS_ACC_BAD)
                print(f"{COLOR_STATS_LABEL}Your final score for this session: {COLOR_STATS_VALUE}{self.game_logic.score} / {self.game_logic.total_questions_session}{COLOR_RESET} ({acc_color}{accuracy:.1f}%{COLOR_RESET})")
            else:
                print(f"{COLOR_STATS_LABEL}No questions were answered in this session.{COLOR_RESET}")
        elif mode == QUIZ_MODE_VERIFY:
            self.show_verify_results()

        # Common end-of-session gamification updates
        if mode != "quick_fire":
            if self.game_logic.total_questions_session > 0:
                accuracy = (self.game_logic.score / self.game_logic.total_questions_session * 100)
                if accuracy == 100 and self.game_logic.total_questions_session >= 3:
                    if "perfect_session" not in self.game_logic.achievements["badges"]:
                        self.game_logic.achievements["badges"].append("perfect_session")
                        print(f"\n{COLOR_CORRECT}{self.game_logic.get_achievement_description('perfect_session')}{COLOR_RESET}")
                self.game_logic.update_leaderboard(self.game_logic.score, self.game_logic.total_questions_session, self.game_logic.session_points)
                self.show_progress_summary()
        
        self.game_logic.save_achievements()
        self.game_logic.save_history()
        try:
            input(f"\n{COLOR_PROMPT}Press Enter to return to the main menu...{COLOR_RESET}")
        except (EOFError, KeyboardInterrupt):
            print(f"\n{COLOR_WARNING} Returning to menu... {COLOR_RESET}")

    def show_verify_results(self):
        """Displays the results after a 'Verify Knowledge' session."""
        self.clear_screen()
        cli_print_header("Verification Results")

        if not self.game_logic.verify_session_answers:
            cli_print_info("No questions were answered in this verification session.")
            return

        num_correct = sum(1 for _, _, is_correct in self.game_logic.verify_session_answers if is_correct)
        total_answered = len(self.game_logic.verify_session_answers)
        accuracy = (num_correct / total_answered * 100) if total_answered > 0 else 0
        acc_color = COLOR_STATS_ACC_GOOD if accuracy >= 75 else (COLOR_STATS_ACC_AVG if accuracy >= 50 else COLOR_STATS_ACC_BAD)

        print(f"\n{COLOR_SUBHEADER}Session Summary:{COLOR_RESET}")
        print(f"  {COLOR_STATS_LABEL}Total Questions Answered:{COLOR_RESET} {COLOR_STATS_VALUE}{total_answered}{COLOR_RESET}")
        print(f"  {COLOR_STATS_LABEL}Correct Answers:         {COLOR_RESET} {COLOR_STATS_VALUE}{num_correct}{COLOR_RESET}")
        print(f"  {COLOR_STATS_LABEL}Accuracy:                {COLOR_RESET} {acc_color}{accuracy:.2f}%{COLOR_RESET}\n")
        cli_print_separator()

        print(f"\n{COLOR_SUBHEADER}Detailed Review:{COLOR_RESET}")
        for i, (q_data, user_answer_idx, is_correct) in enumerate(self.game_logic.verify_session_answers):
            if len(q_data) < 5: continue
            q_text, options, correct_idx, _, explanation = q_data
            print(f"\n{COLOR_QUESTION}{i+1}. {q_text}{COLOR_RESET}")

            if 0 <= user_answer_idx < len(options) and 0 <= correct_idx < len(options):
                user_choice_text = options[user_answer_idx]
                correct_choice_text = options[correct_idx]

                if is_correct:
                    print(f"  {COLOR_CORRECT}Your answer: {user_answer_idx+1}. {user_choice_text} (Correct! \U0001F389){COLOR_RESET}")
                else:
                    print(f"  {COLOR_INCORRECT}Your answer: {user_answer_idx+1}. {user_choice_text} (Incorrect \U0001F61E){COLOR_RESET}")
                    print(f"  {COLOR_CORRECT}Correct answer: {correct_idx+1}. {correct_choice_text}{COLOR_RESET}")
                    if explanation:
                        print(f"  {C['bold']}Explanation:{COLOR_RESET}")
                        explanation_lines = explanation.split('\n')
                        for line in explanation_lines:
                            print(f"    {COLOR_EXPLANATION}{line}{COLOR_RESET}")
                cli_print_separator(char='.', length=50, color=COLOR_BORDER + C["dim"])
            else:
                cli_print_error("Error displaying details for this question: Invalid index.")
    def show_progress_summary(self):
        """Show gamification progress summary."""
        print(f"\n{COLOR_HEADER}📊 Progress Summary{COLOR_RESET}")
        print(f"  {COLOR_STATS_LABEL}Session Points: {COLOR_STATS_VALUE}{self.game_logic.session_points}{COLOR_RESET}")
        print(f"  {COLOR_STATS_LABEL}Total Points: {COLOR_STATS_VALUE}{self.game_logic.achievements.get('points_earned', 0)}{COLOR_RESET}")
        print(f"  {COLOR_STATS_LABEL}Questions Answered: {COLOR_STATS_VALUE}{self.game_logic.achievements.get('questions_answered', 0)}{COLOR_RESET}")
        print(f"  {COLOR_STATS_LABEL}Current Streak: {COLOR_STATS_VALUE}{getattr(self, 'current_streak', 0)}{COLOR_RESET}")
        
        if self.game_logic.achievements["badges"]:
            print(f"\n  {COLOR_SUBHEADER}🏆 Achievements Unlocked:{COLOR_RESET}")
            for badge in self.game_logic.achievements["badges"]:
                print(f"    {self.game_logic.get_achievement_description(badge)}")

    def show_leaderboard(self):
        """Display the leaderboard."""
        print(f"\n{COLOR_HEADER}🏆 Personal Leaderboard (Top Sessions){COLOR_RESET}")
        if not self.game_logic.leaderboard:
            cli_print_info("No sessions recorded yet. Start studying to see your progress!")
            return
        
        print(f"  {COLOR_STATS_LABEL}{'Rank'.rjust(4)} │ {'Date'.ljust(10)} │ {'Score'.rjust(8)} │ {'Accuracy'.rjust(8)} │ {'Points'.rjust(7)}{COLOR_RESET}")
        print(f"  {COLOR_BORDER}─────┼────────────┼──────────┼──────────┼────────{COLOR_RESET}")
        
        for i, entry in enumerate(self.game_logic.leaderboard, 1):
            date_str = entry["date"][:10]
            score_str = f"{entry['score']}/{entry['total']}"
            accuracy_str = f"{entry['accuracy']:.1f}%"
            points_str = str(entry['points'])
            
            acc_color = COLOR_STATS_ACC_GOOD if entry['accuracy'] >= 75 else (COLOR_STATS_ACC_AVG if entry['accuracy'] >= 50 else COLOR_STATS_ACC_BAD)
            
            print(f"  {COLOR_STATS_VALUE}{str(i).rjust(4)}{COLOR_RESET} │ {date_str} │ {COLOR_STATS_VALUE}{score_str.rjust(8)}{COLOR_RESET} │ {acc_color}{accuracy_str.rjust(8)}{COLOR_RESET} │ {COLOR_STATS_VALUE}{points_str.rjust(7)}{COLOR_RESET}")

    def show_achievements_and_leaderboard(self):
        """Display achievements and leaderboard in one view."""
        self.clear_screen()
        cli_print_header("Achievements & Leaderboard")
        
        # Show current points and progress
        print(f"\n{COLOR_SUBHEADER}Current Progress:{COLOR_RESET}")
        print(f"  {COLOR_STATS_LABEL}Total Points Earned: {COLOR_STATS_VALUE}{self.game_logic.achievements.get('points_earned', 0)}{COLOR_RESET}")
        print(f"  {COLOR_STATS_LABEL}Questions Answered: {COLOR_STATS_VALUE}{self.game_logic.achievements.get('questions_answered', 0)}{COLOR_RESET}")
        print(f"  {COLOR_STATS_LABEL}Days Studied: {COLOR_STATS_VALUE}{len(self.game_logic.achievements.get('days_studied', []))}{COLOR_RESET}")
        
        # Show achievements
        print(f"\n{COLOR_SUBHEADER}🏆 Achievements Unlocked:{COLOR_RESET}")
        if self.game_logic.achievements["badges"]:
            for badge in self.game_logic.achievements["badges"]:
                print(f"  {self.game_logic.get_achievement_description(badge)}")
        else:
            cli_print_info("No achievements yet. Keep studying to unlock badges!")
        
        # Show available achievements
        print(f"\n{COLOR_SUBHEADER}🎯 Available Achievements:{COLOR_RESET}")
        all_achievements = {
            "streak_master": "Answer 5 questions correctly in a row",
            "dedicated_learner": "Study for 3 different days",
            "century_club": "Answer 100 questions total",
            "point_collector": "Earn 500 points",
            "quick_fire_champion": "Complete Quick Fire mode",
            "daily_warrior": "Complete a daily challenge",
            "perfect_session": "Get 100% accuracy in a session (3+ questions)"
        }
        
        for badge, description in all_achievements.items():
            if badge not in self.game_logic.achievements["badges"]:
                print(f"  🔒 {description}")
        
        # Show leaderboard
        self.show_leaderboard()
        
        try:
            input(f"\n{COLOR_PROMPT}Press Enter to return to the main menu...{COLOR_RESET}")
        except (EOFError, KeyboardInterrupt):
            print(f"\n{COLOR_WARNING} Returning to menu... {COLOR_RESET}")

    def show_stats(self):
        """Display overall and category-specific statistics with enhanced CLI formatting."""
        self.clear_screen()
        cli_print_header("Study Statistics")
        history = self.game_logic.study_history

        # Overall Performance
        total_attempts = history.get("total_attempts", 0)
        total_correct = history.get("total_correct", 0)
        overall_accuracy = (total_correct / total_attempts * 100) if total_attempts > 0 else 0
        acc_color = COLOR_STATS_ACC_GOOD if overall_accuracy >= 75 else (COLOR_STATS_ACC_AVG if overall_accuracy >= 50 else COLOR_STATS_ACC_BAD)

        print(f"\n{COLOR_SUBHEADER}Overall Performance (All Time):{COLOR_RESET}")
        print(f"  {COLOR_STATS_LABEL}Total Questions Answered:{COLOR_RESET} {COLOR_STATS_VALUE}{total_attempts}{COLOR_RESET}")
        print(f"  {COLOR_STATS_LABEL}Total Correct:           {COLOR_RESET} {COLOR_STATS_VALUE}{total_correct}{COLOR_RESET}")
        print(f"  {COLOR_STATS_LABEL}Overall Accuracy:        {COLOR_RESET} {acc_color}{overall_accuracy:.2f}%{COLOR_RESET}")

        # Performance by Category
        print(f"\n{COLOR_SUBHEADER}Performance by Category:{COLOR_RESET}")
        categories_data = history.get("categories", {})
        sorted_categories = sorted(
            [(cat, stats) for cat, stats in categories_data.items() if isinstance(stats, dict) and stats.get("attempts", 0) > 0],
            key=lambda item: item[0]
        )

        if not sorted_categories:
            print(f"  {COLOR_EXPLANATION}No category data recorded yet (or no attempts made).{COLOR_RESET}")
        else:
            max_len = max((len(cat) for cat, stats in sorted_categories), default=10)
            header = f"  {COLOR_STATS_LABEL}{'Category'.ljust(max_len)} │ {'Correct'.rjust(7)} │ {'Attempts'.rjust(8)} │ {'Accuracy'.rjust(9)}{COLOR_RESET}"
            print(header)
            print(f"  {COLOR_BORDER}{'-' * max_len}─┼─────────┼──────────┼──────────{COLOR_RESET}")
            for category, stats in sorted_categories:
                cat_attempts = stats.get("attempts", 0)
                cat_correct = stats.get("correct", 0)
                cat_accuracy = (cat_correct / cat_attempts * 100)
                acc_color = COLOR_STATS_ACC_GOOD if cat_accuracy >= 75 else (COLOR_STATS_ACC_AVG if cat_accuracy >= 50 else COLOR_STATS_ACC_BAD)
                print(f"  {category.ljust(max_len)} │ {COLOR_STATS_VALUE}{str(cat_correct).rjust(7)}{COLOR_RESET} │ {COLOR_STATS_VALUE}{str(cat_attempts).rjust(8)}{COLOR_RESET} │ {acc_color}{f'{cat_accuracy:.1f}%'.rjust(9)}{COLOR_RESET}")

        # Performance on Specific Questions
        print(f"\n{COLOR_SUBHEADER}Performance on Specific Questions (All History):{COLOR_RESET}")
        question_stats = history.get("questions", {})
        attempted_questions = {q: stats for q, stats in question_stats.items() if isinstance(stats, dict) and stats.get("attempts", 0) > 0}

        if not attempted_questions:
            print(f"  {COLOR_EXPLANATION}No specific question data recorded yet (or no attempts made).{COLOR_RESET}")
        else:
            def sort_key(item):
                q_text, stats = item
                attempts = stats.get("attempts", 0)
                correct = stats.get("correct", 0)
                accuracy = correct / attempts
                return (accuracy, -attempts)

            sorted_questions = sorted(attempted_questions.items(), key=sort_key)

            print(f"  {COLOR_STATS_LABEL}Showing questions sorted by lowest accuracy first:{COLOR_RESET}")
            for i, (q_text, stats) in enumerate(sorted_questions):
                attempts = stats.get("attempts", 0)
                correct = stats.get("correct", 0)
                accuracy = (correct / attempts * 100)
                acc_color = COLOR_STATS_ACC_GOOD if accuracy >= 75 else (COLOR_STATS_ACC_AVG if accuracy >= 50 else COLOR_STATS_ACC_BAD)

                last_result = "N/A"
                last_color = COLOR_EXPLANATION
                if isinstance(stats.get("history"), list) and stats["history"]:
                    last_entry = stats["history"][-1]
                    if isinstance(last_entry, dict) and "correct" in last_entry:
                        last_correct = last_entry.get("correct")
                        last_result = "Correct" if last_correct else "Incorrect"
                        last_color = COLOR_CORRECT if last_correct else COLOR_INCORRECT

                display_text = (q_text[:75] + '...') if len(q_text) > 75 else q_text
                print(f"\n  {COLOR_QUESTION}{i+1}. \"{display_text}\"{COLOR_RESET}")
                print(f"     {C['dim']}({COLOR_STATS_VALUE}{attempts}{C['dim']} attempts, {acc_color}{accuracy:.1f}%{C['dim']} acc.) Last: {last_color}{last_result}{C['dim']}){COLOR_RESET}")

        print()
        cli_print_separator(color=COLOR_BORDER)
        try:
            input(f"\n{COLOR_PROMPT}Press Enter to return to the main menu...{COLOR_RESET}")
        except EOFError:
            cli_print_error("Input interrupted. Returning to menu...")
        except KeyboardInterrupt:
            print(f"\n{COLOR_WARNING} Interrupted. Returning to menu... {COLOR_RESET}")

    def review_incorrect_answers(self):
        """Allows the user to review questions they previously answered incorrectly (CLI - Basic View)."""
        self.clear_screen()
        cli_print_header("Review Incorrect Answers")
        incorrect_list = self.game_logic.study_history.get("incorrect_review", [])
        if not isinstance(incorrect_list, list):
            incorrect_list = []
            self.game_logic.study_history["incorrect_review"] = []

        if not incorrect_list:
            cli_print_info("You haven't marked any questions as incorrect yet, or your history was cleared.")
            cli_print_info("Keep practicing!")
            try:
                input(f"\n{COLOR_PROMPT}Press Enter to return to the main menu...{COLOR_RESET}")
            except (EOFError, KeyboardInterrupt):
                print(f"\n{COLOR_WARNING} Returning to menu... {COLOR_RESET}")
            return

        # Find the full question data based on the text stored in incorrect_review
        questions_to_review = []
        not_found_questions = []
        incorrect_list_copy = list(incorrect_list)
        questions_to_remove_from_history = []

        for incorrect_text in incorrect_list_copy:
            found = False
            for q_data in self.game_logic.questions:
                if isinstance(q_data, (list, tuple)) and len(q_data) > 0 and q_data[0] == incorrect_text:
                    questions_to_review.append(q_data)
                    found = True
                    break
            if not found:
                not_found_questions.append(incorrect_text)
                print(f"{COLOR_WARNING} Could not find full data for question: {incorrect_text[:50]}... (Maybe removed from source?){COLOR_RESET}")
                questions_to_remove_from_history.append(incorrect_text)

        # Remove not found questions from the actual history list
        history_changed = False
        if questions_to_remove_from_history:
            original_len = len(self.game_logic.study_history.get("incorrect_review", []))
            self.game_logic.study_history["incorrect_review"] = [
                q_text for q_text in self.game_logic.study_history.get("incorrect_review", [])
                if q_text not in questions_to_remove_from_history
            ]
            if len(self.game_logic.study_history["incorrect_review"]) != original_len:
                history_changed = True

        if not questions_to_review:
            cli_print_error("Could not load data for any incorrect questions.")
            if history_changed:
                self.game_logic.save_history()
            try:
                input(f"\n{COLOR_PROMPT}Press Enter to return to the main menu...{COLOR_RESET}")
            except (EOFError, KeyboardInterrupt):
                print(f"\n{COLOR_WARNING} Returning to menu... {COLOR_RESET}")
            return

        # Interactive Review Loop
        current_choice = ''
        while True:
            self.clear_screen()
            cli_print_header("Review Incorrect Answers")
            print(f"\n{COLOR_OPTIONS}Select a question to review (displays info):{COLOR_RESET}")
            if not questions_to_review:
                cli_print_info("All incorrect questions cleared from review.")
                time.sleep(2)
                break

            for i, q_data in enumerate(questions_to_review):
                if isinstance(q_data, (list, tuple)) and len(q_data) > 0:
                    q_text_short = (q_data[0][:60] + '...') if len(q_data[0]) > 60 else q_data[0]
                    print(f"  {COLOR_OPTION_NUM}{i + 1}.{COLOR_RESET} {COLOR_OPTIONS}{q_text_short}{COLOR_RESET}")
                else:
                    print(f"  {COLOR_OPTION_NUM}{i + 1}.{COLOR_RESET} {COLOR_ERROR} [Invalid Question Data] {COLOR_RESET}")

            print(f"  {COLOR_OPTION_NUM}c.{COLOR_RESET} {COLOR_WARNING}Clear an item from this review list{COLOR_RESET} (Enter 'c' then the number)")

            try:
                prompt = f"\n{COLOR_PROMPT}Enter question number ({COLOR_OPTION_NUM}1-{len(questions_to_review)}{COLOR_PROMPT}), '{COLOR_INFO}c[num]{COLOR_PROMPT}' to clear, or '{COLOR_INFO}b{COLOR_PROMPT}' to go back: {COLOR_INPUT}"
                choice = input(prompt).lower().strip()
                current_choice = choice
                print(COLOR_RESET, end='')

                if choice == 'b':
                    break

                clear_mode = False
                item_to_clear = -1
                if choice.startswith('c') and len(choice) > 1:
                    try:
                        item_to_clear = int(choice[1:]) -1
                        if 0 <= item_to_clear < len(questions_to_review):
                            clear_mode = True
                        else:
                            cli_print_info("Invalid number after 'c'.")
                            time.sleep(1.5)
                            continue
                    except ValueError:
                        cli_print_info("Invalid format for clear. Use 'c' followed by the number (e.g., c3).")
                        time.sleep(1.5)
                        continue

                if clear_mode:
                    if isinstance(questions_to_review[item_to_clear], (list, tuple)) and len(questions_to_review[item_to_clear]) > 0:
                        question_to_clear_text = questions_to_review[item_to_clear][0]
                        confirm_clear = input(f"{COLOR_PROMPT}Clear question {item_to_clear+1} from the incorrect review list? ({COLOR_OPTIONS}yes{COLOR_PROMPT}/{COLOR_OPTIONS}no{COLOR_PROMPT}): {COLOR_INPUT}").lower().strip()
                        if confirm_clear == 'yes':
                            if isinstance(self.game_logic.study_history.get("incorrect_review"), list) and question_to_clear_text in self.game_logic.study_history["incorrect_review"]:
                                self.game_logic.study_history["incorrect_review"].remove(question_to_clear_text)
                                history_changed = True
                                print(f"{COLOR_CORRECT}Question removed from review list.{COLOR_RESET}")
                                del questions_to_review[item_to_clear]
                                time.sleep(1.5)
                            else:
                                cli_print_error("Error: Question text not found in history's incorrect list anymore?")
                                try:
                                    del questions_to_review[item_to_clear]
                                except IndexError:
                                    pass
                                time.sleep(2)
                        else:
                            cli_print_info("Clear cancelled.")
                            time.sleep(1)
                    else:
                        cli_print_error("Cannot clear invalid question data.")
                        time.sleep(2)
                    continue

                # Display selected question
                num_choice = int(choice)
                if 1 <= num_choice <= len(questions_to_review):
                    self.clear_screen()
                    cli_print_header("Reviewing Question")
                    selected_q_data = questions_to_review[num_choice-1]
                    if len(selected_q_data) < 5:
                        cli_print_error("Invalid data for selected question.")
                        time.sleep(2)
                        continue

                    q_text, options, correct_idx, category, explanation = selected_q_data
                    print(f"{COLOR_CATEGORY}Category: {category}{COLOR_RESET}\n")
                    print(f"{COLOR_QUESTION}Q: {q_text}{COLOR_RESET}\n")
                    for i, option in enumerate(options):
                        prefix = f"  {COLOR_OPTION_NUM}{i + 1}.{COLOR_RESET} "
                        if i == correct_idx:
                            print(f"{prefix}{COLOR_CORRECT}{option} (Correct Answer){COLOR_RESET}")
                        else:
                            print(f"{prefix}{COLOR_OPTIONS}{option}{COLOR_RESET}")
                    if explanation:
                        print(f"\n{C['bold']}Explanation:{COLOR_RESET}")
                        explanation_lines = explanation.split('\n')
                        for line in explanation_lines:
                            print(f"  {COLOR_EXPLANATION}{line}{COLOR_RESET}")
                    cli_print_separator()
                    try:
                        input(f"\n{COLOR_PROMPT}Press Enter to return to the review list...{COLOR_RESET}")
                    except (EOFError, KeyboardInterrupt):
                        print(f"\n{COLOR_WARNING} Returning to list... {COLOR_RESET}")
                        continue

                else:
                    cli_print_info("Invalid choice.")
                    time.sleep(1.5)

            except ValueError:
                cli_print_info("Invalid input. Please enter a number, 'c[num]', or 'b'.")
                time.sleep(1.5)
            except EOFError:
                cli_print_error("Input interrupted. Returning to main menu.")
                current_choice = 'b'
                break
            except KeyboardInterrupt:
                print(f"\n{COLOR_WARNING} Interrupted. Returning to main menu. {COLOR_RESET}")
                current_choice = 'b'
                break

        # Save history if any items were removed
        if history_changed:
            self.game_logic.save_history()

    def clear_stats(self):
        """Clear all stored statistics after confirmation with enhanced CLI."""
        self.clear_screen()
        cli_print_header("Clear Statistics", char='!', color=COLOR_ERROR)
        print(f"\n{COLOR_WARNING} This action will permanently delete ALL study history,")
        print(f"{COLOR_WARNING} including question performance and the list of incorrect answers.")
        print(f"{COLOR_WARNING} This cannot be undone. {COLOR_RESET}")
        confirm = ''
        try:
            confirm = input(f"{COLOR_PROMPT}Are you sure you want to proceed? ({COLOR_OPTIONS}yes{COLOR_PROMPT}/{COLOR_OPTIONS}no{COLOR_PROMPT}): {COLOR_INPUT}").lower().strip()
            print(COLOR_RESET, end='')
        except (EOFError, KeyboardInterrupt):
            print(f"\n{COLOR_WARNING} Clear operation cancelled. {COLOR_RESET}")
            confirm = 'no'

        if confirm == 'yes':
            self.game_logic.study_history = self.game_logic._default_history()
            for category in self.game_logic.categories:
                self.game_logic.study_history["categories"].setdefault(category, {"correct": 0, "attempts": 0})
            self.game_logic.save_history()
            print(f"\n{COLOR_CORRECT}>>> Study history has been cleared. <<<{COLOR_RESET}")
        else:
            cli_print_info("Operation cancelled. History not cleared.")

        print()
        try:
            input(f"{COLOR_PROMPT}Press Enter to return to the main menu...{COLOR_RESET}")
        except (EOFError, KeyboardInterrupt):
            print(f"\n{COLOR_WARNING} Returning to menu... {COLOR_RESET}")

    def export_study_data(self):
        """Exports study history data (JSON export)."""
        self.clear_screen()
        cli_print_header("Export Study Data (History)")

        default_filename = f"linux_plus_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        export_filename = default_filename
        try:
            prompt = f"{COLOR_PROMPT}Enter filename for export ({COLOR_INFO}default: {default_filename}{COLOR_PROMPT}): {COLOR_INPUT}"
            filename_input = input(prompt).strip()
            print(COLOR_RESET, end='')
            export_filename = filename_input if filename_input else default_filename
        except (EOFError, KeyboardInterrupt):
            print(f"\n{COLOR_WARNING} Export cancelled. {COLOR_RESET}")
            try: 
                input(f"\n{COLOR_PROMPT}Press Enter to return to the main menu...{COLOR_RESET}")
            except: 
                pass
            return

        if not export_filename.lower().endswith(".json"):
            export_filename += ".json"
        try:
            export_path = os.path.abspath(export_filename)
            cli_print_info(f"Attempting to export history data to: {COLOR_STATS_VALUE}{export_path}{COLOR_RESET}")
            with open(export_filename, 'w', encoding='utf-8') as f:
                json.dump(self.game_logic.study_history, f, indent=2)
            print(f"\n{COLOR_CORRECT}>>> Study history successfully exported to {export_filename} <<<{COLOR_RESET}")
        except IOError as e:
            cli_print_error(f"Error exporting history: {e}")
            cli_print_error("Please check permissions and filename.")
        except Exception as e:
            cli_print_error(f"An unexpected error occurred during history export: {e}")

        try:
            input(f"\n{COLOR_PROMPT}Press Enter to return to the main menu...{COLOR_RESET}")
        except (EOFError, KeyboardInterrupt):
            print(f"\n{COLOR_WARNING} Returning to menu... {COLOR_RESET}")

    def export_questions_answers_md(self):
        """Exports all loaded questions and answers to a Markdown file."""
        self.clear_screen()
        cli_print_header("Export Questions & Answers to Markdown")

        if not self.game_logic.questions:
            print(f"\n{COLOR_WARNING}No questions are currently loaded to export.{COLOR_RESET}")
            try: 
                input(f"\n{COLOR_PROMPT}Press Enter to return to the main menu...{COLOR_RESET}")
            except: 
                pass
            return

        default_filename = f"Linux_plus_QA_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        export_filename = default_filename
        try:
            prompt = f"{COLOR_PROMPT}Enter filename for export ({COLOR_INFO}default: {default_filename}{COLOR_PROMPT}): {COLOR_INPUT}"
            filename_input = input(prompt).strip()
            print(COLOR_RESET, end='')
            export_filename = filename_input if filename_input else default_filename
        except (EOFError, KeyboardInterrupt):
            print(f"\n{COLOR_WARNING} Export cancelled. {COLOR_RESET}")
            try: 
                input(f"\n{COLOR_PROMPT}Press Enter to return to the main menu...{COLOR_RESET}")
            except: 
                pass
            return

        if not export_filename.lower().endswith(".md"):
            export_filename += ".md"
        
        try:
            export_path = os.path.abspath(export_filename)
            cli_print_info(f"Attempting to export Q&A to: {COLOR_STATS_VALUE}{export_path}{COLOR_RESET}")

            with open(export_filename, 'w', encoding='utf-8') as f:
                # Write Questions Section
                f.write("# Questions\n\n")
                for i, q_data in enumerate(self.game_logic.questions):
                    if len(q_data) < 5: continue
                    question_text, options, _, category, _ = q_data
                    f.write(f"**Q{i+1}.** ({category})\n")
                    f.write(f"{question_text}\n")
                    for j, option in enumerate(options):
                        f.write(f"   {chr(ord('A') + j)}. {option}\n")
                    f.write("\n")

                f.write("---\n\n")

                # Write Answers Section
                f.write("# Answers\n\n")
                for i, q_data in enumerate(self.game_logic.questions):
                    if len(q_data) < 5: continue
                    _, options, correct_answer_index, _, explanation = q_data
                    if 0 <= correct_answer_index < len(options):
                        correct_option_letter = chr(ord('A') + correct_answer_index)
                        correct_option_text = options[correct_answer_index]

                        f.write(f"**A{i+1}.** {correct_option_letter}. {correct_option_text}\n")
                        if explanation:
                            explanation_lines = explanation.split('\n')
                            f.write("   *Explanation:*")
                            first_line = True
                            for line in explanation_lines:
                                if not first_line:
                                    f.write("   ")
                                f.write(f" {line.strip()}\n")
                                first_line = False
                        f.write("\n\n")
                    else:
                        f.write(f"**A{i+1}.** Error: Invalid correct answer index.\n\n")

            print(f"{COLOR_CORRECT}>>> Questions & Answers successfully exported to {export_filename} <<<{COLOR_RESET}")

        except IOError as e:
            cli_print_error(f"Error exporting Q&A: {e}")
            cli_print_error("Please check permissions and filename.")
        except Exception as e:
            cli_print_error(f"An unexpected error occurred during Q&A export: {e}")

        try:
            input(f"\n{COLOR_PROMPT}Press Enter to return to the main menu...{COLOR_RESET}")
        except (EOFError, KeyboardInterrupt):
            print(f"\n{COLOR_WARNING} Returning to menu... {COLOR_RESET}")

    def export_questions_answers_json(self):
        """Exports all loaded questions and answers to a JSON file."""
        self.clear_screen()
        cli_print_header("Export Questions & Answers to JSON")

        if not self.game_logic.questions:
            print(f"\n{COLOR_WARNING}No questions are currently loaded to export.{COLOR_RESET}")
            try: 
                input(f"\n{COLOR_PROMPT}Press Enter to return to the main menu...{COLOR_RESET}")
            except: 
                pass
            return

        default_filename = f"Linux_plus_QA_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        export_filename = default_filename
        try:
            prompt = f"{COLOR_PROMPT}Enter filename for export ({COLOR_INFO}default: {default_filename}{COLOR_PROMPT}): {COLOR_INPUT}"
            filename_input = input(prompt).strip()
            print(COLOR_RESET, end='')
            export_filename = filename_input if filename_input else default_filename
        except (EOFError, KeyboardInterrupt):
            print(f"\n{COLOR_WARNING} Export cancelled. {COLOR_RESET}")
            try: 
                input(f"\n{COLOR_PROMPT}Press Enter to return to the main menu...{COLOR_RESET}")
            except: 
                pass
            return

        if not export_filename.lower().endswith(".json"):
            export_filename += ".json"
        
        try:
            export_path = os.path.abspath(export_filename)
            cli_print_info(f"Attempting to export Q&A to: {COLOR_STATS_VALUE}{export_path}{COLOR_RESET}")

            # Prepare questions data for JSON export
            questions_data = []
            for i, q_data in enumerate(self.game_logic.questions):
                if len(q_data) < 5: continue
                question_text, options, correct_answer_index, category, explanation = q_data
                
                question_obj = {
                    "id": i + 1,
                    "question": question_text,
                    "category": category,
                    "options": options,
                    "correct_answer_index": correct_answer_index,
                    "correct_answer_letter": chr(ord('A') + correct_answer_index) if 0 <= correct_answer_index < len(options) else "Invalid",
                    "correct_answer_text": options[correct_answer_index] if 0 <= correct_answer_index < len(options) else "Invalid index",
                    "explanation": explanation if explanation else ""
                }
                questions_data.append(question_obj)

            # Create the final JSON structure
            export_data = {
                "metadata": {
                    "title": "Linux+ Study Questions",
                    "export_date": datetime.now().isoformat(),
                    "total_questions": len(questions_data),
                    "categories": sorted(list(set(q["category"] for q in questions_data)))
                },
                "questions": questions_data
            }

            with open(export_filename, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)

            print(f"{COLOR_CORRECT}>>> Questions & Answers successfully exported to {export_filename} <<<{COLOR_RESET}")

        except IOError as e:
            cli_print_error(f"Error exporting Q&A: {e}")
            cli_print_error("Please check permissions and filename.")
        except Exception as e:
            cli_print_error(f"An unexpected error occurred during Q&A export: {e}")

        try:
            input(f"\n{COLOR_PROMPT}Press Enter to return to the main menu...{COLOR_RESET}")
        except (EOFError, KeyboardInterrupt):
            print(f"\n{COLOR_WARNING} Returning to menu... {COLOR_RESET}")