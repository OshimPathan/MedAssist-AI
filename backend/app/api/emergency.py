"""
MedAssist AI - Emergency API
Emergency case management and retrieval
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from typing import Optional, List
from datetime import datetime, timedelta
import logging

from app.models.schemas import (
    EmergencyCreate, EmergencyResponse, EmergencyUpdate,
    EmergencySeverity, DispatchStatus,
)
from app.utils.security import get_current_user, require_role
from app.database.connection import get_db
from app.utils.audit_logger import log_action

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/", response_model=List[EmergencyResponse])
async def list_emergencies(
    severity: Optional[EmergencySeverity] = Query(None),
    dispatch_status: Optional[DispatchStatus] = Query(None),
    active_only: bool = Query(True),
    user: dict = Depends(require_role("ADMIN", "EMERGENCY_STAFF")),
):
    """List emergency cases (Admin/Emergency staff only)"""
    db = get_db()
    filters = {}
    if severity:
        filters["severity"] = severity.value
    if dispatch_status:
        filters["dispatchStatus"] = dispatch_status.value
    if active_only:
        filters["dispatchStatus"] = {"in": ["PENDING", "DISPATCHED", "ARRIVED"]}

    emergencies = await db.emergencycase.find_many(
        where=filters,
        order={"createdAt": "desc"},
        take=50,
    )
    return [
        EmergencyResponse(
            id=e.id, patient_id=e.patientId, severity=e.severity,
            symptoms=e.symptoms, location=e.location,
            contact_number=e.contactNumber,
            dispatch_status=e.dispatchStatus, notes=e.notes,
            created_at=e.createdAt,
        ) for e in emergencies
    ]


@router.get("/{emergency_id}", response_model=EmergencyResponse)
async def get_emergency(
    emergency_id: str,
    user: dict = Depends(require_role("ADMIN", "EMERGENCY_STAFF")),
):
    """Get a specific emergency case"""
    db = get_db()
    emergency = await db.emergencycase.find_unique(where={"id": emergency_id})
    if not emergency:
        raise HTTPException(status_code=404, detail="Emergency case not found")
    return EmergencyResponse(
        id=emergency.id, patient_id=emergency.patientId,
        severity=emergency.severity, symptoms=emergency.symptoms,
        location=emergency.location,
        contact_number=emergency.contactNumber,
        dispatch_status=emergency.dispatchStatus,
        notes=emergency.notes, created_at=emergency.createdAt,
    )


@router.put("/{emergency_id}", response_model=EmergencyResponse)
async def update_emergency(
    emergency_id: str,
    update: EmergencyUpdate,
    user: dict = Depends(require_role("ADMIN", "EMERGENCY_STAFF")),
):
    """Update emergency case status"""
    db = get_db()
    existing = await db.emergencycase.find_unique(where={"id": emergency_id})
    if not existing:
        raise HTTPException(status_code=404, detail="Emergency case not found")

    data = {}
    if update.dispatch_status:
        data["dispatchStatus"] = update.dispatch_status.value
    if update.notes is not None:
        data["notes"] = update.notes
    if update.location is not None:
        data["location"] = update.location

    emergency = await db.emergencycase.update(
        where={"id": emergency_id}, data=data,
    )

    await log_action(
        "UPDATE_EMERGENCY", "emergency_cases",
        user["user_id"],
        {"emergency_id": emergency_id, "changes": data},
    )

    return EmergencyResponse(
        id=emergency.id, patient_id=emergency.patientId,
        severity=emergency.severity, symptoms=emergency.symptoms,
        location=emergency.location,
        contact_number=emergency.contactNumber,
        dispatch_status=emergency.dispatchStatus,
        notes=emergency.notes, created_at=emergency.createdAt,
    )


@router.get("/stats/summary")
async def emergency_stats(
    user: dict = Depends(require_role("ADMIN", "EMERGENCY_STAFF")),
):
    """Get emergency statistics for dashboard"""
    db = get_db()
    now = datetime.utcnow()
    week_ago = now - timedelta(days=7)

    active = await db.emergencycase.count(
        where={"dispatchStatus": {"in": ["PENDING", "DISPATCHED", "ARRIVED"]}}
    )
    total_week = await db.emergencycase.count(
        where={"createdAt": {"gte": week_ago}}
    )
    critical = await db.emergencycase.count(
        where={"severity": "CRITICAL", "createdAt": {"gte": week_ago}}
    )

    return {
        "active_emergencies": active,
        "total_this_week": total_week,
        "critical_this_week": critical,
    }
