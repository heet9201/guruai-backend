"""
Intelligent Chat API routes.
"""
import json
import logging
from datetime import datetime
from flask import Blueprint, request, jsonify, g
from typing import Dict, Any

from app.services.intelligent_chat_service import IntelligentChatService
from app.models.chat import ChatSessionType, MessageType
from app.utils.middleware import require_json, validate_required_fields
from app.utils.auth_middleware import token_required
from app.utils.response_helpers import success_response, error_response

logger = logging.getLogger(__name__)

# Create blueprint
intelligent_chat_bp = Blueprint('intelligent_chat', __name__)

# Initialize service
chat_service = IntelligentChatService()

@intelligent_chat_bp.route('/api/v1/chat/intelligent', methods=['POST'])
@token_required
@require_json
@validate_required_fields(['message', 'session_id'])
def send_intelligent_message():
    """Send an intelligent chat message."""
    try:
        data = request.get_json()
        message = data['message']
        session_id = data['session_id']
        user_id = g.current_user.get('id')
        context = data.get('context', {})
        
        logger.info(f"Intelligent chat request from user {user_id}: {message[:50]}...")
        
        # Send intelligent message (sync call since the service should handle async internally)
        response = chat_service.send_intelligent_message(
            message=message,
            session_id=session_id,
            user_id=user_id,
            context=context
        )
        
        return success_response(
            data=response.to_dict(),
            message="Intelligent response generated successfully"
        )
        
    except Exception as e:
        logger.error(f"Error in intelligent chat: {str(e)}")
        return error_response(
            message="Failed to generate intelligent response",
            error=str(e),
            status_code=500
        )

@intelligent_chat_bp.route('/api/v1/chat/sessions', methods=['POST'])
@token_required
@require_json
def create_chat_session():
    """Create a new intelligent chat session."""
    try:
        data = request.get_json()
        title = data.get('title')
        session_type = data.get('type', 'general')
        initial_context = data.get('context', {})
        user_id = g.current_user.get('id')
        
        # Convert string to enum
        try:
            session_type_enum = ChatSessionType(session_type)
        except ValueError:
            session_type_enum = ChatSessionType.GENERAL
        
        logger.info(f"Creating chat session for user {user_id}, type: {session_type}")
        
        # Create session
        session = chat_service.create_intelligent_session(
            title=title,
            user_id=user_id,
            session_type=session_type_enum,
            initial_context=initial_context
        )
        
        return success_response(
            data=session.to_dict(),
            message="Chat session created successfully"
        )
        
    except Exception as e:
        logger.error(f"Error creating chat session: {str(e)}")
        return error_response(
            message="Failed to create chat session",
            error=str(e),
            status_code=500
        )

@intelligent_chat_bp.route('/api/v1/chat/sessions/continue', methods=['POST'])
@token_required
@require_json
def continue_or_create_session():
    """Continue existing session or create new one."""
    try:
        data = request.get_json()
        last_session_id = data.get('last_session_id')
        message_preview = data.get('message_preview')
        user_id = g.current_user.get('id')
        
        logger.info(f"Continue/create session for user {user_id}")
        
        # Continue or create session
        session = chat_service.continue_or_create_session(
            user_id=user_id,
            last_session_id=last_session_id,
            message_preview=message_preview
        )
        
        return success_response(
            data=session.to_dict(),
            message="Session continued or created successfully"
        )
        
    except Exception as e:
        logger.error(f"Error continuing session: {str(e)}")
        return error_response(
            message="Failed to continue session",
            error=str(e),
            status_code=500
        )

@intelligent_chat_bp.route('/api/v1/chat/sessions/<session_id>/messages', methods=['GET'])
@token_required
def get_session_history(session_id: str):
    """Get chat history for a session."""
    try:
        page = request.args.get('page', 1, type=int)
        limit = request.args.get('limit', 50, type=int)
        user_id = g.current_user.get('id')
        
        logger.info(f"Getting session history for {session_id}, page {page}")
        
        # Get history
        import asyncio
        messages, total = asyncio.run(chat_service.get_session_history(
            session_id=session_id,
            page=page,
            limit=limit
        ))
        
        return success_response(
            data={
                'messages': [msg.to_dict() for msg in messages],
                'pagination': {
                    'page': page,
                    'limit': limit,
                    'total': total,
                    'has_next': (page * limit) < total
                }
            },
            message="Session history retrieved successfully"
        )
        
    except Exception as e:
        logger.error(f"Error getting session history: {str(e)}")
        return error_response(
            message="Failed to retrieve session history",
            error=str(e),
            status_code=500
        )

@intelligent_chat_bp.route('/api/v1/chat/sessions', methods=['GET'])
@token_required
def get_user_sessions():
    """Get user's chat sessions."""
    try:
        limit = request.args.get('limit', 20, type=int)
        user_id = g.current_user.get('id')
        
        logger.info(f"Getting sessions for user {user_id}")
        
        # Get sessions
        import asyncio
        sessions = asyncio.run(chat_service.get_user_sessions(
            user_id=user_id,
            limit=limit
        ))
        
        return success_response(
            data={
                'sessions': [session.to_dict() for session in sessions],
                'total': len(sessions)
            },
            message="User sessions retrieved successfully"
        )
        
    except Exception as e:
        logger.error(f"Error getting user sessions: {str(e)}")
        return error_response(
            message="Failed to retrieve user sessions",
            error=str(e),
            status_code=500
        )

@intelligent_chat_bp.route('/api/v1/chat/suggestions', methods=['POST'])
@token_required
@require_json
@validate_required_fields(['session_id'])
def get_personalized_suggestions():
    """Get personalized suggestions."""
    try:
        data = request.get_json()
        session_id = data['session_id']
        current_message = data.get('current_message')
        user_id = g.current_user.get('id')
        
        logger.info(f"Getting suggestions for session {session_id}")
        
        # Get suggestions
        suggestions = chat_service.get_personalized_suggestions(
            session_id=session_id,
            user_id=user_id,
            current_message=current_message
        )
        
        logger.info(f"Generated {len(suggestions)} suggestions")
        
        # Group suggestions by type
        grouped_suggestions = {}
        for suggestion in suggestions:
            logger.info(f"Processing suggestion: {suggestion}")
            suggestion_type = suggestion.suggestion_type.value
            if suggestion_type not in grouped_suggestions:
                grouped_suggestions[suggestion_type] = []
            grouped_suggestions[suggestion_type].append(suggestion.to_dict())
        
        return success_response(
            data={
                'suggestions': grouped_suggestions,
                'total': len(suggestions)
            },
            message="Suggestions generated successfully"
        )
        
    except Exception as e:
        logger.error(f"Error getting suggestions: {str(e)}")
        return error_response(
            message="Failed to generate suggestions",
            error=str(e),
            status_code=500
        )

@intelligent_chat_bp.route('/api/v1/chat/typing-suggestions', methods=['POST'])
@token_required
@require_json
@validate_required_fields(['partial_message', 'session_id'])
def get_typing_suggestions():
    """Get real-time typing suggestions."""
    try:
        data = request.get_json()
        partial_message = data['partial_message']
        session_id = data['session_id']
        user_id = g.current_user.get('id')
        suggestion_count = data.get('suggestion_count', 5)
        
        # Simple typing suggestions based on partial message
        suggestions = []
        
        # Subject-specific completions
        if 'math' in partial_message.lower():
            suggestions.extend([
                "mathematics lesson plan",
                "math worksheets for grade",
                "mathematical concepts explanation"
            ])
        elif 'science' in partial_message.lower():
            suggestions.extend([
                "science experiment ideas",
                "scientific method explanation",
                "science project topics"
            ])
        elif 'lesson' in partial_message.lower():
            suggestions.extend([
                "lesson plan template",
                "lesson objectives examples",
                "lesson activity ideas"
            ])
        elif 'create' in partial_message.lower():
            suggestions.extend([
                "create educational content",
                "create story for students",
                "create worksheet template"
            ])
        
        # Generic helpful suggestions
        if not suggestions:
            suggestions = [
                "How can I help you today?",
                "What subject are you teaching?",
                "Need help with lesson planning?",
                "Looking for content ideas?",
                "Want to create educational materials?"
            ]
        
        return success_response(
            data={
                'suggestions': suggestions[:suggestion_count],
                'partial_message': partial_message
            },
            message="Typing suggestions generated"
        )
        
    except Exception as e:
        logger.error(f"Error getting typing suggestions: {str(e)}")
        return error_response(
            message="Failed to generate typing suggestions",
            error=str(e),
            status_code=500
        )

@intelligent_chat_bp.route('/api/v1/chat/sessions/<session_id>/analysis', methods=['GET'])
@token_required
def analyze_conversation(session_id: str):
    """Analyze conversation for insights."""
    try:
        user_id = g.current_user.get('id')
        
        logger.info(f"Analyzing conversation for session {session_id}")
        
        # Analyze conversation
        import asyncio
        analysis = asyncio.run(chat_service.analyze_conversation(session_id))
        
        return success_response(
            data=analysis,
            message="Conversation analysis completed"
        )
        
    except Exception as e:
        logger.error(f"Error analyzing conversation: {str(e)}")
        return error_response(
            message="Failed to analyze conversation",
            error=str(e),
            status_code=500
        )

@intelligent_chat_bp.route('/api/v1/chat/context/<user_id>', methods=['GET'])
@token_required
def get_user_context(user_id: str):
    """Get user context for chat personalization."""
    try:
        # Verify user can access this context
        current_user_id = g.current_user.get('id')
        if current_user_id != user_id:
            return error_response(
                message="Unauthorized access to user context",
                status_code=403
            )
        
        logger.info(f"Getting context for user {user_id}")
        
        # Get user context
        import asyncio
        context = asyncio.run(chat_service._get_user_context(user_id))
        
        return success_response(
            data=context.to_dict(),
            message="User context retrieved successfully"
        )
        
    except Exception as e:
        logger.error(f"Error getting user context: {str(e)}")
        return error_response(
            message="Failed to retrieve user context",
            error=str(e),
            status_code=500
        )

# Batch endpoint for multiple operations
@intelligent_chat_bp.route('/api/v1/chat/batch', methods=['POST'])
@token_required
@require_json
@validate_required_fields(['requests'])
def batch_chat_requests():
    """Handle multiple chat requests in a single call."""
    try:
        data = request.get_json()
        requests_data = data['requests']
        user_id = g.current_user.get('id')
        
        logger.info(f"Processing batch chat requests for user {user_id}")
        
        results = []
        
        for req in requests_data:
            request_type = req.get('type')
            request_data = req.get('data', {})
            
            try:
                if request_type == 'send_message':
                    # Handle send message
                    response = chat_service.send_intelligent_message(
                        message=request_data['message'],
                        session_id=request_data['session_id'],
                        user_id=user_id,
                        context=request_data.get('context', {})
                    )
                    results.append({
                        'type': request_type,
                        'success': True,
                        'data': response.to_dict()
                    })
                    
                elif request_type == 'get_suggestions':
                    # Handle get suggestions
                    suggestions = chat_service.get_personalized_suggestions(
                        session_id=request_data['session_id'],
                        user_id=user_id,
                        current_message=request_data.get('context_message')
                    )
                    results.append({
                        'type': request_type,
                        'success': True,
                        'data': [s.to_dict() for s in suggestions]
                    })
                    
                else:
                    results.append({
                        'type': request_type,
                        'success': False,
                        'error': f"Unknown request type: {request_type}"
                    })
                    
            except Exception as e:
                results.append({
                    'type': request_type,
                    'success': False,
                    'error': str(e)
                })
        
        return success_response(
            data={'results': results},
            message="Batch requests processed"
        )
        
    except Exception as e:
        logger.error(f"Error processing batch requests: {str(e)}")
        return error_response(
            message="Failed to process batch requests",
            error=str(e),
            status_code=500
        )

# AI-powered features endpoints
@intelligent_chat_bp.route('/api/v1/ai/sentiment-analysis', methods=['POST'])
@token_required
@require_json
@validate_required_fields(['text'])
def analyze_sentiment():
    """Analyze sentiment of text."""
    try:
        data = request.get_json()
        text = data['text']
        context = data.get('context', 'general')
        
        # Simple sentiment analysis (replace with actual NLP service)
        positive_words = ['good', 'great', 'excellent', 'helpful', 'thanks', 'perfect', 'love', 'amazing']
        negative_words = ['bad', 'terrible', 'confused', 'difficult', 'problem', 'stuck', 'hate', 'awful']
        
        text_lower = text.lower()
        positive_count = sum(1 for word in positive_words if word in text_lower)
        negative_count = sum(1 for word in negative_words if word in text_lower)
        
        if positive_count > negative_count:
            sentiment = 'positive'
            confidence = min(0.9, 0.5 + (positive_count * 0.1))
        elif negative_count > positive_count:
            sentiment = 'negative'
            confidence = min(0.9, 0.5 + (negative_count * 0.1))
        else:
            sentiment = 'neutral'
            confidence = 0.6
        
        return success_response(
            data={
                'sentiment': sentiment,
                'confidence': confidence,
                'details': {
                    'positive_indicators': positive_count,
                    'negative_indicators': negative_count
                }
            },
            message="Sentiment analysis completed"
        )
        
    except Exception as e:
        logger.error(f"Error in sentiment analysis: {str(e)}")
        return error_response(
            message="Failed to analyze sentiment",
            error=str(e),
            status_code=500
        )

@intelligent_chat_bp.route('/api/v1/ai/topic-extraction', methods=['POST'])
@token_required
@require_json
@validate_required_fields(['messages'])
def extract_topics():
    """Extract topics from conversation messages."""
    try:
        data = request.get_json()
        messages = data['messages']
        extract_subjects = data.get('extract_subjects', True)
        extract_concepts = data.get('extract_concepts', True)
        
        # Combine all message content
        text = " ".join([msg.get('content', '') for msg in messages])
        
        topics = []
        
        if extract_subjects:
            # Subject extraction
            subject_keywords = {
                'mathematics': ['math', 'algebra', 'geometry', 'calculus', 'arithmetic'],
                'science': ['physics', 'chemistry', 'biology', 'experiment'],
                'english': ['grammar', 'literature', 'writing', 'reading'],
                'history': ['historical', 'timeline', 'civilization', 'events'],
                'geography': ['maps', 'locations', 'climate', 'countries']
            }
            
            for subject, keywords in subject_keywords.items():
                if any(keyword in text.lower() for keyword in keywords):
                    topics.append({
                        'type': 'subject',
                        'topic': subject,
                        'confidence': 0.8
                    })
        
        if extract_concepts:
            # Simple concept extraction
            concepts = ['lesson planning', 'content creation', 'student engagement', 'assessment']
            for concept in concepts:
                if concept.lower() in text.lower():
                    topics.append({
                        'type': 'concept',
                        'topic': concept,
                        'confidence': 0.7
                    })
        
        return success_response(
            data={'topics': topics},
            message="Topic extraction completed"
        )
        
    except Exception as e:
        logger.error(f"Error in topic extraction: {str(e)}")
        return error_response(
            message="Failed to extract topics",
            error=str(e),
            status_code=500
        )

@intelligent_chat_bp.route('/api/v1/ai/intent-recognition', methods=['POST'])
@token_required
@require_json
@validate_required_fields(['message'])
def recognize_intent():
    """Recognize user intent from message."""
    try:
        data = request.get_json()
        message = data['message']
        user_context = data.get('user_context', {})
        possible_intents = data.get('possible_intents', [])
        
        message_lower = message.lower()
        
        # Intent classification
        intent_keywords = {
            'question_answering': ['what', 'how', 'why', 'when', 'where', 'explain', 'tell me'],
            'content_creation_request': ['create', 'generate', 'make', 'write', 'design'],
            'lesson_planning_help': ['plan', 'lesson', 'curriculum', 'schedule', 'organize'],
            'explanation_request': ['explain', 'clarify', 'help understand', 'break down'],
            'problem_solving': ['problem', 'issue', 'stuck', 'trouble', 'difficulty'],
            'general_conversation': ['hello', 'hi', 'thanks', 'goodbye', 'chat']
        }
        
        detected_intent = 'general_conversation'
        confidence = 0.5
        
        for intent, keywords in intent_keywords.items():
            if possible_intents and intent not in possible_intents:
                continue
                
            matches = sum(1 for keyword in keywords if keyword in message_lower)
            if matches > 0:
                detected_intent = intent
                confidence = min(0.9, 0.6 + (matches * 0.1))
                break
        
        return success_response(
            data={
                'intent': detected_intent,
                'confidence': confidence,
                'alternatives': [
                    {'intent': intent, 'confidence': confidence * 0.8}
                    for intent in possible_intents[:2]
                    if intent != detected_intent
                ]
            },
            message="Intent recognition completed"
        )
        
    except Exception as e:
        logger.error(f"Error in intent recognition: {str(e)}")
        return error_response(
            message="Failed to recognize intent",
            error=str(e),
            status_code=500
        )

@intelligent_chat_bp.route('/api/v1/ai/summarize-conversation', methods=['POST'])
@token_required
@require_json
@validate_required_fields(['session_id'])
def summarize_conversation():
    """Summarize conversation for insights."""
    try:
        data = request.get_json()
        session_id = data['session_id']
        include_key_topics = data.get('include_key_topics', True)
        include_action_items = data.get('include_action_items', True)
        include_learning_outcomes = data.get('include_learning_outcomes', True)
        
        # Get conversation analysis
        import asyncio
        analysis = asyncio.run(chat_service.analyze_conversation(session_id))
        
        summary = {
            'session_id': session_id,
            'summary_generated_at': datetime.utcnow().isoformat(),
            'conversation_length': analysis.get('total_messages', 0),
            'duration_minutes': analysis.get('session_duration', 0) // 60
        }
        
        if include_key_topics:
            summary['key_topics'] = analysis.get('topics_discussed', [])
        
        if include_action_items:
            # Simple action item extraction
            summary['action_items'] = [
                'Review lesson planning strategies',
                'Create educational content',
                'Explore new teaching methods'
            ]
        
        if include_learning_outcomes:
            summary['learning_outcomes'] = [
                'Improved understanding of AI tools for education',
                'Enhanced lesson planning capabilities',
                'Better content creation strategies'
            ]
        
        return success_response(
            data=summary,
            message="Conversation summary generated"
        )
        
    except Exception as e:
        logger.error(f"Error summarizing conversation: {str(e)}")
        return error_response(
            message="Failed to summarize conversation",
            error=str(e),
            status_code=500
        )
