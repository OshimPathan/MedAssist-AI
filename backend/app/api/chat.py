"""
MedAssist AI - Chat API
WebSocket and REST endpoints for real-time patient communication
"""

import uuid
import json
import logging
from datetime import datetime
from typing import Set
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException
from pydantic import ValidationError

from app.models.schemas import ChatMessage, ChatResponse, IntentType, UrgencyLevel
from app.ai_engine.intent_classifier import classify_intent
from app.ai_engine.response_generator import generate_response
from app.ai_engine.conversation_manager import session_manager
from app.database.connection import get_db
from app.utils.audit_logger import log_action

logger = logging.getLogger(__name__)
router = APIRouter()

# Track active WebSocket connections for broadcasting
active_connections: Set[WebSocket] = set()
# Track admin connections for emergency alerts
admin_connections: Set[WebSocket] = set()


class ConnectionManager:
    """Manages WebSocket connections for real-time communication"""

    def __init__(self):
        self.patient_connections: dict[str, WebSocket] = {}
        self.admin_connections: Set[WebSocket] = set()

    async def connect_patient(self, websocket: WebSocket, session_id: str):
        await websocket.accept()
        self.patient_connections[session_id] = websocket
        logger.info(f"Patient connected: {session_id}")

    async def connect_admin(self, websocket: WebSocket):
        await websocket.accept()
        self.admin_connections.add(websocket)
        logger.info(f"Admin connected. Total admin connections: {len(self.admin_connections)}")

    def disconnect_patient(self, session_id: str):
        self.patient_connections.pop(session_id, None)
        logger.info(f"Patient disconnected: {session_id}")

    def disconnect_admin(self, websocket: WebSocket):
        self.admin_connections.discard(websocket)
        logger.info(f"Admin disconnected. Total admin connections: {len(self.admin_connections)}")

    async def send_to_patient(self, session_id: str, message: dict):
        ws = self.patient_connections.get(session_id)
        if ws:
            await ws.send_json(message)

    async def broadcast_to_admins(self, message: dict):
        """Broadcast alerts to all connected admin dashboards"""
        disconnected = set()
        for ws in self.admin_connections:
            try:
                await ws.send_json(message)
            except Exception:
                disconnected.add(ws)
        self.admin_connections -= disconnected


manager = ConnectionManager()


# ─── REST Endpoint ─────────────────────────────────────────

@router.post("/message", response_model=ChatResponse)
async def send_message(chat: ChatMessage):
    """
    Process a chat message via REST API.
    For clients that don't support WebSocket.
    """
    session_id = chat.session_id or str(uuid.uuid4())

    # Get or create conversation context
    context = session_manager.get_or_create_session(
        session_id=session_id,
        patient_name=chat.patient_name,
        patient_phone=chat.patient_phone,
    )

    # Add user message to context
    context.add_message("user", chat.message)

    # Classify intent
    classification = await classify_intent(chat.message)

    # Generate response
    ai_response = await generate_response(chat.message, classification, context)

    # Add AI response to context
    context.add_message("assistant", ai_response, {
        "intent": classification.intent.value,
        "urgency": classification.urgency.value,
    })

    is_emergency = classification.intent == IntentType.EMERGENCY

    # Handle emergency detection
    if is_emergency:
        context.emergency_mode = True
        await _handle_emergency(session_id, chat.message, classification, context)

    # Save conversation to database
    await _save_conversation(session_id, context, chat.message, ai_response, classification)

    return ChatResponse(
        message=ai_response,
        session_id=session_id,
        intent=classification.intent,
        urgency=classification.urgency,
        is_emergency=is_emergency,
        suggestions=_get_suggestions(classification),
        timestamp=datetime.utcnow(),
    )


# ─── WebSocket Endpoint ───────────────────────────────────

@router.websocket("/ws/{session_id}")
async def websocket_chat(websocket: WebSocket, session_id: str):
    """
    WebSocket endpoint for real-time bidirectional chat.
    """
    await manager.connect_patient(websocket, session_id)

    # Create or restore session
    context = session_manager.get_or_create_session(session_id=session_id)

    # Send welcome message
    welcome = ChatResponse(
        message=(
            "👋 Welcome to **MedAssist AI**!\n\n"
            "I'm your 24/7 hospital assistant. I can help you with:\n"
            "• 📅 Appointments  • 👨‍⚕️ Doctor info\n"
            "• 🏥 Department guidance  • 🚨 Emergency help\n\n"
            "How can I help you today?"
        ),
        session_id=session_id,
        intent=IntentType.GREETING,
        suggestions=[
            "Book an appointment",
            "Find a doctor",
            "I have a symptom",
            "Hospital information",
        ],
    )
    await websocket.send_json(welcome.model_dump(mode="json"))

    try:
        while True:
            # Receive message
            data = await websocket.receive_text()

            try:
                msg_data = json.loads(data)
                message_text = msg_data.get("message", data)
                patient_name = msg_data.get("patient_name")
                patient_phone = msg_data.get("patient_phone")
            except json.JSONDecodeError:
                message_text = data
                patient_name = None
                patient_phone = None

            if patient_name:
                context.patient_name = patient_name
            if patient_phone:
                context.patient_phone = patient_phone

            # Add to context
            context.add_message("user", message_text)

            # Classify intent
            classification = await classify_intent(message_text)

            # Generate response
            ai_response = await generate_response(message_text, classification, context)

            # Add response to context
            context.add_message("assistant", ai_response, {
                "intent": classification.intent.value,
                "urgency": classification.urgency.value,
            })

            is_emergency = classification.intent == IntentType.EMERGENCY

            # Handle emergency
            if is_emergency:
                context.emergency_mode = True
                await _handle_emergency(session_id, message_text, classification, context)

            # Save to database
            await _save_conversation(session_id, context, message_text, ai_response, classification)

            # Send response
            response = ChatResponse(
                message=ai_response,
                session_id=session_id,
                intent=classification.intent,
                urgency=classification.urgency,
                is_emergency=is_emergency,
                suggestions=_get_suggestions(classification),
            )
            await websocket.send_json(response.model_dump(mode="json"))

    except WebSocketDisconnect:
        manager.disconnect_patient(session_id)
        logger.info(f"Chat session ended: {session_id}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect_patient(session_id)


# ─── Admin WebSocket ──────────────────────────────────────

@router.websocket("/ws/admin/alerts")
async def admin_alerts(websocket: WebSocket):
    """WebSocket endpoint for admin real-time alerts"""
    await manager.connect_admin(websocket)
    try:
        while True:
            await websocket.receive_text()  # Keep alive
    except WebSocketDisconnect:
        manager.disconnect_admin(websocket)


# ─── Helper Functions ─────────────────────────────────────

async def _handle_emergency(
    session_id: str,
    message: str,
    classification,
    context,
):
    """Handle detected emergency: log, alert admins"""
    logger.critical(f"EMERGENCY DETECTED in session {session_id}: {message[:200]}")

    # Create emergency case in DB
    try:
        db = get_db()
        emergency = await db.emergencycase.create(
            data={
                "severity": classification.urgency.value.upper().replace("_", ""),
                "symptoms": message[:500],
                "contactNumber": context.patient_phone or "UNKNOWN",
                "location": None,
                "notes": f"Auto-detected from chat session {session_id}",
            }
        )

        # Broadcast to admin dashboards
        alert = {
            "type": "EMERGENCY_ALERT",
            "data": {
                "id": emergency.id,
                "session_id": session_id,
                "severity": classification.urgency.value,
                "symptoms": message[:200],
                "department": classification.department,
                "patient_name": context.patient_name or "Unknown",
                "patient_phone": context.patient_phone or "Unknown",
                "timestamp": datetime.utcnow().isoformat(),
                "needs_ambulance": classification.needs_ambulance,
            },
        }
        await manager.broadcast_to_admins(alert)

        await log_action(
            "EMERGENCY_DETECTED",
            "emergency_cases",
            details={
                "emergency_id": emergency.id,
                "session_id": session_id,
                "severity": classification.urgency.value,
            },
        )
    except Exception as e:
        logger.error(f"Failed to create emergency case: {e}")


async def _save_conversation(session_id, context, message, ai_response, classification):
    """Save conversation to database"""
    try:
        db = get_db()
        await db.conversation.create(
            data={
                "sessionId": session_id,
                "patientId": context.patient_id,
                "message": message[:2000],
                "aiResponse": ai_response[:2000],
                "intent": classification.intent.value,
                "urgency": classification.urgency.value,
            }
        )
    except Exception as e:
        logger.error(f"Failed to save conversation: {e}")


def _get_suggestions(classification) -> list[str]:
    """Get contextual suggestion buttons based on intent"""
    suggestions_map = {
        IntentType.GREETING: [
            "Book an appointment",
            "Find a doctor",
            "I have a symptom",
            "Hospital information",
        ],
        IntentType.APPOINTMENT_REQUEST: [
            "Cardiology",
            "General Medicine",
            "Orthopedics",
            "Show all departments",
        ],
        IntentType.DOCTOR_INFO: [
            "Show available doctors",
            "Book appointment",
            "Department information",
        ],
        IntentType.SYMPTOM_REPORT: [
            "Book appointment now",
            "Find a specialist",
            "Is this an emergency?",
        ],
        IntentType.EMERGENCY: [
            "Share my location",
            "Call 108",
            "Contact family",
        ],
        IntentType.INSURANCE: [
            "Check coverage",
            "Billing query",
            "Cashless process",
        ],
        IntentType.FAREWELL: [],
    }
    return suggestions_map.get(classification.intent, ["Help", "Contact us"])
