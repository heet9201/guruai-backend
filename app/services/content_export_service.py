"""
Content Export Service
Service for exporting generated content to various formats (PDF, DOCX, HTML).
"""

import logging
import io
import json
from typing import Dict, Any, Optional, List
from datetime import datetime

from app.models.content_generation import (
    GeneratedContent, ExportRequest, ExportFormat,
    StoryContent, WorksheetContent, QuizContent, LessonPlanContent, VisualAidContent
)

logger = logging.getLogger(__name__)

class ContentExportService:
    """Service for exporting generated content to different formats."""
    
    def __init__(self):
        """Initialize the content export service."""
        pass
    
    def export_content(self, content: GeneratedContent, export_request: ExportRequest) -> Dict[str, Any]:
        """
        Export content to specified format.
        
        Args:
            content: Generated content to export
            export_request: Export configuration
            
        Returns:
            Dictionary with export data or file information
        """
        try:
            export_format = export_request.format.lower()
            
            if export_format == ExportFormat.PDF.value:
                return self._export_to_pdf(content, export_request)
            elif export_format == ExportFormat.DOCX.value:
                return self._export_to_docx(content, export_request)
            elif export_format == ExportFormat.HTML.value:
                return self._export_to_html(content, export_request)
            elif export_format == ExportFormat.JSON.value:
                return self._export_to_json(content, export_request)
            else:
                raise ValueError(f"Unsupported export format: {export_format}")
                
        except Exception as e:
            logger.error(f"Error exporting content {content.id} to {export_request.format}: {str(e)}")
            raise
    
    def _export_to_pdf(self, content: GeneratedContent, export_request: ExportRequest) -> Dict[str, Any]:
        """Export content to PDF format."""
        
        # Generate HTML first, then convert to PDF
        html_content = self._generate_html(content, export_request)
        
        # For now, return HTML content with instructions for PDF conversion
        # In production, you would use libraries like WeasyPrint or Puppeteer
        return {
            'format': 'pdf',
            'status': 'ready',
            'content_type': 'application/pdf',
            'filename': f"{self._generate_filename(content)}.pdf",
            'html_content': html_content,  # For now, until PDF generation is implemented
            'message': 'PDF generation framework ready - implement with WeasyPrint or similar',
            'size_estimate': f"{len(html_content)} bytes (HTML preview)",
            'generated_at': datetime.utcnow().isoformat()
        }
    
    def _export_to_docx(self, content: GeneratedContent, export_request: ExportRequest) -> Dict[str, Any]:
        """Export content to DOCX format."""
        
        # Generate structured content for DOCX
        docx_data = self._generate_docx_structure(content, export_request)
        
        # For now, return structured data that can be used with python-docx
        return {
            'format': 'docx',
            'status': 'ready',
            'content_type': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'filename': f"{self._generate_filename(content)}.docx",
            'document_structure': docx_data,
            'message': 'DOCX generation framework ready - implement with python-docx',
            'size_estimate': f"{len(str(docx_data))} bytes (structure preview)",
            'generated_at': datetime.utcnow().isoformat()
        }
    
    def _export_to_html(self, content: GeneratedContent, export_request: ExportRequest) -> Dict[str, Any]:
        """Export content to HTML format."""
        
        html_content = self._generate_html(content, export_request)
        
        return {
            'format': 'html',
            'status': 'ready',
            'content_type': 'text/html',
            'filename': f"{self._generate_filename(content)}.html",
            'content': html_content,
            'size': len(html_content),
            'generated_at': datetime.utcnow().isoformat()
        }
    
    def _export_to_json(self, content: GeneratedContent, export_request: ExportRequest) -> Dict[str, Any]:
        """Export content to JSON format."""
        
        # Create comprehensive JSON export
        export_data = {
            'metadata': {
                'content_id': content.id,
                'content_type': content.content_type,
                'generated_at': content.created_at.isoformat() if content.created_at else None,
                'exported_at': datetime.utcnow().isoformat(),
                'parameters': content.parameters.to_dict(),
                'quality_assessment': content.quality_assessment.to_dict() if content.quality_assessment else None,
                'word_count': content.word_count,
                'generation_time': content.generation_time
            },
            'content': content.content.to_dict(),
            'export_settings': export_request.to_dict()
        }
        
        json_content = json.dumps(export_data, indent=2, ensure_ascii=False)
        
        return {
            'format': 'json',
            'status': 'ready',
            'content_type': 'application/json',
            'filename': f"{self._generate_filename(content)}.json",
            'content': json_content,
            'size': len(json_content),
            'generated_at': datetime.utcnow().isoformat()
        }
    
    def _generate_html(self, content: GeneratedContent, export_request: ExportRequest) -> str:
        """Generate HTML representation of content."""
        
        # Get styling
        styles = self._get_html_styles(export_request.custom_styling)
        
        # Generate content-specific HTML
        if content.content_type == 'story':
            body_html = self._generate_story_html(content.content, export_request)
        elif content.content_type == 'worksheet':
            body_html = self._generate_worksheet_html(content.content, export_request)
        elif content.content_type == 'quiz':
            body_html = self._generate_quiz_html(content.content, export_request)
        elif content.content_type == 'lesson_plan':
            body_html = self._generate_lesson_plan_html(content.content, export_request)
        elif content.content_type == 'visual_aid':
            body_html = self._generate_visual_aid_html(content.content, export_request)
        else:
            body_html = f"<p>Content type {content.content_type} not supported for HTML export</p>"
        
        # Create complete HTML document
        html_template = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>{self._get_content_title(content)}</title>
            <style>
                {styles}
            </style>
        </head>
        <body>
            <div class="container">
                <header>
                    <h1>{self._get_content_title(content)}</h1>
                    <div class="metadata">
                        <p><strong>Subject:</strong> {content.parameters.subject}</p>
                        <p><strong>Grade:</strong> {content.parameters.grade}</p>
                        <p><strong>Topic:</strong> {content.parameters.topic}</p>
                        <p><strong>Generated on:</strong> {content.created_at.strftime('%B %d, %Y') if content.created_at else 'Unknown'}</p>
                    </div>
                </header>
                <main>
                    {body_html}
                </main>
                <footer>
                    <p>Generated by Sahayak AI Assistant</p>
                    <p>Export Date: {datetime.utcnow().strftime('%B %d, %Y at %I:%M %p')}</p>
                </footer>
            </div>
        </body>
        </html>
        """
        
        return html_template
    
    def _generate_story_html(self, story: StoryContent, export_request: ExportRequest) -> str:
        """Generate HTML for story content."""
        
        html = f"""
        <div class="story-content">
            <h2>{story.title}</h2>
            
            <div class="story-info">
                <p><strong>Characters:</strong> {', '.join(story.characters)}</p>
                <p><strong>Setting:</strong> {story.setting}</p>
            </div>
            
            <div class="story-text">
                {self._format_text_with_paragraphs(story.plot)}
            </div>
            
            {f'<div class="moral"><h3>Moral of the Story</h3><p>{story.moral}</p></div>' if story.moral else ''}
            
            {self._format_decision_points(story.decision_points) if story.decision_points else ''}
            
            {self._format_vocabulary(story.vocabulary_words) if story.vocabulary_words else ''}
        </div>
        """
        
        return html
    
    def _generate_worksheet_html(self, worksheet: WorksheetContent, export_request: ExportRequest) -> str:
        """Generate HTML for worksheet content."""
        
        html = f"""
        <div class="worksheet-content">
            <h2>{worksheet.title}</h2>
            
            <div class="instructions">
                <h3>Instructions</h3>
                <p>{worksheet.instructions}</p>
            </div>
            
            <div class="problems">
                <h3>Problems</h3>
                {self._format_problems(worksheet.problems)}
            </div>
            
            {self._format_answer_key(worksheet.answer_key, export_request.include_solutions) if worksheet.answer_key and export_request.include_solutions else ''}
            
            {self._format_solutions(worksheet.solutions, export_request.include_solutions) if worksheet.solutions and export_request.include_solutions else ''}
        </div>
        """
        
        return html
    
    def _generate_quiz_html(self, quiz: QuizContent, export_request: ExportRequest) -> str:
        """Generate HTML for quiz content."""
        
        html = f"""
        <div class="quiz-content">
            <h2>{quiz.title}</h2>
            
            <div class="instructions">
                <h3>Instructions</h3>
                <p>{quiz.instructions}</p>
                {f'<p><strong>Time Limit:</strong> {quiz.time_limit} minutes</p>' if quiz.time_limit else ''}
            </div>
            
            <div class="questions">
                <h3>Questions</h3>
                {self._format_quiz_questions(quiz.questions)}
            </div>
            
            {self._format_quiz_answer_key(quiz.answer_key, export_request.include_solutions) if quiz.answer_key and export_request.include_solutions else ''}
        </div>
        """
        
        return html
    
    def _generate_lesson_plan_html(self, lesson_plan: LessonPlanContent, export_request: ExportRequest) -> str:
        """Generate HTML for lesson plan content."""
        
        html = f"""
        <div class="lesson-plan-content">
            <h2>{lesson_plan.title}</h2>
            
            <div class="lesson-info">
                <p><strong>Duration:</strong> {lesson_plan.duration} minutes</p>
                <p><strong>Materials:</strong> {', '.join(lesson_plan.materials)}</p>
            </div>
            
            <div class="objectives">
                <h3>Learning Objectives</h3>
                <ul>
                    {' '.join([f'<li>{obj}</li>' for obj in lesson_plan.objectives])}
                </ul>
            </div>
            
            <div class="introduction">
                <h3>Introduction</h3>
                <p>{lesson_plan.introduction}</p>
            </div>
            
            <div class="main-activities">
                <h3>Main Activities</h3>
                {self._format_lesson_activities(lesson_plan.main_activities)}
            </div>
            
            <div class="assessment">
                <h3>Assessment</h3>
                <p>{lesson_plan.assessment}</p>
            </div>
            
            {f'<div class="homework"><h3>Homework</h3><p>{lesson_plan.homework}</p></div>' if lesson_plan.homework else ''}
            
            {self._format_differentiation(lesson_plan.differentiation) if lesson_plan.differentiation else ''}
            
            {self._format_extensions(lesson_plan.extensions) if lesson_plan.extensions else ''}
        </div>
        """
        
        return html
    
    def _generate_visual_aid_html(self, visual_aid: VisualAidContent, export_request: ExportRequest) -> str:
        """Generate HTML for visual aid content."""
        
        html = f"""
        <div class="visual-aid-content">
            <h2>{visual_aid.title}</h2>
            
            <div class="description">
                <p>{visual_aid.description}</p>
            </div>
            
            {self._format_svg_content(visual_aid.svg_content) if visual_aid.svg_content else ''}
            
            {self._format_drawing_instructions(visual_aid.drawing_instructions) if visual_aid.drawing_instructions else ''}
            
            {self._format_color_palette(visual_aid.color_palette) if visual_aid.color_palette else ''}
        </div>
        """
        
        return html
    
    def _generate_docx_structure(self, content: GeneratedContent, export_request: ExportRequest) -> Dict[str, Any]:
        """Generate structured data for DOCX creation."""
        
        structure = {
            'title': self._get_content_title(content),
            'metadata': {
                'subject': content.parameters.subject,
                'grade': content.parameters.grade,
                'topic': content.parameters.topic,
                'generated_date': content.created_at.strftime('%B %d, %Y') if content.created_at else 'Unknown'
            },
            'sections': []
        }
        
        # Add content-specific sections
        if content.content_type == 'story':
            structure['sections'] = self._get_story_docx_sections(content.content)
        elif content.content_type == 'worksheet':
            structure['sections'] = self._get_worksheet_docx_sections(content.content, export_request)
        elif content.content_type == 'quiz':
            structure['sections'] = self._get_quiz_docx_sections(content.content, export_request)
        elif content.content_type == 'lesson_plan':
            structure['sections'] = self._get_lesson_plan_docx_sections(content.content)
        elif content.content_type == 'visual_aid':
            structure['sections'] = self._get_visual_aid_docx_sections(content.content)
        
        return structure
    
    def _get_html_styles(self, custom_styling: Optional[Dict[str, Any]]) -> str:
        """Get CSS styles for HTML export."""
        
        default_styles = """
        body {
            font-family: 'Arial', sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
        }
        
        .container {
            background: white;
            border-radius: 8px;
            padding: 30px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        
        h1, h2, h3 {
            color: #2c3e50;
            border-bottom: 2px solid #3498db;
            padding-bottom: 5px;
        }
        
        .metadata {
            background: #f8f9fa;
            padding: 15px;
            border-radius: 5px;
            margin: 20px 0;
        }
        
        .metadata p {
            margin: 5px 0;
        }
        
        .story-content, .worksheet-content, .quiz-content, .lesson-plan-content, .visual-aid-content {
            margin: 20px 0;
        }
        
        .problems, .questions {
            margin: 20px 0;
        }
        
        .problem, .question {
            background: #f8f9fa;
            padding: 15px;
            margin: 10px 0;
            border-radius: 5px;
            border-left: 4px solid #3498db;
        }
        
        .answer-key, .solutions {
            background: #e8f5e8;
            padding: 15px;
            margin: 20px 0;
            border-radius: 5px;
            border-left: 4px solid #27ae60;
        }
        
        .moral {
            background: #fff3cd;
            padding: 15px;
            margin: 20px 0;
            border-radius: 5px;
            border-left: 4px solid #ffc107;
        }
        
        .vocabulary {
            background: #e7f3ff;
            padding: 15px;
            margin: 20px 0;
            border-radius: 5px;
        }
        
        .vocabulary-word {
            font-weight: bold;
            color: #0066cc;
        }
        
        .decision-points {
            background: #f0f0f0;
            padding: 15px;
            margin: 20px 0;
            border-radius: 5px;
        }
        
        ul, ol {
            padding-left: 20px;
        }
        
        footer {
            text-align: center;
            margin-top: 40px;
            padding-top: 20px;
            border-top: 1px solid #eee;
            color: #666;
            font-size: 0.9em;
        }
        
        @media print {
            body { margin: 0; padding: 0; }
            .container { box-shadow: none; }
        }
        """
        
        # Apply custom styling if provided
        if custom_styling:
            # Add custom styles here
            pass
        
        return default_styles
    
    def _get_content_title(self, content: GeneratedContent) -> str:
        """Get title for the content."""
        if hasattr(content.content, 'title'):
            return content.content.title
        else:
            return f"{content.content_type.replace('_', ' ').title()}: {content.parameters.topic}"
    
    def _generate_filename(self, content: GeneratedContent) -> str:
        """Generate filename for export."""
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        safe_topic = content.parameters.topic.replace(' ', '_').replace('/', '_')
        return f"{content.content_type}_{safe_topic}_{timestamp}"
    
    def _format_text_with_paragraphs(self, text: str) -> str:
        """Format text with HTML paragraphs."""
        paragraphs = text.split('\n\n')
        return ''.join([f'<p>{p.strip()}</p>' for p in paragraphs if p.strip()])
    
    def _format_problems(self, problems: List[Dict[str, Any]]) -> str:
        """Format worksheet problems as HTML."""
        html = ""
        for problem in problems:
            html += f"""
            <div class="problem">
                <p><strong>Problem {problem.get('number', '')}:</strong> {problem.get('question', '')}</p>
                {f"<p><em>Points: {problem.get('points', '')}</em></p>" if problem.get('points') else ''}
            </div>
            """
        return html
    
    def _format_quiz_questions(self, questions: List[Dict[str, Any]]) -> str:
        """Format quiz questions as HTML."""
        html = ""
        for question in questions:
            html += f"""
            <div class="question">
                <p><strong>Question {question.get('number', '')}:</strong> {question.get('question', '')}</p>
                {self._format_question_options(question)}
                {f"<p><em>Points: {question.get('points', '')}</em></p>" if question.get('points') else ''}
            </div>
            """
        return html
    
    def _format_question_options(self, question: Dict[str, Any]) -> str:
        """Format question options based on type."""
        q_type = question.get('type', '')
        options = question.get('options', [])
        
        if q_type == 'mcq' and options:
            return "<ol type='A'>" + "".join([f"<li>{option}</li>" for option in options]) + "</ol>"
        elif q_type == 'true_false':
            return "<p>True / False</p>"
        elif q_type == 'fill_blanks':
            return "<p>Fill in the blank: ___________</p>"
        else:
            return ""
    
    def _format_answer_key(self, answer_key: List[Dict[str, Any]], include: bool) -> str:
        """Format answer key as HTML."""
        if not include:
            return ""
        
        html = '<div class="answer-key"><h3>Answer Key</h3>'
        for answer in answer_key:
            html += f"<p><strong>{answer.get('number', '')}:</strong> {answer.get('answer', '')}</p>"
        html += '</div>'
        return html
    
    def _format_solutions(self, solutions: List[Dict[str, Any]], include: bool) -> str:
        """Format solutions as HTML."""
        if not include:
            return ""
        
        html = '<div class="solutions"><h3>Solutions</h3>'
        for solution in solutions:
            html += f"""
            <div class="solution">
                <p><strong>Problem {solution.get('number', '')}:</strong></p>
                <p>{solution.get('solution', '')}</p>
            </div>
            """
        html += '</div>'
        return html
    
    def _format_quiz_answer_key(self, answer_key: List[Dict[str, Any]], include: bool) -> str:
        """Format quiz answer key as HTML."""
        if not include:
            return ""
        
        html = '<div class="answer-key"><h3>Answer Key</h3>'
        for answer in answer_key:
            html += f"""
            <p><strong>Question {answer.get('number', '')}:</strong> {answer.get('answer', '')}</p>
            {f"<p><em>Explanation:</em> {answer.get('explanation', '')}</p>" if answer.get('explanation') else ''}
            """
        html += '</div>'
        return html
    
    def _format_decision_points(self, decision_points: List[Dict[str, Any]]) -> str:
        """Format story decision points as HTML."""
        html = '<div class="decision-points"><h3>Interactive Decision Points</h3>'
        for i, dp in enumerate(decision_points, 1):
            html += f"""
            <div class="decision-point">
                <p><strong>Decision Point {i}:</strong> {dp.get('point', '')}</p>
                <p><strong>Context:</strong> {dp.get('context', '')}</p>
                <p><strong>Options:</strong></p>
                <ul>
                    {' '.join([f'<li>{option}</li>' for option in dp.get('options', [])])}
                </ul>
            </div>
            """
        html += '</div>'
        return html
    
    def _format_vocabulary(self, vocabulary: List[Dict[str, str]]) -> str:
        """Format vocabulary words as HTML."""
        html = '<div class="vocabulary"><h3>Vocabulary Words</h3>'
        for word_def in vocabulary:
            html += f'<p><span class="vocabulary-word">{word_def.get("word", "")}:</span> {word_def.get("definition", "")}</p>'
        html += '</div>'
        return html
    
    def _format_lesson_activities(self, activities: List[Dict[str, Any]]) -> str:
        """Format lesson activities as HTML."""
        html = ""
        for activity in activities:
            html += f"""
            <div class="activity">
                <h4>{activity.get('activity', '')}</h4>
                <p><strong>Duration:</strong> {activity.get('duration', '')} minutes</p>
                <p>{activity.get('description', '')}</p>
                {f"<p><strong>Materials:</strong> {', '.join(activity.get('materials', []))}</p>" if activity.get('materials') else ''}
            </div>
            """
        return html
    
    def _format_differentiation(self, differentiation: List[str]) -> str:
        """Format differentiation strategies as HTML."""
        html = '<div class="differentiation"><h3>Differentiation Strategies</h3><ul>'
        for strategy in differentiation:
            html += f'<li>{strategy}</li>'
        html += '</ul></div>'
        return html
    
    def _format_extensions(self, extensions: List[str]) -> str:
        """Format extension activities as HTML."""
        html = '<div class="extensions"><h3>Extension Activities</h3><ul>'
        for extension in extensions:
            html += f'<li>{extension}</li>'
        html += '</ul></div>'
        return html
    
    def _format_svg_content(self, svg_content: str) -> str:
        """Format SVG content as HTML."""
        return f'<div class="svg-content">{svg_content}</div>'
    
    def _format_drawing_instructions(self, instructions: List[str]) -> str:
        """Format drawing instructions as HTML."""
        html = '<div class="drawing-instructions"><h3>Drawing Instructions</h3><ol>'
        for instruction in instructions:
            html += f'<li>{instruction}</li>'
        html += '</ol></div>'
        return html
    
    def _format_color_palette(self, colors: List[str]) -> str:
        """Format color palette as HTML."""
        html = '<div class="color-palette"><h3>Color Palette</h3><div class="colors">'
        for color in colors:
            html += f'<span style="background-color: {color}; padding: 10px; margin: 5px; border: 1px solid #ccc;">{color}</span>'
        html += '</div></div>'
        return html
    
    # DOCX structure methods (simplified versions)
    def _get_story_docx_sections(self, story: StoryContent) -> List[Dict[str, Any]]:
        """Get DOCX sections for story content."""
        return [
            {'type': 'heading', 'level': 2, 'text': story.title},
            {'type': 'paragraph', 'text': f"Characters: {', '.join(story.characters)}"},
            {'type': 'paragraph', 'text': f"Setting: {story.setting}"},
            {'type': 'paragraph', 'text': story.plot},
            {'type': 'heading', 'level': 3, 'text': 'Moral'},
            {'type': 'paragraph', 'text': story.moral or 'No specific moral provided'}
        ]
    
    def _get_worksheet_docx_sections(self, worksheet: WorksheetContent, export_request: ExportRequest) -> List[Dict[str, Any]]:
        """Get DOCX sections for worksheet content."""
        sections = [
            {'type': 'heading', 'level': 2, 'text': worksheet.title},
            {'type': 'heading', 'level': 3, 'text': 'Instructions'},
            {'type': 'paragraph', 'text': worksheet.instructions}
        ]
        
        # Add problems
        sections.append({'type': 'heading', 'level': 3, 'text': 'Problems'})
        for problem in worksheet.problems:
            sections.append({'type': 'paragraph', 'text': f"Problem {problem.get('number', '')}: {problem.get('question', '')}"})
        
        return sections
    
    def _get_quiz_docx_sections(self, quiz: QuizContent, export_request: ExportRequest) -> List[Dict[str, Any]]:
        """Get DOCX sections for quiz content."""
        sections = [
            {'type': 'heading', 'level': 2, 'text': quiz.title},
            {'type': 'heading', 'level': 3, 'text': 'Instructions'},
            {'type': 'paragraph', 'text': quiz.instructions}
        ]
        
        # Add questions
        sections.append({'type': 'heading', 'level': 3, 'text': 'Questions'})
        for question in quiz.questions:
            sections.append({'type': 'paragraph', 'text': f"Question {question.get('number', '')}: {question.get('question', '')}"})
        
        return sections
    
    def _get_lesson_plan_docx_sections(self, lesson_plan: LessonPlanContent) -> List[Dict[str, Any]]:
        """Get DOCX sections for lesson plan content."""
        return [
            {'type': 'heading', 'level': 2, 'text': lesson_plan.title},
            {'type': 'paragraph', 'text': f"Duration: {lesson_plan.duration} minutes"},
            {'type': 'heading', 'level': 3, 'text': 'Learning Objectives'},
            {'type': 'list', 'items': lesson_plan.objectives},
            {'type': 'heading', 'level': 3, 'text': 'Introduction'},
            {'type': 'paragraph', 'text': lesson_plan.introduction}
        ]
    
    def _get_visual_aid_docx_sections(self, visual_aid: VisualAidContent) -> List[Dict[str, Any]]:
        """Get DOCX sections for visual aid content."""
        return [
            {'type': 'heading', 'level': 2, 'text': visual_aid.title},
            {'type': 'paragraph', 'text': visual_aid.description},
            {'type': 'heading', 'level': 3, 'text': 'Drawing Instructions'},
            {'type': 'list', 'items': visual_aid.drawing_instructions or []}
        ]
