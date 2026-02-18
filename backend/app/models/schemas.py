"""
MedAssist AI - Pydantic Schemas
Request/Response validation models for all API endpoints
"""

from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List
from datetime import datetime
from enum import Enum


# ─── Enums ─────────────────────────────────────────────────

class UserRole(str, Enum):
    ADMIN = "ADMIN"
    DOCTOR = "DOCTOR"
    RECEPTIONIST = "RECEPTIONIST"
    EMERGENCY_STAFF = "EMERGENCY_STAFF"


class Gender(str, Enum):
    MALE = "MALE"
    FEMALE = "FEMALE"
    OTHER = "OTHER"
    PREFER_NOT_TO_SAY = "PREFER_NOT_TO_SAY"


class AppointmentStatus(str, Enum):
    SCHEDULED = "SCHEDULED"
    CONFIRMED = "CONFIRMED"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"
    RESCHEDULED = "RESCHEDULED"
    NO_SHOW = "NO_SHOW"


class EmergencySeverity(str, Enum):
    NON_URGENT = "NON_URGENT"
    URGENT = "URGENT"
    CRITICAL = "CRITICAL"


class DispatchStatus(str, Enum):
    PENDING = "PENDING"
    DISPATCHED = "DISPATCHED"
    ARRIVED = "ARRIVED"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class IntentType(str, Enum):
    GENERAL_QUERY = "general_query"
    APPOINTMENT_REQUEST = "appointment_request"
    DOCTOR_INFO = "doctor_info"
    SYMPTOM_REPORT = "symptom_report"
    EMERGENCY = "emergency"
    INSURANCE = "insurance"
    COMPLAINT = "complaint"
    GREETING = "greeting"
    FAREWELL = "farewell"


class UrgencyLevel(str, Enum):
    NON_URGENT = "non_urgent"
    URGENT = "urgent"
    CRITICAL = "critical"


# ─── Auth Schemas ──────────────────────────────────────────

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class LoginRequest(BaseModel):
    email: str
    password: str


class RegisterRequest(BaseModel):
    email: str
    password: str = Field(min_length=8)
    name: str
    phone: Optional[str] = None
    role: UserRole = UserRole.RECEPTIONIST


class UserResponse(BaseModel):
    id: str
    email: str
    name: str
    role: UserRole
    phone: Optional[str] = None
    is_active: bool

    class Config:
        from_attributes = True


# ─── Patient Schemas ───────────────────────────────────────

class PatientCreate(BaseModel):
    name: str
    phone: str
    email: Optional[str] = None
    age: Optional[int] = None
    gender: Optional[Gender] = None
    consent_status: bool = False


class PatientResponse(BaseModel):
    id: str
    name: str
    phone: str
    email: Optional[str] = None
    age: Optional[int] = None
    gender: Optional[Gender] = None
    consent_status: bool
    created_at: datetime

    class Config:
        from_attributes = True


# ─── Doctor Schemas ────────────────────────────────────────

class DoctorCreate(BaseModel):
    name: str
    department_id: str
    specialization: Optional[str] = None
    consultation_fee: Optional[float] = None
    schedule: Optional[dict] = None
    emergency_availability: bool = False


class DoctorResponse(BaseModel):
    id: str
    name: str
    department_id: str
    specialization: Optional[str] = None
    consultation_fee: Optional[float] = None
    schedule: Optional[dict] = None
    emergency_availability: bool
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


# ─── Department Schemas ────────────────────────────────────

class DepartmentCreate(BaseModel):
    name: str
    description: Optional[str] = None


class DepartmentResponse(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    is_active: bool

    class Config:
        from_attributes = True


# ─── Appointment Schemas ──────────────────────────────────

class AppointmentCreate(BaseModel):
    patient_id: str
    doctor_id: str
    date_time: datetime
    duration: int = 30
    notes: Optional[str] = None


class AppointmentResponse(BaseModel):
    id: str
    patient_id: str
    doctor_id: str
    date_time: datetime
    duration: int
    status: AppointmentStatus
    notes: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class AppointmentUpdate(BaseModel):
    date_time: Optional[datetime] = None
    status: Optional[AppointmentStatus] = None
    notes: Optional[str] = None


# ─── Chat Schemas ──────────────────────────────────────────

class ChatMessage(BaseModel):
    """Incoming chat message from patient"""
    message: str
    session_id: Optional[str] = None
    patient_name: Optional[str] = None
    patient_phone: Optional[str] = None


class AIClassification(BaseModel):
    """Structured output from AI engine"""
    intent: IntentType
    urgency: UrgencyLevel = UrgencyLevel.NON_URGENT
    department: Optional[str] = None
    needs_ambulance: bool = False
    confidence: float = 0.0
    entities: Optional[dict] = None


class ChatResponse(BaseModel):
    """Response sent back to patient"""
    message: str
    session_id: str
    intent: Optional[IntentType] = None
    urgency: Optional[UrgencyLevel] = None
    is_emergency: bool = False
    suggestions: Optional[List[str]] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# ─── Emergency Schemas ─────────────────────────────────────

class EmergencyCreate(BaseModel):
    patient_id: Optional[str] = None
    severity: EmergencySeverity
    symptoms: str
    location: Optional[str] = None
    contact_number: str
    notes: Optional[str] = None


class EmergencyResponse(BaseModel):
    id: str
    patient_id: Optional[str] = None
    severity: EmergencySeverity
    symptoms: str
    location: Optional[str] = None
    contact_number: str
    dispatch_status: DispatchStatus
    notes: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class EmergencyUpdate(BaseModel):
    dispatch_status: Optional[DispatchStatus] = None
    notes: Optional[str] = None
    location: Optional[str] = None


# ─── Knowledge Base Schemas ────────────────────────────────

class KnowledgeBaseCreate(BaseModel):
    title: str
    content: str
    category: str


class KnowledgeBaseResponse(BaseModel):
    id: str
    title: str
    content: str
    category: str
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


# ─── Admin / Analytics Schemas ─────────────────────────────

class DashboardStats(BaseModel):
    total_conversations: int = 0
    active_emergencies: int = 0
    appointments_today: int = 0
    total_patients: int = 0
    emergency_count_week: int = 0
    avg_response_time: float = 0.0


class ConversationLog(BaseModel):
    id: str
    session_id: str
    patient_name: Optional[str] = None
    message: str
    ai_response: str
    intent: Optional[str] = None
    urgency: Optional[str] = None
    timestamp: datetime

    class Config:
        from_attributes = True
