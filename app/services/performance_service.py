"""
Performance optimization service for caching, compression, and monitoring.
"""

import asyncio
import gzip
import zlib
import time
import json
import hashlib
from typing import Dict, List, Optional, Any, Union, Tuple
from datetime import datetime, timedelta
from dataclasses import asdict
import psutil
import threading
from collections import defaultdict, deque

from app.models.performance import (
    CacheConfig, RateLimitRule, PerformanceMetric, QueryOptimization,
    CompressionResult, ImageOptimization, BackgroundJob, ConnectionPoolConfig,
    HealthCheck, HealthStatus, PerformanceAlert, CacheStrategy, CompressionType,
    RateLimitScope, DEFAULT_CACHE_CONFIGS, DEFAULT_RATE_LIMITS, DEFAULT_PERFORMANCE_CONFIG
)

class PerformanceService:
    """Service for performance optimization and monitoring."""
    
    def __init__(self, redis_client=None, db_pool=None):
        """Initialize performance service."""
        self.redis_client = redis_client
        self.db_pool = db_pool
        self.memory_cache: Dict[str, Any] = {}
        self.rate_limit_store: Dict[str, Dict[str, Any]] = defaultdict(dict)
        self.metrics_store: deque = deque(maxlen=10000)
        self.cache_configs = DEFAULT_CACHE_CONFIGS.copy()
        self.rate_limits = {rule.endpoint: rule for rule in DEFAULT_RATE_LIMITS}
        self.performance_config = DEFAULT_PERFORMANCE_CONFIG.copy()
        self.health_checks: List[HealthCheck] = []
        self.alerts: List[PerformanceAlert] = []
        self._monitoring_active = False
        self._start_monitoring()
    
    def _start_monitoring(self):
        """Start background monitoring."""
        if not self._monitoring_active:
            self._monitoring_active = True
            threading.Thread(target=self._monitor_system, daemon=True).start()
    
    def _monitor_system(self):
        """Monitor system performance metrics."""
        while self._monitoring_active:
            try:
                # Collect system metrics
                cpu_percent = psutil.cpu_percent(interval=1)
                memory = psutil.virtual_memory()
                disk = psutil.disk_usage('/')
                
                # Store metrics
                timestamp = datetime.utcnow()
                self.metrics_store.append(PerformanceMetric(
                    "cpu_usage", cpu_percent, "percentage", timestamp
                ))
                self.metrics_store.append(PerformanceMetric(
                    "memory_usage", memory.percent, "percentage", timestamp
                ))
                self.metrics_store.append(PerformanceMetric(
                    "disk_usage", disk.percent, "percentage", timestamp
                ))
                
                # Check thresholds and create alerts
                try:
                    import asyncio
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    loop.run_until_complete(self._check_performance_thresholds(cpu_percent, memory.percent, disk.percent))
                    loop.close()
                except Exception as threshold_error:
                    print(f"Error checking thresholds: {threshold_error}")
                
                time.sleep(30)  # Monitor every 30 seconds
            except Exception as e:
                print(f"Monitoring error: {e}")
                time.sleep(60)
    
    async def _check_performance_thresholds(self, cpu: float, memory: float, disk: float):
        """Check if performance metrics exceed thresholds."""
        try:
            if cpu > self.performance_config["cpu_usage_threshold_percentage"]:
                await self._create_alert("cpu_usage", cpu, "High CPU usage detected")
            
            if memory > self.performance_config["memory_usage_threshold_percentage"]:
                await self._create_alert("memory_usage", memory, "High memory usage detected")
            
            if disk > self.performance_config["disk_usage_threshold_percentage"]:
                await self._create_alert("disk_usage", disk, "High disk usage detected")
        except Exception as e:
            print(f"Threshold check error: {e}")
    
    async def _create_alert(self, alert_type: str, value: float, message: str):
        """Create performance alert."""
        alert_id = f"{alert_type}_{int(time.time())}"
        severity = "critical" if value > 90 else "high" if value > 80 else "medium"
        
        alert = PerformanceAlert(
            alert_id=alert_id,
            alert_type=alert_type,
            threshold_value=self.performance_config.get(f"{alert_type}_threshold_percentage", 80),
            current_value=value,
            severity=severity,
            message=message
        )
        
        self.alerts.append(alert)
        
        # Keep only recent alerts
        if len(self.alerts) > 100:
            self.alerts = self.alerts[-50:]
    
    # Cache Management
    async def get_cached_data(self, key: str, cache_config: Optional[CacheConfig] = None) -> Optional[Any]:
        """Get data from cache with fallback strategies."""
        if not cache_config:
            cache_config = self.cache_configs.get("api_responses")
        
        try:
            # Try Redis first
            if cache_config.strategy in [CacheStrategy.REDIS_ONLY, CacheStrategy.MULTI_TIER] and self.redis_client:
                cached_data = await self.redis_client.get(cache_config.get_cache_key(key))
                if cached_data:
                    # Decompress if needed
                    if cache_config.compression != CompressionType.NONE:
                        cached_data = await self._decompress_data(cached_data, cache_config.compression)
                    return json.loads(cached_data) if isinstance(cached_data, (str, bytes)) else cached_data
            
            # Try memory cache
            if cache_config.strategy in [CacheStrategy.MEMORY_ONLY, CacheStrategy.MULTI_TIER]:
                cache_key = cache_config.get_cache_key(key)
                if cache_key in self.memory_cache:
                    cache_entry = self.memory_cache[cache_key]
                    if cache_entry["expires_at"] > datetime.utcnow():
                        return cache_entry["data"]
                    else:
                        del self.memory_cache[cache_key]
            
            return None
        except Exception as e:
            print(f"Cache get error: {e}")
            return None
    
    async def set_cached_data(
        self, 
        key: str, 
        data: Any, 
        cache_config: Optional[CacheConfig] = None,
        ttl: Optional[int] = None
    ) -> bool:
        """Set data in cache with compression."""
        if not cache_config:
            cache_config = self.cache_configs.get("api_responses")
        
        try:
            ttl = ttl or cache_config.ttl_seconds
            serialized_data = json.dumps(data, default=str)
            
            # Compress data if configured
            if cache_config.compression != CompressionType.NONE:
                serialized_data = await self._compress_data(serialized_data, cache_config.compression)
            
            # Store in Redis
            if cache_config.strategy in [CacheStrategy.REDIS_ONLY, CacheStrategy.MULTI_TIER] and self.redis_client:
                await self.redis_client.setex(cache_config.get_cache_key(key), ttl, serialized_data)
            
            # Store in memory cache
            if cache_config.strategy in [CacheStrategy.MEMORY_ONLY, CacheStrategy.MULTI_TIER]:
                cache_key = cache_config.get_cache_key(key)
                self.memory_cache[cache_key] = {
                    "data": data,
                    "expires_at": datetime.utcnow() + timedelta(seconds=ttl)
                }
            
            return True
        except Exception as e:
            print(f"Cache set error: {e}")
            return False
    
    async def invalidate_cache(self, pattern: str, cache_config: Optional[CacheConfig] = None) -> bool:
        """Invalidate cache entries matching pattern."""
        try:
            if self.redis_client:
                keys = await self.redis_client.keys(pattern)
                if keys:
                    await self.redis_client.delete(*keys)
            
            # Clear matching keys from memory cache
            keys_to_delete = [k for k in self.memory_cache.keys() if pattern.replace('*', '') in k]
            for key in keys_to_delete:
                del self.memory_cache[key]
            
            return True
        except Exception as e:
            print(f"Cache invalidation error: {e}")
            return False
    
    # Compression
    async def _compress_data(self, data: Union[str, bytes], compression_type: CompressionType) -> bytes:
        """Compress data using specified algorithm."""
        if isinstance(data, str):
            data = data.encode('utf-8')
        
        if compression_type == CompressionType.GZIP:
            return gzip.compress(data)
        elif compression_type == CompressionType.DEFLATE:
            return zlib.compress(data)
        elif compression_type == CompressionType.BROTLI:
            try:
                import brotli
                return brotli.compress(data)
            except (ImportError, Exception):
                return gzip.compress(data)  # Fallback to gzip
        
        return data
    
    async def _decompress_data(self, data: bytes, compression_type: CompressionType) -> str:
        """Decompress data using specified algorithm."""
        try:
            if compression_type == CompressionType.GZIP:
                return gzip.decompress(data).decode('utf-8')
            elif compression_type == CompressionType.DEFLATE:
                return zlib.decompress(data).decode('utf-8')
            elif compression_type == CompressionType.BROTLI:
                try:
                    import brotli
                    return brotli.decompress(data).decode('utf-8')
                except (ImportError, Exception):
                    return gzip.decompress(data).decode('utf-8')  # Fallback to gzip
            
            return data.decode('utf-8') if isinstance(data, bytes) else data
        except Exception as e:
            print(f"Decompression error: {e}")
            return data.decode('utf-8') if isinstance(data, bytes) else str(data)
    
    async def compress_response(self, data: Any, compression_type: CompressionType = CompressionType.GZIP) -> CompressionResult:
        """Compress API response data."""
        start_time = time.time()
        
        # Serialize data
        if not isinstance(data, (str, bytes)):
            serialized_data = json.dumps(data, default=str)
        else:
            serialized_data = data
        
        original_size = len(serialized_data.encode('utf-8') if isinstance(serialized_data, str) else serialized_data)
        
        # Compress
        compressed_data = await self._compress_data(serialized_data, compression_type)
        compressed_size = len(compressed_data)
        
        processing_time = (time.time() - start_time) * 1000  # Convert to milliseconds
        compression_ratio = compressed_size / original_size if original_size > 0 else 1.0
        
        return CompressionResult(
            original_size=original_size,
            compressed_size=compressed_size,
            compression_ratio=compression_ratio,
            compression_type=compression_type,
            processing_time_ms=processing_time
        )
    
    # Rate Limiting
    async def check_rate_limit(self, endpoint: str, identifier: str, rule: Optional[RateLimitRule] = None) -> Tuple[bool, Dict[str, Any]]:
        """Check if request is within rate limits."""
        if not rule:
            rule = self.rate_limits.get(endpoint) or self.rate_limits.get("/api/v1/*")
        
        if not rule or not rule.enabled:
            return True, {"allowed": True, "reason": "rate_limiting_disabled"}
        
        current_time = datetime.utcnow()
        window_start = current_time - timedelta(seconds=rule.window_seconds)
        
        # Create rate limit key
        rate_key = f"{rule.scope.value}:{endpoint}:{identifier}"
        
        # Get current requests in window
        if rate_key not in self.rate_limit_store:
            self.rate_limit_store[rate_key] = {"requests": [], "blocked_until": None}
        
        rate_data = self.rate_limit_store[rate_key]
        
        # Check if currently blocked
        if rate_data["blocked_until"] and current_time < rate_data["blocked_until"]:
            return False, {
                "allowed": False,
                "reason": "rate_limit_exceeded",
                "blocked_until": rate_data["blocked_until"].isoformat(),
                "retry_after": (rate_data["blocked_until"] - current_time).total_seconds()
            }
        
        # Clean old requests
        rate_data["requests"] = [req_time for req_time in rate_data["requests"] if req_time > window_start]
        
        # Check current rate
        current_count = len(rate_data["requests"])
        
        if current_count >= rule.limit:
            # Set block duration if configured
            if rule.block_duration_seconds:
                rate_data["blocked_until"] = current_time + timedelta(seconds=rule.block_duration_seconds)
            
            return False, {
                "allowed": False,
                "reason": "rate_limit_exceeded",
                "current_count": current_count,
                "limit": rule.limit,
                "window_seconds": rule.window_seconds,
                "reset_at": (window_start + timedelta(seconds=rule.window_seconds)).isoformat()
            }
        
        # Allow request and record it
        rate_data["requests"].append(current_time)
        
        return True, {
            "allowed": True,
            "current_count": current_count + 1,
            "limit": rule.limit,
            "remaining": rule.limit - current_count - 1,
            "reset_at": (window_start + timedelta(seconds=rule.window_seconds)).isoformat()
        }
    
    async def get_rate_limit_status(self, endpoint: str, identifier: str) -> Dict[str, Any]:
        """Get current rate limit status for an identifier."""
        rule = self.rate_limits.get(endpoint) or self.rate_limits.get("/api/v1/*")
        
        if not rule:
            return {"rate_limiting": False}
        
        allowed, status = await self.check_rate_limit(endpoint, identifier, rule)
        return {
            "rate_limiting": True,
            "endpoint": endpoint,
            "identifier": identifier,
            "status": status
        }
    
    # Performance Metrics
    async def record_metric(self, metric: PerformanceMetric):
        """Record a performance metric."""
        self.metrics_store.append(metric)
        
        # Also store in Redis for persistence
        if self.redis_client:
            try:
                metric_key = f"metrics:{metric.metric_name}:{int(metric.timestamp.timestamp())}"
                await self.redis_client.setex(metric_key, 3600, json.dumps(asdict(metric), default=str))
            except Exception as e:
                print(f"Error storing metric: {e}")
    
    async def get_metrics(
        self, 
        metric_name: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100
    ) -> List[PerformanceMetric]:
        """Get performance metrics with filtering."""
        metrics = list(self.metrics_store)
        
        # Filter by metric name
        if metric_name:
            metrics = [m for m in metrics if m.metric_name == metric_name]
        
        # Filter by time range
        if start_time:
            metrics = [m for m in metrics if m.timestamp >= start_time]
        if end_time:
            metrics = [m for m in metrics if m.timestamp <= end_time]
        
        # Sort by timestamp (most recent first)
        metrics.sort(key=lambda x: x.timestamp, reverse=True)
        
        return metrics[:limit]
    
    async def get_performance_summary(self) -> Dict[str, Any]:
        """Get performance summary statistics."""
        current_time = datetime.utcnow()
        one_hour_ago = current_time - timedelta(hours=1)
        
        # Get recent metrics
        recent_metrics = await self.get_metrics(start_time=one_hour_ago)
        
        # Group by metric name
        metrics_by_name = defaultdict(list)
        for metric in recent_metrics:
            metrics_by_name[metric.metric_name].append(metric.value)
        
        # Calculate statistics
        summary = {}
        for metric_name, values in metrics_by_name.items():
            if values:
                summary[metric_name] = {
                    "count": len(values),
                    "average": sum(values) / len(values),
                    "min": min(values),
                    "max": max(values),
                    "latest": values[0] if values else None
                }
        
        # Add system info
        try:
            summary["system"] = {
                "cpu_count": psutil.cpu_count(),
                "memory_total_gb": round(psutil.virtual_memory().total / (1024**3), 2),
                "disk_total_gb": round(psutil.disk_usage('/').total / (1024**3), 2),
                "uptime_seconds": time.time() - psutil.boot_time()
            }
        except Exception:
            pass
        
        return summary
    
    # Health Checks
    async def add_health_check(self, health_check: HealthCheck):
        """Add a health check."""
        self.health_checks.append(health_check)
    
    async def run_health_check(self, health_check: HealthCheck) -> HealthStatus:
        """Run a single health check."""
        start_time = time.time()
        
        try:
            if health_check.check_type == "database":
                # Test database connection
                if self.db_pool:
                    # Simulate database check
                    await asyncio.sleep(0.01)
                    status = "healthy"
                    error_message = None
                else:
                    status = "unhealthy"
                    error_message = "Database pool not available"
            
            elif health_check.check_type == "redis":
                # Test Redis connection
                if self.redis_client:
                    await self.redis_client.ping()
                    status = "healthy"
                    error_message = None
                else:
                    status = "unhealthy"
                    error_message = "Redis client not available"
            
            elif health_check.check_type == "disk_space":
                # Check disk space
                disk_usage = psutil.disk_usage('/')
                if disk_usage.percent < 90:
                    status = "healthy"
                    error_message = None
                else:
                    status = "unhealthy"
                    error_message = f"Disk usage at {disk_usage.percent}%"
            
            else:
                # Generic health check
                status = "healthy"
                error_message = None
        
        except Exception as e:
            status = "unhealthy"
            error_message = str(e)
        
        response_time = (time.time() - start_time) * 1000  # Convert to milliseconds
        
        return HealthStatus(
            service_name=health_check.name,
            status=status,
            response_time_ms=response_time,
            error_message=error_message
        )
    
    async def run_all_health_checks(self) -> Dict[str, HealthStatus]:
        """Run all configured health checks."""
        results = {}
        
        for health_check in self.health_checks:
            if health_check.enabled:
                status = await self.run_health_check(health_check)
                results[health_check.name] = status
        
        return results
    
    async def get_system_health(self) -> Dict[str, Any]:
        """Get overall system health status."""
        health_results = await self.run_all_health_checks()
        
        # Determine overall status
        all_healthy = all(status.status == "healthy" for status in health_results.values())
        any_unhealthy = any(status.status == "unhealthy" for status in health_results.values())
        
        if all_healthy:
            overall_status = "healthy"
        elif any_unhealthy:
            overall_status = "unhealthy"
        else:
            overall_status = "degraded"
        
        return {
            "overall_status": overall_status,
            "timestamp": datetime.utcnow().isoformat(),
            "services": {name: asdict(status) for name, status in health_results.items()},
            "active_alerts": len([alert for alert in self.alerts if not alert.resolved_at])
        }
    
    # Background Jobs
    async def queue_background_job(self, job: BackgroundJob) -> bool:
        """Queue a background job for processing."""
        try:
            # Store job in Redis for processing
            if self.redis_client:
                job_key = f"background_job:{job.job_id}"
                job_data = asdict(job)
                job_data["created_at"] = job.created_at.isoformat()
                if job.scheduled_at:
                    job_data["scheduled_at"] = job.scheduled_at.isoformat()
                
                await self.redis_client.setex(job_key, 3600, json.dumps(job_data, default=str))
                
                # Add to queue
                queue_key = f"job_queue:{job.queue_name}"
                await self.redis_client.lpush(queue_key, job.job_id)
                
                return True
            
            return False
        except Exception as e:
            print(f"Error queuing background job: {e}")
            return False
    
    async def get_job_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a background job."""
        try:
            if self.redis_client:
                job_key = f"background_job:{job_id}"
                job_data = await self.redis_client.get(job_key)
                if job_data:
                    return json.loads(job_data)
            return None
        except Exception as e:
            print(f"Error getting job status: {e}")
            return None
    
    # Configuration
    async def update_cache_config(self, config_name: str, config: CacheConfig):
        """Update cache configuration."""
        self.cache_configs[config_name] = config
    
    async def update_rate_limit(self, endpoint: str, rule: RateLimitRule):
        """Update rate limiting rule."""
        self.rate_limits[endpoint] = rule
    
    async def get_cache_statistics(self) -> Dict[str, Any]:
        """Get cache performance statistics."""
        stats = {
            "memory_cache_size": len(self.memory_cache),
            "cache_configs": len(self.cache_configs),
            "hit_rate": 0.0,  # Would track this in production
            "miss_rate": 0.0,
            "eviction_count": 0
        }
        
        if self.redis_client:
            try:
                info = await self.redis_client.info()
                stats["redis_memory_usage"] = info.get("used_memory", 0)
                stats["redis_connected_clients"] = info.get("connected_clients", 0)
                stats["redis_keyspace_hits"] = info.get("keyspace_hits", 0)
                stats["redis_keyspace_misses"] = info.get("keyspace_misses", 0)
                
                total_requests = stats["redis_keyspace_hits"] + stats["redis_keyspace_misses"]
                if total_requests > 0:
                    stats["hit_rate"] = stats["redis_keyspace_hits"] / total_requests
                    stats["miss_rate"] = stats["redis_keyspace_misses"] / total_requests
            except Exception as e:
                print(f"Error getting Redis stats: {e}")
        
        return stats
