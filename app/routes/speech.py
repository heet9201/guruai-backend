from flask import Blueprint, request, jsonify
from app.services.speech_service import SpeechService
from app.utils.middleware import require_json, validate_required_fields
from app.services.vertex_ai_service import QuotaExceededError, VertexAIError
import logging

logger = logging.getLogger(__name__)
speech_bp = Blueprint('speech', __name__)
speech_service = SpeechService()

@speech_bp.route('/speech-to-text', methods=['POST'])
@require_json
@validate_required_fields(['audio_data'])
def speech_to_text():
    """Convert speech to text using enhanced Google Speech API."""
    try:
        data = request.get_json()
        audio_data = data['audio_data']
        language = data.get('language', 'en-US')
        encoding = data.get('encoding', 'WEBM_OPUS')
        
        # Validate language code
        supported_languages = speech_service.get_supported_languages()
        valid_languages = [lang['code'] for lang in supported_languages['speech_to_text']]
        
        if language not in valid_languages:
            return jsonify({
                'error': 'Unsupported language',
                'message': f'Language {language} not supported. Supported languages: {valid_languages}',
                'supported_languages': supported_languages['speech_to_text']
            }), 400
        
        logger.info(f"Speech-to-text request in language: {language}")
        
        text = speech_service.transcribe_audio(
            audio_data=audio_data,
            language=language,
            encoding=encoding
        )
        
        return jsonify({
            'text': text,
            'language': language,
            'encoding': encoding,
            'status': 'success'
        })
        
    except Exception as e:
        logger.error(f"Error in speech-to-text endpoint: {str(e)}")
        
        if isinstance(e, QuotaExceededError):
            return jsonify({
                'error': 'Quota exceeded',
                'message': 'Speech-to-text quota limit reached. Please try again later.',
                'retry_after': 3600
            }), 429
        
        return jsonify({
            'error': 'Failed to transcribe audio',
            'message': str(e)
        }), 500

@speech_bp.route('/text-to-speech', methods=['POST'])
@require_json
@validate_required_fields(['text'])
def text_to_speech():
    """Convert text to speech using Google Text-to-Speech API."""
    try:
        data = request.get_json()
        text = data['text']
        language = data.get('language', 'en-US')
        voice_type = data.get('voice_type', 'female')
        
        # Validate input
        if len(text.strip()) == 0:
            return jsonify({
                'error': 'Empty text',
                'message': 'Text cannot be empty'
            }), 400
        
        if len(text) > 5000:
            return jsonify({
                'error': 'Text too long',
                'message': 'Text must be less than 5000 characters'
            }), 400
        
        # Validate language and voice
        supported_languages = speech_service.get_supported_languages()
        supported_tts = {lang['code']: lang['voices'] for lang in supported_languages['text_to_speech']}
        
        if language not in supported_tts:
            return jsonify({
                'error': 'Unsupported language',
                'message': f'Language {language} not supported for TTS',
                'supported_languages': supported_languages['text_to_speech']
            }), 400
        
        if voice_type not in supported_tts[language]:
            return jsonify({
                'error': 'Unsupported voice type',
                'message': f'Voice type {voice_type} not available for {language}',
                'available_voices': supported_tts[language]
            }), 400
        
        logger.info(f"Text-to-speech request: {text[:50]}... in {language} with {voice_type} voice")
        
        audio_url = speech_service.synthesize_speech(
            text=text,
            language=language,
            voice_type=voice_type
        )
        
        return jsonify({
            'audio_url': audio_url,
            'text_length': len(text),
            'language': language,
            'voice_type': voice_type,
            'status': 'success'
        })
        
    except Exception as e:
        logger.error(f"Error in text-to-speech endpoint: {str(e)}")
        return jsonify({
            'error': 'Failed to synthesize speech',
            'message': str(e)
        }), 500

@speech_bp.route('/upload-audio', methods=['POST'])
def upload_audio():
    """Upload and process audio file for transcription."""
    try:
        if 'audio' not in request.files:
            return jsonify({
                'error': 'No audio file provided',
                'message': 'Please upload an audio file using the "audio" field'
            }), 400
        
        audio_file = request.files['audio']
        language = request.form.get('language', 'en-US')
        
        # Validate file
        if audio_file.filename == '':
            return jsonify({
                'error': 'No file selected',
                'message': 'Please select an audio file'
            }), 400
        
        # Check file size (limit to 10MB)
        max_size = 10 * 1024 * 1024  # 10MB
        audio_file.seek(0, 2)  # Seek to end
        file_size = audio_file.tell()
        audio_file.seek(0)  # Reset to beginning
        
        if file_size > max_size:
            return jsonify({
                'error': 'File too large',
                'message': f'File size ({file_size} bytes) exceeds maximum allowed size ({max_size} bytes)'
            }), 400
        
        # Validate file extension
        allowed_extensions = {'.wav', '.mp3', '.m4a', '.flac', '.ogg', '.webm'}
        file_extension = audio_file.filename.lower().split('.')[-1]
        if f'.{file_extension}' not in allowed_extensions:
            return jsonify({
                'error': 'Unsupported file format',
                'message': f'File format .{file_extension} not supported. Allowed: {list(allowed_extensions)}',
                'allowed_formats': list(allowed_extensions)
            }), 400
        
        logger.info(f"Audio upload request: {audio_file.filename} ({file_size} bytes) in {language}")
        
        result = speech_service.process_audio_file(
            audio_file=audio_file,
            language=language
        )
        
        if result.get('success', False):
            return jsonify({
                'transcriptions': result['transcriptions'],
                'filename': result['filename'],
                'file_size': file_size,
                'language': language,
                'execution_time': result.get('execution_time'),
                'status': 'success'
            })
        else:
            return jsonify({
                'error': 'Processing failed',
                'message': result.get('error', 'Unknown error'),
                'filename': audio_file.filename
            }), 500
        
    except Exception as e:
        logger.error(f"Error in audio upload endpoint: {str(e)}")
        
        if isinstance(e, QuotaExceededError):
            return jsonify({
                'error': 'Quota exceeded',
                'message': 'Audio processing quota limit reached. Please try again later.',
                'retry_after': 3600
            }), 429
        
        return jsonify({
            'error': 'Failed to process audio file',
            'message': str(e)
        }), 500

@speech_bp.route('/status', methods=['GET'])
def get_speech_status():
    """Get speech service status and quota information."""
    try:
        status = speech_service.get_service_status()
        return jsonify(status)
        
    except Exception as e:
        logger.error(f"Error getting speech status: {str(e)}")
        return jsonify({
            'error': 'Failed to get status',
            'message': str(e)
        }), 500

@speech_bp.route('/languages', methods=['GET'])
def get_supported_languages():
    """Get list of supported languages for speech services."""
    try:
        languages = speech_service.get_supported_languages()
        return jsonify({
            'supported_languages': languages,
            'status': 'success'
        })
        
    except Exception as e:
        logger.error(f"Error getting supported languages: {str(e)}")
        return jsonify({
            'error': 'Failed to get supported languages',
            'message': str(e)
        }), 500

@speech_bp.route('/batch-transcribe', methods=['POST'])
def batch_transcribe():
    """Process multiple audio files for transcription."""
    try:
        if 'audio_files' not in request.files:
            return jsonify({
                'error': 'No audio files provided',
                'message': 'Please upload audio files using the "audio_files" field'
            }), 400
        
        audio_files = request.files.getlist('audio_files')
        language = request.form.get('language', 'en-US')
        
        if len(audio_files) > 5:
            return jsonify({
                'error': 'Too many files',
                'message': 'Maximum 5 files allowed per batch request'
            }), 400
        
        results = []
        total_size = 0
        max_batch_size = 50 * 1024 * 1024  # 50MB total
        
        for audio_file in audio_files:
            # Check total batch size
            audio_file.seek(0, 2)
            file_size = audio_file.tell()
            audio_file.seek(0)
            total_size += file_size
            
            if total_size > max_batch_size:
                return jsonify({
                    'error': 'Batch too large',
                    'message': f'Total batch size exceeds {max_batch_size} bytes'
                }), 400
            
            try:
                result = speech_service.process_audio_file(
                    audio_file=audio_file,
                    language=language
                )
                
                results.append({
                    'filename': audio_file.filename,
                    'success': result.get('success', False),
                    'transcriptions': result.get('transcriptions', []),
                    'error': result.get('error'),
                    'file_size': file_size
                })
                
            except Exception as e:
                results.append({
                    'filename': audio_file.filename,
                    'success': False,
                    'error': str(e),
                    'file_size': file_size
                })
        
        successful_count = sum(1 for r in results if r['success'])
        
        return jsonify({
            'results': results,
            'total_files': len(audio_files),
            'successful_count': successful_count,
            'failed_count': len(audio_files) - successful_count,
            'total_size': total_size,
            'language': language,
            'status': 'success'
        })
        
    except Exception as e:
        logger.error(f"Error in batch transcribe endpoint: {str(e)}")
        
        if isinstance(e, QuotaExceededError):
            return jsonify({
                'error': 'Quota exceeded',
                'message': 'Batch processing quota limit reached. Please try again later.',
                'retry_after': 3600
            }), 429
        
        return jsonify({
            'error': 'Failed to process batch',
            'message': str(e)
        }), 500
