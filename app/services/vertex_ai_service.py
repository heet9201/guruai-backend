import logging
import time
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from datetime import datetime, timedelta
import json
import redis
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from ratelimit import limits, sleep_and_retry
from google.cloud import aiplatform
from google.cloud.aiplatform import gapic
from google.cloud.aiplatform.gapic.schema import predict
import google.genai as genai
from google.genai import types
from google.cloud import speech
from google.auth import default
from google.auth.exceptions import DefaultCredentialsError
import requests

logger = logging.getLogger(__name__)

logger = logging.getLogger(__name__)

@dataclass
class AIResponse:
    """Standard response format for AI operations."""
    success: bool
    data: Any = None
    error: str = None
    execution_time: float = None
    model_used: str = None
    tokens_used: int = None

@dataclass
class QuotaInfo:
    """Quota tracking information."""
    feature: str
    used: int
    limit: int
    reset_time: datetime
    
    @property
    def remaining(self) -> int:
        return max(0, self.limit - self.used)
    
    @property
    def is_exceeded(self) -> bool:
        return self.used >= self.limit

class VertexAIError(Exception):
    """Custom exception for Vertex AI operations."""
    pass

class QuotaExceededError(VertexAIError):
    """Raised when API quota is exceeded."""
    pass

class ConnectionPoolManager:
    """Manages connection pooling for Vertex AI services."""
    
    def __init__(self, max_pool_size: int = 10):
        self.max_pool_size = max_pool_size
        self._connections = {}
        self._connection_count = 0
    
    def get_session(self) -> requests.Session:
        """Get a requests session with connection pooling."""
        session = requests.Session()
        adapter = requests.adapters.HTTPAdapter(
            pool_connections=self.max_pool_size,
            pool_maxsize=self.max_pool_size,
            max_retries=3
        )
        session.mount('https://', adapter)
        session.mount('http://', adapter)
        return session

class QuotaManager:
    """Manages API quota tracking and rate limiting."""
    
    def __init__(self, redis_client: redis.Redis):
        self.redis_client = redis_client
    
    def check_quota(self, feature: str, limit: int) -> QuotaInfo:
        """Check current quota usage for a feature."""
        try:
            key = f"quota:{feature}:{datetime.now().strftime('%Y%m%d%H')}"
            used = int(self.redis_client.get(key) or 0)
            reset_time = datetime.now().replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
            
            return QuotaInfo(
                feature=feature,
                used=used,
                limit=limit,
                reset_time=reset_time
            )
        except Exception as e:
            logger.warning(f"Redis quota check failed: {e}, allowing request")
            # Return a default quota info that allows the request
            return QuotaInfo(
                feature=feature,
                used=0,
                limit=limit,
                reset_time=datetime.now() + timedelta(hours=1)
            )
    
    def increment_quota(self, feature: str) -> None:
        """Increment quota usage for a feature."""
        try:
            key = f"quota:{feature}:{datetime.now().strftime('%Y%m%d%H')}"
            self.redis_client.incr(key)
            self.redis_client.expire(key, 3600)  # Expire after 1 hour
        except Exception as e:
            logger.warning(f"Redis quota increment failed: {e}, continuing without quota tracking")

class BaseAIService(ABC):
    """Base class for AI services with common functionality."""
    
    def __init__(self):
        self.project_id = None
        self.location = None
        self.credentials = None
        self.redis_client = None
        self.quota_manager = None
        self.connection_pool = None
        self._initialized = False
    
    def _initialize_service(self):
        """Initialize the AI service with authentication and configuration."""
        if self._initialized:
            return
            
        try:
            from flask import current_app, has_app_context
            
            if not has_app_context():
                logger.warning("No Flask app context available during initialization")
                return
            
            # Get configuration
            self.project_id = current_app.config.get('PROJECT_ID')
            self.location = current_app.config.get('LOCATION', 'asia-south1')
            
            # Initialize authentication
            self._setup_authentication()
            
            # Initialize Vertex AI
            aiplatform.init(project=self.project_id, location=self.location)
            
            # Initialize Redis for quota management
            redis_url = current_app.config.get('REDIS_URL')
            self.redis_client = redis.from_url(redis_url) if redis_url else None
            
            if self.redis_client:
                self.quota_manager = QuotaManager(self.redis_client)
            
            # Initialize connection pool
            max_pool_size = current_app.config.get('MAX_POOL_SIZE', 10)
            self.connection_pool = ConnectionPoolManager(max_pool_size)
            
            self._initialized = True
            logger.info(f"AI Service initialized successfully for project {self.project_id}")
            
        except Exception as e:
            logger.error(f"Failed to initialize AI service: {str(e)}")
            raise VertexAIError(f"Service initialization failed: {str(e)}")
    
    def _setup_authentication(self):
        """Setup Google Cloud authentication."""
        try:
            self.credentials, _ = default()
            logger.info("Google Cloud authentication successful")
        except DefaultCredentialsError as e:
            logger.error(f"Authentication failed: {str(e)}")
            raise VertexAIError(f"Authentication failed: {str(e)}")
    
    def _check_quota(self, feature: str, limit: int) -> None:
        """Check if quota allows for another request."""
        if not self.quota_manager:
            return  # Skip quota check if Redis not available
        
        quota_info = self.quota_manager.check_quota(feature, limit)
        if quota_info.is_exceeded:
            raise QuotaExceededError(
                f"Quota exceeded for {feature}. "
                f"Used: {quota_info.used}/{quota_info.limit}. "
                f"Resets at: {quota_info.reset_time}"
            )
    
    def _increment_quota(self, feature: str) -> None:
        """Increment quota usage."""
        if self.quota_manager:
            self.quota_manager.increment_quota(feature)
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((requests.exceptions.RequestException, VertexAIError))
    )
    def _make_api_call(self, func, *args, **kwargs):
        """Make API call with retry logic."""
        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            execution_time = time.time() - start_time
            logger.info(f"API call successful in {execution_time:.3f}s")
            return result
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"API call failed after {execution_time:.3f}s: {str(e)}")
            
            # Convert known exceptions to our custom exceptions
            if "quota" in str(e).lower() or "rate limit" in str(e).lower():
                raise QuotaExceededError(f"API quota/rate limit exceeded: {str(e)}")
            elif "timeout" in str(e).lower():
                raise VertexAIError(f"API timeout: {str(e)}")
            elif "not found" in str(e).lower():
                raise VertexAIError(f"Resource not found: {str(e)}")
            else:
                raise VertexAIError(f"API call failed: {str(e)}")
    
    def get_quota_status(self) -> Dict[str, QuotaInfo]:
        """Get current quota status for all features."""
        if not self.quota_manager:
            return {}
        
        from flask import current_app
        
        features = {
            'text_generation': current_app.config.get('TEXT_GENERATION_QUOTA', 1000),
            'vision_analysis': current_app.config.get('VISION_ANALYSIS_QUOTA', 500),
            'speech_to_text': current_app.config.get('SPEECH_TO_TEXT_QUOTA', 2000)
        }
        
        return {
            feature: self.quota_manager.check_quota(feature, limit)
            for feature, limit in features.items()
        }
    
    @abstractmethod
    def health_check(self) -> bool:
        """Health check for the service."""
        pass

class VertexAIService(BaseAIService):
    """Vertex AI service with Gemini models integration."""
    
    def __init__(self):
        super().__init__()
        self.client = None
        self.text_model_name = None
        self.vision_model_name = None
        self._models_initialized = False
    
    def _ensure_initialized(self):
        """Ensure service is initialized before use."""
        if not self._initialized:
            self._initialize_service()
        if not self._models_initialized:
            self._initialize_models()
    
    def _initialize_models(self):
        """Initialize Gemini models."""
        if self._models_initialized:
            return
            
        try:
            from flask import current_app, has_app_context
            
            if not has_app_context():
                logger.warning("No Flask app context available during model initialization")
                return
            
            # Initialize the genai client with Vertex AI
            self.client = genai.Client(
                vertexai=True,
                project=self.project_id,
                location=self.location
            )
            
            # Model names for text and vision
            self.text_model_name = current_app.config.get('GEMINI_PRO_MODEL', 'gemini-1.5-pro')
            self.vision_model_name = current_app.config.get('GEMINI_PRO_VISION_MODEL', 'gemini-1.5-pro-vision')
            
            self._models_initialized = True
            logger.info("Gemini client initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize models: {str(e)}")
            raise VertexAIError(f"Model initialization failed: {str(e)}")
    
    @sleep_and_retry
    @limits(calls=100, period=3600)  # 100 calls per hour
    def generate_text(self, prompt: str, max_tokens: int = 1000, temperature: float = 0.7) -> AIResponse:
        """Generate text using Gemini Pro model."""
        start_time = time.time()
        
        try:
            self._ensure_initialized()
            from flask import current_app
            
            # Check quota
            quota_limit = current_app.config.get('TEXT_GENERATION_QUOTA', 1000)
            self._check_quota('text_generation', quota_limit)
            
            # Generate content using the new API with simpler configuration
            response = self.client.models.generate_content(
                model=self.text_model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=temperature,
                    max_output_tokens=max_tokens,
                    top_p=0.8,
                    top_k=40
                )
            )
            
            # Increment quota
            self._increment_quota('text_generation')
            
            execution_time = time.time() - start_time
            
            return AIResponse(
                success=True,
                data=response.text,
                execution_time=execution_time,
                model_used=self.text_model_name,
                tokens_used=len(response.text.split()) if response.text else 0
            )
            
        except QuotaExceededError as e:
            return AIResponse(
                success=False,
                error=str(e),
                execution_time=time.time() - start_time
            )
        except Exception as e:
            logger.error(f"Text generation failed: {str(e)}")
            return AIResponse(
                success=False,
                error=f"Text generation failed: {str(e)}",
                execution_time=time.time() - start_time
            )
    
    @sleep_and_retry
    @limits(calls=50, period=3600)  # 50 calls per hour
    def analyze_image(self, image_data: bytes, prompt: str = "Describe this image") -> AIResponse:
        """Analyze image using Gemini Pro Vision model."""
        start_time = time.time()
        
        try:
            self._ensure_initialized()
            from flask import current_app
            
            # Check quota
            quota_limit = current_app.config.get('VISION_ANALYSIS_QUOTA', 500)
            self._check_quota('vision_analysis', quota_limit)
            
            # Create image part using the new API
            image_part = types.Part(
                inline_data=types.Blob(
                    mime_type="image/jpeg",
                    data=image_data
                )
            )
            
            # Create content with both image and text
            content = types.Content(
                parts=[image_part, types.Part(text=prompt)]
            )
            
            # Generate content
            response = self.client.models.generate_content(
                model=self.vision_model_name,
                contents=[content],
                config=types.GenerateContentConfig()
            )
            
            # Increment quota
            self._increment_quota('vision_analysis')
            
            execution_time = time.time() - start_time
            
            return AIResponse(
                success=True,
                data=response.text,
                execution_time=execution_time,
                model_used=self.vision_model_name,
                tokens_used=len(response.text.split()) if response.text else 0
            )
            
        except QuotaExceededError as e:
            return AIResponse(
                success=False,
                error=str(e),
                execution_time=time.time() - start_time
            )
        except Exception as e:
            logger.error(f"Image analysis failed: {str(e)}")
            return AIResponse(
                success=False,
                error=f"Image analysis failed: {str(e)}",
                execution_time=time.time() - start_time
            )
    
    def health_check(self) -> bool:
        """Health check for Vertex AI service."""
        try:
            self._ensure_initialized()
            # Simple test with minimal quota usage
            response = self.generate_text("Hello", max_tokens=10)
            return response.success
        except Exception as e:
            logger.error(f"Health check failed: {str(e)}")
            return False

class EnhancedSpeechService(BaseAIService):
    """Enhanced Speech service with quota management."""
    
    def __init__(self):
        super().__init__()
        self.speech_client = None
        self._speech_initialized = False
    
    def _ensure_initialized(self):
        """Ensure service is initialized before use."""
        if not self._initialized:
            self._initialize_service()
        if not self._speech_initialized:
            self._initialize_speech_client()
    
    def _initialize_speech_client(self):
        """Initialize Google Cloud Speech client."""
        if self._speech_initialized:
            return
            
        try:
            self.speech_client = speech.SpeechClient()
            self._speech_initialized = True
            logger.info("Speech client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize speech client: {str(e)}")
            raise VertexAIError(f"Speech client initialization failed: {str(e)}")
    
    @sleep_and_retry
    @limits(calls=200, period=3600)  # 200 calls per hour
    def transcribe_audio(self, audio_data: bytes, language: str = 'en-US') -> AIResponse:
        """Transcribe audio with quota management."""
        start_time = time.time()
        
        try:
            self._ensure_initialized()
            from flask import current_app
            
            # Check quota
            quota_limit = current_app.config.get('SPEECH_TO_TEXT_QUOTA', 2000)
            self._check_quota('speech_to_text', quota_limit)
            
            # Configure recognition
            config = speech.RecognitionConfig(
                encoding=speech.RecognitionConfig.AudioEncoding.WEBM_OPUS,
                sample_rate_hertz=48000,
                language_code=language,
                enable_automatic_punctuation=True,
                enable_word_time_offsets=True,
                model='latest_long'
            )
            
            audio = speech.RecognitionAudio(content=audio_data)
            
            # Perform recognition
            response = self._make_api_call(
                self.speech_client.recognize,
                config=config,
                audio=audio
            )
            
            # Increment quota
            self._increment_quota('speech_to_text')
            
            # Extract transcription
            transcriptions = []
            for result in response.results:
                transcriptions.append({
                    'transcript': result.alternatives[0].transcript,
                    'confidence': result.alternatives[0].confidence
                })
            
            execution_time = time.time() - start_time
            
            return AIResponse(
                success=True,
                data=transcriptions,
                execution_time=execution_time,
                model_used='google-speech-latest-long'
            )
            
        except QuotaExceededError as e:
            return AIResponse(
                success=False,
                error=str(e),
                execution_time=time.time() - start_time
            )
        except Exception as e:
            logger.error(f"Speech transcription failed: {str(e)}")
            return AIResponse(
                success=False,
                error=f"Speech transcription failed: {str(e)}",
                execution_time=time.time() - start_time
            )
    
    def health_check(self) -> bool:
        """Health check for Speech service."""
        try:
            self._ensure_initialized()
            # Simple client availability check
            return self.speech_client is not None
        except Exception as e:
            logger.error(f"Speech service health check failed: {str(e)}")
            return False
