import logging
from app.services.vertex_ai_service import VertexAIService, AIResponse
from app.utils import retry_on_failure, log_execution_time
import base64
import json

logger = logging.getLogger(__name__)

class AIService:
    """Enhanced AI service using Vertex AI with Gemini models."""
    
    def __init__(self):
        self.vertex_ai_service = None
        self._initialized = False
    
    def _ensure_initialized(self):
        """Ensure service is initialized before use."""
        if not self._initialized:
            self._initialize_service()
    
    def _initialize_service(self):
        """Initialize the Vertex AI service."""
        if self._initialized:
            return
            
        try:
            self.vertex_ai_service = VertexAIService()
            self._initialized = True
            logger.info("AI Service initialized with Vertex AI")
        except Exception as e:
            logger.error(f"Failed to initialize AI Service: {str(e)}")
            # Don't raise to allow app to start
            self.vertex_ai_service = None

    @retry_on_failure(max_retries=3)
    @log_execution_time
    def generate_text(self, prompt: str, max_tokens: int = 1000, temperature: float = 0.7, 
                     context: str = None) -> AIResponse:
        """Generate text using Gemini Pro model."""
        try:
            self._ensure_initialized()
            
            if not self.vertex_ai_service:
                return AIResponse(
                    success=False,
                    error="Vertex AI service not available"
                )
            
            # Prepare the full prompt with context if provided
            full_prompt = prompt
            if context:
                full_prompt = f"Context: {context}\\n\\nPrompt: {prompt}"
            
            response = self.vertex_ai_service.generate_text(
                prompt=full_prompt,
                max_tokens=max_tokens,
                temperature=temperature
            )
            
            if response.success:
                logger.info(f"Text generated successfully in {response.execution_time:.3f}s")
            else:
                logger.error(f"Text generation failed: {response.error}")
            
            return response
            
        except Exception as e:
            logger.error(f"Text generation error: {str(e)}")
            return AIResponse(
                success=False,
                error=f"Text generation failed: {str(e)}"
            )

    @retry_on_failure(max_retries=2)
    @log_execution_time
    def analyze_image(self, image_data: bytes, prompt: str = "Describe this image in detail", 
                     format_instructions: str = None) -> AIResponse:
        """Analyze image using Gemini Pro Vision."""
        try:
            self._ensure_initialized()
            
            if not self.vertex_ai_service:
                return AIResponse(
                    success=False,
                    error="Vertex AI service not available"
                )
            
            # Enhance prompt with format instructions if provided
            full_prompt = prompt
            if format_instructions:
                full_prompt = f"{prompt}\\n\\nFormat your response as follows: {format_instructions}"
            
            response = self.vertex_ai_service.analyze_image(
                image_data=image_data,
                prompt=full_prompt
            )
            
            if response.success:
                logger.info(f"Image analyzed successfully in {response.execution_time:.3f}s")
            else:
                logger.error(f"Image analysis failed: {response.error}")
            
            return response
            
        except Exception as e:
            logger.error(f"Image analysis error: {str(e)}")
            return AIResponse(
                success=False,
                error=f"Image analysis failed: {str(e)}"
            )

    @retry_on_failure(max_retries=2)
    @log_execution_time
    def generate_response(self, message: str, user_id: str = None, context: dict = None, 
                         max_tokens: int = 1000, temperature: float = 0.7) -> str:
        """Generate a chat response using AI."""
        try:
            # Prepare the context-aware prompt
            full_prompt = message
            if context and context.get('previous_messages'):
                conversation_context = "\\n".join([
                    f"User: {msg.get('user', '')}" if msg.get('type') == 'user' 
                    else f"Assistant: {msg.get('assistant', '')}"
                    for msg in context['previous_messages'][-5:]  # Last 5 messages for context
                ])
                full_prompt = f"Previous conversation:\\n{conversation_context}\\n\\nCurrent message: {message}"
            
            response = self.generate_text(
                prompt=full_prompt,
                max_tokens=max_tokens,
                temperature=temperature
            )
            
            if response.success:
                return response.data
            else:
                raise Exception(response.error)
                
        except Exception as e:
            logger.error(f"Response generation error: {str(e)}")
            return "I apologize, but I'm having trouble processing your request right now. Please try again."

    @retry_on_failure(max_retries=2)
    @log_execution_time
    def generate_summary(self, text: str, summary_type: str = "concise", max_length: int = 200) -> str:
        """Generate a summary of the provided text."""
        try:
            summary_prompts = {
                "concise": f"Provide a concise summary of the following text in about {max_length} characters:\\n\\n{text}",
                "bullet_points": f"Summarize the following text as bullet points (max {max_length} characters):\\n\\n{text}",
                "detailed": f"Provide a detailed summary of the following text (max {max_length} characters):\\n\\n{text}",
                "key_points": f"Extract the key points from the following text (max {max_length} characters):\\n\\n{text}"
            }
            
            prompt = summary_prompts.get(summary_type, summary_prompts["concise"])
            
            response = self.generate_text(
                prompt=prompt,
                max_tokens=max_length // 3,  # Rough estimate for token to character ratio
                temperature=0.3  # Lower temperature for more focused summaries
            )
            
            if response.success:
                return response.data
            else:
                raise Exception(response.error)
                
        except Exception as e:
            logger.error(f"Summary generation error: {str(e)}")
            return f"Unable to generate summary: {str(e)}"

    def get_service_status(self) -> dict:
        """Get comprehensive status of AI services."""
        try:
            self._ensure_initialized()
            
            if not self.vertex_ai_service:
                return {
                    'status': 'unavailable',
                    'error': 'Vertex AI service not initialized',
                    'vertex_ai_initialized': False,
                    'models_initialized': False
                }
            
            # Get quota status from Vertex AI service
            quota_status = self.vertex_ai_service.get_quota_status()
            
            # Perform health check
            health_status = self.vertex_ai_service.health_check()
            
            return {
                'status': 'healthy' if health_status else 'unhealthy',
                'vertex_ai_initialized': self.vertex_ai_service._initialized,
                'models_initialized': getattr(self.vertex_ai_service, '_models_initialized', False),
                'quota_status': quota_status,
                'available_features': [
                    'text_generation',
                    'image_analysis'
                ]
            }
            
        except Exception as e:
            logger.error(f"Service status error: {str(e)}")
            return {
                'status': 'error',
                'error': str(e),
                'vertex_ai_initialized': False,
                'models_initialized': False
            }
