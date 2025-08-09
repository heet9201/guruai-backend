"""
Default Activity Templates
Predefined activity templates for different subjects and grades.
"""

from datetime import datetime
from typing import List, Dict
import uuid

from app.models.weekly_planning import ActivityTemplate, ActivityType, TemplateCategory

def get_default_activity_templates() -> List[ActivityTemplate]:
    """Get a collection of default activity templates."""
    
    templates = []
    
    # Math Templates
    templates.extend([
        ActivityTemplate(
            id=str(uuid.uuid4()),
            title="Basic Arithmetic Practice",
            description="Interactive practice session for addition, subtraction, multiplication, and division with visual aids and games.",
            type=ActivityType.EXERCISE,
            subject="Mathematics",
            grade="1-3",
            estimated_duration=30,
            materials=["Math manipulatives", "Whiteboard", "Worksheets", "Counting blocks"],
            objectives=[
                "Master basic arithmetic operations",
                "Improve calculation speed and accuracy",
                "Develop number sense"
            ],
            tags=["arithmetic", "basic-math", "interactive", "visual-learning"],
            difficulty_level="beginner",
            is_public=True,
            user_id="",
            rating=4.5,
            usage_count=150,
            category=TemplateCategory.SUBJECT_SPECIFIC,
            created_at=datetime.utcnow()
        ),
        
        ActivityTemplate(
            id=str(uuid.uuid4()),
            title="Algebra Problem Solving",
            description="Structured approach to solving linear equations with step-by-step demonstrations and guided practice.",
            type=ActivityType.LECTURE,
            subject="Mathematics",
            grade="7-9",
            estimated_duration=45,
            materials=["Graphing calculator", "Algebra textbook", "Graph paper", "Markers"],
            objectives=[
                "Understand linear equation concepts",
                "Master equation solving techniques",
                "Apply algebra to real-world problems"
            ],
            tags=["algebra", "equations", "problem-solving", "step-by-step"],
            difficulty_level="intermediate",
            is_public=True,
            user_id="",
            rating=4.3,
            usage_count=89,
            category=TemplateCategory.SUBJECT_SPECIFIC,
            created_at=datetime.utcnow()
        ),
        
        ActivityTemplate(
            id=str(uuid.uuid4()),
            title="Geometry Shapes Exploration",
            description="Hands-on exploration of 2D and 3D shapes using physical models and interactive software.",
            type=ActivityType.PRACTICAL,
            subject="Mathematics",
            grade="4-6",
            estimated_duration=40,
            materials=["3D shape models", "Rulers", "Protractors", "Geometry software", "Measuring tape"],
            objectives=[
                "Identify and classify geometric shapes",
                "Calculate area and perimeter",
                "Understand spatial relationships"
            ],
            tags=["geometry", "shapes", "hands-on", "spatial-thinking"],
            difficulty_level="intermediate",
            is_public=True,
            user_id="",
            rating=4.7,
            usage_count=112,
            category=TemplateCategory.PRACTICAL,
            created_at=datetime.utcnow()
        )
    ])
    
    # Science Templates
    templates.extend([
        ActivityTemplate(
            id=str(uuid.uuid4()),
            title="Plant Life Cycle Observation",
            description="Week-long observation and documentation of plant growth stages using bean seeds and measurement charts.",
            type=ActivityType.PROJECT,
            subject="Science",
            grade="2-4",
            estimated_duration=60,
            materials=["Bean seeds", "Potting soil", "Measuring rulers", "Observation journals", "Magnifying glasses"],
            objectives=[
                "Understand plant life cycles",
                "Develop observation skills",
                "Practice scientific recording"
            ],
            tags=["biology", "plants", "observation", "life-cycles", "hands-on"],
            difficulty_level="beginner",
            is_public=True,
            user_id="",
            rating=4.8,
            usage_count=203,
            category=TemplateCategory.PROJECT_BASED,
            created_at=datetime.utcnow()
        ),
        
        ActivityTemplate(
            id=str(uuid.uuid4()),
            title="Chemical Reactions Lab",
            description="Safe laboratory experiments demonstrating basic chemical reactions with detailed safety protocols.",
            type=ActivityType.PRACTICAL,
            subject="Science",
            grade="8-10",
            estimated_duration=50,
            materials=["Safety goggles", "Lab coats", "Test tubes", "Various chemicals", "pH strips", "Lab worksheets"],
            objectives=[
                "Observe chemical reactions firsthand",
                "Understand reaction types",
                "Practice laboratory safety"
            ],
            tags=["chemistry", "lab-work", "reactions", "safety", "experiments"],
            difficulty_level="advanced",
            is_public=True,
            user_id="",
            rating=4.4,
            usage_count=67,
            category=TemplateCategory.PRACTICAL,
            created_at=datetime.utcnow()
        )
    ])
    
    # Language Arts Templates
    templates.extend([
        ActivityTemplate(
            id=str(uuid.uuid4()),
            title="Creative Story Writing",
            description="Guided creative writing session with story prompts, character development, and peer sharing.",
            type=ActivityType.PROJECT,
            subject="English Language Arts",
            grade="3-6",
            estimated_duration=45,
            materials=["Writing journals", "Story prompt cards", "Colored pencils", "Sharing circle area"],
            objectives=[
                "Develop creative writing skills",
                "Practice narrative structure",
                "Build confidence in sharing"
            ],
            tags=["writing", "creativity", "storytelling", "peer-sharing"],
            difficulty_level="intermediate",
            is_public=True,
            user_id="",
            rating=4.6,
            usage_count=134,
            category=TemplateCategory.CREATIVE,
            created_at=datetime.utcnow()
        ),
        
        ActivityTemplate(
            id=str(uuid.uuid4()),
            title="Reading Comprehension Discussion",
            description="Interactive discussion of a short story focusing on comprehension strategies and critical thinking.",
            type=ActivityType.DISCUSSION,
            subject="English Language Arts",
            grade="4-8",
            estimated_duration=35,
            materials=["Selected short story", "Discussion questions", "Highlighters", "Notebook paper"],
            objectives=[
                "Improve reading comprehension",
                "Develop critical thinking skills",
                "Practice verbal communication"
            ],
            tags=["reading", "comprehension", "discussion", "critical-thinking"],
            difficulty_level="intermediate",
            is_public=True,
            user_id="",
            rating=4.5,
            usage_count=98,
            category=TemplateCategory.DISCUSSION_BASED,
            created_at=datetime.utcnow()
        )
    ])
    
    # Social Studies Templates
    templates.extend([
        ActivityTemplate(
            id=str(uuid.uuid4()),
            title="Historical Timeline Creation",
            description="Collaborative creation of visual timelines for major historical events with research and presentation components.",
            type=ActivityType.PROJECT,
            subject="Social Studies",
            grade="5-8",
            estimated_duration=55,
            materials=["Timeline templates", "History textbooks", "Colored markers", "Poster boards", "Research materials"],
            objectives=[
                "Understand chronological thinking",
                "Research historical events",
                "Create visual representations"
            ],
            tags=["history", "timeline", "research", "collaboration", "visual"],
            difficulty_level="intermediate",
            is_public=True,
            user_id="",
            rating=4.4,
            usage_count=76,
            category=TemplateCategory.PROJECT_BASED,
            created_at=datetime.utcnow()
        )
    ])
    
    # Physical Education Templates
    templates.extend([
        ActivityTemplate(
            id=str(uuid.uuid4()),
            title="Team Building Games",
            description="Collection of cooperative games designed to build teamwork, communication, and trust among students.",
            type=ActivityType.PRACTICAL,
            subject="Physical Education",
            grade="K-8",
            estimated_duration=30,
            materials=["Cones", "Ropes", "Balls", "Parachute", "Whistle"],
            objectives=[
                "Develop teamwork skills",
                "Improve physical coordination",
                "Build trust and communication"
            ],
            tags=["teamwork", "cooperation", "physical-activity", "social-skills"],
            difficulty_level="beginner",
            is_public=True,
            user_id="",
            rating=4.7,
            usage_count=187,
            category=TemplateCategory.PHYSICAL,
            created_at=datetime.utcnow()
        )
    ])
    
    # Technology Templates
    templates.extend([
        ActivityTemplate(
            id=str(uuid.uuid4()),
            title="Basic Coding with Scratch",
            description="Introduction to programming concepts using Scratch visual programming language with simple projects.",
            type=ActivityType.PRACTICAL,
            subject="Technology",
            grade="3-6",
            estimated_duration=40,
            materials=["Computers/tablets", "Scratch software", "Project examples", "Instruction cards"],
            objectives=[
                "Understand basic programming concepts",
                "Create simple interactive projects",
                "Develop logical thinking"
            ],
            tags=["coding", "programming", "scratch", "logic", "technology"],
            difficulty_level="beginner",
            is_public=True,
            user_id="",
            rating=4.6,
            usage_count=145,
            category=TemplateCategory.TECHNOLOGY,
            created_at=datetime.utcnow()
        )
    ])
    
    # Assessment Templates
    templates.extend([
        ActivityTemplate(
            id=str(uuid.uuid4()),
            title="Formative Assessment Stations",
            description="Multiple station-based assessment activity allowing students to demonstrate learning in various ways.",
            type=ActivityType.ASSESSMENT,
            subject="Any",
            grade="K-12",
            estimated_duration=45,
            materials=["Station materials", "Assessment rubrics", "Timer", "Recording sheets"],
            objectives=[
                "Assess student understanding",
                "Provide multiple demonstration methods",
                "Gather formative feedback"
            ],
            tags=["assessment", "formative", "stations", "multiple-modalities"],
            difficulty_level="intermediate",
            is_public=True,
            user_id="",
            rating=4.3,
            usage_count=89,
            category=TemplateCategory.ASSESSMENT,
            created_at=datetime.utcnow()
        ),
        
        ActivityTemplate(
            id=str(uuid.uuid4()),
            title="Quick Knowledge Check",
            description="Fast-paced review activity using various question formats to check understanding of recent lessons.",
            type=ActivityType.ASSESSMENT,
            subject="Any",
            grade="2-12",
            estimated_duration=15,
            materials=["Question cards", "Response boards", "Timers", "Answer keys"],
            objectives=[
                "Quickly assess comprehension",
                "Identify knowledge gaps",
                "Reinforce key concepts"
            ],
            tags=["quick-check", "review", "assessment", "fast-paced"],
            difficulty_level="beginner",
            is_public=True,
            user_id="",
            rating=4.2,
            usage_count=156,
            category=TemplateCategory.ASSESSMENT,
            created_at=datetime.utcnow()
        )
    ])
    
    # Break/Transition Templates
    templates.extend([
        ActivityTemplate(
            id=str(uuid.uuid4()),
            title="Mindfulness Break",
            description="Short mindfulness and breathing exercise to help students reset and refocus between lessons.",
            type=ActivityType.BREAK,
            subject="Any",
            grade="K-12",
            estimated_duration=10,
            materials=["Calm music", "Comfortable seating", "Dimmed lights"],
            objectives=[
                "Reduce stress and anxiety",
                "Improve focus and attention",
                "Practice self-regulation"
            ],
            tags=["mindfulness", "breathing", "reset", "self-regulation"],
            difficulty_level="beginner",
            is_public=True,
            user_id="",
            rating=4.8,
            usage_count=234,
            category=TemplateCategory.WELLNESS,
            created_at=datetime.utcnow()
        ),
        
        ActivityTemplate(
            id=str(uuid.uuid4()),
            title="Energizing Movement Break",
            description="Quick physical movement activities to re-energize students and improve circulation between seated work.",
            type=ActivityType.BREAK,
            subject="Any",
            grade="K-8",
            estimated_duration=8,
            materials=["Open space", "Upbeat music", "Movement cards"],
            objectives=[
                "Increase energy and alertness",
                "Improve circulation",
                "Provide physical release"
            ],
            tags=["movement", "energy", "circulation", "physical-break"],
            difficulty_level="beginner",
            is_public=True,
            user_id="",
            rating=4.7,
            usage_count=198,
            category=TemplateCategory.PHYSICAL,
            created_at=datetime.utcnow()
        )
    ])
    
    return templates

def get_templates_by_category() -> Dict[str, List[ActivityTemplate]]:
    """Get templates organized by category."""
    templates = get_default_activity_templates()
    categories = {}
    
    for template in templates:
        category = template.category.value
        if category not in categories:
            categories[category] = []
        categories[category].append(template)
    
    return categories

def get_templates_by_subject() -> Dict[str, List[ActivityTemplate]]:
    """Get templates organized by subject."""
    templates = get_default_activity_templates()
    subjects = {}
    
    for template in templates:
        subject = template.subject
        if subject not in subjects:
            subjects[subject] = []
        subjects[subject].append(template)
    
    return subjects

def get_template_statistics() -> Dict[str, int]:
    """Get statistics about available templates."""
    templates = get_default_activity_templates()
    
    stats = {
        'total_templates': len(templates),
        'by_type': {},
        'by_subject': {},
        'by_difficulty': {},
        'average_duration': 0
    }
    
    total_duration = 0
    
    for template in templates:
        # Count by type
        type_name = template.type.value
        stats['by_type'][type_name] = stats['by_type'].get(type_name, 0) + 1
        
        # Count by subject
        stats['by_subject'][template.subject] = stats['by_subject'].get(template.subject, 0) + 1
        
        # Count by difficulty
        stats['by_difficulty'][template.difficulty_level] = stats['by_difficulty'].get(template.difficulty_level, 0) + 1
        
        # Sum duration
        total_duration += template.estimated_duration
    
    if len(templates) > 0:
        stats['average_duration'] = total_duration // len(templates)
    
    return stats
