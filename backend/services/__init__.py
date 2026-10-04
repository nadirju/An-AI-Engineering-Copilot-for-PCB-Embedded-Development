"""Service layer: the only backend surface the UI may call."""

from backend.services.chat_service import ChatService, get_chat_service

__all__ = ["ChatService", "get_chat_service"]