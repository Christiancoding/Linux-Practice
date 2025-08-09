# Unified Time Tracking and Scoring System

## Overview

This document describes the unified time tracking and scoring system implemented to resolve inconsistencies between quiz completion displays and the home page dashboard.

## Key Changes

### 1. Separate Time Tracking
- **Quiz Time**: Daily time spent on quizzes, resets at 12:59 AM each day
- **Study Time**: Total lifetime study time (to be extended for non-quiz activities)

### 2. Unified Scoring System
- All scoring now uses the game values from `utils/game_values.py`
- Session points from `controllers/quiz_controller.py` match home page XP display
- Consistent point calculations across all interfaces

### 3. New Components

#### Time Tracking Service (`services/time_tracking_service.py`)
- Handles daily quiz time reset at 12:59 AM
- Maintains historical data for quiz time
- Provides formatted time strings
- Persistent JSON-based storage in `data/time_tracking.json`

#### Updated APIs
- `/api/dashboard` - Now includes `quiz_time_today` and `quiz_time_formatted`
- `/api/time-tracking` - Dedicated endpoint for time tracking statistics

#### Updated UI
- Home page now shows two separate time cards:
  - "Quiz Time Today" (resets daily)
  - "Total Study Time" (lifetime cumulative)
- Quiz completion page shows session-specific data
- Consistent scoring display between quiz results and home page

## Integration Points

### Quiz Controller
- Tracks session duration and adds to daily quiz time
- Uses unified game values for point calculations

### Web View
- Updated dashboard API to include time tracking data
- Maintains backward compatibility

### Frontend
- Updated JavaScript to handle new time fields
- Improved trend indicators with reset information

## Usage

### For Developers
```python
from services.time_tracking_service import get_time_tracker

tracker = get_time_tracker()
tracker.add_quiz_time(45)  # Add 45 seconds of quiz time
summary = tracker.get_daily_summary()
print(f"Quiz time today: {summary['quiz_time_formatted']}")
```

### For Users
- Quiz time shows cumulative time spent on quizzes today
- Resets at 12:59 AM each day with notification
- Study time shows total learning time across all activities
- Consistent point values across the application

## Data Files

- `data/time_tracking.json` - Time tracking data and settings
- `data/game_values.json` - Unified scoring configuration

## Migration

The system automatically handles migration:
- Existing analytics data is preserved
- Time tracking starts fresh with the new system
- Game values use sensible defaults if not configured

This implementation ensures that quiz completion pages and the dashboard always show consistent, accurate data.