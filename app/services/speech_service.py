import logging
import base64
import io
import tempfile
import os
from app.services.vertex_ai_service import EnhancedSpeechService, AIResponse
from app.utils import retry_on_failure, log_execution_time
from google.cloud import storage
from google.cloud import texttospeech

logger = logging.getLogger(__name__)

class SpeechService:
    """Enhanced Speech service with quota management and better error handling."""
    
    def __init__(self):
        self.enhanced_speech_service = None
        self.storage_client = None
        self.tts_client = None
        self._initialize_services()
    
    def _initialize_services(self):
        """Initialize all speech-related services."""
        try:
            # Initialize enhanced speech service for STT
            self.enhanced_speech_service = EnhancedSpeechService()
            
            # Initialize storage client
            self.storage_client = storage.Client()
            
            # Initialize Text-to-Speech client
            self.tts_client = texttospeech.TextToSpeechClient()
            
            logger.info("Speech services initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize speech services: {str(e)}")
            # Set to None for fallback handling
            self.enhanced_speech_service = None
    
    @log_execution_time
    @retry_on_failure(max_retries=3, delay=1.0)
    def transcribe_audio(self, audio_data: str, language: str = 'en-US', encoding: str = 'WEBM_OPUS') -> str:
        """Transcribe audio data to text with enhanced error handling."""
        try:
            if not self.enhanced_speech_service:
                return "Speech transcription service unavailable"
            
            # Decode base64 audio data
            try:
                audio_bytes = base64.b64decode(audio_data)
            except Exception as e:
                logger.error(f"Failed to decode audio data: {str(e)}")
                raise ValueError("Invalid audio data format")
            
            # Use enhanced speech service
            response = self.enhanced_speech_service.transcribe_audio(
                audio_data=audio_bytes,
                language=language
            )
            
            if response.success:
                # Extract transcription text from response
                transcriptions = response.data
                if transcriptions:
                    # Combine all transcriptions
                    full_text = " ".join([t.get('transcript', '') for t in transcriptions])
                    logger.info(f"Audio transcribed successfully: {len(full_text)} characters")
                    return full_text.strip()
                else:
                    return "No speech detected in audio"
            else:
                logger.error(f"Speech transcription failed: {response.error}")
                return f"Transcription failed: {response.error}"
                
        except Exception as e:
            logger.error(f"Error transcribing audio: {str(e)}")
            return f"Error: {str(e)}"
    
    @log_execution_time
    @retry_on_failure(max_retries=2, delay=2.0)
    def synthesize_speech(self, text: str, language: str = 'en-US', voice_type: str = 'female') -> str:
        """Convert text to speech and return audio URL."""
        try:
            if not self.tts_client:
                return "https://storage.googleapis.com/placeholder/audio.mp3"
            
            # Configure synthesis
            input_text = texttospeech.SynthesisInput(text=text)
            
            # Select voice based on language and type
            voice_name = self._get_voice_name(language, voice_type)
            voice = texttospeech.VoiceSelectionParams(
                language_code=language,
                name=voice_name,
                ssml_gender=texttospeech.SsmlVoiceGender.FEMALE if voice_type == 'female' 
                           else texttospeech.SsmlVoiceGender.MALE
            )
            
            # Configure audio output
            audio_config = texttospeech.AudioConfig(
                audio_encoding=texttospeech.AudioEncoding.MP3,
                speaking_rate=1.0,
                pitch=0.0,
                volume_gain_db=0.0
            )
            
            # Perform synthesis
            response = self.tts_client.synthesize_speech(
                input=input_text,
                voice=voice,
                audio_config=audio_config
            )
            
            # Upload to storage and return URL
            audio_url = self._upload_audio_to_storage(response.audio_content, language, voice_type)
            
            logger.info(f"Speech synthesized successfully: {len(text)} characters")
            return audio_url
            
        except Exception as e:
            logger.error(f"Error synthesizing speech: {str(e)}")
            return "https://storage.googleapis.com/placeholder/audio.mp3"
    
    @log_execution_time
    def process_audio_file(self, audio_file, language: str = 'en-US') -> dict:
        """Process uploaded audio file with enhanced capabilities."""
        try:
            if not self.enhanced_speech_service:
                return {
                    'error': 'Speech service unavailable',
                    'transcriptions': []
                }
            
            # Save uploaded file temporarily
            with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as temp_file:
                audio_file.save(temp_file.name)
                
                # Read file content
                with open(temp_file.name, 'rb') as f:
                    audio_content = f.read()
                
                # Clean up temp file
                os.unlink(temp_file.name)
            
            # Use enhanced speech service
            response = self.enhanced_speech_service.transcribe_audio(
                audio_data=audio_content,
                language=language
            )
            
            if response.success:
                result = {
                    'success': True,
                    'transcriptions': response.data,
                    'execution_time': response.execution_time,
                    'filename': audio_file.filename
                }
                
                logger.info(f"Audio file processed successfully: {audio_file.filename}")
                return result
            else:
                logger.error(f"Audio file processing failed: {response.error}")
                return {
                    'success': False,
                    'error': response.error,
                    'transcriptions': []
                }
                
        except Exception as e:
            logger.error(f"Error processing audio file: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'transcriptions': []
            }
    
    def get_service_status(self) -> dict:
        """Get speech service status including quota information."""
        try:
            status = {
                'speech_to_text_available': self.enhanced_speech_service is not None,
                'text_to_speech_available': self.tts_client is not None,
                'storage_available': self.storage_client is not None,
                'health_check': False
            }
            
            if self.enhanced_speech_service:
                status['health_check'] = self.enhanced_speech_service.health_check()
                
                # Get quota information
                quota_status = self.enhanced_speech_service.get_quota_status()
                if 'speech_to_text' in quota_status:
                    quota = quota_status['speech_to_text']
                    status['quota'] = {
                        'used': quota.used,
                        'limit': quota.limit,
                        'remaining': quota.remaining,
                        'reset_time': quota.reset_time.isoformat()
                    }
            
            return status
            
        except Exception as e:
            logger.error(f"Error getting speech service status: {str(e)}")
            return {
                'speech_to_text_available': False,
                'text_to_speech_available': False,
                'storage_available': False,
                'health_check': False,
                'error': str(e)
            }
    
    def _get_voice_name(self, language: str, voice_type: str) -> str:
        """Get appropriate voice name based on language and type."""
        voice_mapping = {
            'en-US': {
                'female': 'en-US-Neural2-F',
                'male': 'en-US-Neural2-A'
            },
            'en-GB': {
                'female': 'en-GB-Neural2-A',
                'male': 'en-GB-Neural2-B'
            },
            'hi-IN': {
                'female': 'hi-IN-Neural2-A',
                'male': 'hi-IN-Neural2-B'
            },
            'es-ES': {
                'female': 'es-ES-Neural2-A',
                'male': 'es-ES-Neural2-B'
            },
            'fr-FR': {
                'female': 'fr-FR-Neural2-A',
                'male': 'fr-FR-Neural2-B'
            }
        }
        
        return voice_mapping.get(language, {}).get(voice_type, voice_mapping['en-US']['female'])
    
    def _upload_audio_to_storage(self, audio_content: bytes, language: str, voice_type: str) -> str:
        """Upload audio content to Google Cloud Storage with organized naming."""
        try:
            from flask import current_app
            
            bucket_name = current_app.config.get('STORAGE_BUCKET', 'sahayak-audio')
            bucket = self.storage_client.bucket(bucket_name)
            
            # Generate organized filename
            import uuid
            from datetime import datetime
            
            timestamp = datetime.now().strftime('%Y%m%d')
            filename = f"tts/{timestamp}/{language}/{voice_type}/{uuid.uuid4()}.mp3"
            
            blob = bucket.blob(filename)
            
            # Upload with metadata
            blob.metadata = {
                'language': language,
                'voice_type': voice_type,
                'generated_at': datetime.now().isoformat(),
                'service': 'sahayak-tts'
            }
            
            blob.upload_from_string(
                audio_content, 
                content_type='audio/mpeg'
            )
            
            # Make blob publicly accessible (consider using signed URLs for production)
            blob.make_public()
            
            logger.info(f"Audio uploaded to storage: {filename}")
            return blob.public_url
            
        except Exception as e:
            logger.error(f"Error uploading audio to storage: {str(e)}")
            # Return a placeholder URL if upload fails
            return "https://storage.googleapis.com/placeholder/audio.mp3"
    
    def get_supported_languages(self) -> dict:
        """Get list of supported languages for speech services."""
        return {
            'speech_to_text': [
                {'code': 'en-US', 'name': 'English (US)'},
                {'code': 'en-GB', 'name': 'English (UK)'},
                {'code': 'hi-IN', 'name': 'Hindi (India)'},
                {'code': 'es-ES', 'name': 'Spanish (Spain)'},
                {'code': 'fr-FR', 'name': 'French (France)'},
                {'code': 'de-DE', 'name': 'German (Germany)'},
                {'code': 'ja-JP', 'name': 'Japanese (Japan)'},
                {'code': 'ko-KR', 'name': 'Korean (South Korea)'},
                {'code': 'zh-CN', 'name': 'Chinese (Simplified)'},
                {'code': 'ar-XA', 'name': 'Arabic'}
            ],
            'text_to_speech': [
                {'code': 'en-US', 'name': 'English (US)', 'voices': ['female', 'male']},
                {'code': 'en-GB', 'name': 'English (UK)', 'voices': ['female', 'male']},
                {'code': 'hi-IN', 'name': 'Hindi (India)', 'voices': ['female', 'male']},
                {'code': 'es-ES', 'name': 'Spanish (Spain)', 'voices': ['female', 'male']},
                {'code': 'fr-FR', 'name': 'French (France)', 'voices': ['female', 'male']}
            ]
        }
