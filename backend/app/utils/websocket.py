"""
WebSocket connection manager for real-time updates.

Manages WebSocket connections, channel subscriptions, and message broadcasting
using Redis pub/sub for multi-server support.
"""

import json
import logging
from typing import Dict, Set, Any, Optional
from uuid import UUID
import asyncio
from fastapi import WebSocket
from app.core.redis import get_redis_client

logger = logging.getLogger(__name__)


class ConnectionManager:
    """
    Manages WebSocket connections and message broadcasting.
    
    Features:
    - Per-user connection tracking
    - Channel subscriptions (dataset, organization)
    - Personal messaging
    - Broadcasting to channels
    - Redis pub/sub for multi-server setup
    """
    
    def __init__(self):
        """Initialize connection manager."""
        # Active connections: {user_id: websocket}
        self.active_connections: Dict[str, WebSocket] = {}
        
        # User subscriptions: {user_id: set of channels}
        self.subscriptions: Dict[str, Set[str]] = {}
        
        # Channel subscribers: {channel: set of user_ids}
        self.channel_subscribers: Dict[str, Set[str]] = {}
        
        # Redis client for pub/sub
        self.redis_client = None
        self.pubsub = None
        self.pubsub_task = None
    
    async def connect(self, websocket: WebSocket, user_id: str):
        """
        Register a new WebSocket connection.
        
        Args:
            websocket: FastAPI WebSocket instance
            user_id: User ID to associate with connection
        """
        await websocket.accept()
        
        # Store connection
        self.active_connections[user_id] = websocket
        self.subscriptions[user_id] = set()
        
        logger.info(f"WebSocket connected: user_id={user_id}")
        
        # Initialize Redis pub/sub if not already done
        if self.pubsub is None:
            await self._init_pubsub()
        
        # Send connection confirmation
        await self.send_personal_message(
            {
                "type": "connection",
                "status": "connected",
                "user_id": user_id
            },
            user_id
        )
    
    async def disconnect(self, user_id: str):
        """
        Remove a WebSocket connection.
        
        Args:
            user_id: User ID to disconnect
        """
        # Remove from active connections
        if user_id in self.active_connections:
            del self.active_connections[user_id]
        
        # Unsubscribe from all channels
        if user_id in self.subscriptions:
            channels = self.subscriptions[user_id].copy()
            for channel in channels:
                await self.unsubscribe(user_id, channel)
            del self.subscriptions[user_id]
        
        logger.info(f"WebSocket disconnected: user_id={user_id}")
    
    async def subscribe(self, user_id: str, channel: str):
        """
        Subscribe user to a channel.
        
        Args:
            user_id: User ID to subscribe
            channel: Channel name (e.g., 'dataset:123', 'organization:456')
        """
        if user_id not in self.subscriptions:
            self.subscriptions[user_id] = set()
        
        self.subscriptions[user_id].add(channel)
        
        # Add to channel subscribers
        if channel not in self.channel_subscribers:
            self.channel_subscribers[channel] = set()
        
        self.channel_subscribers[channel].add(user_id)
        
        logger.debug(f"User {user_id} subscribed to channel: {channel}")
        
        # Send subscription confirmation
        await self.send_personal_message(
            {
                "type": "subscription",
                "action": "subscribed",
                "channel": channel
            },
            user_id
        )
    
    async def unsubscribe(self, user_id: str, channel: str):
        """
        Unsubscribe user from a channel.
        
        Args:
            user_id: User ID to unsubscribe
            channel: Channel name
        """
        if user_id in self.subscriptions:
            self.subscriptions[user_id].discard(channel)
        
        if channel in self.channel_subscribers:
            self.channel_subscribers[channel].discard(user_id)
            
            # Clean up empty channels
            if not self.channel_subscribers[channel]:
                del self.channel_subscribers[channel]
        
        logger.debug(f"User {user_id} unsubscribed from channel: {channel}")
    
    async def send_personal_message(self, message: Dict[str, Any], user_id: str):
        """
        Send message to a specific user.
        
        Args:
            message: Message dictionary to send
            user_id: Target user ID
        """
        if user_id in self.active_connections:
            websocket = self.active_connections[user_id]
            try:
                await websocket.send_json(message)
                logger.debug(f"Sent personal message to user {user_id}: {message.get('type')}")
            except Exception as e:
                logger.error(f"Failed to send message to user {user_id}: {e}")
                # Connection may be dead, disconnect it
                await self.disconnect(user_id)
    
    async def broadcast(self, message: Dict[str, Any], channel: str):
        """
        Broadcast message to all users subscribed to a channel.
        
        Args:
            message: Message dictionary to broadcast
            channel: Channel to broadcast to
        """
        if channel not in self.channel_subscribers:
            logger.debug(f"No subscribers for channel: {channel}")
            return
        
        # Get all subscribers
        subscribers = self.channel_subscribers[channel].copy()
        
        # Send to each subscriber
        for user_id in subscribers:
            await self.send_personal_message(message, user_id)
        
        logger.debug(f"Broadcast to channel {channel}: {len(subscribers)} users")
    
    async def broadcast_to_organization(self, message: Dict[str, Any], organization_id: str):
        """
        Broadcast message to all users in an organization.
        
        Args:
            message: Message dictionary to broadcast
            organization_id: Organization ID
        """
        channel = f"organization:{organization_id}"
        await self.broadcast(message, channel)
    
    async def send_dataset_update(
        self,
        dataset_id: str,
        status: str,
        progress: Optional[int] = None,
        message: Optional[str] = None,
        metadata: Optional[Dict] = None
    ):
        """
        Send dataset processing update.
        
        Args:
            dataset_id: Dataset ID
            status: Processing status
            progress: Progress percentage (0-100)
            message: Status message
            metadata: Additional metadata
        """
        update = {
            "type": "dataset_update",
            "dataset_id": dataset_id,
            "status": status,
            "progress": progress,
            "message": message,
            "metadata": metadata or {}
        }
        
        channel = f"dataset:{dataset_id}"
        await self.broadcast(update, channel)
        
        # Also publish to Redis for multi-server support
        await self._publish_to_redis(channel, update)
    
    async def send_task_progress(
        self,
        task_id: str,
        current: int,
        total: int,
        status: str,
        message: Optional[str] = None
    ):
        """
        Send background task progress update.
        
        Args:
            task_id: Task ID
            current: Current progress value
            total: Total progress value
            status: Task status
            message: Progress message
        """
        percentage = (current / total * 100) if total > 0 else 0
        
        update = {
            "type": "task_progress",
            "task_id": task_id,
            "current": current,
            "total": total,
            "percentage": round(percentage, 2),
            "status": status,
            "message": message
        }
        
        channel = f"task:{task_id}"
        await self.broadcast(update, channel)
        
        # Also publish to Redis
        await self._publish_to_redis(channel, update)
    
    async def _init_pubsub(self):
        """Initialize Redis pub/sub for multi-server support."""
        try:
            self.redis_client = await get_redis_client()
            self.pubsub = self.redis_client.pubsub()
            
            # Subscribe to all WebSocket channels
            await self.pubsub.psubscribe("ws:*")
            
            # Start listening task
            self.pubsub_task = asyncio.create_task(self._listen_to_redis())
            
            logger.info("Redis pub/sub initialized for WebSocket")
        except Exception as e:
            logger.error(f"Failed to initialize Redis pub/sub: {e}")
    
    async def _listen_to_redis(self):
        """Listen for messages from Redis pub/sub."""
        try:
            async for message in self.pubsub.listen():
                if message["type"] == "pmessage":
                    channel = message["channel"].decode()
                    data = message["data"]
                    
                    try:
                        # Parse message
                        msg = json.loads(data)
                        
                        # Extract actual channel (remove ws: prefix)
                        actual_channel = channel.replace("ws:", "")
                        
                        # Broadcast to local connections
                        await self.broadcast(msg, actual_channel)
                    except json.JSONDecodeError:
                        logger.warning(f"Invalid JSON from Redis: {data}")
                    except Exception as e:
                        logger.error(f"Error processing Redis message: {e}")
        except asyncio.CancelledError:
            logger.info("Redis listener task cancelled")
        except Exception as e:
            logger.error(f"Redis listener error: {e}")
    
    async def _publish_to_redis(self, channel: str, message: Dict[str, Any]):
        """
        Publish message to Redis for multi-server broadcasting.
        
        Args:
            channel: Channel to publish to
            message: Message to publish
        """
        try:
            if self.redis_client:
                # Add ws: prefix to avoid conflicts
                redis_channel = f"ws:{channel}"
                await self.redis_client.publish(
                    redis_channel,
                    json.dumps(message)
                )
                logger.debug(f"Published to Redis channel: {redis_channel}")
        except Exception as e:
            logger.error(f"Failed to publish to Redis: {e}")
    
    def get_connection_count(self) -> int:
        """Get number of active connections."""
        return len(self.active_connections)
    
    def get_subscriptions_for_user(self, user_id: str) -> Set[str]:
        """Get all channels a user is subscribed to."""
        return self.subscriptions.get(user_id, set())
    
    def get_channel_subscriber_count(self, channel: str) -> int:
        """Get number of subscribers for a channel."""
        return len(self.channel_subscribers.get(channel, set()))
    
    async def cleanup(self):
        """Cleanup resources."""
        # Cancel pub/sub task
        if self.pubsub_task:
            self.pubsub_task.cancel()
            try:
                await self.pubsub_task
            except asyncio.CancelledError:
                pass
        
        # Close pub/sub
        if self.pubsub:
            await self.pubsub.unsubscribe()
            await self.pubsub.close()
        
        # Close all connections
        for user_id in list(self.active_connections.keys()):
            await self.disconnect(user_id)
        
        logger.info("WebSocket manager cleaned up")


# Global connection manager instance
manager = ConnectionManager()


# Convenience functions
async def send_dataset_progress(
    dataset_id: str,
    progress: int,
    status: str = "processing",
    message: Optional[str] = None
):
    """
    Convenience function to send dataset processing progress.
    
    Args:
        dataset_id: Dataset ID
        progress: Progress percentage (0-100)
        status: Processing status
        message: Progress message
    """
    await manager.send_dataset_update(
        dataset_id=dataset_id,
        status=status,
        progress=progress,
        message=message
    )


async def send_task_update(
    task_id: str,
    current: int,
    total: int,
    status: str = "processing",
    message: Optional[str] = None
):
    """
    Convenience function to send task progress update.
    
    Args:
        task_id: Task ID
        current: Current progress
        total: Total progress
        status: Task status
        message: Progress message
    """
    await manager.send_task_progress(
        task_id=task_id,
        current=current,
        total=total,
        status=status,
        message=message
    )


# Export main components
__all__ = [
    "ConnectionManager",
    "manager",
    "send_dataset_progress",
    "send_task_update"
]
