"""
Dashboard Service for Analytics and User Activity Tracking
Provides comprehensive dashboard data including stats, activities, and AI recommendations.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum
import uuid

from google.cloud import firestore
from app.services.firebase_auth_service import FirebaseAuthService

logger = logging.getLogger(__name__)

class ActivityType(Enum):
    CHAT = "chat"
    CONTENT = "content"
    LESSON = "lesson"
    ANALYSIS = "analysis"
    PLANNING = "planning"

class RecommendationPriority(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

@dataclass
class ActivityRecord:
    """Represents a user activity record."""
    id: str
    user_id: str
    type: ActivityType
    title: str
    description: str
    metadata: Dict[str, Any]
    timestamp: datetime
    duration_seconds: Optional[int] = None

@dataclass
class WeeklyStats:
    """Weekly statistics for dashboard overview."""
    total_chats: int
    content_generated: int
    lessons_prepared: int
    time_spent: int  # in minutes
    
@dataclass
class RecentActivity:
    """Recent activity for dashboard display."""
    id: str
    type: str
    title: str
    timestamp: str

@dataclass
class Recommendation:
    """AI-powered recommendation."""
    id: str
    title: str
    description: str
    action_url: str
    priority: str

class DashboardService:
    """Service for managing dashboard data and analytics."""
    
    def __init__(self):
        """Initialize the dashboard service."""
        self.db = firestore.Client()
        self.firebase_auth = FirebaseAuthService()
        
    def track_activity(self, user_id: str, activity_type: ActivityType, 
                      title: str, description: str = "", 
                      metadata: Dict[str, Any] = None,
                      duration_seconds: Optional[int] = None) -> str:
        """
        Track user activity for analytics.
        
        Args:
            user_id: User identifier
            activity_type: Type of activity
            title: Activity title
            description: Activity description
            metadata: Additional activity metadata
            duration_seconds: Duration of activity in seconds
            
        Returns:
            Activity ID
        """
        try:
            activity_id = str(uuid.uuid4())
            activity = ActivityRecord(
                id=activity_id,
                user_id=user_id,
                type=activity_type,
                title=title,
                description=description,
                metadata=metadata or {},
                timestamp=datetime.utcnow(),
                duration_seconds=duration_seconds
            )
            
            # Store in Firestore
            activity_ref = self.db.collection('user_activities').document(activity_id)
            activity_ref.set({
                'id': activity.id,
                'user_id': activity.user_id,
                'type': activity.type.value,
                'title': activity.title,
                'description': activity.description,
                'metadata': activity.metadata,
                'timestamp': activity.timestamp,
                'duration_seconds': activity.duration_seconds,
                'created_at': firestore.SERVER_TIMESTAMP
            })
            
            logger.info(f"Activity tracked: {activity_id} for user {user_id}")
            return activity_id
            
        except Exception as e:
            logger.error(f"Error tracking activity: {str(e)}")
            raise

    def get_weekly_stats(self, user_id: str) -> WeeklyStats:
        """
        Get weekly statistics for a user.
        
        Args:
            user_id: User identifier
            
        Returns:
            WeeklyStats object
        """
        try:
            # Calculate date range for the current week
            now = datetime.utcnow()
            week_start = now - timedelta(days=now.weekday())
            week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)
            
            # Query activities for the week
            activities_ref = self.db.collection('user_activities')
            query = activities_ref.where('user_id', '==', user_id)\
                                 .where('timestamp', '>=', week_start)\
                                 .where('timestamp', '<=', now)
            
            activities = query.stream()
            
            # Calculate statistics
            total_chats = 0
            content_generated = 0
            lessons_prepared = 0
            total_time_seconds = 0
            
            for activity_doc in activities:
                activity_data = activity_doc.to_dict()
                activity_type = activity_data.get('type', '')
                duration = activity_data.get('duration_seconds', 0) or 0
                
                if activity_type == ActivityType.CHAT.value:
                    total_chats += 1
                elif activity_type == ActivityType.CONTENT.value:
                    content_generated += 1
                elif activity_type == ActivityType.LESSON.value:
                    lessons_prepared += 1
                
                total_time_seconds += duration
            
            # Convert time to minutes
            time_spent_minutes = total_time_seconds // 60
            
            return WeeklyStats(
                total_chats=total_chats,
                content_generated=content_generated,
                lessons_prepared=lessons_prepared,
                time_spent=time_spent_minutes
            )
            
        except Exception as e:
            logger.error(f"Error getting weekly stats: {str(e)}")
            # Return default stats on error
            return WeeklyStats(
                total_chats=0,
                content_generated=0,
                lessons_prepared=0,
                time_spent=0
            )

    def get_recent_activities(self, user_id: str, limit: int = 10) -> List[RecentActivity]:
        """
        Get recent activities for a user.
        
        Args:
            user_id: User identifier
            limit: Maximum number of activities to return
            
        Returns:
            List of RecentActivity objects
        """
        try:
            activities_ref = self.db.collection('user_activities')
            query = activities_ref.where('user_id', '==', user_id)\
                                 .order_by('timestamp', direction=firestore.Query.DESCENDING)\
                                 .limit(limit)
            
            activities = query.stream()
            recent_activities = []
            
            for activity_doc in activities:
                activity_data = activity_doc.to_dict()
                recent_activity = RecentActivity(
                    id=activity_data.get('id', ''),
                    type=activity_data.get('type', ''),
                    title=activity_data.get('title', ''),
                    timestamp=activity_data.get('timestamp', datetime.utcnow()).isoformat() + 'Z'
                )
                recent_activities.append(recent_activity)
            
            return recent_activities
            
        except Exception as e:
            logger.error(f"Error getting recent activities: {str(e)}")
            return []

    def get_analytics_data(self, user_id: str, period: str = 'week', 
                          start_date: Optional[datetime] = None,
                          end_date: Optional[datetime] = None) -> Dict[str, Any]:
        """
        Get comprehensive analytics data for a user.
        
        Args:
            user_id: User identifier
            period: Analytics period (week, month, quarter, year)
            start_date: Custom start date
            end_date: Custom end date
            
        Returns:
            Analytics data dictionary
        """
        try:
            # Calculate date range based on period
            now = datetime.utcnow()
            
            if start_date and end_date:
                # Use custom date range
                query_start = start_date
                query_end = end_date
            else:
                # Calculate based on period
                if period == 'week':
                    query_start = now - timedelta(days=7)
                elif period == 'month':
                    query_start = now - timedelta(days=30)
                elif period == 'quarter':
                    query_start = now - timedelta(days=90)
                elif period == 'year':
                    query_start = now - timedelta(days=365)
                else:
                    query_start = now - timedelta(days=7)  # Default to week
                
                query_end = now
            
            # Query activities for the period
            activities_ref = self.db.collection('user_activities')
            query = activities_ref.where('user_id', '==', user_id)\
                                 .where('timestamp', '>=', query_start)\
                                 .where('timestamp', '<=', query_end)
            
            activities = query.stream()
            
            # Initialize analytics data
            analytics = {
                'period': period,
                'start_date': query_start.isoformat() + 'Z',
                'end_date': query_end.isoformat() + 'Z',
                'total_activities': 0,
                'activity_breakdown': {
                    'chat': 0,
                    'content': 0,
                    'lesson': 0,
                    'analysis': 0,
                    'planning': 0
                },
                'daily_activity': {},
                'peak_hours': {},
                'total_time_spent': 0,
                'average_session_duration': 0,
                'most_active_day': '',
                'productivity_score': 0,
                'feature_usage': {}
            }
            
            activities_list = []
            total_duration = 0
            daily_counts = {}
            hourly_counts = {}
            
            # Process activities
            for activity_doc in activities:
                activity_data = activity_doc.to_dict()
                activities_list.append(activity_data)
                
                activity_type = activity_data.get('type', '')
                timestamp = activity_data.get('timestamp', now)
                duration = activity_data.get('duration_seconds', 0) or 0
                
                # Count by type
                if activity_type in analytics['activity_breakdown']:
                    analytics['activity_breakdown'][activity_type] += 1
                
                # Daily activity tracking
                day_key = timestamp.strftime('%Y-%m-%d')
                daily_counts[day_key] = daily_counts.get(day_key, 0) + 1
                
                # Hourly activity tracking
                hour_key = str(timestamp.hour)
                hourly_counts[hour_key] = hourly_counts.get(hour_key, 0) + 1
                
                # Total duration
                total_duration += duration
                
                # Feature usage tracking
                feature = activity_data.get('metadata', {}).get('feature', 'unknown')
                analytics['feature_usage'][feature] = analytics['feature_usage'].get(feature, 0) + 1
            
            # Calculate derived metrics
            analytics['total_activities'] = len(activities_list)
            analytics['daily_activity'] = daily_counts
            analytics['peak_hours'] = hourly_counts
            analytics['total_time_spent'] = total_duration // 60  # Convert to minutes
            
            if activities_list:
                analytics['average_session_duration'] = (total_duration // len(activities_list)) // 60
            
            # Find most active day
            if daily_counts:
                analytics['most_active_day'] = max(daily_counts, key=daily_counts.get)
            
            # Calculate productivity score (0-100)
            analytics['productivity_score'] = self._calculate_productivity_score(analytics)
            
            return analytics
            
        except Exception as e:
            logger.error(f"Error getting analytics data: {str(e)}")
            return self._get_default_analytics()

    def generate_ai_recommendations(self, user_id: str) -> List[Recommendation]:
        """
        Generate AI-powered personalized recommendations.
        
        Args:
            user_id: User identifier
            
        Returns:
            List of Recommendation objects
        """
        try:
            # Get user profile and recent activities
            user_profile = self._get_user_profile(user_id)
            weekly_stats = self.get_weekly_stats(user_id)
            recent_activities = self.get_recent_activities(user_id, limit=20)
            
            recommendations = []
            
            # Analyze usage patterns and generate recommendations
            
            # 1. Low activity recommendation
            if weekly_stats.total_chats < 5:
                recommendations.append(Recommendation(
                    id=str(uuid.uuid4()),
                    title="Explore AI Chat Features",
                    description="Try our AI assistant to help with lesson planning and content creation",
                    action_url="/chat",
                    priority=RecommendationPriority.HIGH.value
                ))
            
            # 2. Content generation recommendation
            if weekly_stats.content_generated < 3:
                recommendations.append(Recommendation(
                    id=str(uuid.uuid4()),
                    title="Generate More Content",
                    description="Use our content generator to create engaging materials for your students",
                    action_url="/content-generator",
                    priority=RecommendationPriority.MEDIUM.value
                ))
            
            # 3. Lesson planning recommendation
            if weekly_stats.lessons_prepared < 2:
                recommendations.append(Recommendation(
                    id=str(uuid.uuid4()),
                    title="Try Weekly Lesson Planner",
                    description="Organize your lessons efficiently with our AI-powered planner",
                    action_url="/lesson-planner",
                    priority=RecommendationPriority.HIGH.value
                ))
            
            # 4. Subject-specific recommendations based on user profile
            user_subjects = user_profile.get('subjects', [])
            if 'Math' in user_subjects:
                recommendations.append(Recommendation(
                    id=str(uuid.uuid4()),
                    title="Math Problem Generator",
                    description="Create custom math problems for your students",
                    action_url="/math-generator",
                    priority=RecommendationPriority.MEDIUM.value
                ))
            
            if 'Science' in user_subjects:
                recommendations.append(Recommendation(
                    id=str(uuid.uuid4()),
                    title="Science Experiment Ideas",
                    description="Discover engaging science experiments for your classroom",
                    action_url="/science-experiments",
                    priority=RecommendationPriority.MEDIUM.value
                ))
            
            # 5. Time-based recommendations
            if weekly_stats.time_spent < 60:  # Less than 1 hour per week
                recommendations.append(Recommendation(
                    id=str(uuid.uuid4()),
                    title="Quick Start Guide",
                    description="Learn how to make the most of Sahayak AI in just 10 minutes",
                    action_url="/quick-start",
                    priority=RecommendationPriority.HIGH.value
                ))
            
            # 6. Feature discovery recommendations
            activity_types = {activity.type for activity in recent_activities}
            if 'analysis' not in activity_types:
                recommendations.append(Recommendation(
                    id=str(uuid.uuid4()),
                    title="Try Image Analysis",
                    description="Upload worksheets or student work for AI-powered analysis",
                    action_url="/image-analysis",
                    priority=RecommendationPriority.LOW.value
                ))
            
            # Limit to top 5 recommendations
            return recommendations[:5]
            
        except Exception as e:
            logger.error(f"Error generating AI recommendations: {str(e)}")
            return self._get_default_recommendations()

    def _get_user_profile(self, user_id: str) -> Dict[str, Any]:
        """Get user profile data."""
        try:
            user_ref = self.db.collection('users').document(user_id)
            user_doc = user_ref.get()
            if user_doc.exists:
                return user_doc.to_dict()
            return {}
        except Exception as e:
            logger.error(f"Error getting user profile: {str(e)}")
            return {}

    def _calculate_productivity_score(self, analytics: Dict[str, Any]) -> int:
        """Calculate productivity score based on activity patterns."""
        try:
            score = 50  # Base score
            
            # Activity frequency (up to 30 points)
            total_activities = analytics.get('total_activities', 0)
            if total_activities > 0:
                # 1 point per activity, max 30
                score += min(total_activities, 30)
            
            # Time spent (up to 20 points)
            time_spent = analytics.get('total_time_spent', 0)
            if time_spent > 0:
                # 1 point per 5 minutes, max 20
                score += min(time_spent // 5, 20)
            
            # Activity diversity (up to 20 points)
            activity_breakdown = analytics.get('activity_breakdown', {})
            active_types = sum(1 for count in activity_breakdown.values() if count > 0)
            score += active_types * 4  # 4 points per active type
            
            # Cap at 100
            return min(score, 100)
            
        except Exception as e:
            logger.error(f"Error calculating productivity score: {str(e)}")
            return 50

    def _get_default_analytics(self) -> Dict[str, Any]:
        """Return default analytics data."""
        return {
            'period': 'week',
            'start_date': (datetime.utcnow() - timedelta(days=7)).isoformat() + 'Z',
            'end_date': datetime.utcnow().isoformat() + 'Z',
            'total_activities': 0,
            'activity_breakdown': {
                'chat': 0,
                'content': 0,
                'lesson': 0,
                'analysis': 0,
                'planning': 0
            },
            'daily_activity': {},
            'peak_hours': {},
            'total_time_spent': 0,
            'average_session_duration': 0,
            'most_active_day': '',
            'productivity_score': 50,
            'feature_usage': {}
        }

    def _get_default_recommendations(self) -> List[Recommendation]:
        """Return default recommendations."""
        return [
            Recommendation(
                id=str(uuid.uuid4()),
                title="Get Started with AI Chat",
                description="Explore our AI assistant for lesson planning and content creation",
                action_url="/chat",
                priority=RecommendationPriority.HIGH.value
            ),
            Recommendation(
                id=str(uuid.uuid4()),
                title="Try Content Generator",
                description="Create engaging educational materials with AI assistance",
                action_url="/content-generator",
                priority=RecommendationPriority.MEDIUM.value
            )
        ]
