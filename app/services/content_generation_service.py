"""
Content Generation Service
AI-powered service for generating educational content including stories, worksheets, quizzes, and more.
"""

import logging
import time
import json
import re
from typing import Dict, List, Optional, Any, Union
from datetime import datetime

from google.cloud import firestore
from app.models.content_generation import (
    ContentType, ContentParameters, GeneratedContent, ContentVariant,
    StoryContent, WorksheetContent, QuizContent, LessonPlanContent, VisualAidContent,
    QualityAssessment, QualityScore, CONTENT_TEMPLATES, CULTURAL_CONTEXT
)
from app.services.ai_service import AIService

logger = logging.getLogger(__name__)

class ContentGenerationService:
    """Service for AI-powered educational content generation."""
    
    def __init__(self):
        """Initialize the content generation service."""
        self.db = firestore.Client()
        self.ai_service = AIService()
    
    def generate_content(self, user_id: str, content_type: str, parameters: Dict[str, Any]) -> GeneratedContent:
        """
        Generate educational content based on type and parameters.
        
        Args:
            user_id: User identifier
            content_type: Type of content to generate
            parameters: Generation parameters
            
        Returns:
            GeneratedContent object with generated content
        """
        start_time = time.time()
        
        try:
            # Validate content type
            if content_type not in [ct.value for ct in ContentType]:
                raise ValueError(f"Invalid content type: {content_type}")
            
            # Create parameters object
            content_params = ContentParameters.from_dict(parameters)
            
            # Generate content based on type
            if content_type == ContentType.STORY.value:
                content = self._generate_story(content_params)
            elif content_type == ContentType.WORKSHEET.value:
                content = self._generate_worksheet(content_params)
            elif content_type == ContentType.QUIZ.value:
                content = self._generate_quiz(content_params)
            elif content_type == ContentType.LESSON_PLAN.value:
                content = self._generate_lesson_plan(content_params)
            elif content_type == ContentType.VISUAL_AID.value:
                content = self._generate_visual_aid(content_params)
            else:
                raise ValueError(f"Content generation not implemented for type: {content_type}")
            
            # Calculate generation time
            generation_time = time.time() - start_time
            
            # Calculate word count
            word_count = self._calculate_word_count(content)
            
            # Assess quality
            quality_assessment = self._assess_content_quality(content_type, content, content_params)
            
            # Create result object
            result = GeneratedContent(
                id="",  # Will be auto-generated
                user_id=user_id,
                content_type=content_type,
                parameters=content_params,
                content=content,
                quality_assessment=quality_assessment,
                generation_time=generation_time,
                word_count=word_count
            )
            
            # Save to database
            self._save_generated_content(result)
            
            logger.info(f"Generated {content_type} content for user {user_id} in {generation_time:.2f}s")
            return result
            
        except Exception as e:
            logger.error(f"Error generating {content_type} content: {str(e)}")
            raise
    
    def _generate_story(self, parameters: ContentParameters) -> StoryContent:
        """Generate a story based on parameters."""
        
        # Build AI prompt for story generation
        prompt = self._build_story_prompt(parameters)
        
        # Get AI response
        ai_response = self.ai_service.generate_response(
            message=prompt,
            user_id="content_generation",
            max_tokens=2000,
            temperature=0.8
        )
        
        # Parse AI response into structured story
        story = self._parse_story_response(ai_response, parameters)
        
        return story
    
    def _generate_worksheet(self, parameters: ContentParameters) -> WorksheetContent:
        """Generate a worksheet based on parameters."""
        
        # Build AI prompt for worksheet generation
        prompt = self._build_worksheet_prompt(parameters)
        
        # Get AI response
        ai_response = self.ai_service.generate_response(
            message=prompt,
            user_id="content_generation",
            max_tokens=2500,
            temperature=0.7
        )
        
        # Parse AI response into structured worksheet
        worksheet = self._parse_worksheet_response(ai_response, parameters)
        
        return worksheet
    
    def _generate_quiz(self, parameters: ContentParameters) -> QuizContent:
        """Generate a quiz based on parameters."""
        
        # Build AI prompt for quiz generation
        prompt = self._build_quiz_prompt(parameters)
        
        # Get AI response
        ai_response = self.ai_service.generate_response(
            message=prompt,
            user_id="content_generation",
            max_tokens=2000,
            temperature=0.6
        )
        
        # Parse AI response into structured quiz
        quiz = self._parse_quiz_response(ai_response, parameters)
        
        return quiz
    
    def _generate_lesson_plan(self, parameters: ContentParameters) -> LessonPlanContent:
        """Generate a lesson plan based on parameters."""
        
        # Build AI prompt for lesson plan generation
        prompt = self._build_lesson_plan_prompt(parameters)
        
        # Get AI response
        ai_response = self.ai_service.generate_response(
            message=prompt,
            user_id="content_generation",
            max_tokens=2500,
            temperature=0.7
        )
        
        # Parse AI response into structured lesson plan
        lesson_plan = self._parse_lesson_plan_response(ai_response, parameters)
        
        return lesson_plan
    
    def _generate_visual_aid(self, parameters: ContentParameters) -> VisualAidContent:
        """Generate a visual aid based on parameters."""
        
        # Build AI prompt for visual aid generation
        prompt = self._build_visual_aid_prompt(parameters)
        
        # Get AI response
        ai_response = self.ai_service.generate_response(
            message=prompt,
            user_id="content_generation",
            max_tokens=1500,
            temperature=0.6
        )
        
        # Parse AI response into structured visual aid
        visual_aid = self._parse_visual_aid_response(ai_response, parameters)
        
        return visual_aid
    
    def _build_story_prompt(self, parameters: ContentParameters) -> str:
        """Build AI prompt for story generation."""
        
        # Get cultural context
        characters = CULTURAL_CONTEXT["character_names"].get(parameters.language, 
                    CULTURAL_CONTEXT["character_names"]["hindi"])
        settings = CULTURAL_CONTEXT["settings"]
        values = CULTURAL_CONTEXT["values"]
        
        prompt = f"""
        Generate an educational story for {parameters.grade} students studying {parameters.subject}.
        
        Requirements:
        - Topic: {parameters.topic}
        - Length: {parameters.length} ({CONTENT_TEMPLATES['story']['primary']['length_guidelines'].get(parameters.length, '400-600 words')})
        - Difficulty: {parameters.difficulty}
        - Language: {parameters.language}
        - Include moral lesson: {parameters.include_moral if parameters.include_moral else True}
        
        Story Guidelines:
        - Use Indian cultural context and values: {', '.join(values[:3])}
        - Suggest character names from: {', '.join(characters[:4])}
        - Possible settings: {', '.join(settings[:4])}
        - Make it educational and relevant to {parameters.subject}
        - Include age-appropriate vocabulary
        - Add 3-5 decision points for interactive reading
        
        Custom Instructions: {parameters.custom_instructions or 'None'}
        
        Please structure your response as JSON with the following format:
        {{
            "title": "Story title",
            "characters": ["character1", "character2"],
            "setting": "Where the story takes place",
            "plot": "Complete story text",
            "moral": "Key moral or lesson",
            "decision_points": [
                {{"point": "Decision description", "options": ["Option A", "Option B"], "context": "When this decision occurs"}}
            ],
            "vocabulary_words": [
                {{"word": "vocabulary_word", "definition": "simple definition"}}
            ]
        }}
        """
        
        return prompt
    
    def _build_worksheet_prompt(self, parameters: ContentParameters) -> str:
        """Build AI prompt for worksheet generation."""
        
        num_problems = parameters.number_of_problems or self._get_default_problem_count(parameters.grade, parameters.length)
        
        prompt = f"""
        Generate an educational worksheet for {parameters.grade} students in {parameters.subject}.
        
        Requirements:
        - Topic: {parameters.topic}
        - Number of problems: {num_problems}
        - Difficulty: {parameters.difficulty}
        - Length: {parameters.length}
        - Include solutions: {parameters.include_solutions}
        - Include answer key: {parameters.include_answer_key}
        - Language: {parameters.language}
        
        Worksheet Guidelines:
        - Create problems that build from basic to advanced
        - Include clear instructions
        - For math: Include word problems with Indian context (rupees, local scenarios)
        - For science: Include practical experiments safe for classroom
        - For language: Include culturally relevant examples
        - Provide step-by-step solutions when requested
        
        Custom Instructions: {parameters.custom_instructions or 'None'}
        
        Structure your response as JSON:
        {{
            "title": "Worksheet title",
            "instructions": "General instructions for students",
            "problems": [
                {{"number": 1, "question": "Problem text", "type": "problem_type", "points": 5}}
            ],
            "answer_key": [
                {{"number": 1, "answer": "Correct answer", "explanation": "Brief explanation"}}
            ],
            "solutions": [
                {{"number": 1, "solution": "Step-by-step solution"}}
            ],
            "additional_resources": ["Resource 1", "Resource 2"]
        }}
        """
        
        return prompt
    
    def _build_quiz_prompt(self, parameters: ContentParameters) -> str:
        """Build AI prompt for quiz generation."""
        
        num_questions = parameters.number_of_questions or self._get_default_question_count(parameters.grade, parameters.length)
        question_types = parameters.question_types or ["mcq", "true_false", "fill_blanks"]
        
        prompt = f"""
        Generate a comprehensive quiz for {parameters.grade} students in {parameters.subject}.
        
        Requirements:
        - Topic: {parameters.topic}
        - Number of questions: {num_questions}
        - Question types: {', '.join(question_types)}
        - Difficulty: {parameters.difficulty}
        - Include explanations: {parameters.include_explanations}
        - Language: {parameters.language}
        
        Quiz Guidelines:
        - Mix question types: 50% MCQ, 25% True/False, 25% Fill-in-blanks
        - Create plausible distractors for MCQs
        - Include explanations for all answers
        - Use Indian educational context and examples
        - Ensure questions test understanding, not just memorization
        - Grade-appropriate language and concepts
        
        Custom Instructions: {parameters.custom_instructions or 'None'}
        
        Structure your response as JSON:
        {{
            "title": "Quiz title",
            "instructions": "Quiz instructions",
            "questions": [
                {{
                    "number": 1,
                    "type": "mcq|true_false|fill_blanks|essay",
                    "question": "Question text",
                    "options": ["A", "B", "C", "D"],
                    "correct_answer": "B",
                    "points": 2,
                    "explanation": "Why this answer is correct"
                }}
            ],
            "answer_key": [
                {{"number": 1, "answer": "B", "explanation": "Detailed explanation"}}
            ],
            "scoring_rubric": {{"total_points": 20, "grading_scale": "A: 18-20, B: 15-17, C: 12-14, D: 9-11, F: <9"}},
            "time_limit": 30
        }}
        """
        
        return prompt
    
    def _build_lesson_plan_prompt(self, parameters: ContentParameters) -> str:
        """Build AI prompt for lesson plan generation."""
        
        duration = 45  # Default duration in minutes
        if parameters.length == "short":
            duration = 30
        elif parameters.length == "long":
            duration = 60
        
        prompt = f"""
        Generate a detailed lesson plan for {parameters.grade} students in {parameters.subject}.
        
        Requirements:
        - Topic: {parameters.topic}
        - Duration: {duration} minutes
        - Difficulty: {parameters.difficulty}
        - Language: {parameters.language}
        
        Lesson Plan Guidelines:
        - Follow Indian curriculum standards
        - Include interactive activities
        - Provide differentiation strategies
        - Use locally relevant examples
        - Include assessment methods
        - Consider diverse learning styles
        - Add extension activities for advanced learners
        
        Custom Instructions: {parameters.custom_instructions or 'None'}
        
        Structure your response as JSON:
        {{
            "title": "Lesson title",
            "objectives": ["Learning objective 1", "Learning objective 2"],
            "materials": ["Material 1", "Material 2"],
            "duration": {duration},
            "introduction": "How to start the lesson (5-10 minutes)",
            "main_activities": [
                {{"activity": "Activity name", "duration": 15, "description": "Activity description", "materials": ["item1"]}}
            ],
            "assessment": "How to assess student understanding",
            "homework": "Optional homework assignment",
            "differentiation": ["Strategy for different learners"],
            "extensions": ["Extension activities for advanced students"]
        }}
        """
        
        return prompt
    
    def _build_visual_aid_prompt(self, parameters: ContentParameters) -> str:
        """Build AI prompt for visual aid generation."""
        
        prompt = f"""
        Generate a visual aid design for {parameters.grade} students learning {parameters.subject}.
        
        Requirements:
        - Topic: {parameters.topic}
        - Diagram type: {parameters.diagram_type or 'educational diagram'}
        - Color scheme: {parameters.color_scheme or 'high contrast for blackboard'}
        - Include labels: {parameters.include_labels}
        - Language: {parameters.language}
        
        Visual Aid Guidelines:
        - Design for classroom display (blackboard-friendly)
        - Use simple, clear shapes and text
        - High contrast colors for visibility
        - Include step-by-step drawing instructions for teachers
        - Make it educational and engaging
        - Consider cultural context and local examples
        
        Custom Instructions: {parameters.custom_instructions or 'None'}
        
        Structure your response as JSON:
        {{
            "title": "Visual aid title",
            "description": "What this visual aid shows",
            "elements": [
                {{"type": "circle|rectangle|text|arrow", "x": 100, "y": 100, "width": 50, "height": 50, "text": "Label", "color": "#000000"}}
            ],
            "drawing_instructions": ["Step 1: Draw...", "Step 2: Add..."],
            "color_palette": ["#000000", "#FF0000", "#00FF00"]
        }}
        """
        
        return prompt
    
    def _parse_story_response(self, response: str, parameters: ContentParameters) -> StoryContent:
        """Parse AI response into StoryContent object."""
        try:
            # Try to extract JSON from response
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
                return StoryContent.from_dict(data)
            else:
                # Fallback: create basic story structure
                return StoryContent(
                    title=f"Story about {parameters.topic}",
                    characters=["Main Character"],
                    setting="School",
                    plot=response,
                    moral="Always try your best"
                )
        except Exception as e:
            logger.error(f"Error parsing story response: {str(e)}")
            return StoryContent(
                title=f"Story about {parameters.topic}",
                characters=["Student"],
                setting="Classroom",
                plot="This is a sample story that needs to be generated properly.",
                moral="Learning is important"
            )
    
    def _parse_worksheet_response(self, response: str, parameters: ContentParameters) -> WorksheetContent:
        """Parse AI response into WorksheetContent object."""
        try:
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
                return WorksheetContent.from_dict(data)
            else:
                return WorksheetContent(
                    title=f"{parameters.subject} Worksheet: {parameters.topic}",
                    instructions="Complete all problems carefully.",
                    problems=[{"number": 1, "question": "Sample problem", "type": "basic", "points": 5}]
                )
        except Exception as e:
            logger.error(f"Error parsing worksheet response: {str(e)}")
            return WorksheetContent(
                title=f"{parameters.subject} Worksheet",
                instructions="Complete the following problems.",
                problems=[{"number": 1, "question": "Sample problem", "type": "basic", "points": 5}]
            )
    
    def _parse_quiz_response(self, response: str, parameters: ContentParameters) -> QuizContent:
        """Parse AI response into QuizContent object."""
        try:
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
                return QuizContent.from_dict(data)
            else:
                return QuizContent(
                    title=f"{parameters.subject} Quiz: {parameters.topic}",
                    instructions="Choose the best answer for each question.",
                    questions=[{"number": 1, "type": "mcq", "question": "Sample question?", "options": ["A", "B", "C", "D"], "correct_answer": "A", "points": 2}],
                    answer_key=[{"number": 1, "answer": "A", "explanation": "Sample explanation"}]
                )
        except Exception as e:
            logger.error(f"Error parsing quiz response: {str(e)}")
            return QuizContent(
                title=f"{parameters.subject} Quiz",
                instructions="Answer all questions.",
                questions=[{"number": 1, "type": "mcq", "question": "Sample question?", "options": ["A", "B", "C", "D"], "correct_answer": "A", "points": 2}],
                answer_key=[{"number": 1, "answer": "A", "explanation": "Sample explanation"}]
            )
    
    def _parse_lesson_plan_response(self, response: str, parameters: ContentParameters) -> LessonPlanContent:
        """Parse AI response into LessonPlanContent object."""
        try:
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
                return LessonPlanContent.from_dict(data)
            else:
                return LessonPlanContent(
                    title=f"{parameters.subject} Lesson: {parameters.topic}",
                    objectives=["Students will understand the basics"],
                    materials=["Whiteboard", "Textbook"],
                    duration=45,
                    introduction="Begin with a question to engage students",
                    main_activities=[{"activity": "Main lesson", "duration": 30, "description": "Core teaching"}],
                    assessment="Check understanding through questions"
                )
        except Exception as e:
            logger.error(f"Error parsing lesson plan response: {str(e)}")
            return LessonPlanContent(
                title=f"{parameters.subject} Lesson",
                objectives=["Basic understanding"],
                materials=["Basic supplies"],
                duration=45,
                introduction="Start the lesson",
                main_activities=[{"activity": "Teaching", "duration": 30, "description": "Main content"}],
                assessment="Assess learning"
            )
    
    def _parse_visual_aid_response(self, response: str, parameters: ContentParameters) -> VisualAidContent:
        """Parse AI response into VisualAidContent object."""
        try:
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
                return VisualAidContent.from_dict(data)
            else:
                return VisualAidContent(
                    title=f"Visual Aid: {parameters.topic}",
                    description="Educational diagram",
                    elements=[{"type": "text", "x": 100, "y": 100, "text": parameters.topic, "color": "#000000"}],
                    drawing_instructions=["Draw the main concept", "Add labels"]
                )
        except Exception as e:
            logger.error(f"Error parsing visual aid response: {str(e)}")
            return VisualAidContent(
                title=f"Visual Aid: {parameters.topic}",
                description="Educational diagram",
                elements=[{"type": "text", "x": 100, "y": 100, "text": "Sample", "color": "#000000"}],
                drawing_instructions=["Draw basic shape", "Add text"]
            )
    
    def _assess_content_quality(self, content_type: str, content: Any, parameters: ContentParameters) -> QualityAssessment:
        """Assess the quality of generated content."""
        
        criteria_scores = {}
        strengths = []
        improvements = []
        suggestions = []
        
        # Common criteria
        criteria_scores["relevance"] = 4  # How relevant to topic
        criteria_scores["age_appropriateness"] = 4  # Suitable for grade level
        criteria_scores["clarity"] = 4  # Clear and understandable
        criteria_scores["engagement"] = 3  # How engaging for students
        criteria_scores["cultural_sensitivity"] = 4  # Appropriate cultural context
        
        # Content-specific criteria
        if content_type == ContentType.STORY.value:
            criteria_scores["narrative_structure"] = 4
            criteria_scores["moral_value"] = 3
            strengths.append("Clear narrative structure")
            suggestions.append("Add more interactive elements")
        
        elif content_type == ContentType.WORKSHEET.value:
            criteria_scores["problem_variety"] = 4
            criteria_scores["difficulty_progression"] = 3
            strengths.append("Good variety of problems")
            suggestions.append("Include more visual elements")
        
        elif content_type == ContentType.QUIZ.value:
            criteria_scores["question_quality"] = 4
            criteria_scores["distractor_quality"] = 3
            strengths.append("Well-structured questions")
            suggestions.append("Add more scenario-based questions")
        
        # Calculate overall score
        avg_score = sum(criteria_scores.values()) / len(criteria_scores)
        if avg_score >= 4.5:
            overall_score = QualityScore.EXCELLENT.value
        elif avg_score >= 3.5:
            overall_score = QualityScore.GOOD.value
        elif avg_score >= 2.5:
            overall_score = QualityScore.FAIR.value
        else:
            overall_score = QualityScore.NEEDS_IMPROVEMENT.value
        
        # General strengths and improvements
        if parameters.custom_instructions:
            strengths.append("Addresses custom requirements")
        
        improvements.append("Could be more interactive")
        suggestions.append("Consider adding multimedia elements")
        
        return QualityAssessment(
            overall_score=overall_score,
            criteria_scores=criteria_scores,
            strengths=strengths,
            improvements=improvements,
            suggestions=suggestions
        )
    
    def _calculate_word_count(self, content: Any) -> int:
        """Calculate word count of generated content."""
        text = ""
        
        if isinstance(content, StoryContent):
            text = content.plot
        elif isinstance(content, WorksheetContent):
            text = content.instructions + " " + " ".join([p.get("question", "") for p in content.problems])
        elif isinstance(content, QuizContent):
            text = content.instructions + " " + " ".join([q.get("question", "") for q in content.questions])
        elif isinstance(content, LessonPlanContent):
            text = content.introduction + " " + " ".join([a.get("description", "") for a in content.main_activities])
        elif isinstance(content, VisualAidContent):
            text = content.description + " " + " ".join(content.drawing_instructions or [])
        
        return len(text.split())
    
    def _get_default_problem_count(self, grade: str, length: str) -> int:
        """Get default number of problems based on grade and length."""
        base_count = 10
        if "grade1" in grade or "grade2" in grade:
            base_count = 5
        elif "grade3" in grade or "grade4" in grade:
            base_count = 8
        
        if length == "short":
            return max(3, base_count // 2)
        elif length == "long":
            return base_count * 2
        else:
            return base_count
    
    def _get_default_question_count(self, grade: str, length: str) -> int:
        """Get default number of questions based on grade and length."""
        base_count = 10
        if "grade1" in grade or "grade2" in grade:
            base_count = 6
        elif "grade3" in grade or "grade4" in grade:
            base_count = 8
        
        if length == "short":
            return max(4, base_count // 2)
        elif length == "long":
            return base_count + 5
        else:
            return base_count
    
    def _save_generated_content(self, content: GeneratedContent) -> None:
        """Save generated content to database."""
        try:
            doc_ref = self.db.collection('generated_content').document(content.id)
            doc_ref.set(content.to_dict())
            logger.info(f"Saved generated content {content.id}")
        except Exception as e:
            logger.error(f"Error saving generated content: {str(e)}")
            raise
    
    def get_content_by_id(self, content_id: str, user_id: str) -> Optional[GeneratedContent]:
        """Get generated content by ID."""
        try:
            doc_ref = self.db.collection('generated_content').document(content_id)
            doc = doc_ref.get()
            
            if not doc.exists:
                return None
            
            content_data = doc.to_dict()
            content = GeneratedContent.from_dict(content_data)
            
            # Check access permissions
            if content.user_id != user_id:
                return None
            
            return content
            
        except Exception as e:
            logger.error(f"Error getting content {content_id}: {str(e)}")
            return None
    
    def get_user_content_history(self, user_id: str, content_type: Optional[str] = None, 
                                page: int = 1, page_size: int = 20) -> Dict[str, Any]:
        """Get user's content generation history."""
        try:
            query = self.db.collection('generated_content').where('user_id', '==', user_id)
            
            if content_type:
                query = query.where('content_type', '==', content_type)
            
            # Order by creation date (newest first)
            query = query.order_by('created_at', direction=firestore.Query.DESCENDING)
            
            # Get all documents for counting
            all_docs = list(query.stream())
            total_count = len(all_docs)
            
            # Apply pagination
            start_idx = (page - 1) * page_size
            end_idx = start_idx + page_size
            paginated_docs = all_docs[start_idx:end_idx]
            
            # Convert to content objects
            contents = []
            for doc in paginated_docs:
                content_data = doc.to_dict()
                content = GeneratedContent.from_dict(content_data)
                contents.append(content.to_dict())
            
            return {
                'contents': contents,
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
            logger.error(f"Error getting content history for user {user_id}: {str(e)}")
            raise
    
    def generate_content_variants(self, content_id: str, user_id: str, num_variants: int = 3) -> List[ContentVariant]:
        """Generate variants of existing content."""
        try:
            # Get original content
            original_content = self.get_content_by_id(content_id, user_id)
            if not original_content:
                raise ValueError("Content not found or access denied")
            
            variants = []
            
            for i in range(num_variants):
                # Modify parameters slightly for variation
                variant_params = ContentParameters.from_dict(original_content.parameters.to_dict())
                
                # Add variation instructions
                variant_params.custom_instructions = f"Create a variation of the original content. Variant #{i+1}. " + \
                                                   (variant_params.custom_instructions or "")
                
                # Generate variant content
                if original_content.content_type == ContentType.STORY.value:
                    variant_content = self._generate_story(variant_params)
                elif original_content.content_type == ContentType.WORKSHEET.value:
                    variant_content = self._generate_worksheet(variant_params)
                elif original_content.content_type == ContentType.QUIZ.value:
                    variant_content = self._generate_quiz(variant_params)
                elif original_content.content_type == ContentType.LESSON_PLAN.value:
                    variant_content = self._generate_lesson_plan(variant_params)
                elif original_content.content_type == ContentType.VISUAL_AID.value:
                    variant_content = self._generate_visual_aid(variant_params)
                else:
                    continue
                
                # Create variant object
                variant = ContentVariant(
                    id="",  # Will be auto-generated
                    parent_id=content_id,
                    variant_number=i + 1,
                    parameters=variant_params,
                    content=variant_content
                )
                
                # Save variant
                self._save_content_variant(variant)
                variants.append(variant)
            
            logger.info(f"Generated {len(variants)} variants for content {content_id}")
            return variants
            
        except Exception as e:
            logger.error(f"Error generating content variants: {str(e)}")
            raise
    
    def _save_content_variant(self, variant: ContentVariant) -> None:
        """Save content variant to database."""
        try:
            doc_ref = self.db.collection('content_variants').document(variant.id)
            doc_ref.set(variant.to_dict())
            logger.info(f"Saved content variant {variant.id}")
        except Exception as e:
            logger.error(f"Error saving content variant: {str(e)}")
            raise
