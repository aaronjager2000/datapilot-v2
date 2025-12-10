"""
WebSocket endpoint for real-time updates.

Provides WebSocket connection for receiving real-time updates about:
- Dataset processing progress
- New datasets created
- Dataset status changes
- Background task completions
"""

import logging
import json
from typing import Optional
from uuid import UUID
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, Depends, status
from fastapi.exceptions import HTTPException

from app.utils.websocket import manager
from app.services.auth.jwt import decode_token
from app.core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter()


async def authenticate_websocket(
    websocket: WebSocket,
    token: Optional[str] = Query(None, description="JWT token for authentication")
) -> Optional[dict]:
    """
    Authenticate WebSocket connection via token.
    
    Args:
        websocket: WebSocket connection
        token: JWT token from query param or will be expected in first message
    
    Returns:
        Decoded token payload or None if authentication fails
    """
    if token:
        try:
            payload = decode_token(token)
            return payload
        except Exception as e:
            logger.warning(f"WebSocket authentication failed with query token: {e}")
            return None
    
    return None


@router.websocket("/ws/{user_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    user_id: str,
    token: Optional[str] = Query(None, description="JWT authentication token")
):
    """
    WebSocket endpoint for real-time updates.
    
    **Authentication:**
    - Provide JWT token in query parameter: `?token=<jwt_token>`
    - Or send authentication message after connection: `{"type": "auth", "token": "<jwt_token>"}`
    
    **Message Types:**
    
    **Client to Server:**
    - `{"type": "auth", "token": "<jwt_token>"}` - Authenticate connection
    - `{"type": "subscribe", "channel": "dataset:<id>"}` - Subscribe to dataset updates
    - `{"type": "subscribe", "channel": "organization:<id>"}` - Subscribe to organization updates
    - `{"type": "unsubscribe", "channel": "<channel>"}` - Unsubscribe from channel
    - `{"type": "ping"}` - Keep-alive ping
    
    **Server to Client:**
    - `{"type": "connection", "status": "connected"}` - Connection established
    - `{"type": "dataset_update", "dataset_id": "<id>", "status": "...", "progress": 50}` - Dataset update
    - `{"type": "task_progress", "task_id": "<id>", "percentage": 75}` - Task progress
    - `{"type": "pong"}` - Ping response
    - `{"type": "error", "message": "..."}` - Error message
    """
    authenticated = False
    user_payload = None
    
    try:
        # Try to authenticate with query token
        if token:
            user_payload = await authenticate_websocket(websocket, token)
            if user_payload:
                authenticated = True
                # Verify user_id matches token
                if user_payload.get("sub") != user_id:
                    await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
                    return
        
        # Connect to manager
        await manager.connect(websocket, user_id)
        
        # If not authenticated yet, wait for auth message
        if not authenticated:
            # Send authentication required message
            await websocket.send_json({
                "type": "auth_required",
                "message": "Please send authentication token"
            })
        
        # Listen for messages
        while True:
            # Receive message
            try:
                data = await websocket.receive_text()
                message = json.loads(data)
            except json.JSONDecodeError:
                await websocket.send_json({
                    "type": "error",
                    "message": "Invalid JSON format"
                })
                continue
            
            message_type = message.get("type")
            
            # Handle authentication message
            if message_type == "auth":
                if authenticated:
                    await websocket.send_json({
                        "type": "error",
                        "message": "Already authenticated"
                    })
                    continue
                
                auth_token = message.get("token")
                if not auth_token:
                    await websocket.send_json({
                        "type": "error",
                        "message": "Token required"
                    })
                    continue
                
                try:
                    user_payload = decode_token(auth_token)
                    
                    # Verify user_id matches
                    if user_payload.get("sub") != user_id:
                        await websocket.send_json({
                            "type": "error",
                            "message": "User ID mismatch"
                        })
                        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
                        return
                    
                    authenticated = True
                    
                    await websocket.send_json({
                        "type": "auth_success",
                        "message": "Authentication successful"
                    })
                    
                    logger.info(f"WebSocket authenticated: user_id={user_id}")
                
                except Exception as e:
                    await websocket.send_json({
                        "type": "error",
                        "message": f"Authentication failed: {str(e)}"
                    })
                    await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
                    return
            
            # Require authentication for other operations
            elif not authenticated:
                await websocket.send_json({
                    "type": "error",
                    "message": "Authentication required"
                })
                continue
            
            # Handle subscribe
            elif message_type == "subscribe":
                channel = message.get("channel")
                if not channel:
                    await websocket.send_json({
                        "type": "error",
                        "message": "Channel required"
                    })
                    continue
                
                # Validate channel format
                if not _validate_channel(channel, user_payload):
                    await websocket.send_json({
                        "type": "error",
                        "message": "Invalid or unauthorized channel"
                    })
                    continue
                
                await manager.subscribe(user_id, channel)
                logger.info(f"User {user_id} subscribed to {channel}")
            
            # Handle unsubscribe
            elif message_type == "unsubscribe":
                channel = message.get("channel")
                if not channel:
                    await websocket.send_json({
                        "type": "error",
                        "message": "Channel required"
                    })
                    continue
                
                await manager.unsubscribe(user_id, channel)
                logger.info(f"User {user_id} unsubscribed from {channel}")
            
            # Handle ping
            elif message_type == "ping":
                await websocket.send_json({"type": "pong"})
            
            # Unknown message type
            else:
                await websocket.send_json({
                    "type": "error",
                    "message": f"Unknown message type: {message_type}"
                })
    
    except WebSocketDisconnect:
        await manager.disconnect(user_id)
        logger.info(f"WebSocket client disconnected: user_id={user_id}")
    
    except Exception as e:
        logger.error(f"WebSocket error for user {user_id}: {e}", exc_info=True)
        await manager.disconnect(user_id)
        try:
            await websocket.close(code=status.WS_1011_INTERNAL_ERROR)
        except:
            pass


def _validate_channel(channel: str, user_payload: dict) -> bool:
    """
    Validate that user has access to the channel.
    
    Args:
        channel: Channel name
        user_payload: Decoded JWT payload
    
    Returns:
        True if channel is valid and user has access
    """
    try:
        # Parse channel
        if ":" not in channel:
            return False
        
        channel_type, channel_id = channel.split(":", 1)
        
        # Validate channel types
        if channel_type == "dataset":
            # User can subscribe to any dataset in their organization
            # Additional permission checks could be added here
            return True
        
        elif channel_type == "organization":
            # User can only subscribe to their own organization
            user_org_id = user_payload.get("organization_id")
            return str(user_org_id) == channel_id
        
        elif channel_type == "task":
            # User can subscribe to their own tasks
            # Additional checks could verify task ownership
            return True
        
        elif channel_type == "user":
            # User can only subscribe to their own user channel
            user_id = user_payload.get("sub")
            return str(user_id) == channel_id
        
        else:
            # Unknown channel type
            return False
    
    except Exception as e:
        logger.warning(f"Channel validation error: {e}")
        return False


@router.get("/ws/stats")
async def get_websocket_stats():
    """
    Get WebSocket connection statistics.
    
    Returns information about active connections and subscriptions.
    """
    return {
        "active_connections": manager.get_connection_count(),
        "channels": {
            channel: manager.get_channel_subscriber_count(channel)
            for channel in manager.channel_subscribers.keys()
        }
    }


# Export router
__all__ = ["router"]
