"""
Performance optimization API routes for monitoring and health checks.
"""

from flask import Blueprint, request, jsonify, current_app, Response
from typing import Dict, Any, Optional
import asyncio
import time
import json
import gzip
from functools import wraps
from datetime import datetime, timedelta

from app.services.performance_service import PerformanceService
from app.models.performance import (
    PerformanceMetric, RateLimitRule, BackgroundJob, HealthCheck,
    RateLimitScope, CompressionType
)

# Create blueprint
performance_bp = Blueprint('performance', __name__, url_prefix='/api/v1/performance')

# Initialize service (would be injected in production)
performance_service = PerformanceService()

def async_route(f):
    """Decorator to handle async routes in Flask."""
    @wraps(f)
    def wrapper(*args, **kwargs):
        return asyncio.run(f(*args, **kwargs))
    return wrapper

def compress_response(data: Dict[str, Any], accept_encoding: str = "") -> Response:
    """Compress response based on client capabilities."""
    json_data = json.dumps(data, default=str)
    
    # Check if client accepts compression
    if 'gzip' in accept_encoding.lower():
        compressed_data = gzip.compress(json_data.encode('utf-8'))
        response = Response(
            compressed_data,
            mimetype='application/json',
            headers={'Content-Encoding': 'gzip'}
        )
    else:
        response = Response(json_data, mimetype='application/json')
    
    # Add performance headers
    response.headers['X-Response-Time'] = f"{time.time():.3f}"
    response.headers['Cache-Control'] = 'public, max-age=60'
    
    return response

@performance_bp.route('/health', methods=['GET'])
@async_route
async def health_check():
    """
    Comprehensive system health check.
    """
    try:
        start_time = time.time()
        
        # Run all health checks
        health_status = await performance_service.get_system_health()
        
        # Add response time
        health_status['response_time_ms'] = round((time.time() - start_time) * 1000, 2)
        
        # Determine HTTP status code based on health
        if health_status['overall_status'] == 'healthy':
            status_code = 200
        elif health_status['overall_status'] == 'degraded':
            status_code = 206  # Partial Content
        else:
            status_code = 503  # Service Unavailable
        
        response_data = {
            "success": True,
            "health": health_status
        }
        
        accept_encoding = request.headers.get('Accept-Encoding', '')
        response = compress_response(response_data, accept_encoding)
        response.status_code = status_code
        
        return response
        
    except Exception as e:
        current_app.logger.error(f"Error in health check: {e}")
        return jsonify({
            "success": False,
            "health": {
                "overall_status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
        }), 503

@performance_bp.route('/metrics', methods=['GET'])
@async_route
async def get_performance_metrics():
    """
    Get performance metrics with filtering options.
    
    Query Parameters:
    - metric_name: Filter by specific metric name
    - start_time: Start time in ISO format
    - end_time: End time in ISO format
    - limit: Maximum number of results (default: 100)
    """
    try:
        # Parse query parameters
        metric_name = request.args.get('metric_name')
        start_time_str = request.args.get('start_time')
        end_time_str = request.args.get('end_time')
        limit = int(request.args.get('limit', 100))
        
        # Parse datetime parameters
        start_time = None
        end_time = None
        
        if start_time_str:
            try:
                start_time = datetime.fromisoformat(start_time_str.replace('Z', '+00:00'))
            except ValueError:
                return jsonify({
                    "success": False,
                    "error": {
                        "code": "INVALID_START_TIME",
                        "message": "Invalid start_time format. Use ISO format (YYYY-MM-DDTHH:MM:SS)"
                    }
                }), 400
        
        if end_time_str:
            try:
                end_time = datetime.fromisoformat(end_time_str.replace('Z', '+00:00'))
            except ValueError:
                return jsonify({
                    "success": False,
                    "error": {
                        "code": "INVALID_END_TIME",
                        "message": "Invalid end_time format. Use ISO format (YYYY-MM-DDTHH:MM:SS)"
                    }
                }), 400
        
        # Get metrics
        metrics = await performance_service.get_metrics(
            metric_name=metric_name,
            start_time=start_time,
            end_time=end_time,
            limit=limit
        )
        
        # Convert to dict format
        metrics_data = []
        for metric in metrics:
            metric_dict = {
                "metric_name": metric.metric_name,
                "value": metric.value,
                "unit": metric.unit,
                "timestamp": metric.timestamp.isoformat(),
                "tags": metric.tags,
                "metadata": metric.metadata
            }
            metrics_data.append(metric_dict)
        
        response_data = {
            "success": True,
            "metrics": metrics_data,
            "count": len(metrics_data),
            "filters": {
                "metric_name": metric_name,
                "start_time": start_time_str,
                "end_time": end_time_str,
                "limit": limit
            }
        }
        
        accept_encoding = request.headers.get('Accept-Encoding', '')
        return compress_response(response_data, accept_encoding)
        
    except Exception as e:
        current_app.logger.error(f"Error getting performance metrics: {e}")
        return jsonify({
            "success": False,
            "error": {
                "code": "METRICS_ERROR",
                "message": "Failed to retrieve performance metrics",
                "details": str(e)
            }
        }), 500

@performance_bp.route('/metrics/summary', methods=['GET'])
@async_route
async def get_performance_summary():
    """Get performance summary statistics."""
    try:
        summary = await performance_service.get_performance_summary()
        
        response_data = {
            "success": True,
            "summary": summary,
            "generated_at": datetime.utcnow().isoformat()
        }
        
        accept_encoding = request.headers.get('Accept-Encoding', '')
        return compress_response(response_data, accept_encoding)
        
    except Exception as e:
        current_app.logger.error(f"Error getting performance summary: {e}")
        return jsonify({
            "success": False,
            "error": {
                "code": "SUMMARY_ERROR",
                "message": "Failed to retrieve performance summary",
                "details": str(e)
            }
        }), 500

@performance_bp.route('/cache/stats', methods=['GET'])
@async_route
async def get_cache_statistics():
    """Get cache performance statistics."""
    try:
        cache_stats = await performance_service.get_cache_statistics()
        
        response_data = {
            "success": True,
            "cache_statistics": cache_stats,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        return jsonify(response_data)
        
    except Exception as e:
        current_app.logger.error(f"Error getting cache statistics: {e}")
        return jsonify({
            "success": False,
            "error": {
                "code": "CACHE_STATS_ERROR",
                "message": "Failed to retrieve cache statistics",
                "details": str(e)
            }
        }), 500

@performance_bp.route('/cache/clear', methods=['POST'])
@async_route
async def clear_cache():
    """
    Clear cache entries matching pattern.
    
    Request Body:
    {
        "pattern": "cache_key_pattern*",
        "confirm": true
    }
    """
    try:
        data = request.get_json()
        
        if not data or 'pattern' not in data:
            return jsonify({
                "success": False,
                "error": {
                    "code": "MISSING_PATTERN",
                    "message": "Cache pattern is required"
                }
            }), 400
        
        pattern = data.get('pattern')
        confirm = data.get('confirm', False)
        
        if not confirm:
            return jsonify({
                "success": False,
                "error": {
                    "code": "CONFIRMATION_REQUIRED",
                    "message": "Set 'confirm': true to clear cache"
                }
            }), 400
        
        # Clear cache
        success = await performance_service.invalidate_cache(pattern)
        
        if success:
            return jsonify({
                "success": True,
                "message": f"Cache entries matching '{pattern}' cleared successfully",
                "pattern": pattern,
                "cleared_at": datetime.utcnow().isoformat()
            })
        else:
            return jsonify({
                "success": False,
                "error": {
                    "code": "CACHE_CLEAR_FAILED",
                    "message": "Failed to clear cache entries"
                }
            }), 500
        
    except Exception as e:
        current_app.logger.error(f"Error clearing cache: {e}")
        return jsonify({
            "success": False,
            "error": {
                "code": "CACHE_CLEAR_ERROR",
                "message": "Failed to clear cache",
                "details": str(e)
            }
        }), 500

@performance_bp.route('/rate-limit/status', methods=['GET'])
@async_route
async def get_rate_limit_status():
    """
    Get rate limit status for current user/IP.
    
    Query Parameters:
    - endpoint: Specific endpoint to check (optional)
    - identifier: User ID or IP address (optional, defaults to request IP)
    """
    try:
        endpoint = request.args.get('endpoint', '/api/v1/*')
        identifier = request.args.get('identifier', request.remote_addr)
        
        # Get rate limit status
        status = await performance_service.get_rate_limit_status(endpoint, identifier)
        
        return jsonify({
            "success": True,
            "rate_limit_status": status,
            "endpoint": endpoint,
            "identifier": identifier,
            "timestamp": datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting rate limit status: {e}")
        return jsonify({
            "success": False,
            "error": {
                "code": "RATE_LIMIT_STATUS_ERROR",
                "message": "Failed to get rate limit status",
                "details": str(e)
            }
        }), 500

@performance_bp.route('/compression/test', methods=['POST'])
@async_route
async def test_compression():
    """
    Test compression efficiency on provided data.
    
    Request Body:
    {
        "data": "Data to compress",
        "compression_type": "gzip|deflate|brotli"
    }
    """
    try:
        data = request.get_json()
        
        if not data or 'data' not in data:
            return jsonify({
                "success": False,
                "error": {
                    "code": "MISSING_DATA",
                    "message": "Data to compress is required"
                }
            }), 400
        
        test_data = data.get('data')
        compression_type_str = data.get('compression_type', 'gzip')
        
        # Validate compression type
        try:
            compression_type = CompressionType(compression_type_str)
        except ValueError:
            return jsonify({
                "success": False,
                "error": {
                    "code": "INVALID_COMPRESSION_TYPE",
                    "message": f"Invalid compression type. Supported: {[ct.value for ct in CompressionType]}"
                }
            }), 400
        
        # Test compression
        compression_result = await performance_service.compress_response(test_data, compression_type)
        
        return jsonify({
            "success": True,
            "compression_result": {
                "original_size_bytes": compression_result.original_size,
                "compressed_size_bytes": compression_result.compressed_size,
                "compression_ratio": compression_result.compression_ratio,
                "size_reduction_percentage": compression_result.size_reduction_percentage,
                "compression_type": compression_result.compression_type.value,
                "processing_time_ms": compression_result.processing_time_ms
            }
        })
        
    except Exception as e:
        current_app.logger.error(f"Error testing compression: {e}")
        return jsonify({
            "success": False,
            "error": {
                "code": "COMPRESSION_TEST_ERROR",
                "message": "Failed to test compression",
                "details": str(e)
            }
        }), 500

@performance_bp.route('/jobs/queue', methods=['POST'])
@async_route
async def queue_background_job():
    """
    Queue a background job for processing.
    
    Request Body:
    {
        "job_type": "email|report|cleanup",
        "job_data": {...},
        "priority": 5,
        "queue_name": "default",
        "scheduled_at": "2024-01-15T10:30:00Z"
    }
    """
    try:
        data = request.get_json()
        
        if not data or 'job_type' not in data:
            return jsonify({
                "success": False,
                "error": {
                    "code": "MISSING_JOB_TYPE",
                    "message": "Job type is required"
                }
            }), 400
        
        job_type = data.get('job_type')
        job_data = data.get('job_data', {})
        priority = data.get('priority', 5)
        queue_name = data.get('queue_name', 'default')
        scheduled_at_str = data.get('scheduled_at')
        
        # Parse scheduled time if provided
        scheduled_at = None
        if scheduled_at_str:
            try:
                scheduled_at = datetime.fromisoformat(scheduled_at_str.replace('Z', '+00:00'))
            except ValueError:
                return jsonify({
                    "success": False,
                    "error": {
                        "code": "INVALID_SCHEDULED_TIME",
                        "message": "Invalid scheduled_at format. Use ISO format"
                    }
                }), 400
        
        # Create background job
        import uuid
        job_id = str(uuid.uuid4())
        
        background_job = BackgroundJob(
            job_id=job_id,
            job_type=job_type,
            priority=priority,
            queue_name=queue_name,
            scheduled_at=scheduled_at
        )
        
        # Queue the job
        success = await performance_service.queue_background_job(background_job)
        
        if success:
            return jsonify({
                "success": True,
                "message": "Job queued successfully",
                "job_id": job_id,
                "job_type": job_type,
                "queue_name": queue_name,
                "priority": priority,
                "queued_at": datetime.utcnow().isoformat()
            })
        else:
            return jsonify({
                "success": False,
                "error": {
                    "code": "JOB_QUEUE_FAILED",
                    "message": "Failed to queue background job"
                }
            }), 500
        
    except Exception as e:
        current_app.logger.error(f"Error queuing background job: {e}")
        return jsonify({
            "success": False,
            "error": {
                "code": "JOB_QUEUE_ERROR",
                "message": "Failed to queue background job",
                "details": str(e)
            }
        }), 500

@performance_bp.route('/jobs/<job_id>', methods=['GET'])
@async_route
async def get_job_status(job_id):
    """Get status of a background job."""
    try:
        job_status = await performance_service.get_job_status(job_id)
        
        if job_status:
            return jsonify({
                "success": True,
                "job_status": job_status
            })
        else:
            return jsonify({
                "success": False,
                "error": {
                    "code": "JOB_NOT_FOUND",
                    "message": f"Job with ID {job_id} not found"
                }
            }), 404
        
    except Exception as e:
        current_app.logger.error(f"Error getting job status: {e}")
        return jsonify({
            "success": False,
            "error": {
                "code": "JOB_STATUS_ERROR",
                "message": "Failed to get job status",
                "details": str(e)
            }
        }), 500

@performance_bp.route('/alerts', methods=['GET'])
@async_route
async def get_performance_alerts():
    """
    Get current performance alerts.
    
    Query Parameters:
    - severity: Filter by severity (low|medium|high|critical)
    - resolved: Include resolved alerts (true|false, default: false)
    - limit: Maximum number of alerts (default: 50)
    """
    try:
        severity_filter = request.args.get('severity')
        include_resolved = request.args.get('resolved', 'false').lower() == 'true'
        limit = int(request.args.get('limit', 50))
        
        # Get alerts
        alerts = performance_service.alerts.copy()
        
        # Filter by resolution status
        if not include_resolved:
            alerts = [alert for alert in alerts if not alert.resolved_at]
        
        # Filter by severity
        if severity_filter:
            alerts = [alert for alert in alerts if alert.severity == severity_filter]
        
        # Sort by trigger time (most recent first)
        alerts.sort(key=lambda x: x.triggered_at, reverse=True)
        
        # Limit results
        alerts = alerts[:limit]
        
        # Convert to dict format
        alerts_data = []
        for alert in alerts:
            alert_dict = {
                "alert_id": alert.alert_id,
                "alert_type": alert.alert_type,
                "threshold_value": alert.threshold_value,
                "current_value": alert.current_value,
                "severity": alert.severity,
                "message": alert.message,
                "triggered_at": alert.triggered_at.isoformat(),
                "resolved_at": alert.resolved_at.isoformat() if alert.resolved_at else None,
                "metadata": alert.metadata
            }
            alerts_data.append(alert_dict)
        
        return jsonify({
            "success": True,
            "alerts": alerts_data,
            "count": len(alerts_data),
            "filters": {
                "severity": severity_filter,
                "include_resolved": include_resolved,
                "limit": limit
            }
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting performance alerts: {e}")
        return jsonify({
            "success": False,
            "error": {
                "code": "ALERTS_ERROR",
                "message": "Failed to get performance alerts",
                "details": str(e)
            }
        }), 500

@performance_bp.route('/system/info', methods=['GET'])
@async_route
async def get_system_info():
    """Get system information and resource usage."""
    try:
        import psutil
        import platform
        
        # Get system information
        system_info = {
            "platform": {
                "system": platform.system(),
                "release": platform.release(),
                "version": platform.version(),
                "machine": platform.machine(),
                "processor": platform.processor()
            },
            "cpu": {
                "count": psutil.cpu_count(),
                "usage_percent": psutil.cpu_percent(interval=1),
                "frequency": psutil.cpu_freq()._asdict() if psutil.cpu_freq() else None
            },
            "memory": {
                "total_gb": round(psutil.virtual_memory().total / (1024**3), 2),
                "available_gb": round(psutil.virtual_memory().available / (1024**3), 2),
                "used_percent": psutil.virtual_memory().percent
            },
            "disk": {
                "total_gb": round(psutil.disk_usage('/').total / (1024**3), 2),
                "free_gb": round(psutil.disk_usage('/').free / (1024**3), 2),
                "used_percent": round(psutil.disk_usage('/').percent, 2)
            },
            "network": {
                "interfaces": list(psutil.net_if_addrs().keys()),
                "stats": psutil.net_io_counters()._asdict()
            },
            "uptime_seconds": round(time.time() - psutil.boot_time(), 2)
        }
        
        return jsonify({
            "success": True,
            "system_info": system_info,
            "timestamp": datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting system info: {e}")
        return jsonify({
            "success": False,
            "error": {
                "code": "SYSTEM_INFO_ERROR",
                "message": "Failed to get system information",
                "details": str(e)
            }
        }), 500

# Error handlers
@performance_bp.errorhandler(404)
def not_found(error):
    """Handle 404 errors."""
    return jsonify({
        "success": False,
        "error": {
            "code": "ENDPOINT_NOT_FOUND",
            "message": "Performance endpoint not found",
            "available_endpoints": [
                "/health",
                "/metrics",
                "/metrics/summary",
                "/cache/stats",
                "/cache/clear",
                "/rate-limit/status",
                "/compression/test",
                "/jobs/queue",
                "/jobs/<job_id>",
                "/alerts",
                "/system/info"
            ]
        }
    }), 404

@performance_bp.errorhandler(500)
def internal_error(error):
    """Handle 500 errors."""
    return jsonify({
        "success": False,
        "error": {
            "code": "INTERNAL_SERVER_ERROR",
            "message": "Internal server error in performance service"
        }
    }), 500
