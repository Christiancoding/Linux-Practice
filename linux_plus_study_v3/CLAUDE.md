# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Application Overview

This is the Linux Plus Study System v3, a comprehensive CompTIA Linux+ certification study platform that combines web-based learning, CLI practice, and VM management capabilities. The application supports three main modes:

1. **Web Interface** - Flask-based web application with quiz system, analytics dashboard, and interactive learning
2. **VM Management** - Virtual machine lifecycle management for hands-on Linux practice
3. **CLI Playground** - Interactive command-line practice environment

## Development Commands

### Running the Application
```bash
# Start web interface (primary mode)
python3 main.py --web

# Start with custom host/port
python3 main.py --web --host 0.0.0.0 --port 8080

# Start VM management mode
python3 main.py --vm

# Start CLI playground
python3 main.py --cli

# Interactive menu (no args)
python3 main.py
```

### Testing
```bash
# Run all tests
python3 -m pytest

# Run specific test files
python3 -m pytest tests/

# Run with verbose output
python3 -m pytest -v
```

### Code Quality
```bash
# Format code with black
python3 -m black .

# Lint with flake8
python3 -m flake8 .
```

### To run `data/convert-db-to-csv.sh`:
```bash
./data/convert-db-to-csv.sh /path/to/Filename.db
```

### Database Operations
```bash
# Initialize database
python3 init_database.py

# Run database migrations
python3 -m alembic upgrade head

# Run database migration service
PYTHONPATH=/home/retiredfan/Documents/github/linux_plus_study_v3_main/linux_plus_study_v3 python3 services/db_migration_service.py
```

## Architecture

### Core Components

- **main.py** - Unified application entry point with mode selection and Flask app setup
- **controllers/** - Business logic controllers (quiz, stats, learning)
- **models/** - Data models (game_state, analytics, achievements, questions)
- **views/** - Web interface layer (web_view.py contains Flask routes)
- **services/** - Service layer (analytics, quiz logic, error tracking)
- **utils/** - Utilities (database, config, persistence, validators)
- **cli_sandbox/** - CLI-specific logic and sandbox environment
- **tests/** - Unit and integration tests
- **data/** - Database files

### Data Layer

The application uses a hybrid storage approach:
- **SQLite database** (`data/linux_plus_study.db`) - Primary data storage with SQLAlchemy ORM
- **JSON files** - Configuration and backup data (achievements, history, settings)
- **Database pooling** - Managed through `utils/database.py` for web mode performance

### Key Design Patterns

- **MVC Architecture** - Controllers handle business logic, models manage data, views handle presentation
- **Service Layer** - Business logic abstracted into services for reusability
- **Analytics Integration** - Comprehensive user analytics with error tracking middleware
- **Multi-mode Support** - Single codebase supporting web, CLI, and VM modes

### Configuration Management

- `utils/config.py` - Application constants and configuration
- `web_settings.json` - Web interface settings
- `utils/game_values.py` - Game mechanics configuration
- `requirements.txt` - Python dependencies

### Templates and Static Files

- `templates/` - Jinja2 templates for web interface
- `static/` - CSS, JavaScript, and other web assets
- `static/js/app.js` - Main frontend JavaScript with analytics tracking
- `static/css/style.css` - Main CSS styles for web interface
- `static/img/` - Image assets for web interface
- `static/fonts/` - Font assets for web interface
- `static/videos/` - Video assets for web interface
- `static/docs/` - Documentation files for web interface
- `static/favicon.ico` - Favicon for web interface

## Working with the Codebase
### Analytics Tracking Features
- User interaction tracking (clicks, navigation)
- Error tracking (JavaScript errors, API errors)
- Performance monitoring (load times, resource usage)
- Event logging (signups, completions)
- Usage statistics (time spent, feature usage)

#### Detailed Analytics Data Collection
- **User Identification**: IDs → cookies, localStorage, or a login-based user ID to recognize you later
- **Browser & OS**: Chrome/Firefox, Windows/macOS/Linux/Android/iOS
- **Device Information**: Device type (phone/tablet/desktop), screen size, pixel ratio
- **Localization**: Language & timezone (e.g., en-US, America/Chicago)
- **Hardware Hints**: CPU threads, memory estimate, touch support—useful for performance tuning
- **Page Analytics**: Page views (which pages, in what order)
- **Session Metrics**: Time on page / session length (using timers)
- **User Behavior**: Scroll depth (did you reach 25%/50%/100%?)
- **Interaction Tracking**: Clicks (buttons, menus, outbound links)
- **Form Analytics**: Form activity (started/abandoned/submitted; not the exact text unless the site deliberately logs it)
- **Media Interactions**: Video interactions (play/pause, watch time)
- **Performance Metrics**: Load time (TTFB, First Contentful Paint, etc.)
- **Error Monitoring**: Errors (JavaScript errors, failed network requests)
- **Browser Capabilities**: Feature support (does your browser support WebGL, etc.)
- **A/B Testing**: A/B tests (which variant you saw and how you behaved)
- **User Journey**: Heatmaps / session replays (mouse movement/scroll paths, page snapshots)
- **Custom Events**: Any custom events specific to the application (e.g., quiz started, VM launched)
- **Error Events**: Any error events specific to the application (e.g., API errors, validation errors)
- **Performance Events**: Any performance-related events (e.g., long tasks, resource loading issues)
- **Local IP Address**: The local IP address of the user (useful for network-related analytics)

### Adding New Features

1. Create controller in `controllers/` for business logic
2. Add corresponding service in `services/` if needed
3. Update models in `models/` for data persistence
4. Add web routes in `views/web_view.py`
5. Create templates in `templates/` for UI
6. Add analytics tracking where appropriate
7. Add all analytics tracking data not stated to `data/linux_plus_study.db`
8. Add questions to `data/linux_plus_study_questions.db`
9. Add achievements to `data/linux_plus_study_achivements.db`
10. Add question history to `data/linux_plus_study_history.db`
11. Add settings to `data/linux_plus_study_settings.db`


### Database Changes

1. Modify models in `models/`
2. Create migration in `migrations/`
3. Update related services and controllers
4. Modify cli sandbox in `cli_sandbox/`

### Testing Strategy

- Unit all tests in `tests/`
- If possible, always open the website in a browser
- Integration tests for web endpoints
- Fully remove tests when complete
- Analytics verification scripts (`verify_*.py`)
- Database migration tests
- Performance tests
- Load testing scripts
- Accessibility testing scripts
- Usability testing scripts
- Duplication detection scripts
- Manual testing scripts for debugging

### Error Handling

The application includes comprehensive error handling:
- Centralized logging to `logs/` directory
- Error tracking middleware in `services/error_tracking_middleware.py`
- Analytics error integration
- Graceful degradation for missing dependencies (VM features, etc.)
- User-friendly error pages in web mode
- Custom error messages for different error types
- Detailed error logs for debugging
- Validation error handling
- Python exception handling

## Key Dependencies

- **Flask 2.3.3** - Web framework
- **SQLAlchemy 2.0.20** - Database ORM with Alembic migrations
- **pywebview 4.4.1** - Desktop application wrapper
- **libvirt-python 9.7.0** - VM management (optional)
- **paramiko 3.3.1** - SSH functionality for VM integration
- **rich 13.5.2** - Enhanced CLI output
- **pytest 7.4.2** - Testing framework
- **black 23.7.0** - Code formatting
- **flake8 6.0.0** - Code linting

## Development Notes

- The application automatically handles port conflicts by incrementing the port number
- VM functionality gracefully degrades if libvirt is not available
- Analytics system tracks user interactions across all modes
- The codebase includes extensive type hints for better IDE support
- Database connections use pooling in web mode for performance
- If you can not read a .db file, you can use this `data/convert-db-to-csv.sh` script to read .csv

## Grouped code by responsibilities

- Questions (load/filter)
- Quiz (generate/grade)
- Eplain (hint/links)
- Progress (store/total)
- Interface (CLI/Web)
- Storage (repo/db/JSON) 
- VM Challenges (load/hint)
- Challenge interface (CLI/VM)
- Validator (check/grade)
- Analytics (track/aggregate)
- Error Handling (log/notify)
- User Management (create/switch)

## Coding Standards
## Yes! Yes! List
- Use descriptive commit messages
- Write unit tests for new features
- Follow the DRY principle

## No! No! List

- Do not create any duplacates in the code
- Do not keep any test files when not in use
- Do not keep any csv files when not in use
- No not use python. Use python3.
- Do not create any hardcoded numbers in html code
- Do not hardcode values in JavaScript
- Do not only test the code with `python3 main.py --web --host 0.0.0.0 --port 8080` or similar
- Do not use print statements for debugging