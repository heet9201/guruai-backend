"""
Comprehensive Audit Logger
Track all user actions, system events, and security incidents.
"""

import os
import json
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from enum import Enum
import redis
from flask import request, g

class AuditEventType(Enum):
    # Authentication events
    LOGIN_SUCCESS = "login_success"
    LOGIN_FAILED = "login_failed"
    LOGOUT = "logout"
    TOKEN_REFRESH = "token_refresh"
    PASSWORD_CHANGE = "password_change"
    MFA_SETUP = "mfa_setup"
    MFA_ENABLED = "mfa_enabled"
    MFA_DISABLED = "mfa_disabled"
    
    # Authorization events
    ACCESS_GRANTED = "access_granted"
    ACCESS_DENIED = "access_denied"
    PERMISSION_CHANGE = "permission_change"
    
    # Data events
    DATA_ACCESS = "data_access"
    DATA_MODIFICATION = "data_modification"
    DATA_DELETION = "data_deletion"
    DATA_EXPORT = "data_export"
    FILE_UPLOAD = "file_upload"
    FILE_DOWNLOAD = "file_download"
    FILE_DELETE = "file_delete"
    
    # Security events
    SUSPICIOUS_ACTIVITY = "suspicious_activity"
    SECURITY_VIOLATION = "security_violation"
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    DEVICE_FINGERPRINT_MISMATCH = "device_fingerprint_mismatch"
    
    # System events
    SYSTEM_ERROR = "system_error"
    CONFIGURATION_CHANGE = "configuration_change"
    BACKUP_CREATED = "backup_created"
    
    # Content events
    CONTENT_GENERATED = "content_generated"
    CONTENT_FLAGGED = "content_flagged"
    CONTENT_MODERATED = "content_moderated"

class AuditSeverity(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class AuditLogger:
    def __init__(self):
        self.logger = logging.getLogger('audit')
        self.redis_client = redis.Redis(
            host=os.getenv('REDIS_HOST', 'localhost'),
            port=int(os.getenv('REDIS_PORT', 6379)),
            db=int(os.getenv('REDIS_AUDIT_DB', 2)),
            decode_responses=True
        )
        
        # Configure audit logger
        self._setup_audit_logger()
    
    def _setup_audit_logger(self):
        """Setup dedicated audit logger."""
        if not self.logger.handlers:
            # File handler for audit logs
            audit_file = os.getenv('AUDIT_LOG_FILE', 'logs/audit.log')
            os.makedirs(os.path.dirname(audit_file), exist_ok=True)
            
            file_handler = logging.FileHandler(audit_file)
            file_handler.setLevel(logging.INFO)
            
            # JSON formatter for structured logs
            formatter = logging.Formatter(
                '{"timestamp": "%(asctime)s", "level": "%(levelname)s", "message": %(message)s}'
            )
            file_handler.setFormatter(formatter)
            
            self.logger.addHandler(file_handler)
            self.logger.setLevel(logging.INFO)
    
    def log_event(self, 
                  event_type: AuditEventType, 
                  user_id: Optional[str] = None,
                  severity: AuditSeverity = AuditSeverity.LOW,
                  details: Optional[Dict[str, Any]] = None,
                  resource: Optional[str] = None,
                  outcome: str = "success") -> str:
        """Log audit event with comprehensive details."""
        
        event_id = self._generate_event_id()
        timestamp = datetime.now(timezone.utc).isoformat()
        
        # Gather context information
        context = self._gather_context()
        
        audit_entry = {
            'event_id': event_id,
            'timestamp': timestamp,
            'event_type': event_type.value,
            'severity': severity.value,
            'user_id': user_id,
            'session_id': getattr(g, 'session_id', None),
            'ip_address': context.get('ip_address'),
            'user_agent': context.get('user_agent'),
            'endpoint': context.get('endpoint'),
            'method': context.get('method'),
            'resource': resource,
            'outcome': outcome,
            'details': details or {},
            'request_id': getattr(g, 'request_id', None)
        }
        
        # Log to file
        self.logger.info(json.dumps(audit_entry))
        
        # Store in Redis for real-time monitoring
        self._store_in_redis(audit_entry)
        
        # Check for security alerts
        self._check_security_alerts(audit_entry)
        
        return event_id
    
    def _gather_context(self) -> Dict[str, Any]:
        """Gather request context information."""
        context = {}
        
        try:
            if request:
                context.update({
                    'ip_address': request.remote_addr,
                    'user_agent': request.headers.get('User-Agent', ''),
                    'endpoint': request.endpoint,
                    'method': request.method,
                    'url': request.url,
                    'referrer': request.headers.get('Referer', ''),
                    'content_length': request.content_length,
                    'content_type': request.content_type
                })
        except RuntimeError:
            # Outside request context
            pass
        
        return context
    
    def _store_in_redis(self, audit_entry: Dict[str, Any]):
        """Store audit entry in Redis for real-time access."""
        try:
            # Store individual event
            key = f"audit:{audit_entry['event_id']}"
            self.redis_client.setex(key, 86400 * 7, json.dumps(audit_entry))  # 7 days
            
            # Add to user's audit trail
            if audit_entry.get('user_id'):
                user_key = f"user_audit:{audit_entry['user_id']}"
                self.redis_client.lpush(user_key, audit_entry['event_id'])
                self.redis_client.ltrim(user_key, 0, 999)  # Keep last 1000 events
                self.redis_client.expire(user_key, 86400 * 30)  # 30 days
            
            # Add to event type index
            type_key = f"audit_type:{audit_entry['event_type']}"
            self.redis_client.lpush(type_key, audit_entry['event_id'])
            self.redis_client.ltrim(type_key, 0, 9999)  # Keep last 10000 events
            self.redis_client.expire(type_key, 86400 * 7)  # 7 days
            
            # Add to severity index
            severity_key = f"audit_severity:{audit_entry['severity']}"
            self.redis_client.lpush(severity_key, audit_entry['event_id'])
            self.redis_client.ltrim(severity_key, 0, 9999)
            self.redis_client.expire(severity_key, 86400 * 7)
            
        except Exception as e:
            logging.error(f"Failed to store audit entry in Redis: {str(e)}")
    
    def _check_security_alerts(self, audit_entry: Dict[str, Any]):
        """Check for security patterns and raise alerts."""
        try:
            event_type = audit_entry['event_type']
            user_id = audit_entry.get('user_id')
            ip_address = audit_entry.get('ip_address')
            
            # Failed login attempts
            if event_type == AuditEventType.LOGIN_FAILED.value and user_id:
                self._check_failed_logins(user_id, ip_address)
            
            # Suspicious activity patterns
            if event_type == AuditEventType.SUSPICIOUS_ACTIVITY.value:
                self._raise_security_alert(audit_entry, "Suspicious activity detected")
            
            # Rate limit violations
            if event_type == AuditEventType.RATE_LIMIT_EXCEEDED.value:
                self._check_rate_limit_violations(ip_address)
            
            # Device fingerprint mismatches
            if event_type == AuditEventType.DEVICE_FINGERPRINT_MISMATCH.value:
                self._check_device_anomalies(user_id)
                
        except Exception as e:
            logging.error(f"Security alert check failed: {str(e)}")
    
    def _check_failed_logins(self, user_id: str, ip_address: str):
        """Check for excessive failed login attempts."""
        try:
            # Count failed logins in last hour
            failed_key = f"failed_logins:{user_id}"
            failed_count = self.redis_client.incr(failed_key)
            self.redis_client.expire(failed_key, 3600)  # 1 hour
            
            if failed_count >= 5:
                alert_details = {
                    'user_id': user_id,
                    'ip_address': ip_address,
                    'failed_attempts': failed_count,
                    'time_window': '1 hour'
                }
                self._raise_security_alert(alert_details, "Excessive failed login attempts")
            
            # Check for distributed attacks from same IP
            ip_failed_key = f"ip_failed_logins:{ip_address}"
            ip_failed_count = self.redis_client.incr(ip_failed_key)
            self.redis_client.expire(ip_failed_key, 3600)
            
            if ip_failed_count >= 10:
                alert_details = {
                    'ip_address': ip_address,
                    'failed_attempts': ip_failed_count,
                    'time_window': '1 hour'
                }
                self._raise_security_alert(alert_details, "Potential brute force attack")
                
        except Exception as e:
            logging.error(f"Failed login check error: {str(e)}")
    
    def _check_rate_limit_violations(self, ip_address: str):
        """Check for persistent rate limit violations."""
        try:
            violations_key = f"rate_violations:{ip_address}"
            violation_count = self.redis_client.incr(violations_key)
            self.redis_client.expire(violations_key, 3600)  # 1 hour
            
            if violation_count >= 10:
                alert_details = {
                    'ip_address': ip_address,
                    'violations': violation_count,
                    'time_window': '1 hour'
                }
                self._raise_security_alert(alert_details, "Persistent rate limit violations")
                
        except Exception as e:
            logging.error(f"Rate limit violation check error: {str(e)}")
    
    def _check_device_anomalies(self, user_id: str):
        """Check for unusual device activity."""
        try:
            anomaly_key = f"device_anomalies:{user_id}"
            anomaly_count = self.redis_client.incr(anomaly_key)
            self.redis_client.expire(anomaly_key, 3600)  # 1 hour
            
            if anomaly_count >= 3:
                alert_details = {
                    'user_id': user_id,
                    'anomalies': anomaly_count,
                    'time_window': '1 hour'
                }
                self._raise_security_alert(alert_details, "Device fingerprint anomalies")
                
        except Exception as e:
            logging.error(f"Device anomaly check error: {str(e)}")
    
    def _raise_security_alert(self, details: Dict[str, Any], message: str):
        """Raise security alert."""
        alert_id = self._generate_event_id()
        alert = {
            'alert_id': alert_id,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'message': message,
            'severity': 'high',
            'details': details,
            'status': 'active'
        }
        
        # Store alert
        alert_key = f"security_alert:{alert_id}"
        self.redis_client.setex(alert_key, 86400 * 7, json.dumps(alert))
        
        # Add to alerts list
        self.redis_client.lpush("security_alerts", alert_id)
        self.redis_client.ltrim("security_alerts", 0, 999)  # Keep last 1000 alerts
        
        # Log critical alert
        self.logger.critical(json.dumps(alert))
    
    def _generate_event_id(self) -> str:
        """Generate unique event ID."""
        import uuid
        return str(uuid.uuid4())
    
    def get_user_audit_trail(self, user_id: str, limit: int = 100) -> list:
        """Get audit trail for specific user."""
        try:
            user_key = f"user_audit:{user_id}"
            event_ids = self.redis_client.lrange(user_key, 0, limit - 1)
            
            events = []
            for event_id in event_ids:
                event_key = f"audit:{event_id}"
                event_data = self.redis_client.get(event_key)
                if event_data:
                    events.append(json.loads(event_data))
            
            return events
            
        except Exception as e:
            logging.error(f"Get user audit trail error: {str(e)}")
            return []
    
    def get_security_alerts(self, severity: str = None, limit: int = 100) -> list:
        """Get security alerts."""
        try:
            alert_ids = self.redis_client.lrange("security_alerts", 0, limit - 1)
            
            alerts = []
            for alert_id in alert_ids:
                alert_key = f"security_alert:{alert_id}"
                alert_data = self.redis_client.get(alert_key)
                if alert_data:
                    alert = json.loads(alert_data)
                    if severity is None or alert.get('severity') == severity:
                        alerts.append(alert)
            
            return alerts
            
        except Exception as e:
            logging.error(f"Get security alerts error: {str(e)}")
            return []
    
    def search_audit_logs(self, 
                         event_type: str = None,
                         user_id: str = None,
                         start_time: datetime = None,
                         end_time: datetime = None,
                         limit: int = 100) -> list:
        """Search audit logs with filters."""
        try:
            # This is a simplified implementation
            # In production, you'd want to use a proper search engine like Elasticsearch
            
            if event_type:
                event_ids = self.redis_client.lrange(f"audit_type:{event_type}", 0, limit - 1)
            elif user_id:
                event_ids = self.redis_client.lrange(f"user_audit:{user_id}", 0, limit - 1)
            else:
                # Get recent events from all types
                event_ids = []
                for event_type_enum in AuditEventType:
                    type_events = self.redis_client.lrange(f"audit_type:{event_type_enum.value}", 0, 10)
                    event_ids.extend(type_events)
                event_ids = event_ids[:limit]
            
            events = []
            for event_id in event_ids:
                event_key = f"audit:{event_id}"
                event_data = self.redis_client.get(event_key)
                if event_data:
                    event = json.loads(event_data)
                    
                    # Apply time filters
                    if start_time or end_time:
                        event_time = datetime.fromisoformat(event['timestamp'].replace('Z', '+00:00'))
                        if start_time and event_time < start_time:
                            continue
                        if end_time and event_time > end_time:
                            continue
                    
                    events.append(event)
            
            return events
            
        except Exception as e:
            logging.error(f"Search audit logs error: {str(e)}")
            return []
