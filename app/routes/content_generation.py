"""
Content Generation API Routes
RESTful endpoints for educational content generation.
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

from flask import Blueprint, request, jsonify, current_app
from google.cloud import firestore

from app.models.content_generation import (
    ContentType, Subject, Grade, ContentLength, Difficulty, Language,
    ContentParameters, ExportRequest, ExportFormat,
    GeneratedContent
)
from app.services.content_generation_service import ContentGenerationService
from app.services.content_export_service import ContentExportService

logger = logging.getLogger(__name__)

# Create blueprint
content_generation_bp = Blueprint('content_generation', __name__, url_prefix='/api/v1/content')

# Initialize services
content_service = ContentGenerationService()
export_service = ContentExportService()

@content_generation_bp.route('/generate', methods=['POST'])
def generate_content():
    """
    Generate educational content based on parameters.
    
    Universal endpoint for generating stories, worksheets, quizzes, 
    lesson plans, and visual aids.
    """
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['content_type', 'subject', 'grade', 'topic']
        missing_fields = [field for field in required_fields if field not in data]
        if missing_fields:
            return jsonify({
                'error': 'Missing required fields',
                'missing_fields': missing_fields,
                'required_fields': required_fields
            }), 400
        
        # Validate content type
        try:
            content_type = ContentType(data['content_type'])
        except ValueError:
            return jsonify({
                'error': 'Invalid content type',
                'provided': data['content_type'],
                'valid_types': [ct.value for ct in ContentType]
            }), 400
        
        # Validate subject
        try:
            subject = Subject(data['subject'])
        except ValueError:
            return jsonify({
                'error': 'Invalid subject',
                'provided': data['subject'],
                'valid_subjects': [s.value for s in Subject]
            }), 400
        
        # Validate grade
        try:
            grade = Grade(data['grade'])
        except ValueError:
            return jsonify({
                'error': 'Invalid grade',
                'provided': data['grade'],
                'valid_grades': [g.value for g in Grade]
            }), 400
        
        # Create content parameters
        parameters = ContentParameters(
            content_type=content_type,
            subject=subject,
            grade=grade,
            topic=data['topic'],
            length=ContentLength(data.get('length', 'medium')),
            difficulty=Difficulty(data.get('difficulty', 'grade_appropriate')),
            language=Language(data.get('language', 'english')),
            cultural_context=data.get('cultural_context', 'indian'),
            learning_objectives=data.get('learning_objectives', []),
            keywords=data.get('keywords', []),
            tone=data.get('tone', 'friendly'),
            include_examples=data.get('include_examples', True),
            include_activities=data.get('include_activities', True),
            custom_requirements=data.get('custom_requirements', [])
        )
        
        # Add content-type specific parameters
        if content_type == ContentType.STORY:
            parameters.story_elements = {
                'character_names': data.get('character_names', []),
                'setting_preference': data.get('setting_preference', ''),
                'story_theme': data.get('story_theme', ''),
                'include_moral': data.get('include_moral', True),
                'interactive_elements': data.get('interactive_elements', False)
            }
        elif content_type == ContentType.WORKSHEET:
            parameters.worksheet_elements = {
                'problem_types': data.get('problem_types', []),
                'number_of_problems': data.get('number_of_problems', 10),
                'include_solutions': data.get('include_solutions', True),
                'difficulty_progression': data.get('difficulty_progression', True)
            }
        elif content_type == ContentType.QUIZ:
            parameters.quiz_elements = {
                'question_types': data.get('question_types', ['mcq']),
                'number_of_questions': data.get('number_of_questions', 10),
                'time_limit': data.get('time_limit', 30),
                'randomize_options': data.get('randomize_options', True),
                'include_explanations': data.get('include_explanations', True)
            }
        elif content_type == ContentType.LESSON_PLAN:
            parameters.lesson_elements = {
                'duration': data.get('duration', 45),
                'class_size': data.get('class_size', 30),
                'available_materials': data.get('available_materials', []),
                'teaching_methods': data.get('teaching_methods', []),
                'assessment_type': data.get('assessment_type', 'formative')
            }
        elif content_type == ContentType.VISUAL_AID:
            parameters.visual_elements = {
                'visual_type': data.get('visual_type', 'diagram'),
                'color_preferences': data.get('color_preferences', []),
                'complexity_level': data.get('complexity_level', 'simple'),
                'interactive_features': data.get('interactive_features', False)
            }
        
        # Generate content
        generated_content = content_service.generate_content(parameters)
        
        if generated_content:
            return jsonify({
                'success': True,
                'content_id': generated_content.id,
                'content_type': generated_content.content_type,
                'content': generated_content.content.to_dict(),
                'parameters': generated_content.parameters.to_dict(),
                'quality_assessment': generated_content.quality_assessment.to_dict() if generated_content.quality_assessment else None,
                'word_count': generated_content.word_count,
                'generation_time': generated_content.generation_time,
                'created_at': generated_content.created_at.isoformat() if generated_content.created_at else None,
                'message': f"{content_type.value.replace('_', ' ').title()} generated successfully"
            }), 201
        else:
            return jsonify({
                'error': 'Failed to generate content',
                'message': 'Content generation service returned no content'
            }), 500
            
    except Exception as e:
        logger.error(f"Error generating content: {str(e)}")
        return jsonify({
            'error': 'Content generation failed',
            'message': str(e)
        }), 500

@content_generation_bp.route('/history', methods=['GET'])
def get_content_history():
    """
    Get user's content generation history with filtering and pagination.
    """
    try:
        # Get query parameters
        user_id = request.args.get('user_id')
        content_type = request.args.get('content_type')
        subject = request.args.get('subject')
        grade = request.args.get('grade')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        page = int(request.args.get('page', 1))
        page_size = int(request.args.get('page_size', 20))
        
        # Build Firestore query
        db = firestore.Client()
        query = db.collection('generated_content')
        
        # Apply filters
        if user_id:
            query = query.where('user_id', '==', user_id)
        if content_type:
            query = query.where('content_type', '==', content_type)
        if subject:
            query = query.where('parameters.subject', '==', subject)
        if grade:
            query = query.where('parameters.grade', '==', grade)
        if start_date:
            start_datetime = datetime.fromisoformat(start_date)
            query = query.where('created_at', '>=', start_datetime)
        if end_date:
            end_datetime = datetime.fromisoformat(end_date)
            query = query.where('created_at', '<=', end_datetime)
        
        # Order by creation date (newest first)
        query = query.order_by('created_at', direction=firestore.Query.DESCENDING)
        
        # Apply pagination
        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)
        
        # Execute query
        docs = query.stream()
        content_list = []
        
        for doc in docs:
            doc_data = doc.to_dict()
            content_summary = {
                'id': doc.id,
                'content_type': doc_data.get('content_type'),
                'subject': doc_data.get('parameters', {}).get('subject'),
                'grade': doc_data.get('parameters', {}).get('grade'),
                'topic': doc_data.get('parameters', {}).get('topic'),
                'title': _extract_content_title(doc_data),
                'word_count': doc_data.get('word_count'),
                'quality_score': _extract_quality_score(doc_data),
                'created_at': doc_data.get('created_at').isoformat() if doc_data.get('created_at') else None,
                'generation_time': doc_data.get('generation_time')
            }
            content_list.append(content_summary)
        
        # Get total count for pagination
        total_query = db.collection('generated_content')
        if user_id:
            total_query = total_query.where('user_id', '==', user_id)
        if content_type:
            total_query = total_query.where('content_type', '==', content_type)
        
        total_count = len(list(total_query.stream()))
        total_pages = (total_count + page_size - 1) // page_size
        
        return jsonify({
            'success': True,
            'content': content_list,
            'pagination': {
                'page': page,
                'page_size': page_size,
                'total_count': total_count,
                'total_pages': total_pages,
                'has_next': page < total_pages,
                'has_prev': page > 1
            },
            'filters_applied': {
                'content_type': content_type,
                'subject': subject,
                'grade': grade,
                'start_date': start_date,
                'end_date': end_date
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Error retrieving content history: {str(e)}")
        return jsonify({
            'error': 'Failed to retrieve content history',
            'message': str(e)
        }), 500

@content_generation_bp.route('/<content_id>', methods=['GET'])
def get_content_details(content_id: str):
    """
    Get detailed information about a specific generated content.
    """
    try:
        db = firestore.Client()
        doc_ref = db.collection('generated_content').document(content_id)
        doc = doc_ref.get()
        
        if not doc.exists:
            return jsonify({
                'error': 'Content not found',
                'content_id': content_id
            }), 404
        
        doc_data = doc.to_dict()
        
        return jsonify({
            'success': True,
            'id': doc.id,
            'content_type': doc_data.get('content_type'),
            'content': doc_data.get('content'),
            'parameters': doc_data.get('parameters'),
            'quality_assessment': doc_data.get('quality_assessment'),
            'word_count': doc_data.get('word_count'),
            'generation_time': doc_data.get('generation_time'),
            'created_at': doc_data.get('created_at').isoformat() if doc_data.get('created_at') else None,
            'user_id': doc_data.get('user_id')
        }), 200
        
    except Exception as e:
        logger.error(f"Error retrieving content {content_id}: {str(e)}")
        return jsonify({
            'error': 'Failed to retrieve content',
            'message': str(e)
        }), 500

@content_generation_bp.route('/<content_id>/export', methods=['POST'])
def export_content(content_id: str):
    """
    Export generated content to specified format (PDF, DOCX, HTML, JSON).
    """
    try:
        data = request.get_json()
        
        # Validate export format
        export_format = data.get('format', 'html').lower()
        try:
            format_enum = ExportFormat(export_format)
        except ValueError:
            return jsonify({
                'error': 'Invalid export format',
                'provided': export_format,
                'valid_formats': [f.value for f in ExportFormat]
            }), 400
        
        # Get content from database
        db = firestore.Client()
        doc_ref = db.collection('generated_content').document(content_id)
        doc = doc_ref.get()
        
        if not doc.exists:
            return jsonify({
                'error': 'Content not found',
                'content_id': content_id
            }), 404
        
        # Convert document data to GeneratedContent object
        doc_data = doc.to_dict()
        generated_content = _doc_data_to_generated_content(doc_data, content_id)
        
        # Create export request
        export_request = ExportRequest(
            format=format_enum,
            include_solutions=data.get('include_solutions', True),
            include_metadata=data.get('include_metadata', True),
            custom_styling=data.get('custom_styling', {}),
            page_orientation=data.get('page_orientation', 'portrait'),
            font_size=data.get('font_size', 12)
        )
        
        # Export content
        export_result = export_service.export_content(generated_content, export_request)
        
        return jsonify({
            'success': True,
            'export_data': export_result,
            'content_id': content_id,
            'export_format': export_format
        }), 200
        
    except Exception as e:
        logger.error(f"Error exporting content {content_id}: {str(e)}")
        return jsonify({
            'error': 'Content export failed',
            'message': str(e)
        }), 500

@content_generation_bp.route('/<content_id>/variants', methods=['POST'])
def generate_content_variants(content_id: str):
    """
    Generate variants of existing content with different parameters.
    """
    try:
        data = request.get_json()
        
        # Get original content
        db = firestore.Client()
        doc_ref = db.collection('generated_content').document(content_id)
        doc = doc_ref.get()
        
        if not doc.exists:
            return jsonify({
                'error': 'Original content not found',
                'content_id': content_id
            }), 404
        
        doc_data = doc.to_dict()
        original_parameters = doc_data.get('parameters', {})
        
        # Get variant parameters
        variant_type = data.get('variant_type', 'difficulty')  # difficulty, length, style, language
        variant_count = min(data.get('variant_count', 3), 5)  # Max 5 variants
        
        variants = []
        
        for i in range(variant_count):
            # Modify parameters based on variant type
            new_parameters = original_parameters.copy()
            
            if variant_type == 'difficulty':
                difficulties = ['easy', 'medium', 'hard']
                new_parameters['difficulty'] = difficulties[i % len(difficulties)]
            elif variant_type == 'length':
                lengths = ['short', 'medium', 'long']
                new_parameters['length'] = lengths[i % len(lengths)]
            elif variant_type == 'style':
                tones = ['formal', 'friendly', 'encouraging', 'playful']
                new_parameters['tone'] = tones[i % len(tones)]
            elif variant_type == 'language':
                languages = ['english', 'hindi', 'hinglish']
                new_parameters['language'] = languages[i % len(languages)]
            
            # Create new ContentParameters object
            parameters = ContentParameters.from_dict(new_parameters)
            
            # Generate variant
            variant_content = content_service.generate_content(parameters)
            
            if variant_content:
                variants.append({
                    'id': variant_content.id,
                    'content_type': variant_content.content_type,
                    'content': variant_content.content.to_dict(),
                    'parameters': variant_content.parameters.to_dict(),
                    'quality_assessment': variant_content.quality_assessment.to_dict() if variant_content.quality_assessment else None,
                    'word_count': variant_content.word_count,
                    'generation_time': variant_content.generation_time,
                    'variant_number': i + 1,
                    'variant_type': variant_type
                })
        
        return jsonify({
            'success': True,
            'original_content_id': content_id,
            'variant_type': variant_type,
            'variants_generated': len(variants),
            'variants': variants
        }), 201
        
    except Exception as e:
        logger.error(f"Error generating variants for content {content_id}: {str(e)}")
        return jsonify({
            'error': 'Variant generation failed',
            'message': str(e)
        }), 500

@content_generation_bp.route('/templates', methods=['GET'])
def get_content_templates():
    """
    Get available content templates for different subjects and grades.
    """
    try:
        subject = request.args.get('subject')
        grade = request.args.get('grade')
        content_type = request.args.get('content_type')
        
        templates = content_service.get_content_templates(
            subject=subject,
            grade=grade,
            content_type=content_type
        )
        
        return jsonify({
            'success': True,
            'templates': templates,
            'filters': {
                'subject': subject,
                'grade': grade,
                'content_type': content_type
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Error retrieving content templates: {str(e)}")
        return jsonify({
            'error': 'Failed to retrieve templates',
            'message': str(e)
        }), 500

@content_generation_bp.route('/suggestions', methods=['POST'])
def get_content_suggestions():
    """
    Get AI-powered suggestions for content topics and parameters.
    """
    try:
        data = request.get_json()
        
        # Validate required fields
        if 'subject' not in data or 'grade' not in data:
            return jsonify({
                'error': 'Missing required fields',
                'required_fields': ['subject', 'grade']
            }), 400
        
        suggestions = content_service.get_content_suggestions(
            subject=data['subject'],
            grade=data['grade'],
            content_type=data.get('content_type'),
            current_topic=data.get('current_topic'),
            learning_objectives=data.get('learning_objectives', []),
            student_interests=data.get('student_interests', [])
        )
        
        return jsonify({
            'success': True,
            'suggestions': suggestions,
            'context': {
                'subject': data['subject'],
                'grade': data['grade'],
                'content_type': data.get('content_type')
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Error generating content suggestions: {str(e)}")
        return jsonify({
            'error': 'Failed to generate suggestions',
            'message': str(e)
        }), 500

@content_generation_bp.route('/statistics', methods=['GET'])
def get_content_statistics():
    """
    Get statistics about content generation usage.
    """
    try:
        user_id = request.args.get('user_id')
        time_range = request.args.get('time_range', '30d')  # 7d, 30d, 90d, 1y
        
        stats = content_service.get_content_statistics(
            user_id=user_id,
            time_range=time_range
        )
        
        return jsonify({
            'success': True,
            'statistics': stats,
            'time_range': time_range,
            'user_id': user_id
        }), 200
        
    except Exception as e:
        logger.error(f"Error retrieving content statistics: {str(e)}")
        return jsonify({
            'error': 'Failed to retrieve statistics',
            'message': str(e)
        }), 500

# Helper functions

def _extract_content_title(doc_data: Dict[str, Any]) -> str:
    """Extract title from content data."""
    content = doc_data.get('content', {})
    if 'title' in content:
        return content['title']
    else:
        topic = doc_data.get('parameters', {}).get('topic', 'Unknown Topic')
        content_type = doc_data.get('content_type', 'content')
        return f"{content_type.replace('_', ' ').title()}: {topic}"

def _extract_quality_score(doc_data: Dict[str, Any]) -> Optional[float]:
    """Extract overall quality score from quality assessment."""
    quality_assessment = doc_data.get('quality_assessment')
    if quality_assessment and 'overall_score' in quality_assessment:
        return quality_assessment['overall_score']
    return None

def _doc_data_to_generated_content(doc_data: Dict[str, Any], content_id: str) -> GeneratedContent:
    """Convert Firestore document data to GeneratedContent object."""
    # This is a simplified conversion - in practice, you'd need to properly
    # reconstruct all the nested objects (ContentParameters, specific content types, etc.)
    
    # For now, create a minimal GeneratedContent object
    from app.models.content_generation import GeneratedContent, ContentParameters
    
    parameters = ContentParameters.from_dict(doc_data.get('parameters', {}))
    
    # Create a mock content object - in practice, you'd reconstruct the specific content type
    class MockContent:
        def __init__(self, data):
            self.__dict__.update(data)
        
        def to_dict(self):
            return self.__dict__
    
    content = MockContent(doc_data.get('content', {}))
    
    generated_content = GeneratedContent(
        id=content_id,
        content_type=doc_data.get('content_type'),
        parameters=parameters,
        content=content,
        word_count=doc_data.get('word_count'),
        generation_time=doc_data.get('generation_time'),
        created_at=doc_data.get('created_at'),
        user_id=doc_data.get('user_id')
    )
    
    return generated_content

# Error handlers
@content_generation_bp.errorhandler(400)
def bad_request(error):
    return jsonify({
        'error': 'Bad Request',
        'message': 'Invalid request data'
    }), 400

@content_generation_bp.errorhandler(404)
def not_found(error):
    return jsonify({
        'error': 'Not Found',
        'message': 'Requested resource not found'
    }), 404

@content_generation_bp.errorhandler(500)
def internal_error(error):
    return jsonify({
        'error': 'Internal Server Error',
        'message': 'An unexpected error occurred'
    }), 500
