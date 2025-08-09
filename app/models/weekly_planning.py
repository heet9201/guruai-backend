"""
Weekly Planning Data Models
Comprehensive data models for weekly lesson planning system with templates and activities.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from datetime import datetime, date
from enum import Enum
import uuid

class ActivityType(Enum):
    """Types of lesson activities."""
    LECTURE = "lecture"
    DISCUSSION = "discussion"
    EXERCISE = "exercise"
    PROJECT = "project"
    ASSESSMENT = "assessment"
    BREAK = "break"
    REVIEW = "review"
    PRACTICAL = "practical"
    PRESENTATION = "presentation"
    GROUP_WORK = "group_work"

class TemplateCategory(Enum):
    """Categories for weekly plan templates."""
    GENERAL = "general"
    SUBJECT_SPECIFIC = "subject_specific"
    GRADE_SPECIFIC = "grade_specific"
    SEASONAL = "seasonal"
    EXAM_PREP = "exam_prep"
    PROJECT_BASED = "project_based"
    COMMUNITY = "community"

class ConflictType(Enum):
    """Types of scheduling conflicts."""
    TIME_OVERLAP = "time_overlap"
    RESOURCE_CONFLICT = "resource_conflict"
    DURATION_EXCEEDED = "duration_exceeded"
    BREAK_VIOLATED = "break_violated"

@dataclass
class LessonActivity:
    """Individual lesson activity within a day plan."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    title: str = ""
    description: str = ""
    type: ActivityType = ActivityType.LECTURE
    subject: str = ""
    grade: str = ""
    duration: int = 0  # Duration in minutes
    materials: List[str] = field(default_factory=list)
    objectives: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    color_code: str = "#4F46E5"  # Default indigo color
    start_time: Optional[str] = None  # HH:MM format
    end_time: Optional[str] = None  # HH:MM format
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'type': self.type.value,
            'subject': self.subject,
            'grade': self.grade,
            'duration': self.duration,
            'materials': self.materials,
            'objectives': self.objectives,
            'tags': self.tags,
            'colorCode': self.color_code,
            'startTime': self.start_time,
            'endTime': self.end_time,
            'createdAt': self.created_at.isoformat() + 'Z' if self.created_at else None,
            'updatedAt': self.updated_at.isoformat() + 'Z' if self.updated_at else None
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'LessonActivity':
        """Create from dictionary."""
        activity = cls()
        activity.id = data.get('id', str(uuid.uuid4()))
        activity.title = data.get('title', '')
        activity.description = data.get('description', '')
        activity.type = ActivityType(data.get('type', ActivityType.LECTURE.value))
        activity.subject = data.get('subject', '')
        activity.grade = data.get('grade', '')
        activity.duration = data.get('duration', 0)
        activity.materials = data.get('materials', [])
        activity.objectives = data.get('objectives', [])
        activity.tags = data.get('tags', [])
        activity.color_code = data.get('colorCode', '#4F46E5')
        activity.start_time = data.get('startTime')
        activity.end_time = data.get('endTime')
        
        # Parse timestamps
        if data.get('createdAt'):
            activity.created_at = datetime.fromisoformat(data['createdAt'].replace('Z', '+00:00'))
        if data.get('updatedAt'):
            activity.updated_at = datetime.fromisoformat(data['updatedAt'].replace('Z', '+00:00'))
            
        return activity

@dataclass
class DayPlan:
    """Plan for a single day containing activities and notes."""
    date: date = field(default_factory=date.today)
    activities: List[LessonActivity] = field(default_factory=list)
    notes: str = ""
    total_duration: int = 0  # Calculated total duration in minutes
    day_start_time: str = "08:00"  # School day start time
    day_end_time: str = "15:00"   # School day end time
    break_times: List[Dict[str, str]] = field(default_factory=lambda: [
        {"start": "10:30", "end": "10:45", "name": "Morning Break"},
        {"start": "12:30", "end": "13:15", "name": "Lunch Break"}
    ])
    
    def calculate_total_duration(self) -> int:
        """Calculate total duration of all activities."""
        self.total_duration = sum(activity.duration for activity in self.activities)
        return self.total_duration
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'date': self.date.isoformat(),
            'activities': [activity.to_dict() for activity in self.activities],
            'notes': self.notes,
            'totalDuration': self.calculate_total_duration(),
            'dayStartTime': self.day_start_time,
            'dayEndTime': self.day_end_time,
            'breakTimes': self.break_times
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DayPlan':
        """Create from dictionary."""
        day_plan = cls()
        day_plan.date = date.fromisoformat(data.get('date', date.today().isoformat()))
        day_plan.activities = [
            LessonActivity.from_dict(activity_data) 
            for activity_data in data.get('activities', [])
        ]
        day_plan.notes = data.get('notes', '')
        day_plan.total_duration = data.get('totalDuration', 0)
        day_plan.day_start_time = data.get('dayStartTime', '08:00')
        day_plan.day_end_time = data.get('dayEndTime', '15:00')
        day_plan.break_times = data.get('breakTimes', [])
        return day_plan

@dataclass
class WeeklyPlan:
    """Weekly lesson plan containing multiple day plans."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    week_start: date = field(default_factory=date.today)
    title: str = ""
    description: str = ""
    target_grades: List[str] = field(default_factory=list)
    day_plans: List[DayPlan] = field(default_factory=list)
    is_template: bool = False
    template_category: Optional[TemplateCategory] = None
    user_id: str = ""
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    tags: List[str] = field(default_factory=list)
    subjects: List[str] = field(default_factory=list)
    total_hours: float = 0.0  # Total planned hours for the week
    
    def calculate_total_hours(self) -> float:
        """Calculate total hours across all days."""
        total_minutes = sum(day.calculate_total_duration() for day in self.day_plans)
        self.total_hours = total_minutes / 60.0
        return self.total_hours
    
    def get_week_end(self) -> date:
        """Get the end date of the week."""
        from datetime import timedelta
        return self.week_start + timedelta(days=6)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'id': self.id,
            'weekStart': self.week_start.isoformat(),
            'weekEnd': self.get_week_end().isoformat(),
            'title': self.title,
            'description': self.description,
            'targetGrades': self.target_grades,
            'dayPlans': [day.to_dict() for day in self.day_plans],
            'isTemplate': self.is_template,
            'templateCategory': self.template_category.value if self.template_category else None,
            'userId': self.user_id,
            'createdAt': self.created_at.isoformat() + 'Z' if self.created_at else None,
            'updatedAt': self.updated_at.isoformat() + 'Z' if self.updated_at else None,
            'tags': self.tags,
            'subjects': self.subjects,
            'totalHours': self.calculate_total_hours()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'WeeklyPlan':
        """Create from dictionary."""
        plan = cls()
        plan.id = data.get('id', str(uuid.uuid4()))
        plan.week_start = date.fromisoformat(data.get('weekStart', date.today().isoformat()))
        plan.title = data.get('title', '')
        plan.description = data.get('description', '')
        plan.target_grades = data.get('targetGrades', [])
        plan.day_plans = [
            DayPlan.from_dict(day_data) 
            for day_data in data.get('dayPlans', [])
        ]
        plan.is_template = data.get('isTemplate', False)
        
        # Handle template category
        template_cat = data.get('templateCategory')
        plan.template_category = TemplateCategory(template_cat) if template_cat else None
        
        plan.user_id = data.get('userId', '')
        plan.tags = data.get('tags', [])
        plan.subjects = data.get('subjects', [])
        plan.total_hours = data.get('totalHours', 0.0)
        
        # Parse timestamps
        if data.get('createdAt'):
            plan.created_at = datetime.fromisoformat(data['createdAt'].replace('Z', '+00:00'))
        if data.get('updatedAt'):
            plan.updated_at = datetime.fromisoformat(data['updatedAt'].replace('Z', '+00:00'))
            
        return plan

@dataclass
class ActivityTemplate:
    """Template for lesson activities that can be reused."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    title: str = ""
    description: str = ""
    type: ActivityType = ActivityType.LECTURE
    subject: str = ""
    grade: str = ""
    estimated_duration: int = 0  # Estimated duration in minutes
    materials: List[str] = field(default_factory=list)
    objectives: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    color_code: str = "#4F46E5"
    difficulty_level: str = "medium"  # easy, medium, hard
    is_public: bool = False  # Available to all users
    user_id: str = ""
    usage_count: int = 0
    rating: float = 0.0
    created_at: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'type': self.type.value,
            'subject': self.subject,
            'grade': self.grade,
            'estimatedDuration': self.estimated_duration,
            'materials': self.materials,
            'objectives': self.objectives,
            'tags': self.tags,
            'colorCode': self.color_code,
            'difficultyLevel': self.difficulty_level,
            'isPublic': self.is_public,
            'userId': self.user_id,
            'usageCount': self.usage_count,
            'rating': self.rating,
            'createdAt': self.created_at.isoformat() + 'Z' if self.created_at else None
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ActivityTemplate':
        """Create from dictionary."""
        template = cls()
        template.id = data.get('id', str(uuid.uuid4()))
        template.title = data.get('title', '')
        template.description = data.get('description', '')
        template.type = ActivityType(data.get('type', ActivityType.LECTURE.value))
        template.subject = data.get('subject', '')
        template.grade = data.get('grade', '')
        template.estimated_duration = data.get('estimatedDuration', 0)
        template.materials = data.get('materials', [])
        template.objectives = data.get('objectives', [])
        template.tags = data.get('tags', [])
        template.color_code = data.get('colorCode', '#4F46E5')
        template.difficulty_level = data.get('difficultyLevel', 'medium')
        template.is_public = data.get('isPublic', False)
        template.user_id = data.get('userId', '')
        template.usage_count = data.get('usageCount', 0)
        template.rating = data.get('rating', 0.0)
        
        # Parse timestamp
        if data.get('createdAt'):
            template.created_at = datetime.fromisoformat(data['createdAt'].replace('Z', '+00:00'))
            
        return template

@dataclass
class ScheduleConflict:
    """Represents a scheduling conflict in a weekly plan."""
    type: ConflictType
    message: str
    day_date: date
    activity_ids: List[str]
    severity: str = "medium"  # low, medium, high
    suggested_resolution: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'type': self.type.value,
            'message': self.message,
            'dayDate': self.day_date.isoformat(),
            'activityIds': self.activity_ids,
            'severity': self.severity,
            'suggestedResolution': self.suggested_resolution
        }

@dataclass
class PlanSummary:
    """Summary statistics for a weekly plan."""
    total_activities: int = 0
    total_hours: float = 0.0
    subjects_covered: List[str] = field(default_factory=list)
    activity_type_breakdown: Dict[str, int] = field(default_factory=dict)
    daily_hours: Dict[str, float] = field(default_factory=dict)  # date -> hours
    conflicts: List[ScheduleConflict] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'totalActivities': self.total_activities,
            'totalHours': self.total_hours,
            'subjectsCovered': self.subjects_covered,
            'activityTypeBreakdown': self.activity_type_breakdown,
            'dailyHours': self.daily_hours,
            'conflicts': [conflict.to_dict() for conflict in self.conflicts]
        }
