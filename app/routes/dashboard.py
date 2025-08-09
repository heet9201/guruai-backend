"""
Dashboard Routes
Provides dashboard overview and analytics endpoints with comprehensive user activity tracking.
"""

import logging
from datetime import datetime
from flask import Blueprint, request, jsonify, g
from app.utils.auth_middleware import token_required, teacher_required
from app.services.dashboard_service import DashboardService, ActivityType
from app.utils.auth_utils import JWTUtils

logger = logging.getLogger(__name__)

# Create blueprint
dashboard_bp = Blueprint('dashboard', __name__)

# Initialize dashboard service
dashboard_service = DashboardService()

@dashboard_bp.route('/overview', methods=['GET'])
@teacher_required
def get_dashboard_overview():
    """
    Get dashboard overview with weekly stats, recent activities, and AI recommendations.
    
    Returns:
        JSON response with dashboard data
    """
    try:
        user_id = g.current_user.get('id')
        if not user_id:
            return jsonify({
                'error': 'User identification failed',
                'message': 'Unable to identify current user'
            }), 400
        
        # Track dashboard access
        dashboard_service.track_activity(
            user_id=user_id,
            activity_type=ActivityType.ANALYSIS,
            title="Dashboard Overview Access",
            description="User accessed dashboard overview",
            metadata={'feature': 'dashboard_overview'}
        )
        
        # Get weekly statistics
        weekly_stats = dashboard_service.get_weekly_stats(user_id)
        
        # Get recent activities
        recent_activities = dashboard_service.get_recent_activities(user_id, limit=10)
        
        # Generate AI recommendations
        recommendations = dashboard_service.generate_ai_recommendations(user_id)
        
        # Format response
        response_data = {
            'weeklyStats': {
                'totalChats': weekly_stats.total_chats,
                'contentGenerated': weekly_stats.content_generated,
                'lessonsPrepared': weekly_stats.lessons_prepared,
                'timeSpent': weekly_stats.time_spent
            },
            'recentActivities': [
                {
                    'id': activity.id,
                    'type': activity.type,
                    'title': activity.title,
                    'timestamp': activity.timestamp
                }
                for activity in recent_activities
            ],
            'recommendations': [
                {
                    'id': rec.id,
                    'title': rec.title,
                    'description': rec.description,
                    'actionUrl': rec.action_url,
                    'priority': rec.priority
                }
                for rec in recommendations
            ],
            'status': 'success'
        }
        
        logger.info(f"Dashboard overview retrieved for user {user_id}")
        return jsonify(response_data), 200
        
    except Exception as e:
        logger.error(f"Error getting dashboard overview: {str(e)}")
        return jsonify({
            'error': 'Internal server error',
            'message': 'Failed to retrieve dashboard data'
        }), 500

@dashboard_bp.route('/analytics', methods=['GET'])
@teacher_required
def get_dashboard_analytics():
    """
    Get comprehensive analytics data with customizable time periods.
    
    Query Parameters:
        - period: enum [week, month, quarter, year] (default: week)
        - startDate: ISO date string (optional)
        - endDate: ISO date string (optional)
    
    Returns:
        JSON response with analytics data
    """
    try:
        user_id = g.current_user.get('id')
        if not user_id:
            return jsonify({
                'error': 'User identification failed',
                'message': 'Unable to identify current user'
            }), 400
        
        # Get query parameters
        period = request.args.get('period', 'week')
        start_date_str = request.args.get('startDate')
        end_date_str = request.args.get('endDate')
        
        # Validate period
        valid_periods = ['week', 'month', 'quarter', 'year']
        if period not in valid_periods:
            return jsonify({
                'error': 'Invalid period',
                'message': f'Period must be one of: {", ".join(valid_periods)}'
            }), 400
        
        # Parse custom date range if provided
        start_date = None
        end_date = None
        
        try:
            if start_date_str:
                start_date = datetime.fromisoformat(start_date_str.replace('Z', '+00:00'))
            if end_date_str:
                end_date = datetime.fromisoformat(end_date_str.replace('Z', '+00:00'))
        except ValueError as e:
            return jsonify({
                'error': 'Invalid date format',
                'message': 'Dates must be in ISO format (YYYY-MM-DDTHH:MM:SSZ)'
            }), 400
        
        # Track analytics access
        dashboard_service.track_activity(
            user_id=user_id,
            activity_type=ActivityType.ANALYSIS,
            title="Analytics Data Access",
            description=f"User accessed analytics for period: {period}",
            metadata={
                'feature': 'dashboard_analytics',
                'period': period,
                'custom_range': bool(start_date and end_date)
            }
        )
        
        # Get analytics data
        analytics_data = dashboard_service.get_analytics_data(
            user_id=user_id,
            period=period,
            start_date=start_date,
            end_date=end_date
        )
        
        # Add success status
        analytics_data['status'] = 'success'
        
        logger.info(f"Analytics data retrieved for user {user_id}, period: {period}")
        return jsonify(analytics_data), 200
        
    except Exception as e:
        logger.error(f"Error getting analytics data: {str(e)}")
        return jsonify({
            'error': 'Internal server error',
            'message': 'Failed to retrieve analytics data'
        }), 500

@dashboard_bp.route('/track-activity', methods=['POST'])
@teacher_required
def track_user_activity():
    """
    Track user activity for analytics (manual tracking endpoint).
    
    Request Body:
        {
            "type": "chat|content|lesson|analysis|planning",
            "title": "Activity title",
            "description": "Activity description",
            "metadata": {"feature": "specific_feature"},
            "durationSeconds": 120
        }
    
    Returns:
        JSON response with activity ID
    """
    try:
        user_id = g.current_user.get('id')
        if not user_id:
            return jsonify({
                'error': 'User identification failed',
                'message': 'Unable to identify current user'
            }), 400
        
        # Get request data
        data = request.get_json()
        if not data:
            return jsonify({
                'error': 'No data provided',
                'message': 'Request body is required'
            }), 400
        
        # Validate required fields
        activity_type_str = data.get('type')
        title = data.get('title')
        
        if not activity_type_str or not title:
            return jsonify({
                'error': 'Missing required fields',
                'message': 'type and title are required'
            }), 400
        
        # Validate activity type
        try:
            activity_type = ActivityType(activity_type_str)
        except ValueError:
            valid_types = [t.value for t in ActivityType]
            return jsonify({
                'error': 'Invalid activity type',
                'message': f'type must be one of: {", ".join(valid_types)}'
            }), 400
        
        # Get optional fields
        description = data.get('description', '')
        metadata = data.get('metadata', {})
        duration_seconds = data.get('durationSeconds')
        
        # Track the activity
        activity_id = dashboard_service.track_activity(
            user_id=user_id,
            activity_type=activity_type,
            title=title,
            description=description,
            metadata=metadata,
            duration_seconds=duration_seconds
        )
        
        logger.info(f"Activity tracked: {activity_id} for user {user_id}")
        return jsonify({
            'activityId': activity_id,
            'message': 'Activity tracked successfully',
            'status': 'success'
        }), 201
        
    except Exception as e:
        logger.error(f"Error tracking activity: {str(e)}")
        return jsonify({
            'error': 'Internal server error',
            'message': 'Failed to track activity'
        }), 500

@dashboard_bp.route('/recommendations/refresh', methods=['POST'])
@teacher_required
def refresh_recommendations():
    """
    Refresh AI-powered recommendations for the current user.
    
    Returns:
        JSON response with updated recommendations
    """
    try:
        user_id = g.current_user.get('id')
        if not user_id:
            return jsonify({
                'error': 'User identification failed',
                'message': 'Unable to identify current user'
            }), 400
        
        # Track recommendation refresh
        dashboard_service.track_activity(
            user_id=user_id,
            activity_type=ActivityType.ANALYSIS,
            title="Recommendations Refresh",
            description="User refreshed AI recommendations",
            metadata={'feature': 'recommendations_refresh'}
        )
        
        # Generate fresh recommendations
        recommendations = dashboard_service.generate_ai_recommendations(user_id)
        
        # Format response
        response_data = {
            'recommendations': [
                {
                    'id': rec.id,
                    'title': rec.title,
                    'description': rec.description,
                    'actionUrl': rec.action_url,
                    'priority': rec.priority
                }
                for rec in recommendations
            ],
            'message': 'Recommendations refreshed successfully',
            'status': 'success'
        }
        
        logger.info(f"Recommendations refreshed for user {user_id}")
        return jsonify(response_data), 200
        
    except Exception as e:
        logger.error(f"Error refreshing recommendations: {str(e)}")
        return jsonify({
            'error': 'Internal server error',
            'message': 'Failed to refresh recommendations'
        }), 500

@dashboard_bp.route('/performance-insights', methods=['GET'])
@teacher_required
def get_performance_insights():
    """
    Get AI-generated performance insights and suggestions.
    
    Returns:
        JSON response with performance insights
    """
    try:
        user_id = g.current_user.get('id')
        if not user_id:
            return jsonify({
                'error': 'User identification failed',
                'message': 'Unable to identify current user'
            }), 400
        
        # Track insights access
        dashboard_service.track_activity(
            user_id=user_id,
            activity_type=ActivityType.ANALYSIS,
            title="Performance Insights Access",
            description="User accessed performance insights",
            metadata={'feature': 'performance_insights'}
        )
        
        # Get analytics data for insights
        analytics_data = dashboard_service.get_analytics_data(user_id, period='month')
        
        # Generate insights based on analytics
        insights = []
        
        # Activity level insights
        total_activities = analytics_data.get('total_activities', 0)
        if total_activities < 10:
            insights.append({
                'type': 'activity',
                'level': 'suggestion',
                'title': 'Increase Platform Usage',
                'message': 'You have low activity this month. Try exploring more features to maximize your teaching potential.',
                'actionable': True,
                'action': 'Explore our quick start guide'
            })
        elif total_activities > 50:
            insights.append({
                'type': 'activity',
                'level': 'positive',
                'title': 'Great Engagement!',
                'message': 'You are actively using the platform. Keep up the excellent work!',
                'actionable': False,
                'action': None
            })
        
        # Time management insights
        time_spent = analytics_data.get('total_time_spent', 0)
        avg_session = analytics_data.get('average_session_duration', 0)
        
        if avg_session < 5:
            insights.append({
                'type': 'efficiency',
                'level': 'tip',
                'title': 'Optimize Session Time',
                'message': 'Your sessions are quite short. Consider batching similar tasks for better efficiency.',
                'actionable': True,
                'action': 'Try the weekly planner feature'
            })
        
        # Feature usage insights
        activity_breakdown = analytics_data.get('activity_breakdown', {})
        most_used_feature = max(activity_breakdown, key=activity_breakdown.get) if activity_breakdown else None
        
        if most_used_feature:
            insights.append({
                'type': 'feature',
                'level': 'info',
                'title': f'Top Feature: {most_used_feature.title()}',
                'message': f'You use {most_used_feature} features the most. Consider exploring complementary features.',
                'actionable': True,
                'action': 'Discover related features'
            })
        
        # Productivity score insights
        productivity_score = analytics_data.get('productivity_score', 50)
        if productivity_score < 40:
            insights.append({
                'type': 'productivity',
                'level': 'warning',
                'title': 'Productivity Opportunity',
                'message': 'Your productivity score suggests room for improvement. Focus on consistent daily usage.',
                'actionable': True,
                'action': 'Set daily usage goals'
            })
        elif productivity_score > 80:
            insights.append({
                'type': 'productivity',
                'level': 'achievement',
                'title': 'Excellent Productivity!',
                'message': 'Your productivity score is outstanding. You are making great use of our platform.',
                'actionable': False,
                'action': None
            })
        
        response_data = {
            'insights': insights,
            'productivityScore': productivity_score,
            'period': 'month',
            'generatedAt': datetime.utcnow().isoformat() + 'Z',
            'status': 'success'
        }
        
        logger.info(f"Performance insights generated for user {user_id}")
        return jsonify(response_data), 200
        
    except Exception as e:
        logger.error(f"Error getting performance insights: {str(e)}")
        return jsonify({
            'error': 'Internal server error',
            'message': 'Failed to generate performance insights'
        }), 500

# Error handlers for the dashboard blueprint
@dashboard_bp.errorhandler(404)
def dashboard_not_found(error):
    """Handle 404 errors for dashboard endpoints."""
    return jsonify({
        'error': 'Endpoint not found',
        'message': 'The requested dashboard endpoint does not exist'
    }), 404

@dashboard_bp.errorhandler(500)
def dashboard_internal_error(error):
    """Handle 500 errors for dashboard endpoints."""
    logger.error(f"Dashboard internal error: {str(error)}")
    return jsonify({
        'error': 'Internal server error',
        'message': 'An error occurred while processing your dashboard request'
    }), 500
