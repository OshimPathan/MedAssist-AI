"""
MedAssist AI - Admin Dashboard API
Analytics, conversation logs, and system monitoring
"""

from fastapi import APIRouter, Depends, Query
from typing import Optional
from datetime import datetime, timedelta
import logging

from app.models.schemas import DashboardStats, ConversationLog
from app.utils.security import require_role
from app.database.connection import get_db
from app.ai_engine.conversation_manager import session_manager

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/stats", response_model=DashboardStats)
async def get_dashboard_stats(
    user: dict = Depends(require_role("ADMIN", "RECEPTIONIST")),
):
    """Get real-time dashboard statistics"""
    db = get_db()
    now = datetime.utcnow()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_ago = now - timedelta(days=7)

    total_convos = await db.conversation.count()
    active_emergencies = await db.emergencycase.count(
        where={"dispatchStatus": {"in": ["PENDING", "DISPATCHED", "ARRIVED"]}}
    )
    appointments_today = await db.appointment.count(
        where={
            "dateTime": {"gte": today_start, "lt": today_start + timedelta(days=1)},
            "status": {"in": ["SCHEDULED", "CONFIRMED"]},
        }
    )
    total_patients = await db.patient.count()
    emergency_week = await db.emergencycase.count(
        where={"createdAt": {"gte": week_ago}}
    )

    return DashboardStats(
        total_conversations=total_convos,
        active_emergencies=active_emergencies,
        appointments_today=appointments_today,
        total_patients=total_patients,
        emergency_count_week=emergency_week,
        avg_response_time=1.2,  # Placeholder - would calculate from logs
    )


@router.get("/conversations")
async def get_conversation_logs(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    intent: Optional[str] = Query(None),
    user: dict = Depends(require_role("ADMIN")),
):
    """Get paginated conversation logs"""
    db = get_db()
    skip = (page - 1) * per_page

    filters = {}
    if intent:
        filters["intent"] = intent

    conversations = await db.conversation.find_many(
        where=filters,
        order={"timestamp": "desc"},
        skip=skip,
        take=per_page,
    )

    total = await db.conversation.count(where=filters)

    return {
        "data": [
            {
                "id": c.id,
                "session_id": c.sessionId,
                "message": c.message,
                "ai_response": c.aiResponse,
                "intent": c.intent,
                "urgency": c.urgency,
                "timestamp": c.timestamp.isoformat(),
            }
            for c in conversations
        ],
        "total": total,
        "page": page,
        "per_page": per_page,
        "pages": (total + per_page - 1) // per_page,
    }


@router.get("/sessions/active")
async def get_active_sessions(
    user: dict = Depends(require_role("ADMIN", "RECEPTIONIST")),
):
    """Get count and info of active chat sessions"""
    return {
        "active_sessions": session_manager.active_session_count(),
    }
