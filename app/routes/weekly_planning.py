"""
Weekly Planning Routes
REST API endpoints for managing weekly lesson plans, templates, and activities.
"""

import logging
from datetime import datetime, date
from flask import Blueprint, request, jsonify
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from app.utils.auth_middleware import token_required, require_firebase_auth, get_current_user
from app.services.weekly_planning_service import WeeklyPlanningService
from app.services.template_init_service import TemplateInitializationService
from app.models.weekly_planning import WeeklyPlan, ActivityTemplate

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create blueprint
weekly_planning_bp = Blueprint('weekly_planning', __name__, url_prefix='/api/v1/weekly-planning')

# Initialize services
weekly_planning_service = WeeklyPlanningService()
template_init_service = TemplateInitializationService()

# Rate limiting
limiter = Limiter(
    app=None,
    key_func=get_remote_address,
    default_limits=["1000 per hour"]
)

# Helper function to parse date
def parse_date(date_str):
    """Parse date string to date object."""
    if not date_str:
        return None
    try:
        return datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        return None

# Weekly Plans Endpoints

@weekly_planning_bp.route('/plans', methods=['GET'])
@require_firebase_auth
@limiter.limit("100 per hour")
def get_weekly_plans():
    """
    Get weekly plans with filtering and pagination.
    Query parameters:
    - start_date: Filter plans starting from this date (YYYY-MM-DD)
    - end_date: Filter plans ending before this date (YYYY-MM-DD)
    - grade: Filter by target grade
    - is_template: Filter templates (true/false)
    - page: Page number (default: 1)
    - page_size: Items per page (default: 20, max: 100)
    - search: Search term for title/description
    """
    try:
        user_id = get_current_user()['uid']
        
        # Parse query parameters
        start_date = parse_date(request.args.get('start_date'))
        end_date = parse_date(request.args.get('end_date'))
        grade = request.args.get('grade')
        is_template = request.args.get('is_template')
        page = int(request.args.get('page', 1))
        page_size = min(int(request.args.get('page_size', 20)), 100)
        search = request.args.get('search')
        
        # Convert is_template to boolean
        if is_template is not None:
            is_template = is_template.lower() == 'true'
        
        # Get plans
        result = weekly_planning_service.get_weekly_plans(
            user_id=user_id,
            start_date=start_date,
            end_date=end_date,
            grade=grade,
            is_template=is_template,
            page=page,
            page_size=page_size,
            search=search
        )
        
        return jsonify({
            'success': True,
            'data': result
        }), 200
        
    except ValueError as e:
        return jsonify({
            'success': False,
            'error': 'Invalid parameters',
            'details': str(e)
        }), 400
    except Exception as e:
        logger.error(f"Error getting weekly plans: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to get weekly plans',
            'details': str(e)
        }), 500

@weekly_planning_bp.route('/plans/<plan_id>', methods=['GET'])
@require_firebase_auth
@limiter.limit("200 per hour")
def get_weekly_plan(plan_id):
    """Get a specific weekly plan by ID."""
    try:
        user_id = get_current_user()['uid']
        
        plan = weekly_planning_service.get_weekly_plan_by_id(plan_id, user_id)
        
        if not plan:
            return jsonify({
                'success': False,
                'error': 'Plan not found or access denied'
            }), 404
        
        return jsonify({
            'success': True,
            'data': plan.to_dict()
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting weekly plan {plan_id}: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to get weekly plan',
            'details': str(e)
        }), 500

@weekly_planning_bp.route('/plans', methods=['POST'])
@require_firebase_auth
@limiter.limit("50 per hour")
def create_weekly_plan():
    """Create a new weekly plan."""
    try:
        user_id = get_current_user()['uid']
        plan_data = request.get_json()
        
        if not plan_data:
            return jsonify({
                'success': False,
                'error': 'Request body is required'
            }), 400
        
        # Create plan
        plan = weekly_planning_service.create_weekly_plan(user_id, plan_data)
        
        return jsonify({
            'success': True,
            'data': plan.to_dict(),
            'message': 'Weekly plan created successfully'
        }), 201
        
    except ValueError as e:
        return jsonify({
            'success': False,
            'error': 'Invalid plan data',
            'details': str(e)
        }), 400
    except Exception as e:
        logger.error(f"Error creating weekly plan: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to create weekly plan',
            'details': str(e)
        }), 500

@weekly_planning_bp.route('/plans/<plan_id>', methods=['PUT'])
@require_firebase_auth
@limiter.limit("100 per hour")
def update_weekly_plan(plan_id):
    """Update an existing weekly plan."""
    try:
        user_id = get_current_user()['uid']
        update_data = request.get_json()
        
        if not update_data:
            return jsonify({
                'success': False,
                'error': 'Request body is required'
            }), 400
        
        # Update plan
        plan = weekly_planning_service.update_weekly_plan(plan_id, user_id, update_data)
        
        if not plan:
            return jsonify({
                'success': False,
                'error': 'Plan not found or access denied'
            }), 404
        
        return jsonify({
            'success': True,
            'data': plan.to_dict(),
            'message': 'Weekly plan updated successfully'
        }), 200
        
    except ValueError as e:
        return jsonify({
            'success': False,
            'error': 'Invalid update data',
            'details': str(e)
        }), 400
    except Exception as e:
        logger.error(f"Error updating weekly plan {plan_id}: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to update weekly plan',
            'details': str(e)
        }), 500

@weekly_planning_bp.route('/plans/<plan_id>', methods=['DELETE'])
@require_firebase_auth
@limiter.limit("50 per hour")
def delete_weekly_plan(plan_id):
    """Delete a weekly plan."""
    try:
        user_id = get_current_user()['uid']
        
        success = weekly_planning_service.delete_weekly_plan(plan_id, user_id)
        
        if not success:
            return jsonify({
                'success': False,
                'error': 'Plan not found or access denied'
            }), 404
        
        return jsonify({
            'success': True,
            'message': 'Weekly plan deleted successfully'
        }), 200
        
    except Exception as e:
        logger.error(f"Error deleting weekly plan {plan_id}: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to delete weekly plan',
            'details': str(e)
        }), 500

@weekly_planning_bp.route('/plans/<plan_id>/copy', methods=['POST'])
@require_firebase_auth
@limiter.limit("20 per hour")
def copy_weekly_plan(plan_id):
    """Create a copy of an existing weekly plan."""
    try:
        user_id = get_current_user()['uid']
        data = request.get_json() or {}
        
        # Parse new week start date if provided
        new_week_start = None
        if 'new_week_start' in data:
            new_week_start = parse_date(data['new_week_start'])
            if not new_week_start:
                return jsonify({
                    'success': False,
                    'error': 'Invalid date format for new_week_start (use YYYY-MM-DD)'
                }), 400
        
        # Copy plan
        new_plan = weekly_planning_service.copy_weekly_plan(plan_id, user_id, new_week_start)
        
        if not new_plan:
            return jsonify({
                'success': False,
                'error': 'Plan not found or access denied'
            }), 404
        
        return jsonify({
            'success': True,
            'data': new_plan.to_dict(),
            'message': 'Weekly plan copied successfully'
        }), 201
        
    except Exception as e:
        logger.error(f"Error copying weekly plan {plan_id}: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to copy weekly plan',
            'details': str(e)
        }), 500

@weekly_planning_bp.route('/plans/<plan_id>/summary', methods=['GET'])
@require_firebase_auth
@limiter.limit("100 per hour")
def get_plan_summary(plan_id):
    """Get comprehensive summary of a weekly plan."""
    try:
        user_id = get_current_user()['uid']
        
        plan = weekly_planning_service.get_weekly_plan_by_id(plan_id, user_id)
        
        if not plan:
            return jsonify({
                'success': False,
                'error': 'Plan not found or access denied'
            }), 404
        
        summary = weekly_planning_service.generate_plan_summary(plan)
        
        return jsonify({
            'success': True,
            'data': summary.to_dict()
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting plan summary {plan_id}: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to get plan summary',
            'details': str(e)
        }), 500

# Template Endpoints

@weekly_planning_bp.route('/templates', methods=['GET'])
@require_firebase_auth
@limiter.limit("100 per hour")
def get_templates():
    """
    Get weekly plan templates.
    Query parameters:
    - category: Filter by template category
    - grade: Filter by target grade
    - subject: Filter by subject
    """
    try:
        user_id = get_current_user()['uid']
        
        category = request.args.get('category')
        grade = request.args.get('grade')
        subject = request.args.get('subject')
        
        templates = weekly_planning_service.get_templates(
            category=category,
            grade=grade,
            subject=subject,
            user_id=user_id
        )
        
        return jsonify({
            'success': True,
            'data': [template.to_dict() for template in templates],
            'count': len(templates)
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting templates: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to get templates',
            'details': str(e)
        }), 500

# Activity Management Endpoints

@weekly_planning_bp.route('/activities/templates', methods=['GET'])
@require_firebase_auth
@limiter.limit("200 per hour")
def get_activity_templates():
    """
    Get activity templates for the activity library.
    Query parameters:
    - subject: Filter by subject
    - grade: Filter by grade
    - type: Filter by activity type
    """
    try:
        user_id = get_current_user()['uid']
        
        subject = request.args.get('subject')
        grade = request.args.get('grade')
        activity_type = request.args.get('type')
        
        templates = weekly_planning_service.get_activity_templates(
            user_id=user_id,
            subject=subject,
            grade=grade,
            type=activity_type
        )
        
        return jsonify({
            'success': True,
            'data': [template.to_dict() for template in templates],
            'count': len(templates)
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting activity templates: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to get activity templates',
            'details': str(e)
        }), 500

@weekly_planning_bp.route('/activities/templates', methods=['POST'])
@require_firebase_auth
@limiter.limit("20 per hour")
def create_activity_template():
    """Create a new activity template."""
    try:
        user_id = get_current_user()['uid']
        template_data = request.get_json()
        
        if not template_data:
            return jsonify({
                'success': False,
                'error': 'Request body is required'
            }), 400
        
        template = weekly_planning_service.create_activity_template(user_id, template_data)
        
        return jsonify({
            'success': True,
            'data': template.to_dict(),
            'message': 'Activity template created successfully'
        }), 201
        
    except ValueError as e:
        return jsonify({
            'success': False,
            'error': 'Invalid template data',
            'details': str(e)
        }), 400
    except Exception as e:
        logger.error(f"Error creating activity template: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to create activity template',
            'details': str(e)
        }), 500

@weekly_planning_bp.route('/activities/suggestions', methods=['POST'])
@require_firebase_auth
@limiter.limit("30 per hour")
def get_activity_suggestions():
    """
    Get AI-generated activity suggestions.
    Body parameters:
    - subject: Required subject
    - grade: Required grade
    - available_time: Available time in minutes
    - context: Optional context for personalization
    """
    try:
        user_id = get_current_user()['uid']
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'error': 'Request body is required'
            }), 400
        
        subject = data.get('subject')
        grade = data.get('grade')
        available_time = data.get('available_time', 30)
        context = data.get('context')
        
        if not subject or not grade:
            return jsonify({
                'success': False,
                'error': 'Subject and grade are required'
            }), 400
        
        suggestions = weekly_planning_service.get_ai_activity_suggestions(
            user_id=user_id,
            subject=subject,
            grade=grade,
            available_time=available_time,
            context=context
        )
        
        return jsonify({
            'success': True,
            'data': suggestions,
            'count': len(suggestions)
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting activity suggestions: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to get activity suggestions',
            'details': str(e)
        }), 500

# Scheduling Endpoints

@weekly_planning_bp.route('/plans/<plan_id>/conflicts', methods=['GET'])
@require_firebase_auth
@limiter.limit("100 per hour")
def detect_plan_conflicts(plan_id):
    """Detect scheduling conflicts in a weekly plan."""
    try:
        user_id = get_current_user()['uid']
        
        plan = weekly_planning_service.get_weekly_plan_by_id(plan_id, user_id)
        
        if not plan:
            return jsonify({
                'success': False,
                'error': 'Plan not found or access denied'
            }), 404
        
        conflicts = weekly_planning_service.detect_conflicts(plan)
        
        return jsonify({
            'success': True,
            'data': [conflict.to_dict() for conflict in conflicts],
            'count': len(conflicts)
        }), 200
        
    except Exception as e:
        logger.error(f"Error detecting conflicts for plan {plan_id}: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to detect conflicts',
            'details': str(e)
        }), 500

@weekly_planning_bp.route('/plans/<plan_id>/days/<day_index>/auto-schedule', methods=['POST'])
@require_firebase_auth
@limiter.limit("50 per hour")
def auto_schedule_day(plan_id, day_index):
    """Auto-schedule activities for a specific day."""
    try:
        user_id = get_current_user()['uid']
        day_idx = int(day_index)
        
        if day_idx < 0 or day_idx > 6:
            return jsonify({
                'success': False,
                'error': 'Day index must be between 0 and 6'
            }), 400
        
        plan = weekly_planning_service.get_weekly_plan_by_id(plan_id, user_id)
        
        if not plan:
            return jsonify({
                'success': False,
                'error': 'Plan not found or access denied'
            }), 404
        
        if day_idx >= len(plan.day_plans):
            return jsonify({
                'success': False,
                'error': 'Day index out of range for this plan'
            }), 400
        
        # Auto-schedule the day
        updated_day = weekly_planning_service.auto_schedule_activities(plan.day_plans[day_idx])
        plan.day_plans[day_idx] = updated_day
        
        # Save updated plan
        weekly_planning_service.update_weekly_plan(plan_id, user_id, {'day_plans': [dp.to_dict() for dp in plan.day_plans]})
        
        return jsonify({
            'success': True,
            'data': updated_day.to_dict(),
            'message': 'Day scheduled successfully'
        }), 200
        
    except ValueError as e:
        return jsonify({
            'success': False,
            'error': 'Invalid day index',
            'details': str(e)
        }), 400
    except Exception as e:
        logger.error(f"Error auto-scheduling day {day_index} for plan {plan_id}: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to auto-schedule day',
            'details': str(e)
        }), 500

# System Management Endpoints

@weekly_planning_bp.route('/system/initialize-templates', methods=['POST'])
@require_firebase_auth
@limiter.limit("5 per hour")
def initialize_templates():
    """Initialize default activity templates in the system."""
    try:
        user = get_current_user()
        
        # Only allow admin users to initialize templates
        # You might want to add proper admin role checking here
        
        success = template_init_service.initialize_default_templates()
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Default templates initialized successfully'
            }), 200
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to initialize templates'
            }), 500
            
    except Exception as e:
        logger.error(f"Error initializing templates: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to initialize templates',
            'details': str(e)
        }), 500

@weekly_planning_bp.route('/system/template-stats', methods=['GET'])
@require_firebase_auth
@limiter.limit("100 per hour")
def get_template_stats():
    """Get statistics about activity templates in the system."""
    try:
        stats = template_init_service.get_template_statistics()
        
        return jsonify({
            'success': True,
            'data': stats
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting template stats: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to get template statistics',
            'details': str(e)
        }), 500

@weekly_planning_bp.route('/system/health', methods=['GET'])
@limiter.limit("200 per hour")
def system_health():
    """Check the health of the weekly planning system."""
    try:
        health_data = template_init_service.health_check()
        
        # Add weekly planning service health
        health_data['weekly_planning_service'] = 'healthy'
        health_data['timestamp'] = datetime.utcnow().isoformat()
        
        status_code = 200 if health_data.get('status') == 'healthy' else 503
        
        return jsonify({
            'success': True,
            'data': health_data
        }), status_code
        
    except Exception as e:
        logger.error(f"Error checking system health: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Health check failed',
            'details': str(e)
        }), 500

# Export Endpoints

@weekly_planning_bp.route('/plans/<plan_id>/export/pdf', methods=['GET'])
@require_firebase_auth
@limiter.limit("20 per hour")
def export_plan_to_pdf(plan_id):
    """Export a weekly plan to PDF format."""
    try:
        user_id = get_current_user()['uid']
        
        plan = weekly_planning_service.get_weekly_plan_by_id(plan_id, user_id)
        
        if not plan:
            return jsonify({
                'success': False,
                'error': 'Plan not found or access denied'
            }), 404
        
        # TODO: Implement PDF generation
        # For now, return plan data that can be used by frontend for PDF generation
        
        return jsonify({
            'success': True,
            'message': 'PDF export not yet implemented',
            'data': {
                'plan': plan.to_dict(),
                'export_format': 'pdf',
                'generated_at': datetime.utcnow().isoformat()
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Error exporting plan {plan_id} to PDF: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to export plan to PDF',
            'details': str(e)
        }), 500

@weekly_planning_bp.route('/plans/<plan_id>/export/calendar', methods=['GET'])
@require_firebase_auth
@limiter.limit("20 per hour")  
def export_plan_to_calendar(plan_id):
    """Export a weekly plan to calendar format (ICS)."""
    try:
        user_id = get_current_user()['uid']
        
        plan = weekly_planning_service.get_weekly_plan_by_id(plan_id, user_id)
        
        if not plan:
            return jsonify({
                'success': False,
                'error': 'Plan not found or access denied'
            }), 404
        
        # TODO: Implement ICS calendar generation
        # For now, return plan data that can be used for calendar export
        
        return jsonify({
            'success': True,
            'message': 'Calendar export not yet implemented',
            'data': {
                'plan': plan.to_dict(),
                'export_format': 'ics',
                'generated_at': datetime.utcnow().isoformat()
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Error exporting plan {plan_id} to calendar: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to export plan to calendar',
            'details': str(e)
        }), 500

# Health check endpoint
@weekly_planning_bp.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({
        'status': 'healthy',
        'service': 'weekly-planning',
        'timestamp': datetime.utcnow().isoformat()
    }), 200

# Error handlers
@weekly_planning_bp.errorhandler(429)
def ratelimit_handler(e):
    """Handle rate limit exceeded."""
    return jsonify({
        'success': False,
        'error': 'Rate limit exceeded',
        'retry_after': getattr(e, 'retry_after', None)
    }), 429

@weekly_planning_bp.errorhandler(404)
def not_found_handler(e):
    """Handle 404 errors."""
    return jsonify({
        'success': False,
        'error': 'Endpoint not found'
    }), 404

@weekly_planning_bp.errorhandler(500)
def internal_error_handler(e):
    """Handle internal server errors."""
    logger.error(f"Internal server error: {str(e)}")
    return jsonify({
        'success': False,
        'error': 'Internal server error'
    }), 500
