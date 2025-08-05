# Analytics Integration Guide

This guide shows how to integrate the comprehensive analytics system into your existing Linux study application.

## 🚀 Quick Start

### 1. Database Migration

First, create and run a database migration for the new analytics table:

```python
# Create migration file: migrations/add_analytics_table.py
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import sqlite

def upgrade():
    op.create_table('analytics',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('user_id', sa.String(length=255), nullable=True),
        sa.Column('session_id', sa.String(length=255), nullable=False),
        sa.Column('session_start', sa.DateTime(), nullable=False),
        sa.Column('session_end', sa.DateTime(), nullable=True),
        sa.Column('session_duration', sa.Float(), nullable=True),
        sa.Column('activity_type', sa.String(length=100), nullable=False),
        sa.Column('activity_subtype', sa.String(length=100), nullable=True),
        sa.Column('topic_area', sa.String(length=255), nullable=True),
        sa.Column('difficulty_level', sa.String(length=50), nullable=True),
        sa.Column('questions_attempted', sa.Integer(), default=0),
        sa.Column('questions_correct', sa.Integer(), default=0),
        sa.Column('questions_incorrect', sa.Integer(), default=0),
        sa.Column('accuracy_percentage', sa.Float(), nullable=True),
        sa.Column('completion_percentage', sa.Float(), nullable=True),
        sa.Column('time_per_question', sa.Float(), nullable=True),
        sa.Column('content_pages_viewed', sa.Integer(), default=0),
        sa.Column('time_on_content', sa.Float(), default=0.0),
        sa.Column('practice_commands_executed', sa.Integer(), default=0),
        sa.Column('vm_sessions_started', sa.Integer(), default=0),
        sa.Column('cli_playground_usage', sa.Integer(), default=0),
        sa.Column('study_streak_days', sa.Integer(), default=0),
        sa.Column('return_sessions', sa.Integer(), default=0),
        sa.Column('help_requests', sa.Integer(), default=0),
        sa.Column('hint_usage', sa.Integer(), default=0),
        sa.Column('review_sessions', sa.Integer(), default=0),
        sa.Column('achievements_unlocked', sa.JSON(), nullable=True),
        sa.Column('skill_assessments', sa.JSON(), nullable=True),
        sa.Column('learning_goals_met', sa.Integer(), default=0),
        sa.Column('certification_progress', sa.Float(), default=0.0),
        sa.Column('page_load_time', sa.Float(), nullable=True),
        sa.Column('error_count', sa.Integer(), default=0),
        sa.Column('feature_usage', sa.JSON(), nullable=True),
        sa.Column('browser_info', sa.String(length=255), nullable=True),
        sa.Column('device_type', sa.String(length=50), nullable=True),
        sa.Column('vm_uptime', sa.Float(), default=0.0),
        sa.Column('vm_commands_executed', sa.Integer(), default=0),
        sa.Column('lab_exercises_completed', sa.Integer(), default=0),
        sa.Column('lab_exercises_attempted', sa.Integer(), default=0),
        sa.Column('vm_errors_encountered', sa.Integer(), default=0),
        sa.Column('concept_mastery_scores', sa.JSON(), nullable=True),
        sa.Column('retention_test_scores', sa.JSON(), nullable=True),
        sa.Column('practical_application_success', sa.Float(), nullable=True),
        sa.Column('active_learning_time', sa.Float(), default=0.0),
        sa.Column('interaction_frequency', sa.Float(), nullable=True),
        sa.Column('focus_score', sa.Float(), nullable=True),
        sa.Column('user_feedback_rating', sa.Float(), nullable=True),
        sa.Column('improvement_suggestions', sa.Text(), nullable=True),
        sa.Column('difficulty_rating', sa.Float(), nullable=True),
        sa.Column('preferred_learning_style', sa.String(length=100), nullable=True),
        sa.Column('most_effective_study_method', sa.String(length=100), nullable=True),
        sa.Column('least_effective_study_method', sa.String(length=100), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('tags', sa.JSON(), nullable=True),
        sa.Column('custom_metrics', sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_analytics_user_id'), 'analytics', ['user_id'], unique=False)
    op.create_index(op.f('ix_analytics_session_id'), 'analytics', ['session_id'], unique=False)
    op.create_index(op.f('ix_analytics_activity_type'), 'analytics', ['activity_type'], unique=False)
    op.create_index(op.f('ix_analytics_topic_area'), 'analytics', ['topic_area'], unique=False)

def downgrade():
    op.drop_index(op.f('ix_analytics_topic_area'), table_name='analytics')
    op.drop_index(op.f('ix_analytics_activity_type'), table_name='analytics')
    op.drop_index(op.f('ix_analytics_session_id'), table_name='analytics')
    op.drop_index(op.f('ix_analytics_user_id'), table_name='analytics')
    op.drop_table('analytics')
```

Run the migration:
```bash
alembic upgrade head
```

### 2. Update Your Main Flask App

```python
# main.py - Add analytics initialization
from flask import Flask
from services.analytics_integration import WebAnalyticsTracker

app = Flask(__name__)

# Initialize analytics tracking
analytics_tracker = WebAnalyticsTracker(app)

# Add context processor for analytics
@app.context_processor
def inject_analytics():
    from services.analytics_integration import get_analytics_js_config
    return {
        'analytics_config': get_analytics_js_config(),
        'analytics_js_snippet': '''
        <script>
        // Analytics configuration injected here
        const analyticsConfig = ''' + get_analytics_js_config() + ''';
        // Add your tracking functions here
        </script>
        '''
    }
```

### 3. Add Analytics Routes

```python
# Add to your main routes file or create new routes file
from services.analytics_integration import (
    track_quiz_start, track_study_session, get_user_analytics_summary,
    handle_analytics_api_request
)

@app.route('/api/analytics/track', methods=['POST'])
def analytics_track():
    """General analytics tracking endpoint."""
    return jsonify(handle_analytics_api_request())

@app.route('/api/user/analytics-summary')
def user_analytics_summary():
    """Get user analytics summary."""
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Not authenticated'}), 401
    
    summary = get_user_analytics_summary(user_id)
    return jsonify(summary)

@app.route('/analytics')
def analytics_dashboard():
    """Analytics dashboard page."""
    user_id = session.get('user_id')
    if not user_id:
        return redirect('/login')
    
    stats = get_user_analytics_summary(user_id)
    return render_template('analytics_dashboard.html', stats=stats)
```

### 4. Update Existing Quiz Routes

```python
# Example: Update your existing quiz routes
from services.analytics_integration import track_quiz_start, track_quiz_question

@app.route('/quiz')
def quiz():
    topic = request.args.get('topic', 'general')
    difficulty = request.args.get('difficulty', 'intermediate')
    
    # Add analytics tracking
    track_quiz_start(topic_area=topic, difficulty_level=difficulty)
    
    # Your existing quiz logic
    questions = get_quiz_questions(topic, difficulty)
    return render_template('quiz.html', questions=questions, topic=topic)

@app.route('/quiz/submit', methods=['POST'])
def submit_quiz():
    data = request.get_json()
    
    # Your existing logic
    is_correct = check_answer(data['question_id'], data['answer'])
    
    # Add analytics tracking
    track_quiz_question(correct=is_correct, time_taken=data.get('time_taken'))
    
    return jsonify({'correct': is_correct})
```

### 5. Update VM Integration

```python
# Add to your VM controller
from services.analytics_integration import track_vm_session, track_vm_command

@app.route('/vm/start')
def start_vm():
    topic = request.args.get('topic', 'general')
    
    # Add analytics tracking
    track_vm_session(topic_area=topic)
    
    # Your existing VM start logic
    vm_instance = start_vm_instance()
    return jsonify({'vm_id': vm_instance.id})

@app.route('/vm/execute', methods=['POST'])
def execute_vm_command():
    data = request.get_json()
    command = data['command']
    
    start_time = time.time()
    
    # Your existing command execution logic
    result = execute_command(command)
    
    execution_time = time.time() - start_time
    
    # Add analytics tracking
    track_vm_command(command=command, execution_time=execution_time)
    
    return jsonify(result)
```

### 6. Add to Templates

Add analytics tracking to your base template:

```html
<!-- templates/base.html -->
<!DOCTYPE html>
<html>
<head>
    <!-- Your existing head content -->
</head>
<body>
    <!-- Your existing body content -->
    
    <!-- Analytics tracking -->
    {{ analytics_js_snippet | safe }}
    
    <script>
    // Track page views automatically
    document.addEventListener('DOMContentLoaded', function() {
        const pageName = window.location.pathname.split('/').filter(p => p).join('_') || 'home';
        trackPageView(pageName);
    });
    </script>
</body>
</html>
```

### 7. Add Analytics Widget to Dashboard

```html
<!-- Add this widget to your main dashboard -->
<div class="analytics-widget">
    <h3>📊 Your Progress</h3>
    <div class="stats-row">
        <div class="stat">
            <span class="value" id="total-questions">-</span>
            <span class="label">Questions</span>
        </div>
        <div class="stat">
            <span class="value" id="accuracy">-</span>
            <span class="label">Accuracy</span>
        </div>
        <div class="stat">
            <span class="value" id="study-time">-</span>
            <span class="label">Study Time</span>
        </div>
    </div>
    <a href="/analytics" class="view-details">View Detailed Analytics →</a>
</div>

<script>
// Load analytics summary
fetch('/api/user/analytics-summary')
    .then(response => response.json())
    .then(data => {
        document.getElementById('total-questions').textContent = data.total_questions || 0;
        document.getElementById('accuracy').textContent = (data.accuracy || 0).toFixed(1) + '%';
        document.getElementById('study-time').textContent = Math.round((data.study_time_minutes || 0) / 60 * 10) / 10 + 'h';
    })
    .catch(err => console.log('Analytics load failed:', err));
</script>
```

## 📊 Available Analytics Metrics

### Quiz Performance
- Questions attempted/correct/incorrect
- Accuracy percentage over time
- Time per question
- Topic-specific performance

### Study Behavior
- Time spent studying
- Pages viewed
- Help requests and hint usage
- Return sessions to topics

### VM & Lab Usage
- Commands executed
- Lab exercises completed
- VM session duration
- Success rates

### Engagement Metrics
- Active learning time
- Feature usage patterns
- Error tracking
- Focus and attention metrics

### Achievement Tracking
- Unlocked achievements
- Learning goals progress
- Skill assessments
- Certification progress

## 🔧 Customization

### Adding Custom Metrics
```python
# Track custom events
from flask import g

def track_custom_event(event_name, event_data):
    if hasattr(g, 'current_analytics') and g.current_analytics:
        g.current_analytics.update_feature_usage(f"custom_{event_name}")
        
        # Add to custom metrics
        if not g.current_analytics.custom_metrics:
            g.current_analytics.custom_metrics = {}
        g.current_analytics.custom_metrics[event_name] = event_data
```

### Creating Custom Insights
```python
# Add to AnalyticsService class
def get_custom_insights(self, user_id: str) -> Dict[str, Any]:
    user_sessions = self.get_user_analytics(user_id)
    
    # Your custom insight logic here
    insights = {
        'learning_velocity': calculate_learning_velocity(user_sessions),
        'weak_topics': identify_weak_topics(user_sessions),
        'optimal_study_time': find_optimal_study_time(user_sessions)
    }
    
    return insights
```

## 🚀 Next Steps

1. **Copy the files** from the examples folder to your templates directory
2. **Update your routes** to include analytics tracking
3. **Test the integration** with a few quiz sessions
4. **Customize the dashboard** to match your application's design
5. **Add more specific tracking** for your unique features

## 📈 Benefits You'll Get

- **Data-driven insights** into learning effectiveness
- **Personalized recommendations** for users
- **Performance monitoring** across all features
- **User engagement tracking** to optimize the experience
- **Achievement and progress** gamification
- **Comprehensive dashboards** for both users and admins

The analytics system will help you understand how users learn, what works best, and where they struggle, enabling you to continuously improve the Linux study experience!
