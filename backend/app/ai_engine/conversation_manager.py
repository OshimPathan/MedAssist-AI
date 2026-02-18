"""
MedAssist AI - Conversation Manager
Manages conversation state, context memory, and session tracking
"""

import uuid
import logging
from datetime import datetime
from typing import Optional, Dict, List
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class ConversationContext:
    """Stores context for a single conversation session"""
    session_id: str
    patient_name: Optional[str] = None
    patient_phone: Optional[str] = None
    patient_id: Optional[str] = None
    messages: List[Dict] = field(default_factory=list)
    current_intent: Optional[str] = None
    pending_action: Optional[str] = None
    emergency_mode: bool = False
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_active: datetime = field(default_factory=datetime.utcnow)

    def add_message(self, role: str, content: str, metadata: Optional[dict] = None):
        """Add a message to the conversation history"""
        self.messages.append({
            "role": role,
            "content": content,
            "timestamp": datetime.utcnow().isoformat(),
            "metadata": metadata or {},
        })
        self.last_active = datetime.utcnow()

    def get_history(self, max_messages: int = 10) -> List[Dict]:
        """Get recent conversation history for LLM context"""
        return self.messages[-max_messages:]

    def to_llm_messages(self, system_prompt: str, max_messages: int = 10) -> List[Dict]:
        """Format conversation history for LLM API call"""
        messages = [{"role": "system", "content": system_prompt}]
        for msg in self.get_history(max_messages):
            messages.append({
                "role": msg["role"],
                "content": msg["content"],
            })
        return messages


class SessionManager:
    """
    In-memory session manager for conversation state.
    In production, this should be backed by Redis for persistence and scaling.
    """

    def __init__(self):
        self._sessions: Dict[str, ConversationContext] = {}

    def create_session(
        self,
        session_id: Optional[str] = None,
        patient_name: Optional[str] = None,
        patient_phone: Optional[str] = None,
    ) -> ConversationContext:
        """Create a new conversation session"""
        if session_id is None:
            session_id = str(uuid.uuid4())

        context = ConversationContext(
            session_id=session_id,
            patient_name=patient_name,
            patient_phone=patient_phone,
        )
        self._sessions[session_id] = context
        logger.info(f"Created session: {session_id}")
        return context

    def get_session(self, session_id: str) -> Optional[ConversationContext]:
        """Retrieve an existing session"""
        return self._sessions.get(session_id)

    def get_or_create_session(
        self,
        session_id: Optional[str] = None,
        patient_name: Optional[str] = None,
        patient_phone: Optional[str] = None,
    ) -> ConversationContext:
        """Get existing session or create a new one"""
        if session_id and session_id in self._sessions:
            ctx = self._sessions[session_id]
            if patient_name:
                ctx.patient_name = patient_name
            if patient_phone:
                ctx.patient_phone = patient_phone
            return ctx
        return self.create_session(session_id, patient_name, patient_phone)

    def remove_session(self, session_id: str):
        """Remove a session"""
        if session_id in self._sessions:
            del self._sessions[session_id]
            logger.info(f"Removed session: {session_id}")

    def active_session_count(self) -> int:
        """Get count of active sessions"""
        return len(self._sessions)

    def cleanup_stale_sessions(self, max_age_minutes: int = 60):
        """Remove sessions older than max_age_minutes"""
        now = datetime.utcnow()
        stale = [
            sid for sid, ctx in self._sessions.items()
            if (now - ctx.last_active).total_seconds() > max_age_minutes * 60
        ]
        for sid in stale:
            self.remove_session(sid)
        if stale:
            logger.info(f"Cleaned up {len(stale)} stale sessions")


# Global session manager instance
session_manager = SessionManager()
