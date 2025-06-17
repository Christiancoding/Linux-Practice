#!/usr/bin/env python3
"""
GUI View for the Linux+ Study Game using Tkinter.
"""
from utils.cli_playground import CLIPlayground
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, scrolledtext, filedialog
import json
import os
import time
from datetime import datetime
import utils.cli_playground

from utils.config import (
    GUI_COLORS, get_gui_fonts, QUIZ_MODE_STANDARD, QUIZ_MODE_VERIFY,
    QUICK_FIRE_QUESTIONS, QUICK_FIRE_TIME_LIMIT, MINI_QUIZ_QUESTIONS,
    POINTS_PER_CORRECT, POINTS_PER_INCORRECT, STREAK_BONUS_THRESHOLD,
    STREAK_BONUS_MULTIPLIER
)


class LinuxPlusStudyGUI:
    """Handles the Tkinter Graphical User Interface for the study game with improved styling."""
    
    def __init__(self, root, game_logic):
        self.root = root
        self.game_logic = game_logic

        self.current_question_index = -1
        self.current_question_data = None
        self.selected_answer_var = tk.IntVar(value=-1)
        self.quiz_active = False
        self.current_category_filter = None
        self.current_quiz_mode = QUIZ_MODE_STANDARD
        self.gui_verify_session_answers = []
        self.total_questions_in_filter_gui = 0
        self.questions_answered_in_session_gui = 0
        self.history = self.game_logic.study_history
        self.verify_mode = False
        self.verify_mode_started = False
        self.verify_mode_results = []
        self.verify_mode_current_question = 0
        self.focus_mode_enabled = tk.BooleanVar(value=False)
        self.session_lock_enabled = tk.BooleanVar(value=False)
        self.session_lock_minimum = tk.IntVar(value=5)
        self.break_reminder_enabled = tk.BooleanVar(value=False)
        self.break_reminder_interval = tk.IntVar(value=10)
        self.break_duration_minutes = tk.IntVar(value=2)

        self.questions_since_break = 0
        self.current_streak = 0
        self.on_break = False
        self.break_window = None
        self.original_window_state = None
        
        # Gamification GUI attributes
        self.points_label = None
        self.achievements_window = None
        self.progress_bars = {}
        self.quick_fire_timer_label = None
        self.quick_fire_progress_bar = None
        self.daily_challenge_frame = None
        
        # Enhanced Styling
        self.colors = GUI_COLORS
        self.fonts = get_gui_fonts()
        self.cli_playground = CLIPlayground()
        self._setup_styles()
        self._setup_ui()
        self._load_initial_state()

    def _setup_styles(self):
        """Configure ttk styles for a modern dark theme."""
        self.style = ttk.Style()
        self.style.theme_use('clam')

        # Configure Base Styles
        self.style.configure(".",
                             background=self.colors["bg"],
                             foreground=self.colors["fg"],
                             font=self.fonts.get("base"),
                             borderwidth=0,
                             focuscolor=self.colors["accent"])

        self.style.configure("TFrame", background=self.colors["bg"])
        self.style.configure("TLabel", background=self.colors["bg"], foreground=self.colors["fg"], font=self.fonts.get("base"))
        self.style.configure("Header.TLabel", font=self.fonts.get("header"), foreground=self.colors["fg_header"])
        self.style.configure("Category.TLabel", font=self.fonts.get("italic"), foreground=self.colors["category_fg"])
        self.style.configure("Status.TLabel", font=self.fonts.get("base"), foreground=self.colors["status_fg"])
        self.style.configure("Streak.TLabel", font=self.fonts.get("bold"), foreground=self.colors["streak"])

        # Button Styling
        self.style.configure("TButton",
                             font=self.fonts.get("button"),
                             padding=(10, 5),
                             background=self.colors["button"],
                             foreground=self.colors["button_fg"],
                             borderwidth=1,
                             bordercolor=self.colors["border"],
                             relief="flat")
        self.style.map("TButton",
                       background=[('disabled', self.colors["button_disabled_bg"]),
                                   ('active', self.colors["button_hover"]),
                                   ('!disabled', self.colors["button"])],
                       foreground=[('disabled', self.colors["disabled_fg"])])

        self.style.configure("Accent.TButton",
                             background=self.colors["accent"],
                             foreground=self.colors["bg"],
                             font=self.fonts.get("button"))
        self.style.map("Accent.TButton",
                       background=[('disabled', self.colors["button_disabled_bg"]),
                                   ('active', self.colors["accent_dark"]),
                                   ('!disabled', self.colors["accent"])],
                       foreground=[('disabled', self.colors["disabled_fg"])])

        # Radiobutton Styling
        self.style.configure("TRadiobutton",
                             background=self.colors["bg_widget"],
                             foreground=self.colors["fg"],
                             font=self.fonts.get("option"),
                             indicatorrelief=tk.FLAT,
                             indicatormargin=5,
                             padding=(5, 3))
        self.style.map("TRadiobutton",
                       background=[('selected', self.colors["bg_widget"]), ('active', self.colors["bg_widget"])],
                       indicatorbackground=[('selected', self.colors["accent"]), ('!selected', self.colors["border"])],
                       foreground=[('disabled', self.colors["disabled_fg"])])

        # Feedback Label Styling
        self.style.configure("Feedback.TLabel", font=self.fonts.get("feedback"), padding=5)
        self.style.configure("Correct.Feedback.TLabel", foreground=self.colors["correct"])
        self.style.configure("Incorrect.Feedback.TLabel", foreground=self.colors["incorrect"])
        self.style.configure("Info.Feedback.TLabel", foreground=self.colors["status_fg"])

        # Scrollbar Styling
        self.style.configure("Vertical.TScrollbar",
                             background=self.colors["bg_widget"],
                             troughcolor=self.colors["bg"],
                             bordercolor=self.colors["border"],
                             arrowcolor=self.colors["fg"],
                             relief="flat")
        self.style.map("Vertical.TScrollbar",
                       background=[('active', self.colors["border"])])

        # OptionMenu Styling
        self.style.configure("TMenubutton",
                             font=self.fonts.get("base"),
                             padding=(10, 5),
                             background=self.colors["button"],
                             foreground=self.colors["button_fg"],
                             arrowcolor=self.colors["accent"],
                             relief="flat")
        self.style.map("TMenubutton",
                       background=[('active', self.colors["button_hover"])])
        
        self.style.configure("TCheckbutton",
                             background=self.colors["bg"],
                             foreground=self.colors["fg"],
                             font=self.fonts.get("base"))
        self.style.map("TCheckbutton",
                       indicatorbackground=[('selected', self.colors["accent"]), ('!selected', self.colors["border"])])
        
        self.style.configure("TSpinbox",
                             background=self.colors["bg_widget"],
                             foreground=self.colors["fg"],
                             arrowcolor=self.colors["accent"],
                             fieldbackground=self.colors["bg_widget"],
                             relief="flat")

    def _setup_ui(self):
        """Create the main UI elements with enhanced layout."""
        self.root.title("Linux+ Study Game")
        self.root.geometry("950x900")
        self.root.configure(bg=self.colors["bg"])
        self.root.minsize(750, 650)

        # Main Frame with Padding
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(1, weight=1)
        self.cli_frame = ttk.Frame(main_frame, padding="10 0 0 0")

        # Enhanced Header with Gamification
        header_frame = ttk.Frame(main_frame, padding=(0, 0, 0, 15))
        header_frame.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 15))
        header_frame.columnconfigure(1, weight=1)

        # Left side - Title and Points
        title_points_frame = ttk.Frame(header_frame)
        title_points_frame.grid(row=0, column=0, sticky="w")
        
        ttk.Label(title_points_frame, text="Linux+ Study Game", style="Header.TLabel").pack(side=tk.LEFT)
        
        self.points_label = ttk.Label(title_points_frame, text="Points: 0", style="Streak.TLabel")
        self.points_label.pack(side=tk.LEFT, padx=(20, 0))

        # Right side - Status and counters
        status_count_frame = ttk.Frame(header_frame)
        status_count_frame.grid(row=0, column=1, sticky="e")

        self.streak_label = ttk.Label(status_count_frame, text="", style="Streak.TLabel")
        self.streak_label.pack(side=tk.RIGHT, padx=(10,0))
        
        self.question_count_label = ttk.Label(status_count_frame, text="", style="Status.TLabel")
        self.question_count_label.pack(side=tk.RIGHT, padx=(10,0))

        self.status_label = ttk.Label(status_count_frame, text="Status: Idle", style="Status.TLabel")
        self.status_label.pack(side=tk.RIGHT, padx=(0, 10))
        
        # Quick Fire Timer (hidden by default)
        self.quick_fire_timer_label = ttk.Label(status_count_frame, text="", style="Streak.TLabel")
        self.quick_fire_timer_label.pack(side=tk.RIGHT, padx=(10, 0))
        self.quick_fire_timer_label.pack_forget()

        # Quiz Area Frame
        quiz_frame_outer = tk.Frame(main_frame, bg=self.colors["border"], bd=1, relief="solid")
        quiz_frame_outer.grid(row=1, column=0, columnspan=2, sticky="nsew", pady=10)
        quiz_frame_outer.columnconfigure(0, weight=1)
        quiz_frame_outer.rowconfigure(0, weight=1)

        quiz_frame = ttk.Frame(quiz_frame_outer, padding="20", style="TFrame")
        quiz_frame.grid(row=0, column=0, sticky="nsew")
        quiz_frame.columnconfigure(0, weight=1)
        quiz_frame.rowconfigure(1, weight=2)
        quiz_frame.rowconfigure(2, weight=1)
        quiz_frame.rowconfigure(3, weight=2)

        # Category Label
        self.category_label = ttk.Label(quiz_frame, text="", style="Category.TLabel")
        self.category_label.grid(row=0, column=0, sticky="w", pady=(0, 10))

        # Question Text (Scrollable Text Widget)
        self.question_text = scrolledtext.ScrolledText(quiz_frame, wrap=tk.WORD, height=6,
                                     font=self.fonts.get("question"), relief="flat",
                                     bg=self.colors["bg_widget"], fg=self.colors["fg"],
                                     bd=0, state=tk.DISABLED,
                                     padx=10, pady=10,
                                     selectbackground=self.colors["accent"],
                                     selectforeground=self.colors["bg"])
        self.question_text.grid(row=1, column=0, sticky="nsew", pady=5)
        try:
            self.question_text.vbar.configure(style="Vertical.TScrollbar")
        except tk.TclError:
            print("Note: Could not apply custom style to ScrolledText scrollbar.")

        # Options Frame
        self.options_frame = ttk.Frame(quiz_frame, padding=(0, 15, 0, 10), style="TFrame")
        self.options_frame.grid(row=2, column=0, sticky="nsew", pady=10)
        self.options_frame.columnconfigure(0, weight=1)

        # Feedback & Explanation Area
        feedback_exp_frame = ttk.Frame(quiz_frame, style="TFrame")
        feedback_exp_frame.grid(row=3, column=0, sticky="nsew", pady=(10, 5))
        feedback_exp_frame.columnconfigure(0, weight=1)
        feedback_exp_frame.rowconfigure(1, weight=1)

        self.feedback_label = ttk.Label(feedback_exp_frame, text="", style="Feedback.TLabel", anchor=tk.W, wraplength=600)
        self.feedback_label.grid(row=0, column=0, sticky="ew", pady=(0, 5))

        # Explanation Text
        self.explanation_text = scrolledtext.ScrolledText(feedback_exp_frame, wrap=tk.WORD, height=4,
                                         font=self.fonts.get("explanation"), relief="flat",
                                         bg=self.colors["explanation_bg"], fg=self.colors["fg"],
                                         bd=0, state=tk.DISABLED,
                                         padx=10, pady=10,
                                         selectbackground=self.colors["accent"],
                                         selectforeground=self.colors["bg"])
        try:
            self.explanation_text.vbar.configure(style="Vertical.TScrollbar")
        except tk.TclError:
            print("Note: Could not apply custom style to ScrolledText scrollbar.")
        self.explanation_text.grid(row=1, column=0, sticky="nsew", pady=5)
        self.explanation_text.grid_remove()

        # Control Frame
        self.control_frame = ttk.Frame(main_frame, padding=(0, 20, 0, 0))
        self.control_frame.grid(row=2, column=0, columnspan=2, sticky="ew")
        self.control_frame.columnconfigure(0, weight=0)
        self.control_frame.columnconfigure(1, weight=1)
        self.control_frame.columnconfigure(2, weight=0)

        # Left side (Quiz Controls)
        quiz_controls = ttk.Frame(self.control_frame)
        quiz_controls.grid(row=0, column=0, sticky="w")
        self.submit_button = ttk.Button(quiz_controls, text="Submit Answer", command=self._submit_answer_gui, state=tk.DISABLED, style="Accent.TButton", width=15)
        self.submit_button.pack(side=tk.LEFT, padx=(0, 10))
        self.next_button = ttk.Button(quiz_controls, text="Next Question", command=self._next_question_gui, state=tk.DISABLED, style="Accent.TButton", width=15)
        self.next_button.pack(side=tk.LEFT)
        self.show_results_button = ttk.Button(quiz_controls, text="Show Results", command=self._show_verify_results_gui, state=tk.DISABLED, style="Accent.TButton", width=15)
        self.show_results_button.pack(side=tk.LEFT, padx=(10, 0))
        self.show_results_button.pack_forget()

        # Right side (Main Actions)
        self.main_actions_frame = ttk.Frame(self.control_frame)
        self.main_actions_frame.grid(row=0, column=2, sticky="e")
        
        # Standard quiz options
        quiz_frame = ttk.Frame(self.main_actions_frame)
        quiz_frame.pack(side=tk.LEFT, padx=5)
        ttk.Button(quiz_frame, text="Start Quiz", command=lambda: self._start_quiz_dialog(QUIZ_MODE_STANDARD), style="TButton").pack(pady=1)
        ttk.Button(quiz_frame, text="Verify Knowledge", command=lambda: self._start_quiz_dialog(QUIZ_MODE_VERIFY), style="TButton").pack(pady=1)
        
        # Gamification options
        game_frame = ttk.Frame(self.main_actions_frame)
        game_frame.pack(side=tk.LEFT, padx=5)
        ttk.Button(game_frame, text="⚡ Quick Fire", command=self._start_quick_fire_gui, style="Accent.TButton").pack(pady=1)
        ttk.Button(game_frame, text="🗓️ Daily Challenge", command=self._start_daily_challenge_gui, style="TButton").pack(pady=1)
        ttk.Button(game_frame, text="⚡ Mini Quiz", command=self._start_mini_quiz_gui, style="TButton").pack(pady=1)
        ttk.Button(game_frame, text="📊 Pop Quiz", command=self._start_pop_quiz_gui, style="TButton").pack(pady=1)
        
        # Management options
        mgmt_frame = ttk.Frame(self.main_actions_frame)
        mgmt_frame.pack(side=tk.LEFT, padx=5)
        self.review_button = ttk.Button(mgmt_frame, text="Review Incorrect", command=self._review_incorrect_gui, style="TButton")
        self.review_button.pack(pady=1)
        ttk.Button(mgmt_frame, text="🏆 Achievements", command=self._show_achievements_gui, style="TButton").pack(pady=1)
        ttk.Button(mgmt_frame, text="View Stats", command=self._show_stats_gui, style="TButton").pack(pady=1)
        
        # Export and system options
        sys_frame = ttk.Frame(self.main_actions_frame)
        sys_frame.pack(side=tk.LEFT, padx=5)
        self.export_history_button = ttk.Button(sys_frame, text="Export History", command=self._export_data_gui, style="TButton")
        self.export_history_button.pack(pady=1)
        self.export_qa_button = ttk.Button(sys_frame, text="Export Q&A (MD)", command=self._export_questions_answers_gui, style="TButton")
        self.export_qa_button.pack(pady=1)
        self.export_qa_json_button = ttk.Button(sys_frame, text="Export Q&A (JSON)", command=self._export_questions_answers_json_gui, style="TButton")
        self.export_qa_json_button.pack(pady=1)
        ttk.Button(sys_frame, text="CLI Playground", command=self._toggle_cli_playground, style="TButton").pack(pady=1)
        ttk.Button(sys_frame, text="Clear Stats", command=self._clear_stats_gui, style="TButton").pack(pady=1)
        ttk.Button(sys_frame, text="Quit", command=self.quit_app, style="TButton").pack(pady=1)
        
        self._setup_cli_playground(self.cli_frame)

    def _load_initial_state(self):
        """Set the initial welcome message and check button states."""
        self._update_status("Ready.")
        self._update_question_count_label()
        self._update_streak_label(0)
        self._clear_quiz_area(clear_options=True)
        self.category_label.config(text="")
        self._update_points_display()
        self.quick_fire_timer_label.pack_forget()

        if self.focus_mode_enabled.get():
            self._toggle_focus_mode(enable=False)
        self.focus_mode_enabled.set(False)
        self.session_lock_enabled.set(False)
        self.quiz_active = False

        self.question_text.config(state=tk.NORMAL)
        self.question_text.delete(1.0, tk.END)

        # Add welcome message with basic formatting
        self.question_text.tag_configure("welcome_title", font=self.fonts.get("welcome_title"), foreground=self.colors["welcome_title"], justify='center', spacing3=15)
        self.question_text.tag_configure("welcome_body", font=self.fonts.get("welcome_text"), foreground=self.colors["welcome_text"], justify='left', spacing1=5, lmargin1=20, lmargin2=20)

        self.question_text.insert(tk.END, "LINUX+ STUDY GAME\n", "welcome_title")
        self.question_text.insert(tk.END, "Welcome to the CompTIA Linux+ Study Game!\n\n", "welcome_body")
        self.question_text.insert(tk.END, "Use the buttons below to start a quiz, verify your knowledge, view statistics, or manage your study data.\n\n", "welcome_body")
        self.question_text.insert(tk.END, "Before starting, you can enable focus-enhancing features like fullscreen mode and break reminders.\n\n", "welcome_body")
        self.question_text.insert(tk.END, "Let's get started!", "welcome_body")

        self.question_text.config(state=tk.DISABLED)

        # Ensure quiz control buttons are initially disabled
        self.submit_button.config(state=tk.DISABLED)
        self.next_button.config(state=tk.DISABLED)
        self.show_results_button.pack_forget()

        # Enable/Disable Review based on history content
        incorrect_list = self.game_logic.study_history.get("incorrect_review", [])
        self.review_button.config(state=tk.NORMAL if isinstance(incorrect_list, list) and incorrect_list else tk.DISABLED)

        # History export can always be enabled
        self.export_history_button.config(state=tk.NORMAL)
        # Q&A export enabled if questions are loaded
        self.export_qa_button.config(state=tk.NORMAL if self.game_logic.questions else tk.DISABLED)
        self.export_qa_json_button.config(state=tk.NORMAL if self.game_logic.questions else tk.DISABLED)

    def _clear_quiz_area(self, clear_question=True, clear_options=True, clear_feedback=True, clear_explanation=True):
        """Clear specific parts of the quiz area."""
        if clear_question:
            self.question_text.config(state=tk.NORMAL)
            self.question_text.delete(1.0, tk.END)
            self.question_text.config(state=tk.DISABLED)
            self.category_label.config(text="")

        if clear_options:
            for widget in self.options_frame.winfo_children():
                widget.destroy()
            self.selected_answer_var.set(-1)

        if clear_feedback:
            self.feedback_label.config(text="", style="Feedback.TLabel")

        if clear_explanation:
            self.explanation_text.config(state=tk.NORMAL)
            self.explanation_text.delete(1.0, tk.END)
            self.explanation_text.config(state=tk.DISABLED)
            self.explanation_text.grid_remove()

    def _update_status(self, message):
        """Update the status bar label."""
        self.status_label.config(text=f"Status: {message}")

    def _update_question_count_label(self, current=None, total=None):
        """Update the question count label in the header."""
        if current is not None and total is not None:
            self.question_count_label.config(text=f"Question: {current} / {total}")
        else:
            self.question_count_label.config(text="")

    def _update_streak_label(self, streak_count):
        """Updates the streak counter label in the header."""
        if streak_count > 1:
            self.streak_label.config(text=f"Streak: {streak_count} \U0001F525")
        else:
            self.streak_label.config(text="")

    def _update_points_display(self):
        """Update the points display in the header."""
        total_points = self.game_logic.achievements.get("points_earned", 0)
        session_points = self.game_logic.session_points
        if session_points > 0:
            self.points_label.config(text=f"Points: {total_points} (+{session_points} session)")
        else:
            self.points_label.config(text=f"Points: {total_points}")

    def _toggle_focus_mode(self, enable):
        """Enables or disables distraction-free focus mode."""
        if enable:
            if self.original_window_state is None:
                self.original_window_state = self.root.attributes('-fullscreen')
            self.root.attributes('-fullscreen', True)
            self.main_actions_frame.grid_remove()
        else:
            if self.original_window_state is not None:
                self.root.attributes('-fullscreen', self.original_window_state)
            else:
                self.root.attributes('-fullscreen', False)
            self.original_window_state = None
            self.main_actions_frame.grid()

    def _show_break_reminder(self):
        """Shows a modal window prompting the user to take a break."""
        if self.on_break:
            return
        self.on_break = True
        self.questions_since_break = 0
        
        self.break_window = tk.Toplevel(self.root)
        self.break_window.title("Time for a Break!")
        self.break_window.transient(self.root)
        self.break_window.grab_set()
        self.break_window.resizable(False, False)
        self.break_window.configure(bg=self.colors["bg"])
        
        self.break_window.protocol("WM_DELETE_WINDOW", lambda: None)
        
        # Center the window
        win_width = 400
        win_height = 200
        x_pos = self.root.winfo_x() + (self.root.winfo_width() // 2) - (win_width // 2)
        y_pos = self.root.winfo_y() + (self.root.winfo_height() // 2) - (win_height // 2)
        self.break_window.geometry(f'{win_width}x{win_height}+{x_pos}+{y_pos}')
        
        ttk.Label(self.break_window, text="Time for a quick break!", font=self.fonts.get("subheader"), foreground=self.colors["accent"]).pack(pady=(20, 10))
        ttk.Label(self.break_window, text="Rest your eyes and stretch for a moment.", font=self.fonts.get("base")).pack(pady=5)
        
        timer_label = ttk.Label(self.break_window, text="", font=self.fonts.get("header"))
        timer_label.pack(pady=20)
        
        break_seconds = self.break_duration_minutes.get() * 60
        
        def countdown(seconds_left):
            mins, secs = divmod(seconds_left, 60)
            timer_label.config(text=f"{mins:02d}:{secs:02d}")
            if seconds_left > 0:
                self.break_window.after(1000, countdown, seconds_left - 1)
            else:
                self.on_break = False
                self.break_window.destroy()
                self._update_status("Break over. Let's continue!")

        countdown(break_seconds)

    def quit_app(self):
        """Save history before quitting, with confirmation if quiz active."""
        quit_confirmed = True

        if self.quiz_active and self.session_lock_enabled.get():
            if self.questions_answered_in_session_gui < self.session_lock_minimum.get():
                remaining = self.session_lock_minimum.get() - self.questions_answered_in_session_gui
                messagebox.showwarning("Session Locked",
                                       f"Session Lock is active! Please answer {remaining} more question(s) to complete your goal.",
                                       parent=self.root)
                return

        if self.quiz_active:
            quit_confirmed = messagebox.askyesno("Quit Confirmation",
                                                 "A quiz session is currently active. Are you sure you want to quit?\n"
                                                 "(Progress for this session will be saved)",
                                                 parent=self.root, icon='warning')

        if quit_confirmed:
            if self.focus_mode_enabled.get():
                self._toggle_focus_mode(enable=False)

            print("Attempting to save history before quitting...")
            self.game_logic.save_history()
            print("History saved (or attempted). Quitting GUI.")
            self.root.quit()
            self.root.destroy()
    def _start_quiz_dialog(self, mode):
        """Show dialog to select category and start quiz with focus options."""
        self.current_quiz_mode = mode

        dialog = tk.Toplevel(self.root)
        dialog.title("Start Quiz Session")
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.resizable(False, False)
        dialog.configure(bg=self.colors["bg"])

        main_frame = ttk.Frame(dialog, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Category Selection
        cat_frame = ttk.Labelframe(main_frame, text="Quiz Settings", padding="10")
        cat_frame.pack(fill="x", expand=True, pady=5)
        
        ttk.Label(cat_frame, text="Category:").grid(row=0, column=0, sticky="w", padx=5, pady=5)
        categories = ["All Categories"] + sorted(list(self.game_logic.categories))
        category_var = tk.StringVar(value=categories[0])
        option_menu = ttk.OptionMenu(cat_frame, category_var, categories[0], *categories, style="TMenubutton")
        option_menu.grid(row=0, column=1, sticky="ew", padx=5, pady=5)
        cat_frame.columnconfigure(1, weight=1)

        focus_frame = ttk.Labelframe(main_frame, text="Focus & Engagement Tools", padding="10")
        focus_frame.pack(fill="x", expand=True, pady=10)
        focus_frame.columnconfigure(1, weight=1)

        # Focus Mode Checkbox
        ttk.Checkbutton(focus_frame, text="Enable Focus Mode (Fullscreen)", variable=self.focus_mode_enabled).grid(row=0, column=0, columnspan=2, sticky="w", padx=5, pady=2)
        
        # Session Lock Checkbox
        session_lock_cb = ttk.Checkbutton(focus_frame, text="Enable Session Lock", variable=self.session_lock_enabled)
        session_lock_cb.grid(row=1, column=0, sticky="w", padx=5, pady=2)
        
        lock_spinbox = ttk.Spinbox(focus_frame, from_=1, to=100, textvariable=self.session_lock_minimum, width=5)
        lock_spinbox.grid(row=1, column=1, sticky="w", padx=5, pady=2)
        ttk.Label(focus_frame, text="questions").grid(row=1, column=2, sticky="w", padx=0, pady=2)
        
        # Break Reminder Checkbox
        break_cb = ttk.Checkbutton(focus_frame, text="Enable Break Reminders", variable=self.break_reminder_enabled)
        break_cb.grid(row=2, column=0, sticky="w", padx=5, pady=2)
        
        break_spinbox = ttk.Spinbox(focus_frame, from_=1, to=100, textvariable=self.break_reminder_interval, width=5)
        break_spinbox.grid(row=2, column=1, sticky="w", padx=5, pady=2)
        ttk.Label(focus_frame, text="questions").grid(row=2, column=2, sticky="w", padx=0, pady=2)

        def on_start():
            selected = category_var.get()
            self.current_category_filter = None if selected == "All Categories" else selected

            self.total_questions_in_filter_gui = sum(1 for q in self.game_logic.questions if self.current_category_filter is None or (len(q)>3 and q[3] == self.current_category_filter))

            if self.total_questions_in_filter_gui == 0:
                messagebox.showwarning("No Questions", f"No questions found for the selected filter: {self.current_category_filter}.", parent=self.root)
                dialog.destroy()
                return

            if self.session_lock_enabled.get():
                if not messagebox.askyesno("Confirm Session Lock",
                    f"You have enabled Session Lock for {self.session_lock_minimum.get()} questions.\n\n"
                    "You will not be able to quit the application until you answer this many questions.\n\n"
                    "Are you ready to commit?", parent=dialog):
                    return

            dialog.destroy()
            self._start_quiz_session()

        button_frame = ttk.Frame(main_frame)
        button_frame.pack(pady=(15, 0))
        ttk.Button(button_frame, text="Start", command=on_start, style="Accent.TButton", width=12).pack(side=tk.LEFT, padx=10)
        ttk.Button(button_frame, text="Cancel", command=dialog.destroy, style="TButton", width=12).pack(side=tk.LEFT, padx=10)

        self.root.wait_window(dialog)

    def _start_quiz_session(self):
        """Begin a new quiz session based on self.current_quiz_mode."""
        self.quiz_active = True
        self.game_logic.score = 0
        self.game_logic.total_questions_session = 0
        self.questions_answered_in_session_gui = 0
        self.game_logic.answered_indices_session = []
        self.gui_verify_session_answers = []
        self.current_question_index = -1
        self.current_streak = 0
        self.questions_since_break = 0
        self._update_streak_label(self.current_streak)

        cat_display = self.current_category_filter or 'All Categories'
        mode_display = "Quiz" if self.current_quiz_mode == QUIZ_MODE_STANDARD else "Verify"
        self._update_status(f"{mode_display} started.")
        self._update_question_count_label(current=0, total=self.total_questions_in_filter_gui)
        
        if self.focus_mode_enabled.get():
            self._toggle_focus_mode(enable=True)

        self._clear_quiz_area(clear_question=False, clear_options=True, clear_feedback=True, clear_explanation=True)

        if self.current_quiz_mode == QUIZ_MODE_VERIFY:
            self.question_text.config(state=tk.NORMAL)
            self.question_text.delete(1.0, tk.END)
            self.question_text.tag_configure("verify_title", font=self.fonts.get("subheader"), foreground=self.colors["accent"], justify='center', spacing3=10)
            self.question_text.tag_configure("verify_body", font=self.fonts.get("base"), foreground=self.colors["fg"], justify='center', spacing1=5, lmargin1=20, lmargin2=20)
            self.question_text.insert(tk.END, "VERIFY YOUR KNOWLEDGE\n", "verify_title")
            self.question_text.insert(tk.END, f"Category: {cat_display}\n\n", "verify_body")
            self.question_text.insert(tk.END, "This mode will test your knowledge.\n", "verify_body")
            self.question_text.insert(tk.END, "You won't be told if you're right or wrong until the end.\n\n", "verify_body")
            self.question_text.insert(tk.END, "Click 'Next Question' to begin.", "verify_body")
            self.question_text.config(state=tk.DISABLED)
            self.category_label.config(text=f"Category: {cat_display}")
            self.submit_button.config(state=tk.DISABLED)
            self.next_button.config(state=tk.NORMAL)
            self.show_results_button.pack_forget()
            self.next_button.focus_set()
        else:
            self._next_question_gui()
        
        self.game_logic.session_points = 0
        self._update_points_display()
        
        if self.current_quiz_mode == "mini_quiz":
            self.total_questions_in_filter_gui = min(MINI_QUIZ_QUESTIONS, self.total_questions_in_filter_gui)

    def _display_question_gui(self):
        """Update the GUI with the current question data."""
        if not self.current_question_data:
            self.quiz_active = False
            if self.focus_mode_enabled.get():
                self._toggle_focus_mode(enable=False)
            self._clear_quiz_area(clear_options=True, clear_feedback=True, clear_explanation=True)
            self.question_text.config(state=tk.NORMAL)
            self.question_text.delete(1.0, tk.END)
            self.question_text.insert(tk.END, "Session Complete!\n\n", ("welcome_title",))
            self.question_text.insert(tk.END, "You've answered all available questions in this category/filter for this session.", "welcome_body")

            if self.current_quiz_mode == QUIZ_MODE_STANDARD:
                final_score_msg = ""
                if self.game_logic.total_questions_session > 0:
                    accuracy = (self.game_logic.score / self.game_logic.total_questions_session * 100)
                    final_score_msg = f"\n\nFinal Score: {self.game_logic.score} / {self.game_logic.total_questions_session} ({accuracy:.1f}%)"
                else:
                    final_score_msg = "\n\nNo questions were answered in this session."
                self.question_text.insert(tk.END, final_score_msg, "welcome_body")
                self.submit_button.config(state=tk.DISABLED)
                self.next_button.config(state=tk.DISABLED)
                self.show_results_button.pack_forget()
                self._update_status("Quiz finished.")
            elif self.current_quiz_mode == QUIZ_MODE_VERIFY:
                self.question_text.insert(tk.END, "\n\nClick 'Show Results' to see your performance.", "welcome_body")
                self.submit_button.config(state=tk.DISABLED)
                self.next_button.config(state=tk.DISABLED)
                self.show_results_button.config(state=tk.NORMAL)
                self.show_results_button.pack(side=tk.LEFT, padx=(10, 0))
                self.show_results_button.focus_set()
                self._update_status("Verification finished. Ready for results.")

            # Final gamification updates
            if self.game_logic.total_questions_session > 0:
                accuracy = (self.game_logic.score / self.game_logic.total_questions_session * 100)
                
                if accuracy == 100 and self.game_logic.total_questions_session >= 3:
                    if "perfect_session" not in self.game_logic.achievements["badges"]:
                        self.game_logic.achievements["badges"].append("perfect_session")
                        messagebox.showinfo("🎯 Perfect Session!", 
                                          f"Amazing! You achieved 100% accuracy!\n\n{self.game_logic.get_achievement_description('perfect_session')}", 
                                          parent=self.root)
                
                self.game_logic.update_leaderboard(self.game_logic.score, self.game_logic.total_questions_session, self.game_logic.session_points)
                
                if self.game_logic.session_points > 0:
                    summary = f"Session Complete!\n\nQuestions: {self.game_logic.total_questions_session}\nAccuracy: {accuracy:.1f}%\nPoints Earned: +{self.game_logic.session_points}"
                    messagebox.showinfo("Session Summary", summary, parent=self.root)
            
            self.game_logic.save_achievements()

            self.question_text.config(state=tk.DISABLED)
            self.game_logic.save_history()
            incorrect_list = self.game_logic.study_history.get("incorrect_review", [])
            self.review_button.config(state=tk.NORMAL if isinstance(incorrect_list, list) and incorrect_list else tk.DISABLED)
            return

        # Display the actual question
        self._clear_quiz_area(clear_question=True, clear_options=True, clear_feedback=True, clear_explanation=True)
        if len(self.current_question_data) < 5:
            self._update_status("Error: Invalid question data.")
            self._load_initial_state()
            return
        q_text, options, _, category, _ = self.current_question_data

        self.category_label.config(text=f"Category: {category}")
        self.question_text.config(state=tk.NORMAL)
        self.question_text.delete(1.0, tk.END)
        self.question_text.insert(tk.END, q_text)
        self.question_text.config(state=tk.DISABLED)

        self.selected_answer_var.set(-1)
        for i, option in enumerate(options):
            rb = ttk.Radiobutton(self.options_frame, text=option, variable=self.selected_answer_var,
                                 value=i, style="TRadiobutton", takefocus=False, command=lambda: self.submit_button.config(state=tk.NORMAL))
            rb.pack(anchor=tk.W, padx=5, pady=4, fill=tk.X)

        self.submit_button.config(state=tk.DISABLED)
        self.next_button.config(state=tk.DISABLED)
        self.show_results_button.pack_forget()
        if self.options_frame.winfo_children():
            try:
                self.options_frame.winfo_children()[0].focus_set()
            except tk.TclError:
                pass

    def _next_question_gui(self):
        """Select and display the next question."""
        if self.on_break:
            return
            
        if not self.quiz_active:
            if self.current_quiz_mode == QUIZ_MODE_VERIFY and self.gui_verify_session_answers:
                messagebox.showinfo("Session Complete", "Verification session is complete. Click 'Show Results'.", parent=self.root)
            else:
                messagebox.showinfo("Quiz Over", "The quiz session is not active or has ended. Please start a new quiz.", parent=self.root)
                self._load_initial_state()
            return
        if self.break_reminder_enabled.get() and self.questions_since_break >= self.break_reminder_interval.get():
            self._show_break_reminder()
            return

        question_data, original_index = self.game_logic.select_question(self.current_category_filter)

        if question_data is None:
            self.current_question_data = None
            self.current_question_index = -1
            self._display_question_gui()
        else:
            self.current_question_data = question_data
            self.current_question_index = original_index
            self._update_question_count_label(current=self.questions_answered_in_session_gui + 1, total=self.total_questions_in_filter_gui)
            self._update_status(f"Displaying question {self.questions_answered_in_session_gui + 1}...")
            self._display_question_gui()

    def _submit_answer_gui(self):
        """Process the user's submitted answer based on the current quiz mode."""
        user_answer_index = self.selected_answer_var.get()
        if user_answer_index == -1: return

        if not self.current_question_data or len(self.current_question_data) < 5:
            self._update_status("Error: No valid question data.")
            self._load_initial_state()
            return

        q_text, options, correct_answer_index, category, explanation = self.current_question_data
        
        if self.current_question_index < 0 or self.current_question_index >= len(self.game_logic.questions):
            self.quiz_active = False
            messagebox.showerror("Internal Error", "Invalid question index encountered. Stopping quiz.", parent=self.root)
            self._load_initial_state()
            return
        original_question_text = self.game_logic.questions[self.current_question_index][0]

        is_correct = (user_answer_index == correct_answer_index)

        # Update streak before calculating points for streak bonus
        if is_correct:
            self.current_streak += 1
        else:
            self.current_streak = 0
        self._update_streak_label(self.current_streak)
        
        # Update History
        self.game_logic.update_history(original_question_text, category, is_correct)
        incorrect_list = self.game_logic.study_history.get("incorrect_review", [])
        self.review_button.config(state=tk.NORMAL if isinstance(incorrect_list, list) and incorrect_list else tk.DISABLED)
        
        self.game_logic.total_questions_session += 1
        self.questions_answered_in_session_gui += 1
        self.questions_since_break += 1

        # Update points and check achievements
        points_earned = 0
        if is_correct:
            points_earned = POINTS_PER_CORRECT
            if self.current_streak >= STREAK_BONUS_THRESHOLD:
                points_earned = int(points_earned * STREAK_BONUS_MULTIPLIER)
        else:
            points_earned = POINTS_PER_INCORRECT
        
        self.game_logic.update_points(points_earned)
        self._update_points_display()
        
        # Check for achievements
        new_badges = self.game_logic.check_achievements(is_correct, self.current_streak)
        if new_badges:
            badge_text = "\n".join([self.game_logic.get_achievement_description(badge) for badge in new_badges])
            messagebox.showinfo("🎉 Achievement Unlocked!", f"Congratulations!\n\n{badge_text}", parent=self.root)
        
        # Disable radio buttons and submit button after answer
        for widget in self.options_frame.winfo_children():
            if isinstance(widget, ttk.Radiobutton):
                widget.config(state=tk.DISABLED)
        self.submit_button.config(state=tk.DISABLED)

        if self.current_quiz_mode == "quick_fire":
            self.game_logic.quick_fire_questions_answered += 1
            if is_correct:
                self.feedback_label.config(text="Correct! 🔥", style="Correct.Feedback.TLabel")
            else:
                self.feedback_label.config(text="Incorrect. Keep going!", style="Incorrect.Feedback.TLabel")
            
            if self.game_logic.quick_fire_questions_answered >= QUICK_FIRE_QUESTIONS or not self.game_logic.check_quick_fire_status():
                elapsed_time = time.time() - self.game_logic.quick_fire_start_time
                self._end_quick_fire_gui(time_up=(elapsed_time > QUICK_FIRE_TIME_LIMIT))
                return
            else:
                self.next_button.config(state=tk.NORMAL)
                self.next_button.focus_set()

        elif self.current_quiz_mode == QUIZ_MODE_STANDARD:
            if is_correct:
                feedback_text = "Correct! \U0001F389"
                if self.current_streak >= 3: feedback_text += f" You're on a roll!"
                self.feedback_label.config(text=feedback_text, style="Correct.Feedback.TLabel")
                self.game_logic.score += 1
            else:
                if 0 <= correct_answer_index < len(options):
                    correct_option_text = options[correct_answer_index]
                    feedback_text = f"Incorrect. \U0001F61E Correct was: {correct_answer_index + 1}. {correct_option_text}"
                    self.feedback_label.config(text=feedback_text, style="Incorrect.Feedback.TLabel")
                else:
                    self.feedback_label.config(text="Incorrect (Error displaying correct option)", style="Incorrect.Feedback.TLabel")
                if explanation:
                    self.explanation_text.config(state=tk.NORMAL); self.explanation_text.delete(1.0, tk.END)
                    self.explanation_text.insert(tk.END, f"Explanation:\n{explanation}"); self.explanation_text.config(state=tk.DISABLED); self.explanation_text.grid()
                else: self.explanation_text.grid_remove()
            self.next_button.config(state=tk.NORMAL)
            self.next_button.focus_set()
            score_percent = (self.game_logic.score / self.game_logic.total_questions_session * 100) if self.game_logic.total_questions_session else 0
            self._update_status(f"Answer submitted. Score: {self.game_logic.score}/{self.game_logic.total_questions_session} ({score_percent:.0f}%)")

        elif self.current_quiz_mode == QUIZ_MODE_VERIFY:
            self.gui_verify_session_answers.append((self.current_question_data, user_answer_index, is_correct))
            if is_correct: self.game_logic.score += 1
            self.feedback_label.config(text="Answer recorded.", style="Info.Feedback.TLabel")
            self.explanation_text.grid_remove()
            self.next_button.config(state=tk.NORMAL)
            self.next_button.focus_set()
            self._update_status(f"Answer {self.questions_answered_in_session_gui} recorded.")
        
        elif self.current_quiz_mode == "daily_challenge":
            final_message = ""
            if is_correct:
                self.feedback_label.config(text="Correct! \U0001F389 Well done on the Daily Challenge!", style="Correct.Feedback.TLabel")
                self.game_logic.score += 1 
                self.game_logic.daily_challenge_completed = True
                today_iso = datetime.now().date().isoformat()
                self.game_logic.last_daily_challenge_date = today_iso
                
                self.game_logic.achievements.setdefault("daily_warrior_dates", [])
                if isinstance(self.game_logic.achievements["daily_warrior_dates"], set):
                    self.game_logic.achievements["daily_warrior_dates"] = list(self.game_logic.achievements["daily_warrior_dates"])
                if today_iso not in self.game_logic.achievements["daily_warrior_dates"]:
                    self.game_logic.achievements["daily_warrior_dates"].append(today_iso)
                
                if "daily_warrior" not in self.game_logic.achievements["badges"] and len(self.game_logic.achievements["daily_warrior_dates"]) >= 1:
                    self.game_logic.achievements["badges"].append("daily_warrior")
                    final_message += f"\n\n🏆 Achievement Unlocked!\n{self.game_logic.get_achievement_description('daily_warrior')}"
                final_message = "Daily Challenge: Correct! " + final_message
            else:
                if 0 <= correct_answer_index < len(options):
                    correct_option_text = options[correct_answer_index]
                    self.feedback_label.config(text=f"Incorrect for Daily Challenge. \U0001F61E Correct was: {correct_answer_index + 1}. {correct_option_text}", style="Incorrect.Feedback.TLabel")
                else:
                    self.feedback_label.config(text="Incorrect (Error displaying correct option)", style="Incorrect.Feedback.TLabel")
                if explanation:
                    self.explanation_text.config(state=tk.NORMAL); self.explanation_text.delete(1.0, tk.END)
                    self.explanation_text.insert(tk.END, f"Explanation:\n{explanation}"); self.explanation_text.config(state=tk.DISABLED); self.explanation_text.grid()
                final_message = "Daily Challenge: Incorrect. Better luck next time!"

            self.next_button.config(state=tk.DISABLED)
            self.game_logic.save_achievements()
            self.game_logic.save_history()
            
            messagebox.showinfo("Daily Challenge Complete", f"{final_message}\nPoints Earned This Question: +{points_earned}", parent=self.root)
            if self.focus_mode_enabled.get(): self._toggle_focus_mode(enable=False)
            self._load_initial_state()
            self.quiz_active = False
            return

        elif self.current_quiz_mode == "pop_quiz":
            if is_correct:
                self.feedback_label.config(text="Correct! \U0001F389 Nice job on the Pop Quiz!", style="Correct.Feedback.TLabel")
                self.game_logic.score += 1
            else:
                if 0 <= correct_answer_index < len(options):
                    correct_option_text = options[correct_answer_index]
                    self.feedback_label.config(text=f"Incorrect for Pop Quiz. \U0001F61E Correct was: {correct_answer_index + 1}. {correct_option_text}", style="Incorrect.Feedback.TLabel")
                else:
                    self.feedback_label.config(text="Incorrect (Error displaying correct option)", style="Incorrect.Feedback.TLabel")
                if explanation:
                    self.explanation_text.config(state=tk.NORMAL); self.explanation_text.delete(1.0, tk.END)
                    self.explanation_text.insert(tk.END, f"Explanation:\n{explanation}"); self.explanation_text.config(state=tk.DISABLED); self.explanation_text.grid()

            self.next_button.config(state=tk.DISABLED)
            self.game_logic.save_achievements()
            self.game_logic.save_history()

            messagebox.showinfo("Pop Quiz Complete", f"Your Pop Quiz attempt is complete!\nPoints Earned This Question: +{points_earned}", parent=self.root)
            if self.focus_mode_enabled.get(): self._toggle_focus_mode(enable=False)
            self._load_initial_state()
            self.quiz_active = False
            return

        elif self.current_quiz_mode == "mini_quiz":
            if is_correct:
                feedback_text = "Correct! \U0001F389"
                if self.current_streak >= 3: feedback_text += f" You're on a roll!"
                self.feedback_label.config(text=feedback_text, style="Correct.Feedback.TLabel")
                self.game_logic.score += 1
            else:
                if 0 <= correct_answer_index < len(options):
                    correct_option_text = options[correct_answer_index]
                    feedback_text = f"Incorrect. \U0001F61E Correct was: {correct_answer_index + 1}. {correct_option_text}"
                    self.feedback_label.config(text=feedback_text, style="Incorrect.Feedback.TLabel")
                else:
                    self.feedback_label.config(text="Incorrect (Error displaying correct option)", style="Incorrect.Feedback.TLabel")
                if explanation:
                    self.explanation_text.config(state=tk.NORMAL); self.explanation_text.delete(1.0, tk.END)
                    self.explanation_text.insert(tk.END, f"Explanation:\n{explanation}"); self.explanation_text.config(state=tk.DISABLED); self.explanation_text.grid()
                else: self.explanation_text.grid_remove()

            if self.questions_answered_in_session_gui >= self.total_questions_in_filter_gui:
                self.next_button.config(state=tk.DISABLED)
                self._end_mini_quiz_gui() 
                return 
            else:
                self.next_button.config(state=tk.NORMAL)
                self.next_button.focus_set()
        
        if self.current_quiz_mode not in ["daily_challenge", "pop_quiz", "quick_fire"] or (self.current_quiz_mode == "quick_fire" and self.game_logic.quick_fire_active):
            self._update_question_count_label(current=self.questions_answered_in_session_gui, total=self.total_questions_in_filter_gui)

        self.game_logic.save_history()
        self.game_logic.save_achievements()

    def _end_mini_quiz_gui(self):
        """End Mini Quiz mode and show results."""
        self.quiz_active = False
        self.game_logic.quick_fire_active = False

        self.game_logic.save_achievements()
        self.game_logic.save_history()

        accuracy = (self.game_logic.score / self.questions_answered_in_session_gui * 100) if self.questions_answered_in_session_gui > 0 else 0
        summary_message = (
            f"🎉 Mini Quiz Complete! 🎉\n\n"
            f"Questions Answered: {self.questions_answered_in_session_gui}\n"
            f"Score: {self.game_logic.score} / {self.questions_answered_in_session_gui} ({accuracy:.1f}%)\n"
            f"Points Earned This Session: +{self.game_logic.session_points}\n"
            f"Total Points: {self.game_logic.achievements.get('points_earned', 0)}"
        )
        
        if accuracy == 100 and self.questions_answered_in_session_gui >= 3:
            if "perfect_session" not in self.game_logic.achievements["badges"]:
                self.game_logic.achievements["badges"].append("perfect_session")
                summary_message += f"\n\n🏆 Achievement Unlocked!\n{self.game_logic.get_achievement_description('perfect_session')}"
                self.game_logic.save_achievements()

        if self.questions_answered_in_session_gui > 0:
            self.game_logic.update_leaderboard(self.game_logic.score, self.questions_answered_in_session_gui, self.game_logic.session_points)

        messagebox.showinfo("Mini Quiz Finished", summary_message, parent=self.root)
        
        if self.focus_mode_enabled.get():
            self._toggle_focus_mode(enable=False)
        self._load_initial_state()
        self._update_points_display()
    
    def _show_stats_gui(self):
        """Display statistics in a Toplevel window with improved styling."""
        stats_win = tk.Toplevel(self.root)
        stats_win.title("Study Statistics")
        stats_win.geometry("900x900")
        stats_win.transient(self.root)
        stats_win.grab_set()
        stats_win.configure(bg=self.colors["bg"])
        stats_win.minsize(700, 500)

        try:
            stats_win.tk_setPalette(background=self.colors["bg"], foreground=self.colors["fg"])
        except tk.TclError:
            print("Warning: Could not set Toplevel palette for stats window.")

        stats_frame = ttk.Frame(stats_win, padding="15")
        stats_frame.pack(fill=tk.BOTH, expand=True)

        stats_text_widget = scrolledtext.ScrolledText(stats_frame, wrap=tk.WORD, font=self.fonts.get("stats"),
                             relief="solid", bd=1, borderwidth=1,
                             bg=self.colors["explanation_bg"], fg=self.colors["fg"],
                             padx=15, pady=15,
                             selectbackground=self.colors["accent"],
                             selectforeground=self.colors["bg"])
        stats_text_widget.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        try:
            stats_text_widget.vbar.configure(style="Vertical.TScrollbar")
        except tk.TclError:
            print("Note: Could not apply custom style to ScrolledText scrollbar in stats.")

        # Define tags for coloring/styling
        stats_text_widget.tag_configure("header", font=self.fonts.get("subheader"), foreground=self.colors["fg_header"], spacing1=10, spacing3=10)
        stats_text_widget.tag_configure("subheader", font=self.fonts.get("bold"), foreground=self.colors["accent"], spacing1=8, spacing3=5)
        stats_text_widget.tag_configure("label", foreground=self.colors["status_fg"])
        stats_text_widget.tag_configure("value", foreground=self.colors["fg"])
        stats_text_widget.tag_configure("correct", foreground=self.colors["correct"])
        stats_text_widget.tag_configure("incorrect", foreground=self.colors["incorrect"])
        stats_text_widget.tag_configure("neutral", foreground=self.colors["accent_dark"])
        stats_text_widget.tag_configure("dim", foreground=self.colors["dim"])
        stats_text_widget.tag_configure("q_text", foreground=self.colors["fg"], spacing1=5)
        stats_text_widget.tag_configure("q_details", foreground=self.colors["dim"], spacing3=10)

        # Populate Stats Text
        stats_text_widget.insert(tk.END, "--- Study Statistics ---\n", "header")

        # Overall Performance
        history = self.game_logic.study_history
        total_attempts = history.get("total_attempts", 0)
        total_correct = history.get("total_correct", 0)
        overall_accuracy = (total_correct / total_attempts * 100) if total_attempts > 0 else 0
        acc_tag = "correct" if overall_accuracy >= 75 else ("neutral" if overall_accuracy >= 50 else "incorrect")

        stats_text_widget.insert(tk.END, "Overall Performance (All Time):\n", "subheader")
        stats_text_widget.insert(tk.END, "  Total Questions Answered: ", "label")
        stats_text_widget.insert(tk.END, f"{total_attempts}\n", "value")
        stats_text_widget.insert(tk.END, "  Total Correct:            ", "label")
        stats_text_widget.insert(tk.END, f"{total_correct}\n", "value")
        stats_text_widget.insert(tk.END, "  Overall Accuracy:         ", "label")
        stats_text_widget.insert(tk.END, f"{overall_accuracy:.2f}%\n\n", acc_tag)

        # Performance by Category
        stats_text_widget.insert(tk.END, "Performance by Category:\n", "subheader")
        categories_data = history.get("categories", {})
        sorted_categories = sorted(
            [(cat, stats) for cat, stats in categories_data.items() if isinstance(stats, dict) and stats.get("attempts", 0) > 0],
            key=lambda item: item[0]
        )

        if not sorted_categories:
            stats_text_widget.insert(tk.END, "  No category data recorded yet (or no attempts made).\n", "dim")
        else:
            max_len = max((len(cat) for cat, stats in sorted_categories), default=10)
            header_line = f"  {'Category'.ljust(max_len)} | {'Correct'.rjust(7)} | {'Attempts'.rjust(8)} | {'Accuracy'.rjust(9)}\n"
            stats_text_widget.insert(tk.END, header_line, "label")
            stats_text_widget.insert(tk.END, f"  {'-' * max_len}-+---------+----------+----------\n", "dim")
            for category, stats in sorted_categories:
                cat_attempts = stats.get("attempts", 0)
                cat_correct = stats.get("correct", 0)
                cat_accuracy = (cat_correct / cat_attempts * 100)
                acc_tag = "correct" if cat_accuracy >= 75 else ("neutral" if cat_accuracy >= 50 else "incorrect")

                stats_text_widget.insert(tk.END, f"  {category.ljust(max_len)} | ")
                stats_text_widget.insert(tk.END, f"{str(cat_correct).rjust(7)}", "value")
                stats_text_widget.insert(tk.END, " | ")
                stats_text_widget.insert(tk.END, f"{str(cat_attempts).rjust(8)}", "value")
                stats_text_widget.insert(tk.END, " | ")
                stats_text_widget.insert(tk.END, f"{f'{cat_accuracy:.1f}%'.rjust(9)}\n", acc_tag)
        stats_text_widget.insert(tk.END, "\n")

        # Performance on Specific Questions
        stats_text_widget.insert(tk.END, "Performance on Specific Questions (All History):\n", "subheader")
        question_stats = history.get("questions", {})
        attempted_questions = {q: stats for q, stats in question_stats.items() if isinstance(stats, dict) and stats.get("attempts", 0) > 0}

        if not attempted_questions:
            stats_text_widget.insert(tk.END, "  No specific question data recorded yet (or no attempts made).\n", "dim")
        else:
            def sort_key(item):
                q_text, stats = item
                attempts = stats.get("attempts", 0)
                correct = stats.get("correct", 0)
                accuracy = correct / attempts
                return (accuracy, -attempts)

            sorted_questions = sorted(attempted_questions.items(), key=sort_key)
            stats_text_widget.insert(tk.END, "  (Sorted by lowest accuracy first)\n", "dim")

            for i, (q_text, stats) in enumerate(sorted_questions):
                attempts = stats.get("attempts", 0)
                correct = stats.get("correct", 0)
                accuracy = (correct / attempts * 100)
                acc_tag = "correct" if accuracy >= 75 else ("neutral" if accuracy >= 50 else "incorrect")

                last_result = "N/A"
                last_tag = "dim"
                if isinstance(stats.get("history"), list) and stats["history"]:
                    last_entry = stats["history"][-1]
                    if isinstance(last_entry, dict) and "correct" in last_entry:
                        last_correct = last_entry.get("correct")
                        last_result = "Correct" if last_correct else "Incorrect"
                        last_tag = "correct" if last_correct else "incorrect"

                display_text = (q_text[:100] + '...') if len(q_text) > 100 else q_text
                stats_text_widget.insert(tk.END, f"{i+1}. \"{display_text}\"\n", "q_text")
                stats_text_widget.insert(tk.END, f"      ({attempts} attempts, ", "q_details")
                stats_text_widget.insert(tk.END, f"{accuracy:.1f}%", acc_tag)
                stats_text_widget.insert(tk.END, " acc.) Last: ", "q_details")
                stats_text_widget.insert(tk.END, f"{last_result}\n\n", last_tag)

        stats_text_widget.config(state=tk.DISABLED)

        # Close button frame
        button_frame = ttk.Frame(stats_win, style="TFrame")
        button_frame.pack(pady=(10, 15))
        close_button = ttk.Button(button_frame, text="Close", command=stats_win.destroy, style="TButton", width=12)
        close_button.pack()

        self.root.wait_window(stats_win)

    def _show_verify_results_gui(self):
        """Displays the results after a 'Verify Knowledge' session in a Toplevel window."""
        results_win = tk.Toplevel(self.root)
        results_win.title("Verification Results")
        results_win.geometry("900x900")
        results_win.transient(self.root)
        results_win.grab_set()
        results_win.configure(bg=self.colors["bg"])
        results_win.minsize(700, 550)

        try:
            results_win.tk_setPalette(background=self.colors["bg"], foreground=self.colors["fg"])
        except tk.TclError:
            print("Warning: Could not set Toplevel palette for results window.")

        results_frame = ttk.Frame(results_win, padding="15")
        results_frame.pack(fill=tk.BOTH, expand=True)

        results_text = scrolledtext.ScrolledText(results_frame, wrap=tk.WORD, font=self.fonts.get("base"),
                                                 relief="solid", bd=1, borderwidth=1,
                                                 bg=self.colors["explanation_bg"], fg=self.colors["fg"],
                                                 padx=15, pady=15,
                                                 selectbackground=self.colors["accent"],
                                                 selectforeground=self.colors["bg"])
        results_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        try:
            results_text.vbar.configure(style="Vertical.TScrollbar")
        except tk.TclError:
            print("Note: Could not apply custom style to ScrolledText scrollbar in results.")

        # Define tags
        results_text.tag_configure("header", font=self.fonts.get("subheader"), foreground=self.colors["fg_header"], spacing1=10, spacing3=10)
        results_text.tag_configure("subheader", font=self.fonts.get("bold"), foreground=self.colors["accent"], spacing1=8, spacing3=5)
        results_text.tag_configure("label", foreground=self.colors["status_fg"])
        results_text.tag_configure("value", foreground=self.colors["fg"])
        results_text.tag_configure("correct", foreground=self.colors["correct"])
        results_text.tag_configure("incorrect", foreground=self.colors["incorrect"])
        results_text.tag_configure("neutral", foreground=self.colors["accent_dark"])
        results_text.tag_configure("dim", foreground=self.colors["dim"])
        results_text.tag_configure("q_text", font=self.fonts.get("question"), foreground=self.colors["fg"], spacing1=8, spacing3=5)
        results_text.tag_configure("option", font=self.fonts.get("option"), foreground=self.colors["fg"], lmargin1=20, lmargin2=20)
        results_text.tag_configure("explanation", font=self.fonts.get("explanation"), foreground=self.colors["dim"], lmargin1=20, lmargin2=20, spacing1=5, spacing3=10)
        results_text.tag_configure("separator", foreground=self.colors["border"], justify='center', spacing1=10, spacing3=10)

        # Populate Results
        results_text.insert(tk.END, "--- Verification Results ---\n", "header")

        if not self.gui_verify_session_answers:
            results_text.insert(tk.END, "No questions were answered in this verification session.\n", "dim")
        else:
            num_correct = sum(1 for _, _, is_correct in self.gui_verify_session_answers if is_correct)
            total_answered = len(self.gui_verify_session_answers)
            accuracy = (num_correct / total_answered * 100) if total_answered > 0 else 0
            acc_tag = "correct" if accuracy >= 75 else ("neutral" if accuracy >= 50 else "incorrect")

            results_text.insert(tk.END, "Session Summary:\n", "subheader")
            results_text.insert(tk.END, f"  Total Questions Answered: ", "label")
            results_text.insert(tk.END, f"{total_answered}\n", "value")
            results_text.insert(tk.END, f"  Correct Answers:         ", "label")
            results_text.insert(tk.END, f"{num_correct}\n", "value")
            results_text.insert(tk.END, f"  Accuracy:                ", "label")
            results_text.insert(tk.END, f"{accuracy:.2f}%\n\n", acc_tag)
            results_text.insert(tk.END, f"{'-'*50}\n", "separator")

            results_text.insert(tk.END, "Detailed Review:\n", "subheader")
            for i, (q_data, user_answer_idx, is_correct) in enumerate(self.gui_verify_session_answers):
                if len(q_data) < 5: continue
                q_text, options, correct_idx, _, explanation = q_data
                results_text.insert(tk.END, f"{i+1}. {q_text}\n", "q_text")

                if 0 <= user_answer_idx < len(options) and 0 <= correct_idx < len(options):
                    user_choice_text = options[user_answer_idx]
                    correct_choice_text = options[correct_idx]

                    user_tag = "correct" if is_correct else "incorrect"
                    feedback_icon = "\U0001F389" if is_correct else "\U0001F61E"
                    results_text.insert(tk.END, f"Your answer: {user_answer_idx+1}. {user_choice_text} ({feedback_icon})\n", ("option", user_tag))

                    if not is_correct:
                        results_text.insert(tk.END, f"Correct answer: {correct_idx+1}. {correct_choice_text}\n", ("option", "correct"))

                    if explanation:
                        results_text.insert(tk.END, f"Explanation: {explanation}\n", "explanation")

                    results_text.insert(tk.END, f"{'.'*50}\n", "separator")
                else:
                    results_text.insert(tk.END, f"Error displaying details: Invalid index.\n", "incorrect")
                    results_text.insert(tk.END, f"{'.'*50}\n", "separator")

        results_text.config(state=tk.DISABLED)

        # Close button
        button_frame = ttk.Frame(results_win, style="TFrame")
        button_frame.pack(pady=(10, 15))
        close_button = ttk.Button(button_frame, text="Close", style="TButton", width=12)
        close_button.pack()

        def on_close():
            results_win.destroy()
            self._load_initial_state()

        results_win.protocol("WM_DELETE_WINDOW", on_close)
        close_button.config(command=on_close)

        self.root.wait_window(results_win)

    def _clear_stats_gui(self):
        """Ask for confirmation and clear stats via game logic."""
        if messagebox.askyesno("Confirm Clear",
                               "Are you sure you want to delete ALL study history?\n"
                               "This includes all performance statistics and the list of incorrect answers.\n\n"
                               "This action cannot be undone.",
                               parent=self.root, icon='warning'):
            self.game_logic.study_history = self.game_logic._default_history()
            for category in self.game_logic.categories:
                self.game_logic.study_history["categories"].setdefault(category, {"correct": 0, "attempts": 0})
            self.game_logic.save_history()
            messagebox.showinfo("Stats Cleared", "Study history has been cleared.", parent=self.root)
            self._update_status("Study history cleared.")
            self.review_button.config(state=tk.DISABLED)

    def _review_incorrect_gui(self):
        """Allows reviewing incorrect answers in the GUI (Basic View)."""
        incorrect_list = self.game_logic.study_history.get("incorrect_review", [])
        if not isinstance(incorrect_list, list):
            incorrect_list = []
            self.game_logic.study_history["incorrect_review"] = []

        if not incorrect_list:
            messagebox.showinfo("Review Incorrect", "No incorrect answers recorded in history.", parent=self.root)
            return

        # Find the full question data
        questions_to_review = []
        not_found_questions = []
        questions_to_remove_from_history = []
        incorrect_list_copy = list(incorrect_list)

        for incorrect_text in incorrect_list_copy:
            found = False
            for q_data in self.game_logic.questions:
                if isinstance(q_data, (list, tuple)) and len(q_data) > 0 and q_data[0] == incorrect_text:
                    questions_to_review.append(q_data)
                    found = True
                    break
            if not found:
                not_found_questions.append(incorrect_text)
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
            if not self.game_logic.study_history.get("incorrect_review", []):
                self.review_button.config(state=tk.DISABLED)

        if not questions_to_review and not_found_questions:
            messagebox.showerror("Review Error", "Could not load data for any previously incorrect questions. They may have been removed from the source.", parent=self.root)
            if history_changed:
                self.game_logic.save_history()
            return
        elif not questions_to_review:
            messagebox.showinfo("Review Incorrect", "No incorrect answers available to review.", parent=self.root)
            if history_changed:
                self.game_logic.save_history()
            return

        # Create Review Window
        review_win = tk.Toplevel(self.root)
        review_win.title("Review Incorrect Answers")
        review_win.geometry("900x900")
        review_win.transient(self.root)
        review_win.grab_set()
        review_win.configure(bg=self.colors["bg"])
        review_win.minsize(700, 550)

        try:
            review_win.tk_setPalette(background=self.colors["bg"], foreground=self.colors["fg"])
        except tk.TclError:
            print("Warning: Could not set Toplevel palette for review window.")

        review_frame = ttk.Frame(review_win, padding="15")
        review_frame.pack(fill=tk.BOTH, expand=True, side=tk.TOP)
        review_frame.rowconfigure(1, weight=1)
        review_frame.columnconfigure(0, weight=1)

        ttk.Label(review_frame, text="Incorrectly Answered Questions", style="Header.TLabel").grid(row=0, column=0, pady=(0,15), sticky="w")

        review_text = scrolledtext.ScrolledText(review_frame, wrap=tk.WORD, font=self.fonts.get("base"),
                                                 relief="solid", bd=1, borderwidth=1,
                                                 bg=self.colors["explanation_bg"], fg=self.colors["fg"],
                                                 padx=15, pady=15,
                                                 selectbackground=self.colors["accent"],
                                                 selectforeground=self.colors["bg"])
        review_text.grid(row=1, column=0, sticky="nsew", pady=5)
        try:
            review_text.vbar.configure(style="Vertical.TScrollbar")
        except tk.TclError:
            print("Note: Could not apply custom style to ScrolledText scrollbar in review.")

        # Define tags
        review_text.tag_configure("q_text", font=self.fonts.get("question"), foreground=self.colors["fg"], spacing1=8, spacing3=5)
        review_text.tag_configure("option", font=self.fonts.get("option"), foreground=self.colors["fg"], lmargin1=20, lmargin2=20)
        review_text.tag_configure("correct_option", font=self.fonts.get("option"), foreground=self.colors["correct"], lmargin1=20, lmargin2=20)
        review_text.tag_configure("explanation", font=self.fonts.get("explanation"), foreground=self.colors["dim"], lmargin1=20, lmargin2=20, spacing1=5, spacing3=10)
        review_text.tag_configure("category", font=self.fonts.get("italic"), foreground=self.colors["category_fg"], spacing1=5)
        review_text.tag_configure("separator", foreground=self.colors["border"], justify='center', spacing1=10, spacing3=10)
        review_text.tag_configure("warning", foreground=self.colors["incorrect"], font=self.fonts.get("italic"))

        def populate_review_text():
            review_text.config(state=tk.NORMAL)
            review_text.delete(1.0, tk.END)
            for i, q_data in enumerate(questions_to_review):
                if len(q_data) < 5: continue
                q_text, options, correct_idx, category, explanation = q_data
                review_text.insert(tk.END, f"{i+1}. {q_text}\n", "q_text")
                review_text.insert(tk.END, f"Category: {category}\n", "category")

                for j, option in enumerate(options):
                    if 0 <= correct_idx < len(options):
                        if j == correct_idx:
                            review_text.insert(tk.END, f"   \u2714 {option} (Correct Answer)\n", "correct_option")
                        else:
                            review_text.insert(tk.END, f"   \u2022 {option}\n", "option")
                    else:
                        review_text.insert(tk.END, f"   \u2022 {option}\n", "option")

                if explanation:
                    review_text.insert(tk.END, f"Explanation: {explanation}\n", "explanation")

                review_text.insert(tk.END, f"{'-'*50}\n", "separator")

            if not_found_questions:
                review_text.insert(tk.END, "\nWarning: Some questions previously marked incorrect could not be found (they might have been removed from the source data and were removed from this list):\n", "warning")
                for nf_text in not_found_questions:
                    review_text.insert(tk.END, f"- {nf_text[:80]}...\n", "warning")
            review_text.config(state=tk.DISABLED)

        populate_review_text()

        # Action Buttons Frame
        button_frame = ttk.Frame(review_win, style="TFrame")
        button_frame.pack(pady=(10, 15), fill='x', side=tk.BOTTOM)

        def clear_item_from_review_list():
            nonlocal history_changed
            num_str = simpledialog.askstring("Clear Item", "Enter the number of the question to remove from this review list:", parent=review_win)
            if num_str:
                try:
                    num_to_clear = int(num_str) - 1
                    if 0 <= num_to_clear < len(questions_to_review):
                        if isinstance(questions_to_review[num_to_clear], (list, tuple)) and len(questions_to_review[num_to_clear]) > 0:
                            question_to_clear_text = questions_to_review[num_to_clear][0]
                            if messagebox.askyesno("Confirm Clear", f"Remove question {num_to_clear+1} from the review list?", parent=review_win):
                                if isinstance(self.game_logic.study_history.get("incorrect_review"), list) and question_to_clear_text in self.game_logic.study_history["incorrect_review"]:
                                    self.game_logic.study_history["incorrect_review"].remove(question_to_clear_text)
                                    history_changed = True
                                    messagebox.showinfo("Cleared", "Question removed from review list.", parent=review_win)
                                    del questions_to_review[num_to_clear]
                                    populate_review_text()
                                    if not self.game_logic.study_history.get("incorrect_review", []):
                                        self.review_button.config(state=tk.DISABLED)
                                        clear_button.config(state=tk.DISABLED)
                                else:
                                    messagebox.showerror("Error", "Question not found in history list.", parent=review_win)
                        else:
                            messagebox.showerror("Error", "Cannot clear invalid question data.", parent=review_win)
                    else:
                        messagebox.showwarning("Invalid Number", f"Please enter a number between 1 and {len(questions_to_review)}.", parent=review_win)
                except ValueError:
                    messagebox.showerror("Invalid Input", "Please enter a valid number.", parent=review_win)

        clear_button_state = tk.NORMAL if questions_to_review else tk.DISABLED
        clear_button = ttk.Button(button_frame, text="Clear Item from List", command=clear_item_from_review_list, style="TButton", width=20, state=clear_button_state)
        clear_button.pack(side=tk.LEFT, padx=(15, 5))

        close_button = ttk.Button(button_frame, text="Close", style="TButton", width=12)
        close_button.pack(side=tk.RIGHT, padx=(5, 15))

        def on_close():
            if history_changed:
                self.game_logic.save_history()
            review_win.destroy()
        review_win.protocol("WM_DELETE_WINDOW", on_close)
        close_button.config(command=on_close)

        self.root.wait_window(review_win)

    def _export_data_gui(self):
        """Exports study history data via GUI using asksaveasfilename."""
        initial_filename = f"linux_plus_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        export_filename = filedialog.asksaveasfilename(
            parent=self.root,
            title="Export Study History",
            initialfile=initial_filename,
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )

        if not export_filename:
            self._update_status("History export cancelled.")
            return

        try:
            export_path = os.path.abspath(export_filename)
            self._update_status(f"Exporting history to {os.path.basename(export_path)}...")
            self.root.update_idletasks()

            with open(export_filename, 'w', encoding='utf-8') as f:
                json.dump(self.game_logic.study_history, f, indent=2)

            messagebox.showinfo("Export Successful", f"Study history successfully exported to:\n{export_path}", parent=self.root)
            self._update_status("History export successful.")

        except IOError as e:
            messagebox.showerror("Export Error", f"Error exporting history: {e}\nPlease check permissions and filename.", parent=self.root)
            self._update_status("History export failed.")
        except Exception as e:
            messagebox.showerror("Export Error", f"An unexpected error occurred during history export: {e}", parent=self.root)
            self._update_status("History export failed.")

    def _export_questions_answers_gui(self):
        """Exports loaded questions and answers via GUI using asksaveasfilename."""
        if not self.game_logic.questions:
            messagebox.showwarning("Export Q&A", "No questions are currently loaded to export.", parent=self.root)
            self.export_qa_button.config(state=tk.DISABLED)
            return

        initial_filename = f"Linux_plus_QA_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        export_filename = filedialog.asksaveasfilename(
            parent=self.root,
            title="Export Questions & Answers",
            initialfile=initial_filename,
            defaultextension=".md",
            filetypes=[("Markdown files", "*.md"), ("Text files", "*.txt"), ("All files", "*.*")]
        )

        if not export_filename:
            self._update_status("Q&A export cancelled.")
            return

        try:
            export_path = os.path.abspath(export_filename)
            self._update_status(f"Exporting Q&A to {os.path.basename(export_path)}...")
            self.root.update_idletasks()

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

            messagebox.showinfo("Export Successful", f"Questions & Answers successfully exported to:\n{export_path}", parent=self.root)
            self._update_status("Q&A export successful.")

        except IOError as e:
            messagebox.showerror("Export Error", f"Error exporting Q&A: {e}\nPlease check permissions and filename.", parent=self.root)
            self._update_status("Q&A export failed.")
        except Exception as e:
            messagebox.showerror("Export Error", f"An unexpected error occurred during Q&A export: {e}", parent=self.root)
            self._update_status("Q&A export failed.")

    def _export_questions_answers_json_gui(self):
        """Exports loaded questions and answers to JSON via GUI using asksaveasfilename."""
        if not self.game_logic.questions:
            messagebox.showwarning("Export Q&A", "No questions are currently loaded to export.", parent=self.root)
            self.export_qa_json_button.config(state=tk.DISABLED)
            return

        initial_filename = f"Linux_plus_QA_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        export_filename = filedialog.asksaveasfilename(
            parent=self.root,
            title="Export Questions & Answers (JSON)",
            initialfile=initial_filename,
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )

        if not export_filename:
            self._update_status("JSON Q&A export cancelled.")
            return

        try:
            export_path = os.path.abspath(export_filename)
            self._update_status(f"Exporting Q&A to {os.path.basename(export_path)}...")
            self.root.update_idletasks()

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

            messagebox.showinfo("Export Successful", f"Questions & Answers successfully exported to:\n{export_path}", parent=self.root)
            self._update_status("JSON Q&A export successful.")

        except IOError as e:
            messagebox.showerror("Export Error", f"Error exporting Q&A: {e}\nPlease check permissions and filename.", parent=self.root)
            self._update_status("JSON Q&A export failed.")
        except Exception as e:
            messagebox.showerror("Export Error", f"An unexpected error occurred during Q&A export: {e}", parent=self.root)
            self._update_status("JSON Q&A export failed.")

    def _setup_cli_playground(self, parent):
        """Create the widgets for the CLI playground."""
        parent.columnconfigure(0, weight=1)

        # Output area
        self.cli_output = scrolledtext.ScrolledText(parent, wrap=tk.WORD, height=10,
                                    font=("Consolas", 10), relief="flat",
                                    bg="#1E1E1E", fg="#CCCCCC",
                                    bd=1, state=tk.DISABLED,
                                    padx=10, pady=10, insertbackground="#FFFFFF",
                                    selectbackground=self.colors["accent"],
                                    selectforeground=self.colors["bg"])
        self.cli_output.grid(row=0, column=0, sticky="nsew")
        try:
            self.cli_output.vbar.configure(style="Vertical.TScrollbar")
        except tk.TclError:
            print("Note: Could not apply custom style to CLI ScrolledText scrollbar.")
        
        # Input Frame
        input_frame = ttk.Frame(parent, style="TFrame")
        input_frame.grid(row=1, column=0, sticky="ew")
        input_frame.columnconfigure(1, weight=1)

        self.prompt_label = ttk.Label(input_frame, text=self.cli_playground.get_prompt(), 
                                    foreground=self.colors["accent"], font=("Consolas", 10, "bold"))
        self.prompt_label.grid(row=0, column=0, sticky="w", padx=(5, 5))

        self.cli_input = ttk.Entry(input_frame, font=("Consolas", 10), style="TEntry")
        self.cli_input.grid(row=0, column=1, sticky="ew")
        self.cli_input.bind("<Return>", self._execute_cli_command)

        self._add_cli_output(self.cli_playground.get_welcome_message())

    def _toggle_cli_playground(self):
        """Shows or hides the CLI playground frame."""
        if self.cli_frame.winfo_viewable():
            self.cli_frame.grid_remove()
            self.root.rowconfigure(2, weight=0)
        else:
            self.cli_frame.grid(row=3, column=0, columnspan=2, sticky="nsew", pady=(10,0))
            self.root.rowconfigure(2, weight=1)
            self.cli_input.focus_set()

    def _add_cli_output(self, text):
        """Appends text to the CLI output widget."""
        self.cli_output.config(state=tk.NORMAL)
        self.cli_output.insert(tk.END, text)
        self.cli_output.config(state=tk.DISABLED)
        self.cli_output.see(tk.END)

    def _execute_cli_command(self, event=None):
        """Handles the execution of a command from the CLI input."""
        command = self.cli_input.get().strip()
        if not command:
            return

        # Echo the command to the output
        prompt = self.cli_playground.get_prompt()
        self._add_cli_output(f"\n{prompt}{command}\n")

        # Process the command and get the result
        result = self.cli_playground.process_command(command)
        
        # Handle special commands
        if result == "CLEAR_SCREEN":
            self.cli_output.config(state=tk.NORMAL)
            self.cli_output.delete(1.0, tk.END)
            self.cli_output.config(state=tk.DISABLED)
        else:
            self._add_cli_output(result + "\n")
        
        # Update prompt in case directory changed
        self.prompt_label.config(text=self.cli_playground.get_prompt())

        self.cli_input.delete(0, tk.END)

    def _start_quick_fire_gui(self):
        """Start Quick Fire mode in GUI."""
        if self.quiz_active:
            messagebox.showwarning("Quiz Active", "Please finish the current quiz before starting Quick Fire mode.", parent=self.root)
            return
        
        if messagebox.askyesno("Quick Fire Mode", 
                              f"Ready for Quick Fire?\n\nAnswer {QUICK_FIRE_QUESTIONS} questions in {QUICK_FIRE_TIME_LIMIT//60} minutes!\n\nAre you ready?", 
                              parent=self.root):
            self.current_quiz_mode = "quick_fire"
            self.current_category_filter = None
            self.total_questions_in_filter_gui = QUICK_FIRE_QUESTIONS
            self._start_quick_fire_session()

    def _start_quick_fire_session(self):
        """Begin Quick Fire session with timer."""
        self.game_logic.start_quick_fire_mode()
        self.quiz_active = True
        self.game_logic.score = 0
        self.game_logic.total_questions_session = 0
        self.questions_answered_in_session_gui = 0
        self.game_logic.answered_indices_session = []
        self.current_streak = 0
        self.game_logic.session_points = 0
        
        self._update_status("Quick Fire mode active!")
        self._update_question_count_label(current=0, total=QUICK_FIRE_QUESTIONS)
        self._update_points_display()
        
        # Show timer
        self.quick_fire_timer_label.pack(side=tk.RIGHT, padx=(10, 0))
        self._update_quick_fire_timer()
        
        self._next_question_gui()

    def _update_quick_fire_timer(self):
        """Update the Quick Fire timer display."""
        if not self.game_logic.quick_fire_active:
            self.quick_fire_timer_label.pack_forget()
            return
        
        elapsed = time.time() - self.game_logic.quick_fire_start_time
        remaining = max(0, QUICK_FIRE_TIME_LIMIT - elapsed)
        
        if remaining <= 0:
            self.quick_fire_timer_label.config(text="⏰ TIME'S UP!")
            self.quick_fire_timer_label.pack_forget()
            self._end_quick_fire_gui(time_up=True)
            return
        
        mins, secs = divmod(int(remaining), 60)
        color = "red" if remaining < 30 else "orange" if remaining < 60 else "green"
        self.quick_fire_timer_label.config(text=f"⏱️ {mins:02d}:{secs:02d}")
        
        # Schedule next update
        self.root.after(1000, self._update_quick_fire_timer)

    def _end_quick_fire_gui(self, time_up=False):
        """End Quick Fire mode and show results."""
        self.game_logic.quick_fire_active = False
        self.quiz_active = False
        self.quick_fire_timer_label.pack_forget()
        
        # Show results
        questions_answered = self.game_logic.quick_fire_questions_answered
        elapsed_time = time.time() - self.game_logic.quick_fire_start_time
        
        if time_up:
            title = "⏰ Quick Fire - Time's Up!"
            message = f"Time ran out!\n\nQuestions answered: {questions_answered}/{QUICK_FIRE_QUESTIONS}\nTime taken: {elapsed_time:.1f} seconds"
        else:
            title = "🎉 Quick Fire Complete!"
            message = f"Congratulations!\n\nQuestions answered: {questions_answered}/{QUICK_FIRE_QUESTIONS}\nTime taken: {elapsed_time:.1f} seconds"
            
            # Award achievement
            if "quick_fire_champion" not in self.game_logic.achievements["badges"]:
                self.game_logic.achievements["badges"].append("quick_fire_champion")
                message += f"\n\n🏆 Achievement Unlocked!\n{self.game_logic.get_achievement_description('quick_fire_champion')}"
        
        messagebox.showinfo(title, message, parent=self.root)
        self._load_initial_state()

    def _start_daily_challenge_gui(self):
        """Start daily challenge in GUI."""
        if self.quiz_active:
            messagebox.showwarning("Quiz Active", "Please finish the current quiz before starting the daily challenge.", parent=self.root)
            return
        
        today_iso = datetime.now().date().isoformat()
        if self.game_logic.last_daily_challenge_date == today_iso and self.game_logic.daily_challenge_completed:
            messagebox.showinfo("Daily Challenge", "You've already completed today's daily challenge!\nCome back tomorrow for a new challenge.", parent=self.root)
            return
            
        question_data, original_index = self.game_logic.get_daily_challenge_question()
        
        if question_data is None:
            messagebox.showinfo("Daily Challenge", "Today's daily challenge is currently unavailable or already completed.\nCome back tomorrow!", parent=self.root)
            return
        
        # Start single question mode
        self.current_quiz_mode = "daily_challenge"
        self.current_question_data = question_data
        self.current_question_index = original_index
        self.quiz_active = True
        
        # Reset counters for this single question session
        self.game_logic.score = 0 
        self.game_logic.total_questions_session = 0 
        self.questions_answered_in_session_gui = 0 
        self.game_logic.session_points = 0
        self.current_streak = 0
        
        self._update_status("Daily Challenge active!")
        self._update_question_count_label(current=1, total=1)
        self._update_points_display()
        self._update_streak_label(self.current_streak)

        self.category_label.config(text="🗓️ Daily Challenge - Special Question of the Day!")
        self._display_question_gui()

    def _start_mini_quiz_gui(self):
        """Start mini quiz in GUI."""
        if self.quiz_active:
            messagebox.showwarning("Quiz Active", "Please finish the current quiz before starting a mini quiz.", parent=self.root)
            return
        
        self.current_quiz_mode = "mini_quiz"
        self.current_category_filter = None
        self.total_questions_in_filter_gui = min(MINI_QUIZ_QUESTIONS, len(self.game_logic.questions))
        
        if self.total_questions_in_filter_gui == 0:
            messagebox.showwarning("No Questions", "No questions available for mini quiz.", parent=self.root)
            return
        
        self._start_quiz_session()

    def _start_pop_quiz_gui(self):
        """Start a single random question pop quiz."""
        if self.quiz_active:
            messagebox.showwarning("Quiz Active", "Please finish the current quiz before starting a pop quiz.", parent=self.root)
            return
        
        question_data, original_index = self.game_logic.select_question(None)
        if not question_data:
            messagebox.showwarning("No Questions", "No questions available for pop quiz.", parent=self.root)
            return
        
        # Start single question mode
        self.current_quiz_mode = "pop_quiz"
        self.current_question_data = question_data
        self.current_question_index = original_index
        self.quiz_active = True
        
        # Reset counters for this single question session
        self.game_logic.score = 0
        self.game_logic.total_questions_session = 0
        self.questions_answered_in_session_gui = 0
        self.game_logic.session_points = 0
        self.current_streak = 0
        
        self._update_status("Pop Quiz!")
        self._update_question_count_label(current=1, total=1)
        self._update_points_display()
        self._update_streak_label(self.current_streak)

        self.category_label.config(text="📊 Random Pop Quiz")
        self._display_question_gui()

    def _show_achievements_gui(self):
        """Display achievements and leaderboard in a GUI window."""
        if self.achievements_window and self.achievements_window.winfo_exists():
            self.achievements_window.lift()
            return
        
        self.achievements_window = tk.Toplevel(self.root)
        self.achievements_window.title("🏆 Achievements & Leaderboard")
        self.achievements_window.geometry("900x900")
        self.achievements_window.transient(self.root)
        self.achievements_window.configure(bg=self.colors["bg"])
        self.achievements_window.minsize(600, 500)

        # Create notebook for tabs
        notebook = ttk.Notebook(self.achievements_window)
        notebook.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)

        # Achievements Tab
        achievements_frame = ttk.Frame(notebook, padding="15")
        notebook.add(achievements_frame, text="🏆 Achievements")
        
        # Progress section
        progress_label_frame = ttk.LabelFrame(achievements_frame, text="Current Progress", padding="10")
        progress_label_frame.pack(fill="x", pady=(0, 15))
        
        total_points = self.game_logic.achievements.get("points_earned", 0)
        questions_answered = self.game_logic.achievements.get("questions_answered", 0)
        days_studied = len(self.game_logic.achievements.get("days_studied", []))
        
        ttk.Label(progress_label_frame, text=f"💰 Total Points: {total_points}", font=self.fonts.get("bold")).pack(anchor="w", pady=2)
        ttk.Label(progress_label_frame, text=f"📝 Questions Answered: {questions_answered}", font=self.fonts.get("base")).pack(anchor="w", pady=2)
        ttk.Label(progress_label_frame, text=f"📅 Days Studied: {days_studied}", font=self.fonts.get("base")).pack(anchor="w", pady=2)
        
        # Progress bars for goals
        if questions_answered < 100:
            progress_frame = ttk.Frame(progress_label_frame)
            progress_frame.pack(fill="x", pady=5)
            ttk.Label(progress_frame, text="Progress to Century Club (100 questions):").pack(anchor="w")
            progress_bar = ttk.Progressbar(progress_frame, length=300, mode='determinate')
            progress_bar.pack(fill="x", pady=2)
            progress_bar['value'] = (questions_answered / 100) * 100
            ttk.Label(progress_frame, text=f"{questions_answered}/100 ({(questions_answered/100)*100:.1f}%)").pack(anchor="w")
        
        # Unlocked achievements
        unlocked_frame = ttk.LabelFrame(achievements_frame, text="🎉 Unlocked Achievements", padding="10")
        unlocked_frame.pack(fill="both", expand=True, pady=(0, 15))
        
        unlocked_scroll = scrolledtext.ScrolledText(unlocked_frame, height=8, wrap=tk.WORD,
                                                   bg=self.colors["explanation_bg"], fg=self.colors["fg"],
                                                   font=self.fonts.get("base"))
        unlocked_scroll.pack(fill="both", expand=True)
        
        if self.game_logic.achievements["badges"]:
            for badge in self.game_logic.achievements["badges"]:
                unlocked_scroll.insert(tk.END, f"{self.game_logic.get_achievement_description(badge)}\n\n")
        else:
            unlocked_scroll.insert(tk.END, "No achievements unlocked yet.\nKeep studying to earn your first badge! 🌟")
        
        unlocked_scroll.config(state=tk.DISABLED)
        
        # Available achievements
        available_frame = ttk.LabelFrame(achievements_frame, text="🎯 Available Achievements", padding="10")
        available_frame.pack(fill="both", expand=True)
        
        available_scroll = scrolledtext.ScrolledText(available_frame, height=6, wrap=tk.WORD,
                                                    bg=self.colors["explanation_bg"], fg=self.colors["fg"],
                                                    font=self.fonts.get("base"))
        available_scroll.pack(fill="both", expand=True)
        
        all_achievements = {
            "streak_master": "🔥 Answer 5 questions correctly in a row",
            "dedicated_learner": "📚 Study for 3 different days",
            "century_club": "💯 Answer 100 questions total",
            "point_collector": "⭐ Earn 500 points",
            "quick_fire_champion": "⚡ Complete Quick Fire mode",
            "daily_warrior": "🗓️ Complete a daily challenge",
            "perfect_session": "🎯 Get 100% accuracy in a session (3+ questions)"
        }
        
        for badge, description in all_achievements.items():
            if badge not in self.game_logic.achievements["badges"]:
                available_scroll.insert(tk.END, f"🔒 {description}\n")
        
        available_scroll.config(state=tk.DISABLED)
        
        # Leaderboard Tab
        leaderboard_frame = ttk.Frame(notebook, padding="15")
        notebook.add(leaderboard_frame, text="📊 Leaderboard")
        
        ttk.Label(leaderboard_frame, text="🏆 Personal Best Sessions", style="Header.TLabel").pack(pady=(0, 15))
        
        if self.game_logic.leaderboard:
            # Create treeview for leaderboard
            columns = ("Rank", "Date", "Score", "Accuracy", "Points")
            tree = ttk.Treeview(leaderboard_frame, columns=columns, show="headings", height=12)
            
            for col in columns:
                tree.heading(col, text=col)
                tree.column(col, width=120, anchor="center")
            
            # Add scrollbar
            scrollbar = ttk.Scrollbar(leaderboard_frame, orient="vertical", command=tree.yview)
            tree.configure(yscrollcommand=scrollbar.set)
            
            # Pack treeview and scrollbar
            tree_frame = ttk.Frame(leaderboard_frame)
            tree_frame.pack(fill="both", expand=True)
            tree.pack(side="left", fill="both", expand=True)
            scrollbar.pack(side="right", fill="y")
            
            # Populate leaderboard
            for i, entry in enumerate(self.game_logic.leaderboard, 1):
                date_str = entry["date"][:10]
                score_str = f"{entry['score']}/{entry['total']}"
                accuracy_str = f"{entry['accuracy']:.1f}%"
                points_str = str(entry['points'])
                
                tree.insert("", "end", values=(i, date_str, score_str, accuracy_str, points_str))
        else:
            ttk.Label(leaderboard_frame, text="No sessions recorded yet.\nStart studying to see your progress!", 
                     style="Status.TLabel").pack(expand=True)
        
        # Close button
        ttk.Button(self.achievements_window, text="Close", command=self.achievements_window.destroy, 
                  style="TButton").pack(pady=15)