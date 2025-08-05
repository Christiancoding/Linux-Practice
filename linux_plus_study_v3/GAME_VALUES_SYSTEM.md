# Game Values Configuration System

## Overview

The Game Values Configuration System centralizes all hardcoded numbers, display values, and game mechanics that were previously scattered throughout the codebase. This system provides:

- **Centralized Configuration**: All game values in one place
- **Settings Interface**: Web UI for easy configuration
- **Real-time Updates**: Changes apply immediately
- **Type Safety**: Structured configuration with validation
- **Backward Compatibility**: Works with existing code

## Architecture

### Core Components

1. **`utils/game_values.py`** - Main configuration system
2. **Settings UI Tab** - Web interface for configuration
3. **API Endpoints** - Backend for saving/loading values
4. **Integration Points** - Updated controllers and models

### Configuration Categories

#### Scoring Settings
- `points_per_correct` (default: 10)
- `points_per_incorrect` (default: 0)  
- `hint_penalty` (default: 5)
- `speed_bonus` (default: 5)
- `streak_bonus` (default: 5)
- `max_streak_bonus` (default: 50)
- `streak_bonus_threshold` (default: 3)
- `streak_bonus_multiplier` (default: 2.0)
- `perfect_quiz_bonus` (default: 25)
- `daily_challenge_bonus` (default: 50)
- `achievement_point_threshold` (default: 500)
- `achievement_question_threshold` (default: 100)

#### Streak Settings
- `daily_streak_threshold` (default: 3)
- `weekly_streak_threshold` (default: 7)
- `streak_display_threshold` (default: 3)
- `default_streak_value` (default: 0)

#### Quiz Settings
- `default_question_count` (default: 10)
- `max_question_count` (default: 50)
- `min_question_count` (default: 1)
- `quick_fire_count` (default: 5)
- `time_per_question` (default: 30)
- `strike_limit` (default: 3)

#### Accuracy Settings
- `excellent_threshold` (default: 90)
- `good_threshold` (default: 75)
- `average_threshold` (default: 50)
- `passing_percentage` (default: 70)

#### Display Settings
- Various default display values and fallbacks

#### Time Settings
- File cleanup, calendar, and session timeout values

## Usage Examples

### Accessing Values in Python

```python
from utils.game_values import get_game_value, get_game_value_manager

# Get individual values
points = get_game_value('scoring', 'points_per_correct', 10)
streak_threshold = get_game_value('streaks', 'daily_streak_threshold', 3)

# Get the manager for advanced operations
manager = get_game_value_manager()
all_config = manager.get_all_config()
```

### Updating Values

```python
from utils.game_values import get_game_value_manager

manager = get_game_value_manager()

# Update specific category
success = manager.update_settings(
    scoring={
        'points_per_correct': 15,
        'hint_penalty': 3
    },
    streaks={
        'daily_streak_threshold': 5
    }
)
```

### Using in Templates

```html
<!-- Template variables are automatically injected -->
<span>Hint penalty: {{ game_values.scoring.hint_penalty }}</span>
<button onclick="useHint()">
    Use Hint (-<span id="hint-penalty">{{ game_values.scoring.hint_penalty }}</span> points)
</button>
```

### JavaScript Integration

```javascript
// Values are passed to templates and accessible in JavaScript
const hintPenalty = parseInt(document.getElementById('hint-penalty')?.textContent) || 5;

// Or fetch current values via API
fetch('/api/load_game_values')
    .then(response => response.json())
    .then(data => {
        const values = data.values;
        console.log('Points per correct:', values.scoring.points_per_correct);
    });
```

## Web Interface

### Game Values Settings Tab

The new "Game Values" tab in Settings provides:

1. **Scoring Configuration**
   - Points per correct/incorrect answer
   - Hint penalty and speed bonus
   - Streak bonus settings

2. **Streak Configuration**
   - Bonus thresholds
   - Daily/weekly streak requirements
   - Multiplier settings

3. **Achievement Configuration**
   - Point and question thresholds
   - Bonus values for achievements

4. **Display Settings**
   - Accuracy thresholds for color coding
   - Passing percentages

### API Endpoints

- `GET /api/load_game_values` - Load current configuration
- `POST /api/save_game_values` - Save new configuration
- `POST /api/reset_game_values` - Reset to defaults

## Migration Summary

### Before (Hardcoded)
```python
# Scattered throughout codebase
POINTS_PER_CORRECT = 10
HINT_PENALTY = 5
STREAK_THRESHOLD = 3

# In templates
<button>Use Hint (-5 points)</button>

# In JavaScript  
quizState.score -= 5;
```

### After (Centralized)
```python
# Centralized configuration
from utils.game_values import get_game_value

points = get_game_value('scoring', 'points_per_correct', 10)
penalty = get_game_value('scoring', 'hint_penalty', 5)

# Dynamic templates
<button>Use Hint (-{{ game_values.scoring.hint_penalty }} points)</button>

# Dynamic JavaScript
const penalty = parseInt(document.getElementById('hint-penalty')?.textContent) || 5;
quizState.score -= penalty;
```

## Updated Files

### Core System
- `utils/game_values.py` - Main configuration system
- `templates/settings.html` - Added Game Values tab
- `views/web_view.py` - Added API endpoints and template injection

### Controllers & Models  
- `controllers/quiz_controller.py` - Uses dynamic scoring values
- `models/achievements.py` - Dynamic achievement thresholds

### Templates
- `templates/quiz.html` - Dynamic hint penalty display

## Benefits

1. **Maintainability**: All values in one place
2. **Flexibility**: Easy to adjust game balance
3. **User Control**: Settings UI for customization  
4. **Consistency**: Single source of truth
5. **Testing**: Easy to test different configurations
6. **Debugging**: Clear configuration state

## Future Enhancements

1. **Import/Export**: Configuration backup/restore
2. **Presets**: Pre-defined difficulty settings
3. **A/B Testing**: Different configurations for testing
4. **Analytics**: Track how settings affect engagement
5. **Advanced Validation**: More complex validation rules

## Notes

- Configuration is stored in `data/game_values.json`
- System provides sensible defaults if file is missing
- All changes are validated before saving
- Controllers automatically refresh values when settings change
- Templates receive current values on each render
