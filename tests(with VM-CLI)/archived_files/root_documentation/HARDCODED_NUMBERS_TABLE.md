# Hardcoded Numbers and Display Values Reference Table

## Overview
This document catalogs all hardcoded numbers, default values, and display text patterns found in the Linux+ Study Game codebase that create patterns like "Study Streak 0 days" or "0 XP".

---

## 🎯 **SCORING & POINTS**

| **Display Pattern** | **Location** | **File** | **Line** | **Purpose** |
|---------------------|--------------|----------|----------|-------------|
| `0 XP` | Default XP display | `templates/achievements.html` | 94, 108, 122, 137, 156, 170, 190 | Achievement XP rewards |
| `Level 0 • 0 XP` | Player stats display | `templates/achievements.html` | 218, 226, 234, 242, 250 | Leaderboard player stats |
| `+0 XP` | CLI playground rewards | `templates/cli_playground.html` | 186, 197, 208, 219 | Command completion rewards |
| `Total XP: 0` | Hero section | `templates/index.html` | 22 | Main dashboard XP display |
| `data.xp \|\| 0` | JavaScript fallback | `templates/index.html` | 619, 634, 654, 666, 707 | XP value fallbacks |
| `0 points` | Question points | `templates/quiz.html` | 171 | Points per question display |
| `points_earned \|\| 10` | Default points | `templates/quiz.html` | 1433 | Fallback points per question |
| `-5 points` | Hint penalty | `templates/quiz.html` | 213, 1631, 1632 | Hint usage penalty |
| `+5 points` | Speed bonus | `controllers/quiz_controller.py` | 432 | Fast answer bonus |
| `500 points` | Achievement threshold | `models/achievements.py` | 271, 290 | Point Collector achievement |

---

## 🔥 **STREAKS & DAYS**

| **Display Pattern** | **Location** | **File** | **Line** | **Purpose** |
|---------------------|--------------|----------|----------|-------------|
| `Study Streak 0 days` | Hero display | `templates/index.html` | 26-28 | Main streak display |
| `Day Streak: 0` | Stats card | `templates/index.html` | 152 | Dashboard streak card |
| `Day Streak: 0` | Stats page | `templates/stats.html` | 87 | Statistics page streak |
| `Current Streak: 0` | CLI display | `views/cli_view.py` | 708 | Command line streak display |
| `streak: 0` | JavaScript state | `templates/quiz.html` | 938, 1108, 1441 | Quiz state management |
| `data.streak \|\| 0` | JavaScript fallback | `templates/index.html` | 620, 625, 635, 655, 660 | Streak value fallbacks |
| `Streak: 0` | Quiz display | `templates/quiz.html` | 227 | Active quiz streak |
| `3 days in a row` | Achievement text | `models/achievements.py` | 269, 287 | Dedicated Learner requirement |
| `7-day study streak` | Achievement requirement | `templates/achievements.html` | 120 | Weekly streak achievement |
| `Last 7 Days` | Time period button | `templates/stats.html` | 19 | Stats time filter |
| `Last 30 Days` | Time period button | `templates/stats.html` | 20 | Stats time filter |

---

## ❓ **QUESTIONS & ATTEMPTS**

| **Display Pattern** | **Location** | **File** | **Line** | **Purpose** |
|---------------------|--------------|----------|----------|-------------|
| `0 questions` | Stats display | `templates/stats.html` | 142, 160 | Category question counts |
| `0 questions` | Tooltip text | `templates/stats.html` | 872 | Activity calendar tooltips |
| `0 questions` | Index tooltip | `templates/index.html` | 698 | Calendar activity tooltips |
| `currentQuestion: 0` | Quiz state | `templates/quiz.html` | 931, 1104 | Current question index |
| `questions_answered: 0` | Achievement data | `models/achievements.py` | 499 | Default achievement state |
| `questions_attempted: 0` | Database default | `models/analytics.py` | 44 | Analytics table default |
| `questions_correct: 0` | Database default | `models/analytics.py` | 45 | Analytics table default |
| `questions_incorrect: 0` | Database default | `models/analytics.py` | 46 | Analytics table default |
| `Total Questions: 0` | Analytics display | `examples/quiz_with_analytics.html` | 37 | Analytics dashboard |
| `100 questions` | Achievement threshold | `models/achievements.py` | 274, 291 | Century Club achievement |

---

## 📊 **SCORES & ACCURACY**

| **Display Pattern** | **Location** | **File** | **Line** | **Purpose** |
|---------------------|--------------|----------|----------|-------------|
| `Score: 0` | Quiz state | `templates/quiz.html` | 937 | Initial quiz score |
| `0%` | Accuracy display | `templates/stats.html` | 186, 195, 204, 222, 234 | Category accuracy percentages |
| `0%` | Achievement progress | `templates/achievements.html` | 220, 228, 236, 244, 252 | Player score percentages |
| `session_score: 0` | Controller state | `controllers/quiz_controller.py` | 51, 84, 127, 276, 311, 553 | Session score tracking |
| `score: 0` | Game state | `models/game_state.py` | 67, 290 | Initial game score |
| `accuracy: 0` | Default calculation | Various files | Multiple | Accuracy percentage fallbacks |
| `0/10` | Score display | `examples/quiz_with_analytics.html` | 15 | Score format example |

---

## 🎮 **GAME MECHANICS**

| **Display Pattern** | **Location** | **File** | **Line** | **Purpose** |
|---------------------|--------------|----------|----------|-------------|
| `5 questions` | Quick Fire mode | `utils/config.py` | 41 | Quick Fire question count |
| `30 seconds` | Timed challenge | `utils/config.py` | 49 | Time per question |
| `3 strikes` | Survival mode | `templates/quiz.html` | 55 | Strike limit |
| `streak >= 3` | Streak threshold | `templates/quiz.html` | 1437 | Streak display threshold |
| `Level 0` | Default level | `templates/achievements.html` | 218, 226, 234, 242, 250 | Player level display |
| `data-level="0"` | Activity level | `templates/stats.html` | 264, 866 | Calendar activity levels |
| `data-level="0"` | Activity level | `templates/index.html` | 226, 692 | Calendar activity levels |

---

## ⚙️ **CONFIGURATION VALUES**

| **Display Pattern** | **Location** | **File** | **Line** | **Purpose** |
|---------------------|--------------|----------|----------|-------------|
| `DEFAULT_CHALLENGE_SCORE: 100` | VM challenges | `utils/config.py` | 430 | Default challenge points |
| `streak_bonus: 5` | Game mechanics | `models/game_state.py` | 86, 685 | Streak bonus points |
| `max_streak_bonus: 50` | Game mechanics | `models/game_state.py` | 87, 685 | Maximum streak bonus |
| `points_per_question: 10` | Scoring system | `models/game_state.py` | 685 | Default points per question |
| `STREAK_BONUS_THRESHOLD: 3` | Configuration | `utils/config.py` | 238 | Minimum streak for bonus |
| `STREAK_BONUS_MULTIPLIER: 2` | Configuration | `utils/config.py` | 239 | Streak multiplier value |
| `score: 50` | VM challenge | `vm_integration/challenges/set_hostname.yaml` | 6 | Individual challenge score |
| `cost: 5` | Hint cost | `vm_integration/challenges/set_hostname.yaml` | 26 | Hint penalty cost |
| `cost: 10` | Hint cost | `vm_integration/challenges/set_hostname.yaml` | 28 | Higher hint penalty |

---

## 🗓️ **TIME & DATE PATTERNS**

| **Display Pattern** | **Location** | **File** | **Line** | **Purpose** |
|---------------------|--------------|----------|----------|-------------|
| `30 days` | File cleanup | `views/web_view.py` | 3344, 3349 | File age threshold |
| `7 days worth` | Stats calculation | `templates/stats.html` | 723 | Weekly data slice |
| `365 days` | Calendar generation | `templates/stats.html` | 860 | Full year calendar |
| `35 days` | Calendar generation | `templates/index.html` | 686 | Dashboard calendar |
| `study_streak_days: 0` | Database default | `models/analytics.py` | 59 | Default streak days |

---

## 💯 **PERCENTAGE & THRESHOLDS**

| **Display Pattern** | **Location** | **File** | **Line** | **Purpose** |
|---------------------|--------------|----------|----------|-------------|
| `100%` | Perfect accuracy | `templates/achievements.html` | 809 | Perfect Score achievement |
| `75%` | Good accuracy threshold | Multiple files | Various | Color coding threshold |
| `50%` | Average accuracy threshold | Multiple files | Various | Color coding threshold |
| `data-level="1,2,3,4"` | Activity levels | `templates/stats.html` | 573-576 | Calendar intensity levels |
| `0.2, 0.4, 0.6, 0.8` | Opacity levels | `templates/stats.html` | 573-576 | Activity level opacity |

---

## 🎯 **SPECIAL CASES**

| **Display Pattern** | **Location** | **File** | **Line** | **Purpose** |
|---------------------|--------------|----------|----------|-------------|
| `+100 bonus XP` | Easter egg | `templates/error.html` | 485 | Hidden bonus reward |
| `100 XP` | Legendary achievement | `templates/achievements.html` | 790 | High-value achievement |
| `8/20 achievements` | Progress display | `templates/achievements.html` | 274 | Achievement counter |
| `top 10 sessions` | Leaderboard limit | `models/achievements.py` | 358 | Session history limit |
| `up 2 days` | CLI simulation | `utils/cli_playground.py` | 995 | Uptime command output |

---

## 📝 **NOTES**

### **Common Patterns:**
- Most "0" values are JavaScript fallbacks using `|| 0` syntax
- Database columns use `default=0` for integer fields
- Template displays often show hardcoded "0" as placeholder text
- Achievement thresholds are hardcoded constants (3, 5, 100, 500)

### **Impact Areas:**
- **UI Display**: Templates show "0" as initial/fallback values
- **Game Logic**: Controllers use 0 for initialization and resets
- **Database**: Analytics tables default to 0 for numeric columns
- **Configuration**: Settings files contain hardcoded thresholds

### **Centralization Opportunities:**
Consider moving these values to a central configuration file for easier management and customization.
