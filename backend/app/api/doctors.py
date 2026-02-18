"""
MedAssist AI - Doctors API
CRUD operations for doctor management and schedule handling
"""

from fastapi import APIRouter, HTTPException, status, Depends, Query
from typing import Optional, List
import logging

from app.models.schemas import DoctorCreate, DoctorResponse, DepartmentCreate, DepartmentResponse
from app.utils.security import get_current_user, require_role
from app.database.connection import get_db
from app.utils.audit_logger import log_action

logger = logging.getLogger(__name__)
router = APIRouter()


# ─── Departments ──────────────────────────────────────────

@router.get("/departments", response_model=List[DepartmentResponse])
async def list_departments():
    """List all active departments"""
    db = get_db()
    departments = await db.department.find_many(
        where={"isActive": True},
        order={"name": "asc"},
    )
    return [
        DepartmentResponse(
            id=d.id, name=d.name,
            description=d.description, is_active=d.isActive,
        ) for d in departments
    ]


@router.post("/departments", response_model=DepartmentResponse, status_code=201)
async def create_department(
    dept: DepartmentCreate,
    user: dict = Depends(require_role("ADMIN")),
):
    """Create a new department (Admin only)"""
    db = get_db()
    department = await db.department.create(
        data={"name": dept.name, "description": dept.description}
    )
    await log_action("CREATE_DEPARTMENT", "departments", user["user_id"], {"name": dept.name})
    return DepartmentResponse(
        id=department.id, name=department.name,
        description=department.description, is_active=department.isActive,
    )


# ─── Doctors ──────────────────────────────────────────────

@router.get("/", response_model=List[DoctorResponse])
async def list_doctors(
    department_id: Optional[str] = Query(None),
    emergency_only: bool = Query(False),
):
    """List doctors, optionally filtered by department or emergency availability"""
    db = get_db()
    filters = {"isActive": True}
    if department_id:
        filters["departmentId"] = department_id
    if emergency_only:
        filters["emergencyAvailability"] = True

    doctors = await db.doctor.find_many(
        where=filters,
        order={"name": "asc"},
        include={"department": True},
    )
    return [
        DoctorResponse(
            id=d.id, name=d.name, department_id=d.departmentId,
            specialization=d.specialization,
            consultation_fee=d.consultationFee,
            schedule=d.schedule, emergency_availability=d.emergencyAvailability,
            is_active=d.isActive, created_at=d.createdAt,
        ) for d in doctors
    ]


@router.get("/{doctor_id}", response_model=DoctorResponse)
async def get_doctor(doctor_id: str):
    """Get a specific doctor's details"""
    db = get_db()
    doctor = await db.doctor.find_unique(
        where={"id": doctor_id},
        include={"department": True},
    )
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor not found")
    return DoctorResponse(
        id=doctor.id, name=doctor.name, department_id=doctor.departmentId,
        specialization=doctor.specialization,
        consultation_fee=doctor.consultationFee,
        schedule=doctor.schedule,
        emergency_availability=doctor.emergencyAvailability,
        is_active=doctor.isActive, created_at=doctor.createdAt,
    )


@router.post("/", response_model=DoctorResponse, status_code=201)
async def create_doctor(
    doc: DoctorCreate,
    user: dict = Depends(require_role("ADMIN")),
):
    """Add a new doctor (Admin only)"""
    db = get_db()
    dept = await db.department.find_unique(where={"id": doc.department_id})
    if not dept:
        raise HTTPException(status_code=400, detail="Department not found")

    doctor = await db.doctor.create(data={
        "name": doc.name,
        "departmentId": doc.department_id,
        "specialization": doc.specialization,
        "consultationFee": doc.consultation_fee,
        "schedule": doc.schedule or {},
        "emergencyAvailability": doc.emergency_availability,
    })
    await log_action("CREATE_DOCTOR", "doctors", user["user_id"], {"name": doc.name})
    return DoctorResponse(
        id=doctor.id, name=doctor.name, department_id=doctor.departmentId,
        specialization=doctor.specialization,
        consultation_fee=doctor.consultationFee,
        schedule=doctor.schedule,
        emergency_availability=doctor.emergencyAvailability,
        is_active=doctor.isActive, created_at=doctor.createdAt,
    )


@router.put("/{doctor_id}", response_model=DoctorResponse)
async def update_doctor(
    doctor_id: str,
    doc: DoctorCreate,
    user: dict = Depends(require_role("ADMIN")),
):
    """Update doctor details (Admin only)"""
    db = get_db()
    existing = await db.doctor.find_unique(where={"id": doctor_id})
    if not existing:
        raise HTTPException(status_code=404, detail="Doctor not found")

    doctor = await db.doctor.update(
        where={"id": doctor_id},
        data={
            "name": doc.name,
            "departmentId": doc.department_id,
            "specialization": doc.specialization,
            "consultationFee": doc.consultation_fee,
            "schedule": doc.schedule or {},
            "emergencyAvailability": doc.emergency_availability,
        },
    )
    await log_action("UPDATE_DOCTOR", "doctors", user["user_id"], {"doctor_id": doctor_id})
    return DoctorResponse(
        id=doctor.id, name=doctor.name, department_id=doctor.departmentId,
        specialization=doctor.specialization,
        consultation_fee=doctor.consultationFee,
        schedule=doctor.schedule,
        emergency_availability=doctor.emergencyAvailability,
        is_active=doctor.isActive, created_at=doctor.createdAt,
    )
