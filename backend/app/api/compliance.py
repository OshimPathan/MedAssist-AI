"""
MedAssist AI - GDPR Consent Management API
Patient data consent, right to access, and right to erasure
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from typing import Optional
from datetime import datetime
import logging

from app.database.connection import get_db
from app.utils.security import get_current_user, require_role
from app.utils.audit_logger import log_action
from app.utils.encryption import mask_phone, mask_email

logger = logging.getLogger(__name__)
router = APIRouter()


# ─── Consent Management ───────────────────────────

@router.post("/consent")
async def update_consent(
    patient_id: str,
    consent: bool = True,
    consent_type: str = "data_processing",
):
    """Record or update patient consent for data processing"""
    db = get_db()

    patient = await db.patient.find_unique(where={"id": patient_id})
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    await db.patient.update(
        where={"id": patient_id},
        data={"consentStatus": consent},
    )

    await log_action("CONSENT_UPDATE", "patients", details={
        "patient_id": patient_id,
        "consent_type": consent_type,
        "consent_given": consent,
        "timestamp": datetime.utcnow().isoformat(),
    })

    return {
        "patient_id": patient_id,
        "consent_status": consent,
        "consent_type": consent_type,
        "recorded_at": datetime.utcnow().isoformat(),
    }


@router.get("/consent/{patient_id}")
async def get_consent_status(patient_id: str):
    """Get current consent status for a patient"""
    db = get_db()

    patient = await db.patient.find_unique(where={"id": patient_id})
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    return {
        "patient_id": patient.id,
        "name": patient.name,
        "consent_status": patient.consentStatus,
    }


# ─── Right to Access (GDPR Art. 15) ──────────────

@router.get("/data-export/{patient_id}")
async def export_patient_data(
    patient_id: str,
    user: dict = Depends(require_role("ADMIN", "RECEPTIONIST")),
):
    """
    Export all data held about a patient (Right to Access).
    Returns structured data suitable for delivery to the patient.
    """
    db = get_db()

    patient = await db.patient.find_unique(
        where={"id": patient_id},
        include={
            "appointments": {"include": {"doctor": True}},
            "conversations": True,
            "emergencyCases": True,
        },
    )
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    # Compile all patient data
    export = {
        "export_date": datetime.utcnow().isoformat(),
        "patient": {
            "id": patient.id,
            "name": patient.name,
            "phone": mask_phone(patient.phone),
            "email": mask_email(patient.email) if patient.email else None,
            "age": patient.age,
            "gender": patient.gender,
            "consent_status": patient.consentStatus,
            "registered_on": patient.createdAt.isoformat(),
        },
        "appointments": [
            {
                "id": a.id,
                "doctor": a.doctor.name if a.doctor else None,
                "date": a.dateTime.isoformat(),
                "status": a.status,
                "notes": a.notes,
            }
            for a in (patient.appointments or [])
        ],
        "conversations": [
            {
                "id": c.id,
                "message": c.message[:100] + "..." if len(c.message) > 100 else c.message,
                "intent": c.intent,
                "timestamp": c.timestamp.isoformat(),
            }
            for c in (patient.conversations or [])
        ],
        "emergency_cases": [
            {
                "id": e.id,
                "severity": e.severity,
                "symptoms": e.symptoms,
                "status": e.dispatchStatus,
                "created_at": e.createdAt.isoformat(),
            }
            for e in (patient.emergencyCases or [])
        ],
    }

    await log_action("GDPR_DATA_EXPORT", "patients", user.get("user_id"), details={
        "patient_id": patient_id,
    })

    return export


# ─── Right to Erasure (GDPR Art. 17) ─────────────

@router.delete("/data-erasure/{patient_id}")
async def erase_patient_data(
    patient_id: str,
    confirm: bool = Query(False, description="Must be true to confirm deletion"),
    user: dict = Depends(require_role("ADMIN")),
):
    """
    Erase all patient data (Right to Erasure / Right to be Forgotten).
    Anonymizes conversations and deletes personal data.
    Requires admin role and explicit confirmation.
    """
    if not confirm:
        raise HTTPException(
            status_code=400,
            detail="You must set confirm=true to proceed with data erasure. This action is irreversible.",
        )

    db = get_db()

    patient = await db.patient.find_unique(where={"id": patient_id})
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    # Step 1: Anonymize conversations (keep for analytics, remove PII)
    await db.conversation.update_many(
        where={"patientId": patient_id},
        data={"patientId": None},
    )

    # Step 2: Cancel all future appointments
    await db.appointment.update_many(
        where={
            "patientId": patient_id,
            "status": {"in": ["SCHEDULED", "CONFIRMED", "RESCHEDULED"]},
        },
        data={"status": "CANCELLED", "notes": "Cancelled due to data erasure request"},
    )

    # Step 3: Anonymize emergency cases
    await db.emergencycase.update_many(
        where={"patientId": patient_id},
        data={"patientId": None, "contactNumber": "REDACTED", "notes": "Data erased per GDPR request"},
    )

    # Step 4: Delete the patient record
    await db.patient.delete(where={"id": patient_id})

    await log_action("GDPR_DATA_ERASURE", "patients", user.get("user_id"), details={
        "patient_id": patient_id,
        "patient_name_hash": "REDACTED",
    })

    logger.warning(f"GDPR data erasure completed for patient {patient_id}")

    return {
        "status": "erased",
        "patient_id": patient_id,
        "actions": [
            "Conversations anonymized",
            "Future appointments cancelled",
            "Emergency cases anonymized",
            "Patient record deleted",
        ],
    }


# ─── Audit Trail Access ──────────────────────────

@router.get("/audit-trail/{patient_id}")
async def get_audit_trail(
    patient_id: str,
    user: dict = Depends(require_role("ADMIN")),
):
    """Get all audit log entries related to a patient (for compliance)"""
    db = get_db()

    logs = await db.auditlog.find_many(
        where={
            "details": {"path": ["patient_id"], "equals": patient_id},
        },
        order={"timestamp": "desc"},
        take=100,
    )

    return {
        "patient_id": patient_id,
        "total_entries": len(logs),
        "entries": [
            {
                "id": log.id,
                "action": log.action,
                "resource": log.resource,
                "user_id": log.userId,
                "timestamp": log.timestamp.isoformat(),
                "details": log.details,
            }
            for log in logs
        ],
    }
