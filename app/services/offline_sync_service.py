"""
Offline Synchronization Service
Handles offline data synchronization, conflict resolution, and incremental updates.
"""

import logging
import json
import gzip
import hashlib
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
import uuid

from app.models.offline_sync import (
    SyncChange, SyncBatch, SyncConflict, SyncMetadata, SyncResponse,
    EntityType, SyncAction, ConflictResolution, SyncStatus
)

logger = logging.getLogger(__name__)

class OfflineSyncService:
    """Service for managing offline synchronization and conflict resolution."""
    
    def __init__(self):
        """Initialize offline sync service."""
        # In-memory storage for demonstration (replace with database)
        self.sync_changes: Dict[str, SyncChange] = {}
        self.sync_batches: Dict[str, SyncBatch] = {}
        self.sync_conflicts: Dict[str, SyncConflict] = {}
        self.sync_metadata: Dict[str, SyncMetadata] = {}
        self.entity_versions: Dict[str, int] = {}  # entity_id -> version
        
    async def upload_offline_changes(self, user_id: str, device_id: str, 
                                   changes_data: List[Dict[str, Any]]) -> SyncResponse:
        """Process and apply offline changes from client."""
        try:
            batch_id = str(uuid.uuid4())
            conflicts = []
            applied_changes = []
            server_changes = []
            
            # Create sync batch
            changes = [SyncChange.from_dict({**change, 'userId': user_id}) for change in changes_data]
            sync_batch = SyncBatch(
                batch_id=batch_id,
                user_id=user_id,
                device_id=device_id,
                changes=changes,
                created_at=datetime.utcnow(),
                status=SyncStatus.IN_PROGRESS
            )
            
            self.sync_batches[batch_id] = sync_batch
            
            # Process each change
            for change in changes:
                try:
                    conflict = await self._check_for_conflicts(change)
                    
                    if conflict:
                        conflicts.append(conflict)
                        # Store conflict for later resolution
                        self.sync_conflicts[conflict.conflict_id] = conflict
                    else:
                        # Apply change
                        success = await self._apply_change(change)
                        if success:
                            applied_changes.append(change.change_id)
                            self.sync_changes[change.change_id] = change
                        
                except Exception as e:
                    logger.error(f"Error processing change {change.change_id}: {str(e)}")
            
            # Update sync metadata
            await self._update_sync_metadata(user_id, device_id)
            
            # Get server changes for client
            last_sync = await self._get_last_sync_time(user_id, device_id)
            server_changes = await self._get_server_changes_since(user_id, last_sync)
            
            # Update batch status
            sync_batch.status = SyncStatus.COMPLETED if not conflicts else SyncStatus.CONFLICT
            sync_batch.processed_at = datetime.utcnow()
            
            response = SyncResponse(
                success=len(conflicts) == 0,
                message=f"Processed {len(changes)} changes, {len(conflicts)} conflicts",
                sync_time=datetime.utcnow(),
                applied_changes=applied_changes,
                conflicts=conflicts,
                server_changes=server_changes,
                next_sync_token=self._generate_sync_token(user_id, device_id)
            )
            
            logger.info(f"Uploaded offline changes for user {user_id}, batch {batch_id}")
            return response
            
        except Exception as e:
            logger.error(f"Error uploading offline changes: {str(e)}")
            raise
    
    async def download_server_changes(self, user_id: str, device_id: str, 
                                    last_sync_time: Optional[datetime] = None) -> SyncResponse:
        """Download incremental changes from server."""
        try:
            if not last_sync_time:
                last_sync_time = await self._get_last_sync_time(user_id, device_id)
            
            # Get all server changes since last sync
            server_changes = await self._get_server_changes_since(user_id, last_sync_time)
            
            # Check for any pending conflicts
            pending_conflicts = await self._get_pending_conflicts(user_id)
            
            # Compress data if needed (for mobile networks)
            compression_used = len(server_changes) > 10  # Simple threshold
            
            response = SyncResponse(
                success=True,
                message=f"Retrieved {len(server_changes)} server changes",
                sync_time=datetime.utcnow(),
                applied_changes=[],
                conflicts=pending_conflicts,
                server_changes=server_changes,
                next_sync_token=self._generate_sync_token(user_id, device_id),
                compression_used=compression_used
            )
            
            # Update sync metadata
            await self._update_sync_metadata(user_id, device_id)
            
            logger.info(f"Downloaded server changes for user {user_id}")
            return response
            
        except Exception as e:
            logger.error(f"Error downloading server changes: {str(e)}")
            raise
    
    async def _check_for_conflicts(self, client_change: SyncChange) -> Optional[SyncConflict]:
        """Check if incoming change conflicts with server state."""
        try:
            entity_key = f"{client_change.entity_type.value}_{client_change.entity_id}"
            current_version = self.entity_versions.get(entity_key, 0)
            
            # Check for version conflicts
            if client_change.version <= current_version and client_change.action in [SyncAction.UPDATE, SyncAction.DELETE]:
                # Find the conflicting server change
                server_change = await self._get_latest_server_change(client_change.entity_id, client_change.entity_type)
                
                if server_change:
                    conflict = SyncConflict(
                        conflict_id=str(uuid.uuid4()),
                        entity_type=client_change.entity_type,
                        entity_id=client_change.entity_id,
                        client_change=client_change,
                        server_change=server_change,
                        created_at=datetime.utcnow()
                    )
                    return conflict
            
            return None
            
        except Exception as e:
            logger.error(f"Error checking for conflicts: {str(e)}")
            return None
    
    async def _apply_change(self, change: SyncChange) -> bool:
        """Apply a sync change to the server state."""
        try:
            entity_key = f"{change.entity_type.value}_{change.entity_id}"
            
            if change.action == SyncAction.CREATE:
                # Create new entity
                logger.info(f"Creating new {change.entity_type.value} with ID {change.entity_id}")
                self.entity_versions[entity_key] = change.version
                
            elif change.action == SyncAction.UPDATE:
                # Update existing entity
                logger.info(f"Updating {change.entity_type.value} with ID {change.entity_id}")
                self.entity_versions[entity_key] = change.version
                
            elif change.action == SyncAction.DELETE:
                # Delete entity
                logger.info(f"Deleting {change.entity_type.value} with ID {change.entity_id}")
                if entity_key in self.entity_versions:
                    del self.entity_versions[entity_key]
            
            # Generate checksum for verification
            change.checksum = self._generate_checksum(change.data)
            
            return True
            
        except Exception as e:
            logger.error(f"Error applying change {change.change_id}: {str(e)}")
            return False
    
    async def _get_server_changes_since(self, user_id: str, since_time: datetime) -> List[SyncChange]:
        """Get all server changes for user since specified time."""
        try:
            server_changes = []
            
            # Filter changes by user and timestamp
            for change in self.sync_changes.values():
                if (change.user_id == user_id and 
                    change.timestamp > since_time):
                    server_changes.append(change)
            
            # Sort by timestamp
            server_changes.sort(key=lambda x: x.timestamp)
            
            return server_changes
            
        except Exception as e:
            logger.error(f"Error getting server changes: {str(e)}")
            return []
    
    async def _get_latest_server_change(self, entity_id: str, entity_type: EntityType) -> Optional[SyncChange]:
        """Get the latest server change for a specific entity."""
        try:
            latest_change = None
            latest_timestamp = datetime.min
            
            for change in self.sync_changes.values():
                if (change.entity_id == entity_id and 
                    change.entity_type == entity_type and
                    change.timestamp > latest_timestamp):
                    latest_change = change
                    latest_timestamp = change.timestamp
            
            return latest_change
            
        except Exception as e:
            logger.error(f"Error getting latest server change: {str(e)}")
            return None
    
    async def resolve_conflict(self, conflict_id: str, resolution_strategy: ConflictResolution,
                             resolved_data: Optional[Dict[str, Any]] = None,
                             resolved_by: str = "system") -> bool:
        """Resolve a sync conflict using specified strategy."""
        try:
            if conflict_id not in self.sync_conflicts:
                logger.warning(f"Conflict {conflict_id} not found")
                return False
            
            conflict = self.sync_conflicts[conflict_id]
            
            if resolution_strategy == ConflictResolution.SERVER_WINS:
                # Keep server version
                final_data = conflict.server_change.data
                
            elif resolution_strategy == ConflictResolution.CLIENT_WINS:
                # Use client version
                final_data = conflict.client_change.data
                
            elif resolution_strategy == ConflictResolution.TIMESTAMP_WINS:
                # Use the change with the latest timestamp
                if conflict.client_change.timestamp > conflict.server_change.timestamp:
                    final_data = conflict.client_change.data
                else:
                    final_data = conflict.server_change.data
                    
            elif resolution_strategy == ConflictResolution.MERGE:
                # Merge both changes (simple field-level merge)
                final_data = conflict.server_change.data.copy()
                final_data.update(conflict.client_change.data)
                
            elif resolution_strategy == ConflictResolution.USER_CHOICE:
                # Use user-provided resolution
                if resolved_data is None:
                    logger.error("User choice resolution requires resolved_data")
                    return False
                final_data = resolved_data
            
            # Apply the resolved change
            resolved_change = SyncChange(
                change_id=str(uuid.uuid4()),
                entity_type=conflict.entity_type,
                entity_id=conflict.entity_id,
                action=SyncAction.UPDATE,
                data=final_data,
                timestamp=datetime.utcnow(),
                user_id=conflict.client_change.user_id,
                version=max(conflict.client_change.version, conflict.server_change.version) + 1
            )
            
            await self._apply_change(resolved_change)
            
            # Update conflict record
            conflict.resolution_strategy = resolution_strategy
            conflict.resolved_data = final_data
            conflict.resolved_at = datetime.utcnow()
            conflict.resolved_by = resolved_by
            
            logger.info(f"Resolved conflict {conflict_id} using {resolution_strategy.value}")
            return True
            
        except Exception as e:
            logger.error(f"Error resolving conflict {conflict_id}: {str(e)}")
            return False
    
    async def _get_pending_conflicts(self, user_id: str) -> List[SyncConflict]:
        """Get all pending conflicts for a user."""
        pending_conflicts = []
        
        for conflict in self.sync_conflicts.values():
            if (conflict.client_change.user_id == user_id and 
                conflict.resolved_at is None):
                pending_conflicts.append(conflict)
        
        return pending_conflicts
    
    async def _get_last_sync_time(self, user_id: str, device_id: str) -> datetime:
        """Get the last sync time for a user/device."""
        metadata_key = f"{user_id}_{device_id}"
        
        if metadata_key in self.sync_metadata:
            return self.sync_metadata[metadata_key].last_sync_time
        
        # Return a time far in the past for initial sync
        return datetime.utcnow() - timedelta(days=365)
    
    async def _update_sync_metadata(self, user_id: str, device_id: str):
        """Update sync metadata for user/device."""
        metadata_key = f"{user_id}_{device_id}"
        
        if metadata_key in self.sync_metadata:
            metadata = self.sync_metadata[metadata_key]
            metadata.last_sync_time = datetime.utcnow()
            metadata.total_synced_changes += 1
        else:
            metadata = SyncMetadata(
                user_id=user_id,
                device_id=device_id,
                last_sync_time=datetime.utcnow(),
                device_info={'platform': 'unknown'},
                app_version='1.0.0',
                total_synced_changes=1
            )
            self.sync_metadata[metadata_key] = metadata
    
    def _generate_sync_token(self, user_id: str, device_id: str) -> str:
        """Generate a sync token for incremental sync."""
        timestamp = datetime.utcnow().isoformat()
        token_data = f"{user_id}_{device_id}_{timestamp}"
        return hashlib.md5(token_data.encode()).hexdigest()
    
    def _generate_checksum(self, data: Dict[str, Any]) -> str:
        """Generate checksum for data integrity verification."""
        data_str = json.dumps(data, sort_keys=True)
        return hashlib.sha256(data_str.encode()).hexdigest()
    
    async def compress_sync_data(self, data: Dict[str, Any]) -> bytes:
        """Compress sync data for mobile networks."""
        try:
            json_data = json.dumps(data).encode('utf-8')
            compressed_data = gzip.compress(json_data)
            
            compression_ratio = len(compressed_data) / len(json_data)
            logger.info(f"Compressed sync data by {(1-compression_ratio)*100:.1f}%")
            
            return compressed_data
            
        except Exception as e:
            logger.error(f"Error compressing sync data: {str(e)}")
            return json.dumps(data).encode('utf-8')
    
    async def decompress_sync_data(self, compressed_data: bytes) -> Dict[str, Any]:
        """Decompress sync data."""
        try:
            decompressed_data = gzip.decompress(compressed_data)
            return json.loads(decompressed_data.decode('utf-8'))
            
        except Exception as e:
            logger.error(f"Error decompressing sync data: {str(e)}")
            # Try to parse as uncompressed JSON
            return json.loads(compressed_data.decode('utf-8'))
    
    async def get_sync_statistics(self, user_id: str) -> Dict[str, Any]:
        """Get synchronization statistics for a user."""
        user_changes = [change for change in self.sync_changes.values() if change.user_id == user_id]
        user_conflicts = [conflict for conflict in self.sync_conflicts.values() 
                         if conflict.client_change.user_id == user_id]
        
        stats = {
            'total_synced_changes': len(user_changes),
            'pending_conflicts': len([c for c in user_conflicts if c.resolved_at is None]),
            'resolved_conflicts': len([c for c in user_conflicts if c.resolved_at is not None]),
            'sync_success_rate': 0.0,
            'last_sync_time': None,
            'entity_breakdown': {}
        }
        
        # Calculate success rate
        total_attempts = len(user_changes) + len(user_conflicts)
        if total_attempts > 0:
            stats['sync_success_rate'] = len(user_changes) / total_attempts
        
        # Get last sync time
        user_metadata = [m for m in self.sync_metadata.values() if m.user_id == user_id]
        if user_metadata:
            stats['last_sync_time'] = max(m.last_sync_time for m in user_metadata).isoformat()
        
        # Entity breakdown
        entity_counts = {}
        for change in user_changes:
            entity_type = change.entity_type.value
            entity_counts[entity_type] = entity_counts.get(entity_type, 0) + 1
        stats['entity_breakdown'] = entity_counts
        
        return stats
