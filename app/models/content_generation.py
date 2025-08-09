"""
Content Generation Models
Data models for the comprehensive content generation system.
"""

from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Dict, List, Optional, Any, Union
from enum import Enum
import uuid

class ContentType(Enum):
    """Types of content that can be generated."""
    STORY = "story"
    WORKSHEET = "worksheet"
    QUIZ = "quiz"
    LESSON_PLAN = "lesson_plan"
    VISUAL_AID = "visual_aid"

class Subject(Enum):
    """Academic subjects."""
    MATH = "math"
    SCIENCE = "science"
    ENGLISH = "english"
    SOCIAL_STUDIES = "social_studies"
    HINDI = "hindi"
    MARATHI = "marathi"
    GUJARATI = "gujarati"
    TAMIL = "tamil"

class Grade(Enum):
    """Academic grade levels."""
    GRADE1 = "grade1"
    GRADE2 = "grade2"
    GRADE3 = "grade3"
    GRADE4 = "grade4"
    GRADE5 = "grade5"
    GRADE6 = "grade6"
    GRADE7 = "grade7"
    GRADE8 = "grade8"
    GRADE9 = "grade9"
    GRADE10 = "grade10"
    GRADE11 = "grade11"
    GRADE12 = "grade12"

class ContentLength(Enum):
    """Content length options."""
    SHORT = "short"
    MEDIUM = "medium"
    LONG = "long"

class Difficulty(Enum):
    """Difficulty levels."""
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"

class Language(Enum):
    """Supported languages."""
    ENGLISH = "en"
    HINDI = "hi"
    MARATHI = "mr"
    GUJARATI = "gu"
    TAMIL = "ta"

class ExportFormat(Enum):
    """Export format options."""
    PDF = "pdf"
    DOCX = "docx"
    HTML = "html"
    JSON = "json"

class QualityScore(Enum):
    """Quality assessment scores."""
    EXCELLENT = "excellent"
    GOOD = "good"
    FAIR = "fair"
    NEEDS_IMPROVEMENT = "needs_improvement"

@dataclass
class ContentParameters:
    """Parameters for content generation."""
    subject: str
    grade: str
    topic: str
    length: str = "medium"
    difficulty: str = "medium"
    language: str = "en"
    include_images: bool = False
    custom_instructions: Optional[str] = None
    
    # Story-specific parameters
    include_moral: Optional[bool] = None
    character_names: Optional[List[str]] = None
    setting: Optional[str] = None
    
    # Worksheet-specific parameters
    number_of_problems: Optional[int] = None
    include_solutions: Optional[bool] = True
    include_answer_key: Optional[bool] = True
    
    # Quiz-specific parameters
    number_of_questions: Optional[int] = None
    question_types: Optional[List[str]] = None  # ["mcq", "true_false", "fill_blanks", "essay"]
    include_explanations: Optional[bool] = True
    
    # Visual aid-specific parameters
    diagram_type: Optional[str] = None
    color_scheme: Optional[str] = None
    include_labels: Optional[bool] = True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ContentParameters':
        """Create from dictionary."""
        return cls(**data)

@dataclass
class StoryContent:
    """Story content structure."""
    title: str
    characters: List[str]
    setting: str
    plot: str
    moral: Optional[str] = None
    decision_points: Optional[List[Dict[str, Any]]] = None
    vocabulary_words: Optional[List[Dict[str, str]]] = None  # word: definition
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'StoryContent':
        """Create from dictionary."""
        return cls(**data)

@dataclass
class WorksheetContent:
    """Worksheet content structure."""
    title: str
    instructions: str
    problems: List[Dict[str, Any]]
    answer_key: Optional[List[Dict[str, Any]]] = None
    solutions: Optional[List[Dict[str, Any]]] = None
    additional_resources: Optional[List[str]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'WorksheetContent':
        """Create from dictionary."""
        return cls(**data)

@dataclass
class QuizContent:
    """Quiz content structure."""
    title: str
    instructions: str
    questions: List[Dict[str, Any]]
    answer_key: List[Dict[str, Any]]
    scoring_rubric: Optional[Dict[str, Any]] = None
    time_limit: Optional[int] = None  # in minutes
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'QuizContent':
        """Create from dictionary."""
        return cls(**data)

@dataclass
class LessonPlanContent:
    """Lesson plan content structure."""
    title: str
    objectives: List[str]
    materials: List[str]
    duration: int  # in minutes
    introduction: str
    main_activities: List[Dict[str, Any]]
    assessment: str
    homework: Optional[str] = None
    differentiation: Optional[List[str]] = None
    extensions: Optional[List[str]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'LessonPlanContent':
        """Create from dictionary."""
        return cls(**data)

@dataclass
class VisualAidContent:
    """Visual aid content structure."""
    title: str
    description: str
    elements: List[Dict[str, Any]]  # shapes, text, images
    svg_content: Optional[str] = None
    drawing_instructions: Optional[List[str]] = None
    color_palette: Optional[List[str]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'VisualAidContent':
        """Create from dictionary."""
        return cls(**data)

@dataclass
class QualityAssessment:
    """Quality assessment for generated content."""
    overall_score: str  # QualityScore enum value
    criteria_scores: Dict[str, int]  # 1-5 scale for different criteria
    strengths: List[str]
    improvements: List[str]
    suggestions: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'QualityAssessment':
        """Create from dictionary."""
        return cls(**data)

@dataclass
class GeneratedContent:
    """Main content generation result."""
    id: str
    user_id: str
    content_type: str
    parameters: ContentParameters
    content: Union[StoryContent, WorksheetContent, QuizContent, LessonPlanContent, VisualAidContent]
    quality_assessment: Optional[QualityAssessment] = None
    generation_time: Optional[float] = None  # seconds
    word_count: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    def __post_init__(self):
        """Initialize after creation."""
        if not self.id:
            self.id = str(uuid.uuid4())
        if not self.created_at:
            self.created_at = datetime.utcnow()
        if not self.updated_at:
            self.updated_at = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = asdict(self)
        # Convert datetime objects to ISO format
        if self.created_at:
            data['created_at'] = self.created_at.isoformat()
        if self.updated_at:
            data['updated_at'] = self.updated_at.isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'GeneratedContent':
        """Create from dictionary."""
        # Convert ISO format strings back to datetime
        if 'created_at' in data and isinstance(data['created_at'], str):
            data['created_at'] = datetime.fromisoformat(data['created_at'])
        if 'updated_at' in data and isinstance(data['updated_at'], str):
            data['updated_at'] = datetime.fromisoformat(data['updated_at'])
        
        # Convert parameters
        if 'parameters' in data and isinstance(data['parameters'], dict):
            data['parameters'] = ContentParameters.from_dict(data['parameters'])
        
        # Convert content based on type
        if 'content' in data and isinstance(data['content'], dict):
            content_type = data.get('content_type')
            if content_type == ContentType.STORY.value:
                data['content'] = StoryContent.from_dict(data['content'])
            elif content_type == ContentType.WORKSHEET.value:
                data['content'] = WorksheetContent.from_dict(data['content'])
            elif content_type == ContentType.QUIZ.value:
                data['content'] = QuizContent.from_dict(data['content'])
            elif content_type == ContentType.LESSON_PLAN.value:
                data['content'] = LessonPlanContent.from_dict(data['content'])
            elif content_type == ContentType.VISUAL_AID.value:
                data['content'] = VisualAidContent.from_dict(data['content'])
        
        # Convert quality assessment
        if 'quality_assessment' in data and isinstance(data['quality_assessment'], dict):
            data['quality_assessment'] = QualityAssessment.from_dict(data['quality_assessment'])
        
        return cls(**data)

@dataclass
class ContentVariant:
    """Variant of generated content."""
    id: str
    parent_id: str
    variant_number: int
    parameters: ContentParameters
    content: Union[StoryContent, WorksheetContent, QuizContent, LessonPlanContent, VisualAidContent]
    created_at: Optional[datetime] = None
    
    def __post_init__(self):
        """Initialize after creation."""
        if not self.id:
            self.id = str(uuid.uuid4())
        if not self.created_at:
            self.created_at = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = asdict(self)
        if self.created_at:
            data['created_at'] = self.created_at.isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ContentVariant':
        """Create from dictionary."""
        if 'created_at' in data and isinstance(data['created_at'], str):
            data['created_at'] = datetime.fromisoformat(data['created_at'])
        
        if 'parameters' in data and isinstance(data['parameters'], dict):
            data['parameters'] = ContentParameters.from_dict(data['parameters'])
        
        return cls(**data)

@dataclass
class ExportRequest:
    """Export request for generated content."""
    content_id: str
    format: str
    include_solutions: bool = True
    include_images: bool = True
    custom_styling: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ExportRequest':
        """Create from dictionary."""
        return cls(**data)

# Content generation templates for different subjects and grades
CONTENT_TEMPLATES = {
    "story": {
        "primary": {
            "structure": ["introduction", "problem", "solution", "moral"],
            "length_guidelines": {
                "short": "200-400 words",
                "medium": "400-800 words", 
                "long": "800-1200 words"
            }
        },
        "secondary": {
            "structure": ["setting", "characters", "conflict", "climax", "resolution"],
            "length_guidelines": {
                "short": "400-600 words",
                "medium": "600-1000 words",
                "long": "1000-1500 words"
            }
        }
    },
    "worksheet": {
        "math": {
            "problem_types": ["arithmetic", "word_problems", "geometry", "algebra"],
            "solution_format": "step_by_step"
        },
        "science": {
            "activity_types": ["experiments", "observations", "diagrams", "analysis"],
            "include_safety": True
        },
        "language": {
            "exercise_types": ["grammar", "vocabulary", "comprehension", "writing"],
            "skill_levels": ["basic", "intermediate", "advanced"]
        }
    },
    "quiz": {
        "question_distribution": {
            "mcq": 0.5,
            "true_false": 0.2,
            "fill_blanks": 0.2,
            "essay": 0.1
        },
        "difficulty_distribution": {
            "easy": 0.3,
            "medium": 0.5,
            "hard": 0.2
        }
    }
}

# Cultural context for Indian education system
CULTURAL_CONTEXT = {
    "festivals": ["Diwali", "Holi", "Dussehra", "Eid", "Christmas", "Pongal"],
    "values": ["respect for elders", "helping others", "honesty", "hard work", "unity in diversity"],
    "settings": ["village", "city", "school", "home", "market", "temple", "park"],
    "character_names": {
        "hindi": ["Arjun", "Priya", "Ravi", "Meera", "Karan", "Anita"],
        "regional": ["Aarav", "Diya", "Vivaan", "Saanvi", "Ishaan", "Aanya"]
    }
}
