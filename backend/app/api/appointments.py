"""
MedAssist AI - Appointments API
Booking, rescheduling, cancellation, slot management, and notifications
"""

from fastapi import APIRouter, HTTPException, status, Depends, Query
from typing import Optional, List
from datetime import datetime, timedelta
import logging

from app.models.schemas import (
    AppointmentCreate, AppointmentResponse, AppointmentUpdate, AppointmentStatus,
)
from app.utils.security import get_current_user
from app.database.connection import get_db
from app.utils.audit_logger import log_action
from app.services.notification_service import notification_service

logger = logging.getLogger(__name__)
router = APIRouter()

# ─── In-memory slot locks (for concurrent booking protection) ─────
# In production, use Redis. This prevents double-booking during concurrent requests.
_slot_locks: dict[str, datetime] = {}  # key: "doctor_id:datetime_iso" → lock_expiry
LOCK_DURATION_SECONDS = 120  # 2-minute reservation window


def _get_lock_key(doctor_id: str, dt: datetime) -> str:
    return f"{doctor_id}:{dt.isoformat()}"


def _acquire_lock(doctor_id: str, dt: datetime) -> bool:
    """Try to lock a time slot (returns False if already locked)"""
    key = _get_lock_key(doctor_id, dt)
    now = datetime.utcnow()
    # Clean expired lock
    if key in _slot_locks and _slot_locks[key] < now:
        del _slot_locks[key]
    if key in _slot_locks:
        return False  # Slot is locked by another request
    _slot_locks[key] = now + timedelta(seconds=LOCK_DURATION_SECONDS)
    return True


def _release_lock(doctor_id: str, dt: datetime):
    """Release a slot lock"""
    key = _get_lock_key(doctor_id, dt)
    _slot_locks.pop(key, None)


# ─── Endpoints ────────────────────────────────────────────

@router.get("/", response_model=List[AppointmentResponse])
async def list_appointments(
    doctor_id: Optional[str] = Query(None),
    patient_id: Optional[str] = Query(None),
    status_filter: Optional[AppointmentStatus] = Query(None, alias="status"),
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
    user: dict = Depends(get_current_user),
):
    """List appointments with filters"""
    db = get_db()
    filters = {}
    if doctor_id:
        filters["doctorId"] = doctor_id
    if patient_id:
        filters["patientId"] = patient_id
    if status_filter:
        filters["status"] = status_filter.value
    if date_from:
        filters["dateTime"] = {"gte": date_from}
    if date_to:
        if "dateTime" in filters:
            filters["dateTime"]["lte"] = date_to
        else:
            filters["dateTime"] = {"lte": date_to}

    appointments = await db.appointment.find_many(
        where=filters,
        order={"dateTime": "asc"},
        include={"patient": True, "doctor": True},
    )
    return [
        AppointmentResponse(
            id=a.id, patient_id=a.patientId, doctor_id=a.doctorId,
            date_time=a.dateTime, duration=a.duration,
            status=a.status, notes=a.notes, created_at=a.createdAt,
        ) for a in appointments
    ]


@router.post("/", response_model=AppointmentResponse, status_code=201)
async def book_appointment(appt: AppointmentCreate):
    """Book a new appointment with slot locking and conflict detection"""
    db = get_db()

    # Verify doctor exists
    doctor = await db.doctor.find_unique(
        where={"id": appt.doctor_id},
        include={"department": True},
    )
    if not doctor:
        raise HTTPException(status_code=400, detail="Doctor not found")

    # Verify patient exists
    patient = await db.patient.find_unique(where={"id": appt.patient_id})
    if not patient:
        raise HTTPException(status_code=400, detail="Patient not found")

    # Acquire slot lock (prevents concurrent double-booking)
    if not _acquire_lock(appt.doctor_id, appt.date_time):
        raise HTTPException(
            status_code=status.HTTP_423_LOCKED,
            detail="This time slot is currently being booked by another user. Please try again in a moment.",
        )

    try:
        # Check for slot conflicts (double-booking prevention)
        end_time = appt.date_time + timedelta(minutes=appt.duration)
        conflicts = await db.appointment.find_many(
            where={
                "doctorId": appt.doctor_id,
                "status": {"in": ["SCHEDULED", "CONFIRMED"]},
                "dateTime": {"lt": end_time},
            },
        )
        real_conflicts = [
            c for c in conflicts
            if c.dateTime + timedelta(minutes=c.duration) > appt.date_time
        ]
        if real_conflicts:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This time slot conflicts with an existing appointment",
            )

        # Create appointment
        appointment = await db.appointment.create(data={
            "patientId": appt.patient_id,
            "doctorId": appt.doctor_id,
            "dateTime": appt.date_time,
            "duration": appt.duration,
            "notes": appt.notes,
        })

        await log_action("BOOK_APPOINTMENT", "appointments", details={
            "appointment_id": appointment.id,
            "doctor_id": appt.doctor_id,
            "patient_id": appt.patient_id,
        })

        # Send confirmation notification
        try:
            await notification_service.send_appointment_confirmation(
                patient_name=patient.name,
                patient_phone=patient.phone,
                patient_email=patient.email,
                doctor_name=doctor.name,
                department=doctor.department.name if doctor.department else "General",
                date_time=appt.date_time,
                appointment_id=appointment.id,
            )
        except Exception as e:
            logger.error(f"Notification send failed: {e}")

        return AppointmentResponse(
            id=appointment.id, patient_id=appointment.patientId,
            doctor_id=appointment.doctorId, date_time=appointment.dateTime,
            duration=appointment.duration, status=appointment.status,
            notes=appointment.notes, created_at=appointment.createdAt,
        )
    finally:
        _release_lock(appt.doctor_id, appt.date_time)


@router.put("/{appointment_id}", response_model=AppointmentResponse)
async def reschedule_appointment(
    appointment_id: str,
    update: AppointmentUpdate,
):
    """Reschedule or update an appointment with conflict re-check"""
    db = get_db()

    existing = await db.appointment.find_unique(
        where={"id": appointment_id},
        include={"patient": True, "doctor": {"include": {"department": True}}},
    )
    if not existing:
        raise HTTPException(status_code=404, detail="Appointment not found")

    if existing.status in ("CANCELLED", "COMPLETED"):
        raise HTTPException(
            status_code=400,
            detail=f"Cannot modify {existing.status.lower()} appointment",
        )

    data = {}

    # If rescheduling to a new time, re-check conflicts
    if update.date_time and update.date_time != existing.dateTime:
        duration = existing.duration
        end_time = update.date_time + timedelta(minutes=duration)

        conflicts = await db.appointment.find_many(
            where={
                "doctorId": existing.doctorId,
                "id": {"not": appointment_id},
                "status": {"in": ["SCHEDULED", "CONFIRMED"]},
                "dateTime": {"lt": end_time},
            },
        )
        real_conflicts = [
            c for c in conflicts
            if c.dateTime + timedelta(minutes=c.duration) > update.date_time
        ]
        if real_conflicts:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="New time slot conflicts with an existing appointment",
            )

        data["dateTime"] = update.date_time
        data["status"] = "RESCHEDULED"

    if update.status:
        data["status"] = update.status.value
    if update.notes is not None:
        data["notes"] = update.notes

    appointment = await db.appointment.update(
        where={"id": appointment_id}, data=data,
    )

    await log_action("RESCHEDULE_APPOINTMENT", "appointments", details={
        "appointment_id": appointment_id,
        "changes": {k: str(v) for k, v in data.items()},
    })

    # Send reschedule notification
    if update.date_time and existing.patient:
        try:
            await notification_service.send_appointment_reschedule(
                patient_name=existing.patient.name,
                patient_phone=existing.patient.phone,
                patient_email=existing.patient.email,
                doctor_name=existing.doctor.name if existing.doctor else "Unknown",
                old_time=existing.dateTime,
                new_time=update.date_time,
                appointment_id=appointment_id,
            )
        except Exception as e:
            logger.error(f"Reschedule notification failed: {e}")

    return AppointmentResponse(
        id=appointment.id, patient_id=appointment.patientId,
        doctor_id=appointment.doctorId, date_time=appointment.dateTime,
        duration=appointment.duration, status=appointment.status,
        notes=appointment.notes, created_at=appointment.createdAt,
    )


@router.delete("/{appointment_id}")
async def cancel_appointment(appointment_id: str):
    """Cancel an appointment with notification"""
    db = get_db()

    existing = await db.appointment.find_unique(
        where={"id": appointment_id},
        include={"patient": True, "doctor": True},
    )
    if not existing:
        raise HTTPException(status_code=404, detail="Appointment not found")

    if existing.status == "CANCELLED":
        raise HTTPException(status_code=400, detail="Appointment is already cancelled")

    await db.appointment.update(
        where={"id": appointment_id},
        data={"status": "CANCELLED"},
    )

    await log_action("CANCEL_APPOINTMENT", "appointments", details={
        "appointment_id": appointment_id,
    })

    # Send cancellation notification
    if existing.patient:
        try:
            await notification_service.send_appointment_cancellation(
                patient_name=existing.patient.name,
                patient_phone=existing.patient.phone,
                patient_email=existing.patient.email,
                doctor_name=existing.doctor.name if existing.doctor else "Unknown",
                date_time=existing.dateTime,
                appointment_id=appointment_id,
            )
        except Exception as e:
            logger.error(f"Cancellation notification failed: {e}")

    return {"message": "Appointment cancelled successfully"}


@router.get("/available-slots")
async def get_available_slots(
    doctor_id: str = Query(..., description="Doctor ID"),
    date: str = Query(..., description="Date in YYYY-MM-DD format"),
    duration: int = Query(30, description="Appointment duration in minutes"),
):
    """Get available time slots for a doctor on a given date"""
    db = get_db()

    # Verify doctor
    doctor = await db.doctor.find_unique(where={"id": doctor_id})
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor not found")

    # Parse date
    try:
        target_date = datetime.strptime(date, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")

    # Full working day: 9 AM – 5 PM
    day_start = target_date.replace(hour=9, minute=0, second=0)
    day_end = target_date.replace(hour=17, minute=0, second=0)

    # Get existing appointments for the day
    existing = await db.appointment.find_many(
        where={
            "doctorId": doctor_id,
            "status": {"in": ["SCHEDULED", "CONFIRMED", "RESCHEDULED"]},
            "dateTime": {"gte": day_start, "lt": day_end},
        },
        order={"dateTime": "asc"},
    )

    # Build occupied intervals
    occupied = []
    for a in existing:
        occupied.append((a.dateTime, a.dateTime + timedelta(minutes=a.duration)))

    # Generate available slots
    slots = []
    current = day_start
    while current + timedelta(minutes=duration) <= day_end:
        slot_end = current + timedelta(minutes=duration)

        # Check if slot overlaps with any existing appointment
        is_free = True
        for occ_start, occ_end in occupied:
            if current < occ_end and slot_end > occ_start:
                is_free = False
                break

        # Check if slot is locked by another booking
        lock_key = _get_lock_key(doctor_id, current)
        is_locked = lock_key in _slot_locks and _slot_locks[lock_key] > datetime.utcnow()

        if is_free and not is_locked:
            slots.append({
                "start": current.isoformat(),
                "end": slot_end.isoformat(),
                "available": True,
            })
        elif not is_free:
            slots.append({
                "start": current.isoformat(),
                "end": slot_end.isoformat(),
                "available": False,
                "reason": "booked",
            })

        current += timedelta(minutes=duration)

    return {
        "doctor_id": doctor_id,
        "date": date,
        "slot_duration_minutes": duration,
        "total_slots": len([s for s in slots if s["available"]]),
        "slots": slots,
    }


@router.post("/lock-slot")
async def lock_slot(
    doctor_id: str = Query(...),
    date_time: datetime = Query(...),
):
    """Temporarily lock a time slot while the patient fills in details"""
    if not _acquire_lock(doctor_id, date_time):
        raise HTTPException(
            status_code=status.HTTP_423_LOCKED,
            detail="This slot is currently reserved by another user",
        )
    return {
        "locked": True,
        "expires_in_seconds": LOCK_DURATION_SECONDS,
        "message": f"Slot locked for {LOCK_DURATION_SECONDS} seconds. Complete booking before it expires.",
    }


@router.post("/release-slot")
async def release_slot(
    doctor_id: str = Query(...),
    date_time: datetime = Query(...),
):
    """Release a previously locked time slot"""
    _release_lock(doctor_id, date_time)
    return {"released": True}
