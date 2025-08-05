"""
Example Flask routes with analytics integration

This file shows how to integrate analytics tracking into your existing Flask routes.
"""

from flask import Blueprint, render_template, request, jsonify, session
from services.analytics_integration import (
    track_quiz_start, track_quiz_question, track_study_session, 
    track_vm_session, track_cli_playground, track_page_view,
    track_achievement, get_user_analytics_summary, get_global_analytics,
    track_route_activity, handle_analytics_api_request
)

# Create blueprint for analytics-enabled routes
analytics_bp = Blueprint('analytics', __name__)

@analytics_bp.route('/quiz')
@track_route_activity('quiz')
def quiz_page():
    """Quiz page with analytics tracking."""
    # Track page view
    track_page_view('quiz_main')
    
    # Get topic from query params
    topic = request.args.get('topic', 'general')
    difficulty = request.args.get('difficulty', 'intermediate')
    
    # Start quiz analytics session
    track_quiz_start(topic_area=topic, difficulty_level=difficulty)
    
    return render_template('quiz.html', topic=topic, difficulty=difficulty)

@analytics_bp.route('/api/quiz/answer', methods=['POST'])
def submit_quiz_answer():
    """Handle quiz answer submission with analytics."""
    data = request.get_json()
    
    correct = data.get('correct', False)
    time_taken = data.get('time_taken', 0)
    question_id = data.get('question_id')
    
    # Track the answer
    track_quiz_question(correct=correct, time_taken=time_taken)
    
    # If this was correct, check for achievements
    if correct and question_id:
        # Example achievement logic
        user_stats = get_user_analytics_summary()
        if user_stats.get('total_correct', 0) >= 50:
            track_achievement('quiz_master_50')
    
    return jsonify({'status': 'success', 'correct': correct})

@analytics_bp.route('/study/<topic>')
@track_route_activity('study')
def study_topic(topic):
    """Study page for specific topic."""
    track_page_view(f'study_{topic}')
    track_study_session(topic_area=topic)
    
    return render_template('study.html', topic=topic)

@analytics_bp.route('/vm-lab')
@track_route_activity('vm_lab')
def vm_lab():
    """VM lab environment."""
    track_page_view('vm_lab')
    
    # Get topic from query params
    topic = request.args.get('topic', 'general')
    track_vm_session(topic_area=topic)
    
    return render_template('vm_playground.html', topic=topic)

@analytics_bp.route('/api/vm/command', methods=['POST'])
def vm_command():
    """Handle VM command execution."""
    data = request.get_json()
    
    command = data.get('command', '')
    execution_time = data.get('execution_time', 0)
    
    # Use the analytics integration function
    from services.analytics_integration import track_vm_command
    track_vm_command(command=command, execution_time=execution_time)
    
    return jsonify({'status': 'success'})

@analytics_bp.route('/cli-playground')
@track_route_activity('cli_playground')
def cli_playground():
    """CLI playground page."""
    track_page_view('cli_playground')
    track_cli_playground()
    
    return render_template('cli_playground.html')

@analytics_bp.route('/stats')
def user_stats():
    """User statistics dashboard."""
    track_page_view('user_stats')
    
    user_id = session.get('user_id')
    if not user_id:
        return render_template('error.html', message='Please log in to view stats')
    
    # Get comprehensive user analytics
    stats = get_user_analytics_summary(user_id)
    
    return render_template('stats.html', stats=stats)

@analytics_bp.route('/admin/analytics')
def admin_analytics():
    """Admin analytics dashboard."""
    track_page_view('admin_analytics')
    
    # Check admin permissions here
    # if not is_admin(): return redirect('/login')
    
    global_stats = get_global_analytics()
    
    return render_template('admin_analytics.html', stats=global_stats)

@analytics_bp.route('/api/analytics/track', methods=['POST'])
def track_event():
    """General analytics tracking endpoint for AJAX calls."""
    return jsonify(handle_analytics_api_request())

# Add analytics tracking to existing routes
def add_analytics_to_existing_routes(app):
    """Add analytics tracking to existing routes in your application."""
    
    # Example: Add to your existing quiz controller
    @app.route('/quiz/review')
    def quiz_review():
        track_page_view('quiz_review')
        track_route_activity('review')
        # Your existing logic here
        return render_template('review.html')
    
    # Example: Add to settings page
    @app.route('/settings')
    def settings():
        track_page_view('settings')
        # Your existing logic here
        return render_template('settings.html')

# JavaScript snippet for client-side tracking
ANALYTICS_JS_SNIPPET = """
<script>
// Analytics tracking configuration
const analyticsConfig = {{ analytics_config | safe }};

// Track page views automatically
function trackPageView(pageName) {
    fetch('/api/analytics/track', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            event_type: 'page_view',
            page_name: pageName
        })
    });
}

// Track quiz answers
function trackQuizAnswer(correct, timeTaken) {
    fetch('/api/analytics/track', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            event_type: 'quiz_answer',
            correct: correct,
            time_taken: timeTaken
        })
    });
}

// Track VM commands
function trackVMCommand(command, executionTime) {
    fetch('/api/analytics/track', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            event_type: 'vm_command',
            command: command,
            execution_time: executionTime
        })
    });
}

// Track help requests
function trackHelpRequest(helpType) {
    fetch('/api/analytics/track', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            event_type: 'help_request',
            help_type: helpType
        })
    });
}

// Track feature usage
function trackFeatureUsage(featureName, usageCount = 1) {
    fetch('/api/analytics/track', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            event_type: 'feature_usage',
            feature_name: featureName,
            usage_count: usageCount
        })
    });
}

// Auto-track time spent on page
let pageStartTime = Date.now();
window.addEventListener('beforeunload', function() {
    const timeSpent = (Date.now() - pageStartTime) / 1000;
    navigator.sendBeacon('/api/analytics/track', JSON.stringify({
        event_type: 'page_time',
        time_spent: timeSpent
    }));
});

// Track scroll depth
let maxScrollDepth = 0;
window.addEventListener('scroll', function() {
    const scrollDepth = Math.round((window.scrollY / (document.body.scrollHeight - window.innerHeight)) * 100);
    if (scrollDepth > maxScrollDepth) {
        maxScrollDepth = scrollDepth;
        if (scrollDepth >= 25 && scrollDepth % 25 === 0) {
            trackFeatureUsage(`scroll_depth_${scrollDepth}`);
        }
    }
});
</script>
"""

# Template context processor for analytics
def inject_analytics_config():
    """Inject analytics configuration into all templates."""
    from services.analytics_integration import get_analytics_js_config
    return {
        'analytics_config': get_analytics_js_config(),
        'analytics_js_snippet': ANALYTICS_JS_SNIPPET
    }
