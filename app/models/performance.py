"""
Performance optimization models and configurations.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timedelta
from enum import Enum
import json

class CacheStrategy(Enum):
    """Different caching strategies."""
    NO_CACHE = "no-cache"
    MEMORY_ONLY = "memory"
    REDIS_ONLY = "redis"
    MULTI_TIER = "multi-tier"
    WRITE_THROUGH = "write-through"
    WRITE_BEHIND = "write-behind"

class CompressionType(Enum):
    """Supported compression types."""
    NONE = "none"
    GZIP = "gzip"
    DEFLATE = "deflate"
    BROTLI = "br"

class RateLimitScope(Enum):
    """Rate limit scopes."""
    IP_ADDRESS = "ip"
    USER_ID = "user"
    API_KEY = "api_key"
    ENDPOINT = "endpoint"
    GLOBAL = "global"

@dataclass
class CacheConfig:
    """Cache configuration for different data types."""
    key_prefix: str
    ttl_seconds: int
    strategy: CacheStrategy = CacheStrategy.REDIS_ONLY
    compression: CompressionType = CompressionType.GZIP
    max_size_mb: int = 10
    enabled: bool = True
    
    def get_cache_key(self, identifier: str) -> str:
        """Generate cache key with prefix."""
        return f"{self.key_prefix}:{identifier}"

@dataclass
class RateLimitRule:
    """Rate limiting rule configuration."""
    endpoint: str
    scope: RateLimitScope
    limit: int
    window_seconds: int
    burst_limit: Optional[int] = None
    block_duration_seconds: Optional[int] = None
    enabled: bool = True
    
    def __post_init__(self):
        """Set default burst limit if not provided."""
        if self.burst_limit is None:
            self.burst_limit = int(self.limit * 1.2)  # 20% burst allowance

@dataclass
class PerformanceMetric:
    """Performance metric data."""
    metric_name: str
    value: float
    unit: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    tags: Dict[str, str] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class QueryOptimization:
    """Database query optimization configuration."""
    table_name: str
    query_pattern: str
    optimization_type: str  # index, cache, rewrite, etc.
    enabled: bool = True
    performance_gain: Optional[float] = None
    
@dataclass
class CompressionResult:
    """Result of content compression."""
    original_size: int
    compressed_size: int
    compression_ratio: float
    compression_type: CompressionType
    processing_time_ms: float
    
    @property
    def size_reduction_percentage(self) -> float:
        """Calculate size reduction percentage."""
        return ((self.original_size - self.compressed_size) / self.original_size) * 100

@dataclass
class ImageOptimization:
    """Image optimization configuration."""
    format_preference: List[str] = field(default_factory=lambda: ["webp", "avif", "jpg", "png"])
    quality_settings: Dict[str, int] = field(default_factory=lambda: {
        "webp": 85,
        "jpg": 80,
        "png": 95,
        "avif": 80
    })
    max_width: int = 1920
    max_height: int = 1080
    enable_progressive: bool = True
    enable_responsive: bool = True
    
@dataclass
class BackgroundJob:
    """Background job configuration."""
    job_id: str
    job_type: str
    priority: int = 5  # 1-10, higher is more important
    retry_count: int = 3
    retry_delay_seconds: int = 60
    timeout_seconds: int = 300
    queue_name: str = "default"
    scheduled_at: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    
@dataclass
class ConnectionPoolConfig:
    """Database connection pool configuration."""
    min_connections: int = 5
    max_connections: int = 20
    connection_timeout_seconds: int = 30
    idle_timeout_seconds: int = 300
    max_lifetime_seconds: int = 3600
    health_check_interval_seconds: int = 60
    
@dataclass
class HealthCheck:
    """Health check configuration."""
    name: str
    endpoint: str
    check_type: str  # database, redis, external_api, disk_space, etc.
    timeout_seconds: int = 10
    interval_seconds: int = 30
    failure_threshold: int = 3
    success_threshold: int = 2
    enabled: bool = True
    
@dataclass
class HealthStatus:
    """Health check status result."""
    service_name: str
    status: str  # healthy, unhealthy, degraded
    response_time_ms: float
    error_message: Optional[str] = None
    last_check: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class PerformanceAlert:
    """Performance monitoring alert."""
    alert_id: str
    alert_type: str  # response_time, error_rate, cpu_usage, memory_usage
    threshold_value: float
    current_value: float
    severity: str  # low, medium, high, critical
    message: str
    triggered_at: datetime = field(default_factory=datetime.utcnow)
    resolved_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

# Default cache configurations
DEFAULT_CACHE_CONFIGS = {
    "localization_strings": CacheConfig(
        key_prefix="loc_strings",
        ttl_seconds=3600,  # 1 hour
        strategy=CacheStrategy.REDIS_ONLY,
        compression=CompressionType.GZIP
    ),
    "user_sessions": CacheConfig(
        key_prefix="user_session",
        ttl_seconds=1800,  # 30 minutes
        strategy=CacheStrategy.REDIS_ONLY
    ),
    "chat_history": CacheConfig(
        key_prefix="chat_hist",
        ttl_seconds=300,  # 5 minutes
        strategy=CacheStrategy.MEMORY_ONLY
    ),
    "file_metadata": CacheConfig(
        key_prefix="file_meta",
        ttl_seconds=7200,  # 2 hours
        strategy=CacheStrategy.MULTI_TIER
    ),
    "api_responses": CacheConfig(
        key_prefix="api_resp",
        ttl_seconds=60,  # 1 minute
        strategy=CacheStrategy.REDIS_ONLY,
        compression=CompressionType.GZIP
    )
}

# Default rate limiting rules
DEFAULT_RATE_LIMITS = [
    # Authentication endpoints
    RateLimitRule(
        endpoint="/api/v1/auth/login",
        scope=RateLimitScope.IP_ADDRESS,
        limit=10,
        window_seconds=60
    ),
    RateLimitRule(
        endpoint="/api/v1/auth/register",
        scope=RateLimitScope.IP_ADDRESS,
        limit=5,
        window_seconds=60
    ),
    
    # Chat endpoints
    RateLimitRule(
        endpoint="/api/v1/chat/send",
        scope=RateLimitScope.USER_ID,
        limit=60,
        window_seconds=60
    ),
    
    # Content generation
    RateLimitRule(
        endpoint="/api/v1/content/generate",
        scope=RateLimitScope.USER_ID,
        limit=10,
        window_seconds=3600  # per hour
    ),
    
    # File upload (data-based limit)
    RateLimitRule(
        endpoint="/api/v1/files/upload",
        scope=RateLimitScope.USER_ID,
        limit=100,  # 100 MB per hour
        window_seconds=3600
    ),
    
    # General API
    RateLimitRule(
        endpoint="/api/v1/*",
        scope=RateLimitScope.USER_ID,
        limit=1000,
        window_seconds=3600
    )
]

# Default performance monitoring configuration
DEFAULT_PERFORMANCE_CONFIG = {
    "response_time_threshold_ms": 2000,
    "error_rate_threshold_percentage": 5.0,
    "cpu_usage_threshold_percentage": 80.0,
    "memory_usage_threshold_percentage": 85.0,
    "disk_usage_threshold_percentage": 90.0,
    "connection_pool_usage_threshold_percentage": 80.0,
    "cache_hit_rate_threshold_percentage": 80.0,
    "queue_length_threshold": 100
}

# Default health checks
DEFAULT_HEALTH_CHECKS = [
    HealthCheck("database", "/health/database", "database"),
    HealthCheck("redis", "/health/redis", "redis"),
    HealthCheck("storage", "/health/storage", "disk_space"),
    HealthCheck("external_apis", "/health/external", "external_api")
]
