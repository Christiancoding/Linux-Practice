"""Add analytics table

Revision ID: analytics_v1
Revises: 
Create Date: 2025-08-04

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import sqlite

# revision identifiers
revision = 'analytics_v1'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    """Create analytics table with comprehensive tracking fields."""
    op.create_table('analytics',
        sa.Column('id', sa.Integer(), nullable=False),
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
        sa.Column('quiz_mode', sa.String(length=50), nullable=True),
        sa.Column('question_categories', sa.JSON(), nullable=True),
        sa.Column('response_times', sa.JSON(), nullable=True),
        sa.Column('learning_path', sa.String(length=255), nullable=True),
        sa.Column('study_materials_accessed', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column('deleted_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for better query performance
    op.create_index('ix_analytics_user_id', 'analytics', ['user_id'], unique=False)
    op.create_index('ix_analytics_session_id', 'analytics', ['session_id'], unique=False)
    op.create_index('ix_analytics_activity_type', 'analytics', ['activity_type'], unique=False)
    op.create_index('ix_analytics_topic_area', 'analytics', ['topic_area'], unique=False)
    op.create_index('ix_analytics_created_at', 'analytics', ['created_at'], unique=False)
    op.create_index('ix_analytics_session_start', 'analytics', ['session_start'], unique=False)
    op.create_index('ix_analytics_quiz_mode', 'analytics', ['quiz_mode'], unique=False)
    op.create_index('ix_analytics_difficulty_level', 'analytics', ['difficulty_level'], unique=False)


def downgrade():
    """Drop analytics table and indexes."""
    op.drop_index('ix_analytics_difficulty_level', table_name='analytics')
    op.drop_index('ix_analytics_quiz_mode', table_name='analytics')
    op.drop_index('ix_analytics_session_start', table_name='analytics')
    op.drop_index('ix_analytics_created_at', table_name='analytics')
    op.drop_index('ix_analytics_topic_area', table_name='analytics')
    op.drop_index('ix_analytics_activity_type', table_name='analytics')
    op.drop_index('ix_analytics_session_id', table_name='analytics')
    op.drop_index('ix_analytics_user_id', table_name='analytics')
    op.drop_table('analytics')
