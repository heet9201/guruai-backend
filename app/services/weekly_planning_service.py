"""
Weekly Planning Service
Comprehensive service for managing weekly lesson plans, templates, and activities.
"""

import logging
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Any, Tuple
import uuid

from google.cloud import firestore
from app.models.weekly_planning import (
    WeeklyPlan, DayPlan, LessonActivity, ActivityTemplate, 
    ScheduleConflict, PlanSummary, ActivityType, TemplateCategory, ConflictType
)
from app.services.ai_service import AIService

logger = logging.getLogger(__name__)

class WeeklyPlanningService:
    """Service for managing weekly lesson plans and activities."""
    
    def __init__(self):
        """Initialize the weekly planning service."""
        self.db = firestore.Client()
        self.ai_service = AIService()
        
    # Weekly Plans Management
    
    def get_weekly_plans(self, user_id: str, start_date: Optional[date] = None,
                        end_date: Optional[date] = None, grade: Optional[str] = None,
                        is_template: Optional[bool] = None, page: int = 1,
                        page_size: int = 20, search: Optional[str] = None) -> Dict[str, Any]:
        """
        Get weekly plans with filtering, pagination, and search.
        
        Args:
            user_id: User identifier
            start_date: Filter plans starting from this date
            end_date: Filter plans ending before this date
            grade: Filter by target grade
            is_template: Filter templates or regular plans
            page: Page number for pagination
            page_size: Number of items per page
            search: Search term for title/description
            
        Returns:
            Dictionary with plans and pagination info
        """
        try:
            # Build query
            query = self.db.collection('weekly_plans')
            
            # Filter by user (unless looking for public templates)
            if is_template is True:
                # For templates, include public ones and user's own
                query = query.where('is_template', '==', True)
            else:
                query = query.where('user_id', '==', user_id)
                if is_template is False:
                    query = query.where('is_template', '==', False)
            
            # Date filtering
            if start_date:
                query = query.where('week_start', '>=', start_date)
            if end_date:
                query = query.where('week_start', '<=', end_date)
            
            # Execute query
            docs = query.stream()
            plans = []
            
            for doc in docs:
                plan_data = doc.to_dict()
                plan = WeeklyPlan.from_dict(plan_data)
                
                # Apply additional filters
                if grade and grade not in plan.target_grades:
                    continue
                    
                if search and search.lower() not in (plan.title + ' ' + plan.description).lower():
                    continue
                
                plans.append(plan)
            
            # Sort by creation date (newest first)
            plans.sort(key=lambda x: x.created_at, reverse=True)
            
            # Apply pagination
            total_count = len(plans)
            start_idx = (page - 1) * page_size
            end_idx = start_idx + page_size
            paginated_plans = plans[start_idx:end_idx]
            
            # Convert to dict format
            plans_data = [plan.to_dict() for plan in paginated_plans]
            
            return {
                'plans': plans_data,
                'pagination': {
                    'page': page,
                    'pageSize': page_size,
                    'totalCount': total_count,
                    'totalPages': (total_count + page_size - 1) // page_size,
                    'hasNext': end_idx < total_count,
                    'hasPrevious': page > 1
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting weekly plans: {str(e)}")
            raise
    
    def get_weekly_plan_by_id(self, plan_id: str, user_id: str) -> Optional[WeeklyPlan]:
        """Get a specific weekly plan by ID."""
        try:
            doc_ref = self.db.collection('weekly_plans').document(plan_id)
            doc = doc_ref.get()
            
            if not doc.exists:
                return None
            
            plan_data = doc.to_dict()
            plan = WeeklyPlan.from_dict(plan_data)
            
            # Check access permissions
            if plan.user_id != user_id and not plan.is_template:
                return None
            
            return plan
            
        except Exception as e:
            logger.error(f"Error getting weekly plan {plan_id}: {str(e)}")
            return None
    
    def create_weekly_plan(self, user_id: str, plan_data: Dict[str, Any]) -> WeeklyPlan:
        """Create a new weekly plan."""
        try:
            # Create plan from data
            plan = WeeklyPlan.from_dict(plan_data)
            plan.user_id = user_id
            plan.created_at = datetime.utcnow()
            plan.updated_at = datetime.utcnow()
            
            # Validate and process the plan
            self._validate_weekly_plan(plan)
            self._process_plan_subjects(plan)
            
            # Save to Firestore
            doc_ref = self.db.collection('weekly_plans').document(plan.id)
            doc_ref.set(plan.to_dict())
            
            logger.info(f"Created weekly plan {plan.id} for user {user_id}")
            return plan
            
        except Exception as e:
            logger.error(f"Error creating weekly plan: {str(e)}")
            raise
    
    def update_weekly_plan(self, plan_id: str, user_id: str, 
                          update_data: Dict[str, Any]) -> Optional[WeeklyPlan]:
        """Update an existing weekly plan."""
        try:
            # Get existing plan
            plan = self.get_weekly_plan_by_id(plan_id, user_id)
            if not plan:
                return None
            
            # Check permissions
            if plan.user_id != user_id:
                return None
            
            # Update fields
            for key, value in update_data.items():
                if hasattr(plan, key):
                    setattr(plan, key, value)
            
            plan.updated_at = datetime.utcnow()
            
            # Validate and process
            self._validate_weekly_plan(plan)
            self._process_plan_subjects(plan)
            
            # Save changes
            doc_ref = self.db.collection('weekly_plans').document(plan_id)
            doc_ref.update(plan.to_dict())
            
            logger.info(f"Updated weekly plan {plan_id}")
            return plan
            
        except Exception as e:
            logger.error(f"Error updating weekly plan {plan_id}: {str(e)}")
            raise
    
    def delete_weekly_plan(self, plan_id: str, user_id: str) -> bool:
        """Delete a weekly plan."""
        try:
            # Get plan to check permissions
            plan = self.get_weekly_plan_by_id(plan_id, user_id)
            if not plan or plan.user_id != user_id:
                return False
            
            # Delete from Firestore
            doc_ref = self.db.collection('weekly_plans').document(plan_id)
            doc_ref.delete()
            
            logger.info(f"Deleted weekly plan {plan_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting weekly plan {plan_id}: {str(e)}")
            return False
    
    def copy_weekly_plan(self, plan_id: str, user_id: str, 
                        new_week_start: Optional[date] = None) -> Optional[WeeklyPlan]:
        """Create a copy of an existing weekly plan."""
        try:
            # Get original plan
            original_plan = self.get_weekly_plan_by_id(plan_id, user_id)
            if not original_plan:
                return None
            
            # Create copy
            new_plan = WeeklyPlan.from_dict(original_plan.to_dict())
            new_plan.id = str(uuid.uuid4())
            new_plan.user_id = user_id
            new_plan.is_template = False  # Copies are not templates
            new_plan.created_at = datetime.utcnow()
            new_plan.updated_at = datetime.utcnow()
            
            # Update title
            new_plan.title = f"Copy of {original_plan.title}"
            
            # Update week start if provided
            if new_week_start:
                new_plan.week_start = new_week_start
                # Update day plan dates accordingly
                for i, day_plan in enumerate(new_plan.day_plans):
                    day_plan.date = new_week_start + timedelta(days=i)
            
            # Generate new IDs for activities
            for day_plan in new_plan.day_plans:
                for activity in day_plan.activities:
                    activity.id = str(uuid.uuid4())
                    activity.created_at = datetime.utcnow()
                    activity.updated_at = datetime.utcnow()
            
            # Save copy
            doc_ref = self.db.collection('weekly_plans').document(new_plan.id)
            doc_ref.set(new_plan.to_dict())
            
            logger.info(f"Copied weekly plan {plan_id} to {new_plan.id}")
            return new_plan
            
        except Exception as e:
            logger.error(f"Error copying weekly plan {plan_id}: {str(e)}")
            raise
    
    # Template Management
    
    def get_templates(self, category: Optional[str] = None, grade: Optional[str] = None,
                     subject: Optional[str] = None, user_id: Optional[str] = None) -> List[WeeklyPlan]:
        """Get weekly plan templates with filtering."""
        try:
            query = self.db.collection('weekly_plans').where('is_template', '==', True)
            
            # Apply filters
            if category:
                query = query.where('template_category', '==', category)
            
            docs = query.stream()
            templates = []
            
            for doc in docs:
                template_data = doc.to_dict()
                template = WeeklyPlan.from_dict(template_data)
                
                # Apply additional filters
                if grade and grade not in template.target_grades:
                    continue
                if subject and subject not in template.subjects:
                    continue
                
                # Include public templates and user's own templates
                if template.user_id == '' or template.user_id == user_id:
                    templates.append(template)
            
            # Sort by usage/popularity (you could track this)
            templates.sort(key=lambda x: x.created_at, reverse=True)
            
            return templates
            
        except Exception as e:
            logger.error(f"Error getting templates: {str(e)}")
            return []
    
    # Activity Management
    
    def get_activity_templates(self, user_id: str, subject: Optional[str] = None,
                              grade: Optional[str] = None, type: Optional[str] = None) -> List[ActivityTemplate]:
        """Get activity templates for the activity library."""
        try:
            query = self.db.collection('activity_templates')
            
            docs = query.stream()
            templates = []
            
            for doc in docs:
                template_data = doc.to_dict()
                template = ActivityTemplate.from_dict(template_data)
                
                # Include public templates and user's own
                if template.is_public or template.user_id == user_id:
                    # Apply filters
                    if subject and template.subject != subject:
                        continue
                    if grade and template.grade != grade:
                        continue
                    if type and template.type.value != type:
                        continue
                    
                    templates.append(template)
            
            # Sort by usage count and rating
            templates.sort(key=lambda x: (x.usage_count, x.rating), reverse=True)
            
            return templates
            
        except Exception as e:
            logger.error(f"Error getting activity templates: {str(e)}")
            return []
    
    def create_activity_template(self, user_id: str, template_data: Dict[str, Any]) -> ActivityTemplate:
        """Create a new activity template."""
        try:
            template = ActivityTemplate.from_dict(template_data)
            template.user_id = user_id
            template.created_at = datetime.utcnow()
            
            # Save to Firestore
            doc_ref = self.db.collection('activity_templates').document(template.id)
            doc_ref.set(template.to_dict())
            
            logger.info(f"Created activity template {template.id}")
            return template
            
        except Exception as e:
            logger.error(f"Error creating activity template: {str(e)}")
            raise
    
    def get_ai_activity_suggestions(self, user_id: str, subject: str, grade: str,
                                   available_time: int, context: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get AI-generated activity suggestions."""
        try:
            # Get user profile for personalization
            user_profile = self._get_user_profile(user_id)
            
            # Build prompt for AI
            prompt = f"""
            Generate 5 creative lesson activity suggestions for:
            - Subject: {subject}
            - Grade: {grade}
            - Available time: {available_time} minutes
            - Context: {context or 'General lesson planning'}
            - User teaches: {', '.join(user_profile.get('subjects', []))}
            
            For each activity, provide:
            1. Title (engaging and descriptive)
            2. Type (lecture, discussion, exercise, project, assessment, practical, etc.)
            3. Description (2-3 sentences)
            4. Estimated duration (realistic for the time available)
            5. Materials needed (list)
            6. Learning objectives (2-3 specific objectives)
            7. Tags (for categorization)
            
            Focus on engaging, age-appropriate activities that promote active learning.
            Consider different learning styles and make activities practical to implement.
            """
            
            # Get AI response
            ai_response = self.ai_service.generate_response(
                message=prompt,
                user_id=user_id,
                max_tokens=1500,
                temperature=0.8  # Higher creativity for suggestions
            )
            
            # Parse AI response into structured suggestions
            suggestions = self._parse_ai_activity_suggestions(ai_response, subject, grade)
            
            logger.info(f"Generated {len(suggestions)} AI activity suggestions for user {user_id}")
            return suggestions
            
        except Exception as e:
            logger.error(f"Error getting AI activity suggestions: {str(e)}")
            return self._get_fallback_activity_suggestions(subject, grade, available_time)
    
    # Scheduling and Conflict Detection
    
    def detect_conflicts(self, weekly_plan: WeeklyPlan) -> List[ScheduleConflict]:
        """Detect scheduling conflicts in a weekly plan."""
        conflicts = []
        
        for day_plan in weekly_plan.day_plans:
            conflicts.extend(self._detect_day_conflicts(day_plan))
        
        return conflicts
    
    def auto_schedule_activities(self, day_plan: DayPlan) -> DayPlan:
        """Automatically schedule activities in a day plan."""
        try:
            # Sort activities by priority/type
            activities = sorted(day_plan.activities, key=self._get_activity_priority)
            
            # Parse day times
            day_start = datetime.strptime(day_plan.day_start_time, "%H:%M").time()
            day_end = datetime.strptime(day_plan.day_end_time, "%H:%M").time()
            
            current_time = datetime.combine(day_plan.date, day_start)
            day_end_datetime = datetime.combine(day_plan.date, day_end)
            
            # Schedule each activity
            for activity in activities:
                # Check if activity fits
                activity_end = current_time + timedelta(minutes=activity.duration)
                
                if activity_end <= day_end_datetime:
                    activity.start_time = current_time.strftime("%H:%M")
                    activity.end_time = activity_end.strftime("%H:%M")
                    current_time = activity_end
                    
                    # Add break time if needed
                    current_time = self._add_break_if_needed(current_time, day_plan.break_times)
                else:
                    # Activity doesn't fit, leave unscheduled
                    activity.start_time = None
                    activity.end_time = None
            
            return day_plan
            
        except Exception as e:
            logger.error(f"Error auto-scheduling activities: {str(e)}")
            return day_plan
    
    def generate_plan_summary(self, weekly_plan: WeeklyPlan) -> PlanSummary:
        """Generate comprehensive summary of a weekly plan."""
        summary = PlanSummary()
        
        # Count activities and calculate hours
        for day_plan in weekly_plan.day_plans:
            day_total = day_plan.calculate_total_duration()
            summary.total_activities += len(day_plan.activities)
            summary.daily_hours[day_plan.date.isoformat()] = day_total / 60.0
            
            # Track subjects
            for activity in day_plan.activities:
                if activity.subject and activity.subject not in summary.subjects_covered:
                    summary.subjects_covered.append(activity.subject)
                
                # Track activity types
                activity_type = activity.type.value
                summary.activity_type_breakdown[activity_type] = \
                    summary.activity_type_breakdown.get(activity_type, 0) + 1
        
        summary.total_hours = sum(summary.daily_hours.values())
        
        # Detect conflicts
        summary.conflicts = self.detect_conflicts(weekly_plan)
        
        return summary
    
    # Helper Methods
    
    def _validate_weekly_plan(self, plan: WeeklyPlan) -> None:
        """Validate a weekly plan."""
        if not plan.title:
            raise ValueError("Plan title is required")
        
        if not plan.target_grades:
            raise ValueError("At least one target grade is required")
        
        # Validate day plans
        for day_plan in plan.day_plans:
            for activity in day_plan.activities:
                if activity.duration <= 0:
                    raise ValueError(f"Activity '{activity.title}' must have a positive duration")
    
    def _process_plan_subjects(self, plan: WeeklyPlan) -> None:
        """Extract and update subjects from activities."""
        subjects = set()
        for day_plan in plan.day_plans:
            for activity in day_plan.activities:
                if activity.subject:
                    subjects.add(activity.subject)
        plan.subjects = list(subjects)
    
    def _get_user_profile(self, user_id: str) -> Dict[str, Any]:
        """Get user profile for personalization."""
        try:
            user_ref = self.db.collection('users').document(user_id)
            user_doc = user_ref.get()
            return user_doc.to_dict() if user_doc.exists else {}
        except Exception:
            return {}
    
    def _parse_ai_activity_suggestions(self, ai_response: str, subject: str, grade: str) -> List[Dict[str, Any]]:
        """Parse AI response into structured activity suggestions."""
        suggestions = []
        
        # Simple parsing logic - in production, you might want more sophisticated parsing
        try:
            # Split by activity markers
            activities = ai_response.split('\n\n')
            
            for activity_text in activities[:5]:  # Limit to 5 suggestions
                if len(activity_text.strip()) < 50:  # Skip short entries
                    continue
                
                suggestion = {
                    'id': str(uuid.uuid4()),
                    'title': f"AI Suggested Activity for {subject}",
                    'description': activity_text.strip()[:200] + "...",
                    'type': 'exercise',
                    'subject': subject,
                    'grade': grade,
                    'estimatedDuration': 30,  # Default duration
                    'materials': ['Whiteboard', 'Textbook'],
                    'objectives': [f'Understand {subject} concepts', 'Apply learning'],
                    'tags': ['ai-generated', subject.lower()],
                    'colorCode': '#10B981',  # Green for AI suggestions
                    'source': 'ai'
                }
                suggestions.append(suggestion)
        
        except Exception as e:
            logger.error(f"Error parsing AI suggestions: {str(e)}")
        
        return suggestions if suggestions else self._get_fallback_activity_suggestions(subject, grade, 30)
    
    def _get_fallback_activity_suggestions(self, subject: str, grade: str, duration: int) -> List[Dict[str, Any]]:
        """Get fallback activity suggestions when AI fails."""
        return [
            {
                'id': str(uuid.uuid4()),
                'title': f'{subject} Review Session',
                'description': f'Interactive review of key {subject} concepts for {grade} students',
                'type': 'review',
                'subject': subject,
                'grade': grade,
                'estimatedDuration': min(duration, 45),
                'materials': ['Whiteboard', 'Textbook', 'Worksheets'],
                'objectives': [f'Review {subject} fundamentals', 'Assess understanding'],
                'tags': ['review', subject.lower()],
                'colorCode': '#6366F1',
                'source': 'template'
            }
        ]
    
    def _detect_day_conflicts(self, day_plan: DayPlan) -> List[ScheduleConflict]:
        """Detect conflicts in a single day plan."""
        conflicts = []
        
        # Check for time overlaps
        scheduled_activities = [a for a in day_plan.activities if a.start_time and a.end_time]
        
        for i, activity1 in enumerate(scheduled_activities):
            for activity2 in scheduled_activities[i+1:]:
                if self._activities_overlap(activity1, activity2):
                    conflict = ScheduleConflict(
                        type=ConflictType.TIME_OVERLAP,
                        message=f"Time overlap between '{activity1.title}' and '{activity2.title}'",
                        day_date=day_plan.date,
                        activity_ids=[activity1.id, activity2.id],
                        severity="high",
                        suggested_resolution="Adjust activity times or durations"
                    )
                    conflicts.append(conflict)
        
        # Check if total duration exceeds day length
        total_duration = sum(a.duration for a in day_plan.activities)
        day_duration = self._calculate_day_duration(day_plan)
        
        if total_duration > day_duration:
            conflict = ScheduleConflict(
                type=ConflictType.DURATION_EXCEEDED,
                message=f"Total activities ({total_duration} min) exceed day duration ({day_duration} min)",
                day_date=day_plan.date,
                activity_ids=[a.id for a in day_plan.activities],
                severity="medium",
                suggested_resolution="Reduce activity durations or move some to another day"
            )
            conflicts.append(conflict)
        
        return conflicts
    
    def _activities_overlap(self, activity1: LessonActivity, activity2: LessonActivity) -> bool:
        """Check if two activities have overlapping times."""
        try:
            start1 = datetime.strptime(activity1.start_time, "%H:%M").time()
            end1 = datetime.strptime(activity1.end_time, "%H:%M").time()
            start2 = datetime.strptime(activity2.start_time, "%H:%M").time()
            end2 = datetime.strptime(activity2.end_time, "%H:%M").time()
            
            return not (end1 <= start2 or end2 <= start1)
        except (ValueError, TypeError):
            return False
    
    def _calculate_day_duration(self, day_plan: DayPlan) -> int:
        """Calculate available minutes in a day (excluding breaks)."""
        try:
            start = datetime.strptime(day_plan.day_start_time, "%H:%M")
            end = datetime.strptime(day_plan.day_end_time, "%H:%M")
            
            total_minutes = (end - start).seconds // 60
            
            # Subtract break times
            for break_time in day_plan.break_times:
                break_start = datetime.strptime(break_time['start'], "%H:%M")
                break_end = datetime.strptime(break_time['end'], "%H:%M")
                break_duration = (break_end - break_start).seconds // 60
                total_minutes -= break_duration
            
            return total_minutes
        except (ValueError, TypeError):
            return 420  # Default 7 hours
    
    def _get_activity_priority(self, activity: LessonActivity) -> int:
        """Get priority score for activity scheduling."""
        priority_map = {
            ActivityType.ASSESSMENT: 1,
            ActivityType.LECTURE: 2,
            ActivityType.PRACTICAL: 3,
            ActivityType.DISCUSSION: 4,
            ActivityType.EXERCISE: 5,
            ActivityType.PROJECT: 6,
            ActivityType.REVIEW: 7,
            ActivityType.BREAK: 8
        }
        return priority_map.get(activity.type, 5)
    
    def _add_break_if_needed(self, current_time: datetime, break_times: List[Dict[str, str]]) -> datetime:
        """Add break time if current time falls within a break period."""
        current_time_str = current_time.strftime("%H:%M")
        
        for break_time in break_times:
            if break_time['start'] <= current_time_str <= break_time['end']:
                break_end = datetime.strptime(break_time['end'], "%H:%M").time()
                return datetime.combine(current_time.date(), break_end)
        
        return current_time
