"""
Offline Synchronization Models
Data structures for offline sync, conflict resolution, and data management.
"""

from dataclasses import dataclass, asdict
from typing import Dict, Any, List, Optional, Union
from enum import Enum
from datetime import datetime
import uuid

class EntityType(Enum):
    """Types of entities that can be synchronized."""
    CHAT = "chat"
    WEEKLY_PLAN = "weekly_plan"
    ACTIVITY = "activity"
    CONTENT = "content"
    FILE = "file"
    SETTINGS = "settings"

class SyncAction(Enum):
    """Actions that can be performed on entities."""
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    RESTORE = "restore"

class ConflictResolution(Enum):
    """Strategies for resolving sync conflicts."""
    SERVER_WINS = "server_wins"
    CLIENT_WINS = "client_wins"
    MERGE = "merge"
    USER_CHOICE = "user_choice"
    TIMESTAMP_WINS = "timestamp_wins"

class SyncStatus(Enum):
    """Status of sync operations."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CONFLICT = "conflict"

@dataclass
class SyncChange:
    """Individual change to be synchronized."""
    change_id: str
    entity_type: EntityType
    entity_id: str
    action: SyncAction
    data: Dict[str, Any]
    timestamp: datetime
    user_id: str
    device_id: Optional[str] = None
    version: int = 1
    checksum: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            'changeId': self.change_id,
            'entityType': self.entity_type.value,
            'entityId': self.entity_id,
            'action': self.action.value,
            'data': self.data,
            'timestamp': self.timestamp.isoformat(),
            'userId': self.user_id,
            'deviceId': self.device_id,
            'version': self.version,
            'checksum': self.checksum
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SyncChange':
        """Create from dictionary data."""
        return cls(
            change_id=data.get('changeId', str(uuid.uuid4())),
            entity_type=EntityType(data['entityType']),
            entity_id=data['entityId'],
            action=SyncAction(data['action']),
            data=data['data'],
            timestamp=datetime.fromisoformat(data['timestamp']),
            user_id=data['userId'],
            device_id=data.get('deviceId'),
            version=data.get('version', 1),
            checksum=data.get('checksum')
        )

@dataclass
class SyncBatch:
    """Batch of changes to be synchronized."""
    batch_id: str
    user_id: str
    device_id: str
    changes: List[SyncChange]
    created_at: datetime
    status: SyncStatus = SyncStatus.PENDING
    error_message: Optional[str] = None
    processed_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            'batchId': self.batch_id,
            'userId': self.user_id,
            'deviceId': self.device_id,
            'changes': [change.to_dict() for change in self.changes],
            'createdAt': self.created_at.isoformat(),
            'status': self.status.value,
            'errorMessage': self.error_message,
            'processedAt': self.processed_at.isoformat() if self.processed_at else None
        }

@dataclass
class SyncConflict:
    """Conflict between local and server changes."""
    conflict_id: str
    entity_type: EntityType
    entity_id: str
    client_change: SyncChange
    server_change: SyncChange
    resolution_strategy: Optional[ConflictResolution] = None
    resolved_data: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    resolved_by: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            'conflictId': self.conflict_id,
            'entityType': self.entity_type.value,
            'entityId': self.entity_id,
            'clientChange': self.client_change.to_dict(),
            'serverChange': self.server_change.to_dict(),
            'resolutionStrategy': self.resolution_strategy.value if self.resolution_strategy else None,
            'resolvedData': self.resolved_data,
            'createdAt': self.created_at.isoformat() if self.created_at else None,
            'resolvedAt': self.resolved_at.isoformat() if self.resolved_at else None,
            'resolvedBy': self.resolved_by
        }

@dataclass
class SyncMetadata:
    """Metadata for sync operations."""
    user_id: str
    device_id: str
    last_sync_time: datetime
    device_info: Dict[str, Any]
    app_version: str
    sync_version: int = 1
    total_synced_changes: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            'userId': self.user_id,
            'deviceId': self.device_id,
            'lastSyncTime': self.last_sync_time.isoformat(),
            'deviceInfo': self.device_info,
            'appVersion': self.app_version,
            'syncVersion': self.sync_version,
            'totalSyncedChanges': self.total_synced_changes
        }

@dataclass
class SyncResponse:
    """Response from sync operations."""
    success: bool
    message: str
    sync_time: datetime
    applied_changes: List[str]  # Change IDs that were applied
    conflicts: List[SyncConflict]
    server_changes: List[SyncChange]
    next_sync_token: Optional[str] = None
    compression_used: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            'success': self.success,
            'message': self.message,
            'syncTime': self.sync_time.isoformat(),
            'appliedChanges': self.applied_changes,
            'conflicts': [conflict.to_dict() for conflict in self.conflicts],
            'serverChanges': [change.to_dict() for change in self.server_changes],
            'nextSyncToken': self.next_sync_token,
            'compressionUsed': self.compression_used
        }
