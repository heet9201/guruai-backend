"""
Content Filter and Safety System
AI safety filters, inappropriate content detection, and child safety measures.
"""

import os
import re
import json
import logging
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timezone
from enum import Enum
import redis

class ContentType(Enum):
    TEXT = "text"
    IMAGE = "image"
    AUDIO = "audio"
    VIDEO = "video"
    FILE = "file"

class FilterResult(Enum):
    SAFE = "safe"
    FLAGGED = "flagged"
    BLOCKED = "blocked"
    REQUIRES_REVIEW = "requires_review"

class ContentCategory(Enum):
    # Harmful content
    EXPLICIT_SEXUAL = "explicit_sexual"
    VIOLENCE = "violence"
    HATE_SPEECH = "hate_speech"
    HARASSMENT = "harassment"
    SELF_HARM = "self_harm"
    
    # Inappropriate for children
    ADULT_THEMES = "adult_themes"
    PROFANITY = "profanity"
    DISTURBING = "disturbing"
    
    # Educational concerns
    MISINFORMATION = "misinformation"
    ACADEMIC_DISHONESTY = "academic_dishonesty"
    INAPPROPRIATE_EDUCATIONAL = "inappropriate_educational"
    
    # Spam and abuse
    SPAM = "spam"
    REPETITIVE = "repetitive"
    MALICIOUS_LINKS = "malicious_links"

class ContentFilter:
    def __init__(self):
        self.redis_client = redis.Redis(
            host=os.getenv('REDIS_HOST', 'localhost'),
            port=int(os.getenv('REDIS_PORT', 6379)),
            db=int(os.getenv('REDIS_CONTENT_DB', 3)),
            decode_responses=True
        )
        
        # Load filter configurations
        self._load_filter_rules()
        
        # Initialize AI safety components
        self._init_ai_safety()
        
        # Setup logging
        self.logger = logging.getLogger('content_filter')
    
    def _load_filter_rules(self):
        """Load content filtering rules and patterns."""
        
        # Profanity words (basic list - in production, use comprehensive database)
        self.profanity_words = {
            'mild': ['damn', 'hell', 'crap'],
            'moderate': ['stupid', 'idiot', 'moron'],
            'severe': ['offensive_word1', 'offensive_word2']  # Replace with actual list
        }
        
        # Hate speech patterns
        self.hate_patterns = [
            r'\b(racist|sexist|homophobic)\b',
            r'\b(kill yourself|kys)\b',
            r'\b(you should die)\b'
        ]
        
        # Spam indicators
        self.spam_patterns = [
            r'(click here|buy now|free money)',
            r'(win \$\d+|lottery winner)',
            r'(urgent|act now|limited time)'
        ]
        
        # Educational red flags
        self.academic_dishonesty_patterns = [
            r'\b(write my essay|do my homework)\b',
            r'\b(plagiarize|copy paste)\b',
            r'\b(cheat on exam|test answers)\b'
        ]
        
        # Child safety keywords
        self.child_unsafe_patterns = [
            r'\b(meet in person|send photos)\b',
            r'\b(keep this secret|don\'t tell)\b',
            r'\b(home alone|parents away)\b'
        ]
        
        # Load custom rules from environment or database
        self._load_custom_rules()
    
    def _load_custom_rules(self):
        """Load custom filtering rules from configuration."""
        try:
            # Load from Redis if available
            custom_rules = self.redis_client.get('content_filter_rules')
            if custom_rules:
                rules = json.loads(custom_rules)
                self.custom_patterns = rules.get('patterns', [])
                self.custom_blocklist = rules.get('blocklist', [])
            else:
                self.custom_patterns = []
                self.custom_blocklist = []
        except Exception as e:
            self.logger.error(f"Failed to load custom rules: {str(e)}")
            self.custom_patterns = []
            self.custom_blocklist = []
    
    def _init_ai_safety(self):
        """Initialize AI safety components."""
        # In production, integrate with AI safety APIs like:
        # - OpenAI Moderation API
        # - Google Perspective API
        # - Azure Content Moderator
        
        self.ai_safety_enabled = os.getenv('AI_SAFETY_ENABLED', 'true').lower() == 'true'
        self.ai_safety_threshold = float(os.getenv('AI_SAFETY_THRESHOLD', '0.7'))
    
    def filter_content(self, 
                      content: str, 
                      content_type: ContentType = ContentType.TEXT,
                      user_age: Optional[int] = None,
                      context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Comprehensive content filtering.
        
        Returns:
            {
                'result': FilterResult,
                'categories': List[ContentCategory],
                'confidence': float,
                'reasons': List[str],
                'safe_version': str (if available),
                'recommendations': List[str]
            }
        """
        
        if not content or not content.strip():
            return {
                'result': FilterResult.SAFE,
                'categories': [],
                'confidence': 1.0,
                'reasons': [],
                'safe_version': content,
                'recommendations': []
            }
        
        filter_results = []
        detected_categories = []
        reasons = []
        
        # Apply different filters based on content type
        if content_type == ContentType.TEXT:
            # Text-specific filters
            filter_results.extend([
                self._check_profanity(content),
                self._check_hate_speech(content),
                self._check_harassment(content),
                self._check_spam(content),
                self._check_academic_dishonesty(content),
                self._check_misinformation_indicators(content)
            ])
            
            # Child safety filters
            if user_age and user_age < 18:
                filter_results.append(self._check_child_safety(content))
        
        # AI-powered safety check
        if self.ai_safety_enabled:
            ai_result = self._ai_safety_check(content, content_type)
            filter_results.append(ai_result)
        
        # Custom filters
        custom_result = self._apply_custom_filters(content)
        filter_results.append(custom_result)
        
        # Aggregate results
        return self._aggregate_filter_results(filter_results, content, context)
    
    def _check_profanity(self, content: str) -> Dict[str, Any]:
        """Check for profanity."""
        content_lower = content.lower()
        detected = []
        severity = 'safe'
        
        for level, words in self.profanity_words.items():
            for word in words:
                if word in content_lower:
                    detected.append({'word': word, 'level': level})
                    if level == 'severe':
                        severity = 'blocked'
                    elif level == 'moderate' and severity != 'blocked':
                        severity = 'flagged'
                    elif level == 'mild' and severity == 'safe':
                        severity = 'flagged'
        
        return {
            'category': ContentCategory.PROFANITY,
            'severity': severity,
            'detected': detected,
            'confidence': 0.9 if detected else 1.0
        }
    
    def _check_hate_speech(self, content: str) -> Dict[str, Any]:
        """Check for hate speech patterns."""
        detected_patterns = []
        
        for pattern in self.hate_patterns:
            matches = re.finditer(pattern, content, re.IGNORECASE)
            for match in matches:
                detected_patterns.append({
                    'pattern': pattern,
                    'match': match.group(),
                    'position': match.span()
                })
        
        severity = 'blocked' if detected_patterns else 'safe'
        
        return {
            'category': ContentCategory.HATE_SPEECH,
            'severity': severity,
            'detected': detected_patterns,
            'confidence': 0.85 if detected_patterns else 1.0
        }
    
    def _check_harassment(self, content: str) -> Dict[str, Any]:
        """Check for harassment indicators."""
        harassment_indicators = [
            r'\b(you are (so )?stupid|you\'re an idiot)\b',
            r'\b(shut up|go away|nobody likes you)\b',
            r'\b(you should (die|kill yourself))\b'
        ]
        
        detected = []
        for pattern in harassment_indicators:
            matches = re.finditer(pattern, content, re.IGNORECASE)
            for match in matches:
                detected.append({
                    'pattern': pattern,
                    'match': match.group(),
                    'position': match.span()
                })
        
        severity = 'blocked' if detected else 'safe'
        
        return {
            'category': ContentCategory.HARASSMENT,
            'severity': severity,
            'detected': detected,
            'confidence': 0.8 if detected else 1.0
        }
    
    def _check_spam(self, content: str) -> Dict[str, Any]:
        """Check for spam content."""
        detected_patterns = []
        
        for pattern in self.spam_patterns:
            matches = re.finditer(pattern, content, re.IGNORECASE)
            for match in matches:
                detected_patterns.append({
                    'pattern': pattern,
                    'match': match.group(),
                    'position': match.span()
                })
        
        # Check for repetitive content
        words = content.split()
        if len(words) > 10:
            unique_words = set(words)
            repetition_ratio = len(words) / len(unique_words)
            if repetition_ratio > 3:
                detected_patterns.append({
                    'type': 'repetitive',
                    'ratio': repetition_ratio
                })
        
        severity = 'flagged' if detected_patterns else 'safe'
        
        return {
            'category': ContentCategory.SPAM,
            'severity': severity,
            'detected': detected_patterns,
            'confidence': 0.75 if detected_patterns else 1.0
        }
    
    def _check_academic_dishonesty(self, content: str) -> Dict[str, Any]:
        """Check for academic dishonesty indicators."""
        detected = []
        
        for pattern in self.academic_dishonesty_patterns:
            matches = re.finditer(pattern, content, re.IGNORECASE)
            for match in matches:
                detected.append({
                    'pattern': pattern,
                    'match': match.group(),
                    'position': match.span()
                })
        
        severity = 'flagged' if detected else 'safe'
        
        return {
            'category': ContentCategory.ACADEMIC_DISHONESTY,
            'severity': severity,
            'detected': detected,
            'confidence': 0.7 if detected else 1.0
        }
    
    def _check_child_safety(self, content: str) -> Dict[str, Any]:
        """Enhanced child safety checks."""
        detected = []
        
        for pattern in self.child_unsafe_patterns:
            matches = re.finditer(pattern, content, re.IGNORECASE)
            for match in matches:
                detected.append({
                    'pattern': pattern,
                    'match': match.group(),
                    'position': match.span(),
                    'risk_level': 'high'
                })
        
        # Check for personal information sharing
        personal_info_patterns = [
            r'\b\d{3}-\d{3}-\d{4}\b',  # Phone numbers
            r'\b\w+@\w+\.\w+\b',       # Email addresses
            r'\b\d+\s+\w+\s+(street|avenue|road|drive)\b'  # Addresses
        ]
        
        for pattern in personal_info_patterns:
            matches = re.finditer(pattern, content, re.IGNORECASE)
            for match in matches:
                detected.append({
                    'type': 'personal_info',
                    'match': match.group(),
                    'position': match.span(),
                    'risk_level': 'medium'
                })
        
        severity = 'blocked' if any(d.get('risk_level') == 'high' for d in detected) else 'safe'
        if not severity == 'blocked' and detected:
            severity = 'flagged'
        
        return {
            'category': ContentCategory.ADULT_THEMES,
            'severity': severity,
            'detected': detected,
            'confidence': 0.9 if detected else 1.0
        }
    
    def _check_misinformation_indicators(self, content: str) -> Dict[str, Any]:
        """Check for potential misinformation indicators."""
        misinformation_patterns = [
            r'\b(scientists are lying|research is fake)\b',
            r'\b(proven fact|100% true|everyone knows)\b',
            r'\b(they don\'t want you to know|hidden truth)\b'
        ]
        
        detected = []
        for pattern in misinformation_patterns:
            matches = re.finditer(pattern, content, re.IGNORECASE)
            for match in matches:
                detected.append({
                    'pattern': pattern,
                    'match': match.group(),
                    'position': match.span()
                })
        
        severity = 'requires_review' if detected else 'safe'
        
        return {
            'category': ContentCategory.MISINFORMATION,
            'severity': severity,
            'detected': detected,
            'confidence': 0.6 if detected else 1.0
        }
    
    def _ai_safety_check(self, content: str, content_type: ContentType) -> Dict[str, Any]:
        """AI-powered safety check (mock implementation)."""
        # In production, integrate with actual AI safety APIs
        
        # Mock implementation - always return safe for now
        # In real implementation, call services like:
        # - OpenAI Moderation API
        # - Google Perspective API
        # - Custom trained models
        
        return {
            'category': 'ai_safety',
            'severity': 'safe',
            'detected': [],
            'confidence': 0.95,
            'ai_scores': {
                'toxicity': 0.1,
                'threat': 0.05,
                'identity_attack': 0.03,
                'insult': 0.08
            }
        }
    
    def _apply_custom_filters(self, content: str) -> Dict[str, Any]:
        """Apply custom filtering rules."""
        detected = []
        
        # Check custom patterns
        for pattern in self.custom_patterns:
            try:
                matches = re.finditer(pattern, content, re.IGNORECASE)
                for match in matches:
                    detected.append({
                        'type': 'custom_pattern',
                        'pattern': pattern,
                        'match': match.group(),
                        'position': match.span()
                    })
            except re.error:
                # Invalid regex pattern
                continue
        
        # Check blocklist
        content_lower = content.lower()
        for blocked_term in self.custom_blocklist:
            if blocked_term.lower() in content_lower:
                detected.append({
                    'type': 'blocklist',
                    'term': blocked_term
                })
        
        severity = 'flagged' if detected else 'safe'
        
        return {
            'category': 'custom',
            'severity': severity,
            'detected': detected,
            'confidence': 0.8 if detected else 1.0
        }
    
    def _aggregate_filter_results(self, 
                                filter_results: List[Dict[str, Any]], 
                                original_content: str,
                                context: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Aggregate all filter results into final decision."""
        
        # Determine overall severity
        severities = [result.get('severity', 'safe') for result in filter_results]
        
        if 'blocked' in severities:
            final_result = FilterResult.BLOCKED
        elif 'requires_review' in severities:
            final_result = FilterResult.REQUIRES_REVIEW
        elif 'flagged' in severities:
            final_result = FilterResult.FLAGGED
        else:
            final_result = FilterResult.SAFE
        
        # Collect categories and reasons
        categories = []
        reasons = []
        all_detected = []
        
        for result in filter_results:
            if result.get('detected'):
                category = result.get('category')
                if category and hasattr(ContentCategory, category.name if hasattr(category, 'name') else str(category).upper()):
                    categories.append(category)
                
                # Add specific reasons
                detected_items = result.get('detected', [])
                for item in detected_items:
                    if isinstance(item, dict):
                        if 'match' in item:
                            reasons.append(f"Detected: {item['match']}")
                        elif 'type' in item:
                            reasons.append(f"Flagged for: {item['type']}")
                
                all_detected.extend(detected_items)
        
        # Calculate overall confidence
        confidences = [result.get('confidence', 1.0) for result in filter_results if result.get('detected')]
        overall_confidence = min(confidences) if confidences else 1.0
        
        # Generate safe version if needed
        safe_version = self._generate_safe_version(original_content, all_detected) if final_result != FilterResult.SAFE else original_content
        
        # Generate recommendations
        recommendations = self._generate_recommendations(categories, final_result)
        
        # Log the filtering action
        self._log_filter_action({
            'content_preview': original_content[:100],
            'result': final_result.value,
            'categories': [cat.value if hasattr(cat, 'value') else str(cat) for cat in categories],
            'confidence': overall_confidence,
            'context': context
        })
        
        return {
            'result': final_result,
            'categories': categories,
            'confidence': overall_confidence,
            'reasons': reasons,
            'safe_version': safe_version,
            'recommendations': recommendations
        }
    
    def _generate_safe_version(self, content: str, detected_items: List[Dict[str, Any]]) -> str:
        """Generate a safe version of the content by removing/replacing problematic parts."""
        safe_content = content
        
        # Sort detected items by position (descending) to avoid position shifts
        positional_items = [item for item in detected_items if 'position' in item]
        positional_items.sort(key=lambda x: x['position'][0], reverse=True)
        
        # Replace or remove detected content
        for item in positional_items:
            start, end = item['position']
            replacement = '[FILTERED]'
            
            # Customize replacement based on type
            if 'profanity' in str(item.get('category', '')).lower():
                replacement = '*' * (end - start)
            elif 'personal_info' in item.get('type', ''):
                replacement = '[PERSONAL INFO REMOVED]'
            
            safe_content = safe_content[:start] + replacement + safe_content[end:]
        
        return safe_content
    
    def _generate_recommendations(self, categories: List[ContentCategory], result: FilterResult) -> List[str]:
        """Generate recommendations based on filter results."""
        recommendations = []
        
        if result == FilterResult.BLOCKED:
            recommendations.append("Content has been blocked due to policy violations")
            recommendations.append("Please review our community guidelines")
        
        elif result == FilterResult.FLAGGED:
            recommendations.append("Content has been flagged for review")
            recommendations.append("Consider revising your message")
        
        elif result == FilterResult.REQUIRES_REVIEW:
            recommendations.append("Content requires manual review")
            recommendations.append("Your message will be reviewed by our team")
        
        # Category-specific recommendations
        for category in categories:
            if category == ContentCategory.PROFANITY:
                recommendations.append("Consider using more appropriate language")
            elif category == ContentCategory.ACADEMIC_DISHONESTY:
                recommendations.append("Remember to complete assignments independently")
            elif category == ContentCategory.SPAM:
                recommendations.append("Avoid repetitive or promotional content")
        
        return list(set(recommendations))  # Remove duplicates
    
    def _log_filter_action(self, details: Dict[str, Any]):
        """Log content filtering action."""
        try:
            log_entry = {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'action': 'content_filter',
                'details': details
            }
            
            # Store in Redis for monitoring
            key = f"content_filter_log:{int(datetime.now().timestamp())}"
            self.redis_client.setex(key, 86400 * 7, json.dumps(log_entry))  # 7 days
            
            # Add to filter stats
            result = details.get('result', 'unknown')
            stats_key = f"filter_stats:{result}"
            self.redis_client.incr(stats_key)
            self.redis_client.expire(stats_key, 86400 * 30)  # 30 days
            
        except Exception as e:
            self.logger.error(f"Failed to log filter action: {str(e)}")
    
    def update_filter_rules(self, new_rules: Dict[str, Any]) -> bool:
        """Update content filtering rules."""
        try:
            # Store new rules in Redis
            self.redis_client.setex('content_filter_rules', 86400 * 30, json.dumps(new_rules))
            
            # Reload rules
            self._load_custom_rules()
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to update filter rules: {str(e)}")
            return False
    
    def get_filter_stats(self) -> Dict[str, Any]:
        """Get content filtering statistics."""
        try:
            stats = {}
            
            # Get result counts
            for result in FilterResult:
                key = f"filter_stats:{result.value}"
                count = self.redis_client.get(key)
                stats[result.value] = int(count) if count else 0
            
            return stats
            
        except Exception as e:
            self.logger.error(f"Failed to get filter stats: {str(e)}")
            return {}
