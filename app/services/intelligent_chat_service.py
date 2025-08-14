"""
Intelligent Chat Service for enhanced AI interactions.
"""
import json
import logging
import uuid
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, Tuple
import re

from google.cloud import firestore
from app.models.chat import (
    ChatMessage, ChatSession, ChatSuggestion, RelatedTopic, StudyRecommendation,
    UserContext, IntelligentChatResponse, ConversationContext, ChatAnalytics,
    ChatSessionType, MessageType, SuggestionType
)
from app.services.ai_service import AIService
from app.services.user_service import UserService
from app.services.dashboard_service import DashboardService, ActivityType
from app.utils.cache_manager import CacheManager
from app.utils import log_execution_time

logger = logging.getLogger(__name__)

class IntelligentChatService:
    """Service for managing intelligent chat functionality."""
    
    def __init__(self):
        # Initialize database client
        self.db = firestore.Client()
        
        # Initialize services with database
        self.ai_service = AIService()
        self.user_service = UserService(self.db)
        self.dashboard_service = DashboardService()
        self.cache_manager = CacheManager()
        
        # In-memory storage for sessions and messages (replace with database in production)
        self.sessions: Dict[str, ChatSession] = {}
        self.messages: Dict[str, List[ChatMessage]] = {}
        self.message_history: Dict[str, List[Dict]] = {}
        self.user_contexts: Dict[str, UserContext] = {}
        
        # Educational topic mapping
        self.subject_keywords = {
            'mathematics': ['math', 'algebra', 'geometry', 'calculus', 'arithmetic', 'numbers', 'equations'],
            'science': ['physics', 'chemistry', 'biology', 'experiment', 'hypothesis', 'theory'],
            'english': ['grammar', 'literature', 'writing', 'reading', 'vocabulary', 'essay'],
            'social_studies': ['history', 'geography', 'civics', 'culture', 'society', 'government'],
            'art': ['drawing', 'painting', 'creativity', 'design', 'visual', 'artistic'],
            'physical_education': ['sports', 'exercise', 'fitness', 'health', 'physical', 'movement']
        }
    
    @log_execution_time
    def send_intelligent_message(self, 
                                     message: str, 
                                     session_id: str, 
                                     user_id: Optional[str] = None,
                                     context: Optional[Dict[str, Any]] = None) -> IntelligentChatResponse:
        """Send an intelligent message and get AI response with suggestions."""
        try:
            # For now, create a simple response until we fix the async issue
            # Get session from memory storage
            session = self._get_session_simple(session_id, user_id)
            
            # Generate a basic AI response using the existing AI service
            basic_response = self.ai_service.generate_response(
                message=message,
                user_id=user_id,
                context=context or {}
            )
            
            # Create a simple intelligent response
            response = IntelligentChatResponse(
                message_id=str(uuid.uuid4()),
                content=basic_response,
                timestamp=datetime.utcnow(),
                suggestions=[
                    ChatSuggestion(
                        id=str(uuid.uuid4()),
                        content="What specific aspect would you like to explore further?",
                        suggestion_type=SuggestionType.FOLLOW_UP_QUESTION,
                        priority=1
                    ),
                    ChatSuggestion(
                        id=str(uuid.uuid4()),
                        content="Would you like practical examples for this?",
                        suggestion_type=SuggestionType.EXPLORATION_PROMPT,
                        priority=2
                    )
                ],
                related_topics=[
                    RelatedTopic(
                        id=str(uuid.uuid4()),
                        title="Related Educational Strategies",
                        description="Explore evidence-based teaching methods",
                        subject="education",
                        grades=["8", "9"],
                        difficulty="intermediate",
                        keywords=["teaching", "strategies", "education"]
                    )
                ],
                study_recommendations=[
                    StudyRecommendation(
                        id=str(uuid.uuid4()),
                        title="Educational Best Practices",
                        description="Explore evidence-based teaching methods",
                        action_type="plan_lesson",
                        action_data={"subject": "mathematics", "grade": "8"},
                        reasoning="Based on your interest in engaging math lessons",
                        priority=1
                    )
                ],
                analytics={
                    "processing_time": 0.5,
                    "confidence_score": 0.85,
                    "educational_focus": True,
                    "user_context": self._get_simple_user_context(user_id).to_dict()
                }
            )
            
            # Store both user message and AI response in memory
            self._store_message_simple(session_id, message, user_id, MessageType.USER)
            self._store_message_simple(session_id, response.content, user_id, MessageType.AI)
            
            return response
            
        except Exception as e:
            logger.error(f"Error in intelligent chat: {str(e)}")
            raise
    
    def _get_session_simple(self, session_id: str, user_id: Optional[str]) -> ChatSession:
        """Get session from in-memory storage or create new one."""
        if session_id not in self.sessions:
            session = ChatSession(
                id=session_id,
                user_id=user_id,
                title="Chat Session",
                session_type=ChatSessionType.GENERAL,
                created_at=datetime.utcnow(),
                last_activity_at=datetime.utcnow()
            )
            self.sessions[session_id] = session
        return self.sessions[session_id]
    
    def _get_simple_user_context(self, user_id: Optional[str]) -> UserContext:
        """Get simple user context."""
        return UserContext(
            user_id=user_id or "anonymous",
            profile={
                "teaching_subjects": ["Mathematics", "Science"],
                "grade_levels": ["Grade 8", "Grade 9"]
            },
            preferences={
                "learning_style": "visual",
                "difficulty_level": "intermediate"
            },
            recent_activities=[
                {"type": "lesson_planning", "subject": "mathematics"},
                {"type": "quiz_creation", "subject": "algebra"}
            ],
            current_tasks=[
                {"task": "Create engaging math activities", "priority": "high"}
            ]
        )
    
    def _store_message_simple(self, session_id: str, message: str, user_id: Optional[str], message_type: MessageType = MessageType.USER):
        """Store message in memory."""
        # Simple in-memory storage for now
        if session_id not in self.message_history:
            self.message_history[session_id] = []
        
        self.message_history[session_id].append({
            "message": message,
            "user_id": user_id,
            "message_type": message_type,
            "timestamp": datetime.utcnow().isoformat()
        })
    
    def create_intelligent_session(self,
                                       title: Optional[str] = None,
                                       user_id: Optional[str] = None,
                                       session_type: ChatSessionType = ChatSessionType.GENERAL,
                                       initial_context: Optional[Dict[str, Any]] = None) -> ChatSession:
        """Create a new intelligent chat session."""
        session_id = str(uuid.uuid4())
        
        # Generate intelligent title if not provided
        if not title:
            title = self._generate_session_title_simple(session_type, initial_context)
        
        session = ChatSession(
            id=session_id,
            user_id=user_id or "anonymous",
            title=title,
            session_type=session_type,
            created_at=datetime.utcnow(),
            last_activity_at=datetime.utcnow(),
            context=initial_context or {},
            settings={
                'enable_suggestions': True,
                'enable_topic_tracking': True,
                'enable_personalization': True,
                'max_history_context': 20,
                'creativity_level': 0.7
            }
        )
        
        self.sessions[session_id] = session
        self.messages[session_id] = []
        
        logger.info(f"Created intelligent chat session {session_id} for user {user_id}")
        return session
    
    def get_personalized_suggestions(self,
                                         session_id: str,
                                         user_id: Optional[str] = None,
                                         current_message: Optional[str] = None) -> List[ChatSuggestion]:
        """Get personalized suggestions based on context."""
        try:
            logger.info(f"Generating suggestions for session {session_id}")
            
            # Return simple demo suggestions for testing
            suggestions = [
                ChatSuggestion(
                    id=str(uuid.uuid4()),
                    content="Try using visual aids to explain algebra concepts",
                    suggestion_type=SuggestionType.STUDY_SUGGESTION,
                    priority=1
                ),
                ChatSuggestion(
                    id=str(uuid.uuid4()),
                    content="What are some real-world applications of algebra?",
                    suggestion_type=SuggestionType.FOLLOW_UP_QUESTION,
                    priority=2
                ),
                ChatSuggestion(
                    id=str(uuid.uuid4()),
                    content="Consider using interactive math games",
                    suggestion_type=SuggestionType.EXPLORATION_PROMPT,
                    priority=3
                )
            ]
            
            logger.info(f"Created {len(suggestions)} suggestions")
            return suggestions
            
        except Exception as e:
            logger.error(f"Error generating suggestions: {str(e)}")
            return []
    
    def get_session_history(self, 
                                session_id: str, 
                                page: int = 1, 
                                limit: int = 50) -> Tuple[List[ChatMessage], int]:
        """Get chat history for a session with pagination."""
        # Use message_history instead of messages for retrieval
        if session_id not in self.message_history:
            return [], 0
        
        raw_messages = self.message_history[session_id]
        total = len(raw_messages)
        
        start_idx = (page - 1) * limit
        end_idx = start_idx + limit
        
        paginated_raw = raw_messages[start_idx:end_idx]
        
        # Convert raw message data to ChatMessage objects
        chat_messages = []
        for i, raw_msg in enumerate(paginated_raw):
            chat_message = ChatMessage(
                id=str(uuid.uuid4()),
                content=raw_msg["message"],
                message_type=raw_msg.get("message_type", MessageType.USER),
                timestamp=datetime.fromisoformat(raw_msg["timestamp"]) if isinstance(raw_msg["timestamp"], str) else raw_msg["timestamp"],
                session_id=session_id,
                user_id=raw_msg.get("user_id")
            )
            chat_messages.append(chat_message)
        
        return chat_messages, total
    
    def get_user_sessions(self, 
                              user_id: str, 
                              limit: int = 20) -> List[ChatSession]:
        """Get recent sessions for a user."""
        user_sessions = [
            session for session in self.sessions.values() 
            if session.user_id == user_id
        ]
        
        # Sort by last activity
        user_sessions.sort(key=lambda s: s.last_activity_at, reverse=True)
        
        return user_sessions[:limit]
    
    def continue_or_create_session(self,
                                       user_id: str,
                                       last_session_id: Optional[str] = None,
                                       message_preview: Optional[str] = None) -> ChatSession:
        """Continue existing session or create new one."""
        # Check if last session is still active (within 24 hours)
        if last_session_id and last_session_id in self.sessions:
            session = self.sessions[last_session_id]
            time_since_activity = datetime.utcnow() - session.last_activity_at
            
            if time_since_activity < timedelta(hours=24):
                return session
        
        # Determine session type from message preview (simplified)
        session_type = self._determine_session_type_simple(message_preview)
        
        # Create new session with context
        return self.create_intelligent_session(
            user_id=user_id,
            session_type=session_type,
            initial_context=self._get_user_context_dict_simple(user_id)
        )
    
    async def analyze_conversation(self, session_id: str) -> Dict[str, Any]:
        """Analyze conversation for insights."""
        if session_id not in self.messages:
            return {}
        
        messages = self.messages[session_id]
        if not messages:
            return {}
        
        # Extract topics
        topics = await self._extract_topics_from_messages(messages)
        
        # Analyze sentiment
        sentiments = await self._analyze_sentiment(messages)
        
        # Calculate engagement metrics
        engagement = await self._calculate_engagement_metrics(messages)
        
        return {
            'topics_discussed': topics,
            'sentiment_analysis': sentiments,
            'engagement_metrics': engagement,
            'total_messages': len(messages),
            'session_duration': self._calculate_session_duration(messages)
        }
    
    # Private helper methods
    
    async def _get_or_create_session(self, session_id: str, user_id: Optional[str]) -> ChatSession:
        """Get existing session or create new one."""
        if session_id in self.sessions:
            return self.sessions[session_id]
        
        return await self.create_intelligent_session(
            user_id=user_id,
            session_type=ChatSessionType.GENERAL
        )
    
    async def _build_conversation_context(self, 
                                        session_id: str, 
                                        user_id: Optional[str],
                                        current_message: Optional[str] = None) -> ConversationContext:
        """Build comprehensive conversation context."""
        # Get recent messages
        recent_messages = []
        if session_id in self.messages:
            recent_messages = self.messages[session_id][-10:]  # Last 10 messages
        
        # Get user context
        user_context = await self._get_user_context(user_id) if user_id else UserContext("anonymous")
        
        # Extract topics from conversation
        extracted_topics = await self._extract_topics_from_messages(recent_messages)
        
        # Analyze intent if current message provided
        intent = None
        if current_message:
            intent = await self._analyze_intent(current_message, user_context)
        
        return ConversationContext(
            session_id=session_id,
            recent_messages=recent_messages,
            user_context=user_context,
            extracted_topics=extracted_topics,
            intent=intent
        )
    
    async def _generate_intelligent_response(self, context: ConversationContext) -> IntelligentChatResponse:
        """Generate intelligent AI response with suggestions."""
        # Build enhanced prompt with context
        prompt = await self._build_enhanced_prompt(context)
        
        # Generate AI response
        ai_response = await self.ai_service.generate_text(
            prompt=prompt,
            max_tokens=1000,
            temperature=0.7,
            context=json.dumps(context.to_dict())
        )
        
        if not ai_response.success:
            raise Exception(f"AI generation failed: {ai_response.error}")
        
        # Generate suggestions
        suggestions = await self._generate_suggestions(context)
        
        # Generate related topics
        related_topics = await self._generate_related_topics(context)
        
        # Generate study recommendations
        study_recommendations = await self._generate_study_recommendations(context)
        
        return IntelligentChatResponse(
            message_id=str(uuid.uuid4()),
            content=ai_response.response,
            timestamp=datetime.utcnow(),
            suggestions=suggestions,
            related_topics=related_topics,
            study_recommendations=study_recommendations,
            analytics={'response_time': ai_response.response_time}
        )
    
    async def _generate_suggestions(self, context: ConversationContext) -> List[ChatSuggestion]:
        """Generate contextual suggestions."""
        suggestions = []
        
        # Follow-up questions based on conversation
        if context.recent_messages:
            last_ai_message = next(
                (msg for msg in reversed(context.recent_messages) if msg.message_type == MessageType.AI),
                None
            )
            if last_ai_message:
                follow_ups = await self._generate_follow_up_questions(last_ai_message.content)
                suggestions.extend(follow_ups)
        
        # Subject-specific suggestions
        if context.user_context.profile:
            subject_suggestions = await self._generate_subject_suggestions(context)
            suggestions.extend(subject_suggestions)
        
        # Study suggestions based on topics
        study_suggestions = await self._generate_study_suggestions(context.extracted_topics)
        suggestions.extend(study_suggestions)
        
        return suggestions[:10]  # Limit to top 10 suggestions
    
    async def _generate_related_topics(self, context: ConversationContext) -> List[RelatedTopic]:
        """Generate related educational topics."""
        topics = []
        
        for topic in context.extracted_topics[:5]:  # Top 5 topics
            related_topic = RelatedTopic(
                id=str(uuid.uuid4()),
                title=f"Exploring {topic.title()}",
                description=f"Learn more about {topic} and its applications",
                subject=await self._classify_subject(topic),
                grades=await self._suggest_grades_for_topic(topic, context.user_context),
                difficulty="intermediate",
                keywords=[topic] + await self._get_related_keywords(topic)
            )
            topics.append(related_topic)
        
        return topics
    
    async def _generate_study_recommendations(self, context: ConversationContext) -> List[StudyRecommendation]:
        """Generate personalized study recommendations."""
        recommendations = []
        
        # Based on conversation topics
        for topic in context.extracted_topics[:3]:
            recommendation = StudyRecommendation(
                id=str(uuid.uuid4()),
                title=f"Create content about {topic}",
                description=f"Generate educational materials focusing on {topic}",
                action_type="create_content",
                action_data={"topic": topic, "type": "story"},
                reasoning=f"Based on your interest in {topic} from our conversation",
                priority=1
            )
            recommendations.append(recommendation)
        
        # Based on user profile
        if context.user_context.profile:
            profile = context.user_context.profile
            subjects = profile.get('subjects', [])
            grades = profile.get('grades', [])
            
            for subject in subjects[:2]:
                recommendation = StudyRecommendation(
                    id=str(uuid.uuid4()),
                    title=f"Plan {subject} lesson",
                    description=f"Create a comprehensive lesson plan for {subject}",
                    action_type="plan_lesson",
                    action_data={"subject": subject, "grades": grades},
                    reasoning=f"You teach {subject} and might need lesson planning support",
                    priority=2
                )
                recommendations.append(recommendation)
        
        return recommendations[:5]  # Top 5 recommendations
    
    async def _store_message(self, message: ChatMessage):
        """Store message in memory (replace with database)."""
        if message.session_id not in self.messages:
            self.messages[message.session_id] = []
        
        self.messages[message.session_id].append(message)
    
    async def _update_session_activity(self, session_id: str):
        """Update session last activity time."""
        if session_id in self.sessions:
            self.sessions[session_id].last_activity_at = datetime.utcnow()
            self.sessions[session_id].message_count += 1
    
    async def _get_user_context(self, user_id: str) -> UserContext:
        """Get comprehensive user context."""
        if user_id in self.user_contexts:
            return self.user_contexts[user_id]
        
        # Build user context from various sources
        try:
            user_profile = await self.user_service.get_user_profile(user_id)
            recent_activities = await self.dashboard_service.get_recent_activities(user_id, limit=10)
            
            context = UserContext(
                user_id=user_id,
                profile=user_profile,
                recent_activities=[activity.to_dict() for activity in recent_activities],
                preferences={}
            )
            
            self.user_contexts[user_id] = context
            return context
            
        except Exception as e:
            logger.warning(f"Could not build user context for {user_id}: {str(e)}")
            return UserContext(user_id=user_id)
    
    async def _get_user_context_dict(self, user_id: str) -> Dict[str, Any]:
        """Get user context as dictionary."""
        context = await self._get_user_context(user_id)
        return context.to_dict()
    
    async def _extract_topics_from_messages(self, messages: List[ChatMessage]) -> List[str]:
        """Extract topics from conversation messages."""
        text = " ".join([msg.content for msg in messages])
        topics = []
        
        # Simple keyword-based extraction (replace with NLP)
        for subject, keywords in self.subject_keywords.items():
            for keyword in keywords:
                if keyword.lower() in text.lower():
                    topics.append(subject)
                    break
        
        return list(set(topics))
    
    async def _classify_subject(self, topic: str) -> str:
        """Classify topic into educational subject."""
        topic_lower = topic.lower()
        
        for subject, keywords in self.subject_keywords.items():
            if any(keyword in topic_lower for keyword in keywords):
                return subject
        
        return "general"
    
    async def _suggest_grades_for_topic(self, topic: str, user_context: UserContext) -> List[str]:
        """Suggest appropriate grades for topic."""
        # Use user's profile grades if available
        if user_context.profile and 'grades' in user_context.profile:
            return user_context.profile['grades']
        
        # Default grade suggestions
        return ["6", "7", "8"]
    
    async def _get_related_keywords(self, topic: str) -> List[str]:
        """Get related keywords for a topic."""
        # Simple related keyword mapping (replace with more sophisticated approach)
        keyword_map = {
            'mathematics': ['numbers', 'equations', 'problem-solving'],
            'science': ['experiments', 'observation', 'hypothesis'],
            'english': ['reading', 'writing', 'communication'],
            'history': ['timeline', 'events', 'civilization'],
            'geography': ['maps', 'locations', 'climate']
        }
        
        return keyword_map.get(topic, [topic])
    
    async def _build_enhanced_prompt(self, context: ConversationContext) -> str:
        """Build enhanced prompt with full context."""
        prompt_parts = []
        
        # Base instruction
        prompt_parts.append(
            "You are an intelligent educational AI assistant for teachers. "
            "Provide helpful, accurate, and engaging responses that support teaching and learning."
        )
        
        # User context
        if context.user_context.profile:
            profile = context.user_context.profile
            subjects = profile.get('subjects', [])
            grades = profile.get('grades', [])
            
            if subjects:
                prompt_parts.append(f"The teacher teaches: {', '.join(subjects)}")
            if grades:
                prompt_parts.append(f"For grades: {', '.join(grades)}")
        
        # Conversation history
        if context.recent_messages:
            prompt_parts.append("\\nRecent conversation:")
            for msg in context.recent_messages[-5:]:  # Last 5 messages
                role = "Teacher" if msg.message_type == MessageType.USER else "AI"
                prompt_parts.append(f"{role}: {msg.content}")
        
        # Current topics
        if context.extracted_topics:
            prompt_parts.append(f"\\nCurrent topics of discussion: {', '.join(context.extracted_topics)}")
        
        # Intent
        if context.intent:
            prompt_parts.append(f"\\nUser intent: {context.intent}")
        
        # Latest message
        if context.recent_messages:
            latest_msg = context.recent_messages[-1]
            if latest_msg.message_type == MessageType.USER:
                prompt_parts.append(f"\\nCurrent question/request: {latest_msg.content}")
        
        return "\\n".join(prompt_parts)
    
    async def _generate_session_title(self, 
                                    session_type: ChatSessionType, 
                                    context: Optional[Dict[str, Any]]) -> str:
        """Generate intelligent session title."""
        type_titles = {
            ChatSessionType.GENERAL: "General Teaching Discussion",
            ChatSessionType.LESSON_PLANNING: "Lesson Planning Session",
            ChatSessionType.CONTENT_CREATION: "Content Creation Workshop",
            ChatSessionType.PROBLEM_SOLVING: "Problem Solving Session",
            ChatSessionType.QUICK_HELP: "Quick Teaching Help",
            ChatSessionType.SUBJECT_SPECIFIC: "Subject-Focused Discussion"
        }
        
        base_title = type_titles.get(session_type, "Chat Session")
        
        # Add context if available
        if context and 'subject' in context:
            return f"{context['subject']} - {base_title}"
        
        return base_title
    
    async def _determine_session_type(self, 
                                    message_preview: Optional[str], 
                                    user_id: str) -> ChatSessionType:
        """Determine optimal session type based on message and user context."""
        if not message_preview:
            return ChatSessionType.GENERAL
        
        message_lower = message_preview.lower()
        
        # Keyword-based classification
        if any(word in message_lower for word in ['lesson', 'plan', 'curriculum']):
            return ChatSessionType.LESSON_PLANNING
        elif any(word in message_lower for word in ['create', 'generate', 'make', 'write']):
            return ChatSessionType.CONTENT_CREATION
        elif any(word in message_lower for word in ['problem', 'issue', 'help', 'stuck']):
            return ChatSessionType.PROBLEM_SOLVING
        elif any(word in message_lower for word in ['quick', 'fast', 'brief']):
            return ChatSessionType.QUICK_HELP
        
        return ChatSessionType.GENERAL
    
    async def _track_chat_analytics(self, 
                                  session_id: str, 
                                  user_id: Optional[str],
                                  user_message: str, 
                                  ai_response: IntelligentChatResponse):
        """Track analytics for chat interaction."""
        if user_id:
            # Track with dashboard service
            await self.dashboard_service.track_activity(
                user_id=user_id,
                activity_type=ActivityType.CHAT,
                title="AI Chat Interaction",
                description=f"Discussed: {user_message[:50]}...",
                metadata={
                    'session_id': session_id,
                    'suggestions_provided': len(ai_response.suggestions),
                    'topics_provided': len(ai_response.related_topics),
                    'recommendations_provided': len(ai_response.study_recommendations)
                }
            )
    
    async def _generate_follow_up_questions(self, ai_content: str) -> List[ChatSuggestion]:
        """Generate follow-up questions based on AI response."""
        # Simple pattern-based generation (replace with AI)
        suggestions = []
        
        if "explain" in ai_content.lower():
            suggestions.append(ChatSuggestion(
                id=str(uuid.uuid4()),
                suggestion_type=SuggestionType.FOLLOW_UP_QUESTION,
                content="Can you provide a specific example?",
                priority=1
            ))
        
        if "concept" in ai_content.lower():
            suggestions.append(ChatSuggestion(
                id=str(uuid.uuid4()),
                suggestion_type=SuggestionType.FOLLOW_UP_QUESTION,
                content="How can I teach this to my students?",
                priority=1
            ))
        
        return suggestions
    
    async def _generate_subject_suggestions(self, context: ConversationContext) -> List[ChatSuggestion]:
        """Generate subject-specific suggestions."""
        suggestions = []
        
        if context.user_context.profile:
            subjects = context.user_context.profile.get('subjects', [])
            
            for subject in subjects[:2]:  # Top 2 subjects
                suggestions.append(ChatSuggestion(
                    id=str(uuid.uuid4()),
                    suggestion_type=SuggestionType.STUDY_SUGGESTION,
                    content=f"Create {subject} lesson materials",
                    metadata={'subject': subject},
                    priority=2
                ))
        
        return suggestions
    
    async def _generate_study_suggestions(self, topics: List[str]) -> List[ChatSuggestion]:
        """Generate study suggestions based on topics."""
        suggestions = []
        
        for topic in topics[:3]:  # Top 3 topics
            suggestions.append(ChatSuggestion(
                id=str(uuid.uuid4()),
                suggestion_type=SuggestionType.STUDY_SUGGESTION,
                content=f"Explore {topic} activities",
                metadata={'topic': topic},
                priority=2
            ))
        
        return suggestions
    
    async def _analyze_intent(self, message: str, user_context: UserContext) -> str:
        """Analyze user intent from message."""
        message_lower = message.lower()
        
        # Simple intent classification
        if any(word in message_lower for word in ['create', 'generate', 'make']):
            return 'content_creation'
        elif any(word in message_lower for word in ['plan', 'schedule', 'organize']):
            return 'lesson_planning'
        elif any(word in message_lower for word in ['help', 'how', 'what', 'why']):
            return 'question_answering'
        elif any(word in message_lower for word in ['problem', 'issue', 'trouble']):
            return 'problem_solving'
        
        return 'general_conversation'
    
    async def _analyze_sentiment(self, messages: List[ChatMessage]) -> Dict[str, Any]:
        """Analyze sentiment of conversation."""
        # Simple sentiment analysis (replace with NLP)
        user_messages = [msg.content for msg in messages if msg.message_type == MessageType.USER]
        
        if not user_messages:
            return {'overall': 'neutral', 'confidence': 0.5}
        
        # Basic keyword-based sentiment
        positive_words = ['good', 'great', 'excellent', 'helpful', 'thanks', 'perfect']
        negative_words = ['bad', 'terrible', 'confused', 'difficult', 'problem', 'stuck']
        
        text = " ".join(user_messages).lower()
        positive_count = sum(1 for word in positive_words if word in text)
        negative_count = sum(1 for word in negative_words if word in text)
        
        if positive_count > negative_count:
            return {'overall': 'positive', 'confidence': 0.7}
        elif negative_count > positive_count:
            return {'overall': 'negative', 'confidence': 0.7}
        else:
            return {'overall': 'neutral', 'confidence': 0.6}
    
    async def _calculate_engagement_metrics(self, messages: List[ChatMessage]) -> Dict[str, Any]:
        """Calculate engagement metrics."""
        if not messages:
            return {'engagement_score': 0, 'avg_message_length': 0}
        
        user_messages = [msg for msg in messages if msg.message_type == MessageType.USER]
        
        avg_length = sum(len(msg.content) for msg in user_messages) / len(user_messages) if user_messages else 0
        
        # Simple engagement score based on message count and length
        engagement_score = min(1.0, (len(user_messages) * avg_length) / 1000)
        
        return {
            'engagement_score': engagement_score,
            'avg_message_length': avg_length,
            'total_user_messages': len(user_messages),
            'total_ai_messages': len(messages) - len(user_messages)
        }
    
    def _calculate_session_duration(self, messages: List[ChatMessage]) -> int:
        """Calculate session duration in seconds."""
        if len(messages) < 2:
            return 0
        
        start_time = messages[0].timestamp
        end_time = messages[-1].timestamp
        
        return int((end_time - start_time).total_seconds())
    
    def _generate_session_title_simple(self, session_type: ChatSessionType, context: Optional[Dict[str, Any]]) -> str:
        """Generate a simple session title based on type and context."""
        if context and 'subject' in context:
            subject = context['subject'].title()
            return f"{subject} Discussion"
        
        type_titles = {
            ChatSessionType.GENERAL: "General Chat",
            ChatSessionType.SUBJECT_SPECIFIC: "Subject Discussion", 
            ChatSessionType.LESSON_PLANNING: "Lesson Planning",
            ChatSessionType.QUICK_HELP: "Quick Help",
            ChatSessionType.CONTENT_CREATION: "Content Creation"
        }
        
        return type_titles.get(session_type, "Chat Session")
    
    def _determine_session_type_simple(self, message_preview: Optional[str]) -> ChatSessionType:
        """Determine session type from message preview."""
        if not message_preview:
            return ChatSessionType.GENERAL
            
        message_lower = message_preview.lower()
        
        if any(word in message_lower for word in ['lesson', 'plan', 'teach', 'curriculum']):
            return ChatSessionType.LESSON_PLANNING
        elif any(word in message_lower for word in ['math', 'science', 'english', 'history']):
            return ChatSessionType.SUBJECT_SPECIFIC
        else:
            return ChatSessionType.GENERAL
    
    def _get_user_context_dict_simple(self, user_id: str) -> Dict[str, Any]:
        """Get simple user context dictionary."""
        return {
            "user_preferences": {
                "learning_style": "visual",
                "difficulty_level": "intermediate"
            },
            "recent_topics": ["mathematics", "teaching"],
            "subjects": ["Mathematics", "Science"],
            "grades": ["8", "9"]
        }
