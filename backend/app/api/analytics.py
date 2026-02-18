"""
MedAssist AI - Analytics API
Provides aggregated data for Chart.js visualizations: trends, distributions, timelines
"""

from fastapi import APIRouter, Depends, Query
from datetime import datetime, timedelta
from collections import defaultdict
import logging

from app.utils.security import require_role
from app.database.connection import get_db

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/overview")
async def get_analytics_overview(
    user: dict = Depends(require_role("ADMIN", "RECEPTIONIST")),
):
    """Complete analytics overview for dashboard charts"""
    db = get_db()
    now = datetime.utcnow()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    # ── Core Metrics ──
    total_patients = await db.patient.count()
    total_conversations = await db.conversation.count()
    total_appointments = await db.appointment.count()
    total_emergencies = await db.emergencycase.count()
    active_emergencies = await db.emergencycase.count(
        where={"dispatchStatus": {"in": ["PENDING", "DISPATCHED", "ARRIVED"]}}
    )
    appointments_today = await db.appointment.count(
        where={
            "dateTime": {"gte": today_start, "lt": today_start + timedelta(days=1)},
            "status": {"in": ["SCHEDULED", "CONFIRMED"]},
        }
    )

    # ── 7-Day Trend Data ──
    daily_data = []
    for i in range(6, -1, -1):
        day = today_start - timedelta(days=i)
        next_day = day + timedelta(days=1)

        convos = await db.conversation.count(
            where={"timestamp": {"gte": day, "lt": next_day}}
        )
        appts = await db.appointment.count(
            where={"dateTime": {"gte": day, "lt": next_day}}
        )
        emergencies = await db.emergencycase.count(
            where={"createdAt": {"gte": day, "lt": next_day}}
        )

        daily_data.append({
            "date": day.strftime("%b %d"),
            "day": day.strftime("%a"),
            "conversations": convos,
            "appointments": appts,
            "emergencies": emergencies,
        })

    # ── Emergency Severity Distribution ──
    critical = await db.emergencycase.count(where={"severity": "CRITICAL"})
    urgent = await db.emergencycase.count(where={"severity": "URGENT"})
    non_urgent = await db.emergencycase.count(where={"severity": "NON_URGENT"})

    severity_distribution = {
        "CRITICAL": critical,
        "URGENT": urgent,
        "NON_URGENT": non_urgent,
    }

    # ── Appointment Status Breakdown ──
    scheduled = await db.appointment.count(where={"status": "SCHEDULED"})
    confirmed = await db.appointment.count(where={"status": "CONFIRMED"})
    completed = await db.appointment.count(where={"status": "COMPLETED"})
    cancelled = await db.appointment.count(where={"status": "CANCELLED"})
    rescheduled = await db.appointment.count(where={"status": "RESCHEDULED"})
    no_show = await db.appointment.count(where={"status": "NO_SHOW"})

    appointment_status = {
        "Scheduled": scheduled,
        "Confirmed": confirmed,
        "Completed": completed,
        "Cancelled": cancelled,
        "Rescheduled": rescheduled,
        "No Show": no_show,
    }

    # ── Intent Distribution (from conversations) ──
    all_convos = await db.conversation.find_many(
        where={"intent": {"not": None}},
        order={"timestamp": "desc"},
        take=500,
    )
    intent_counts: dict[str, int] = defaultdict(int)
    for c in all_convos:
        if c.intent:
            intent_counts[c.intent] += 1

    # ── Department Load (from appointments) ──
    recent_appts = await db.appointment.find_many(
        where={"createdAt": {"gte": now - timedelta(days=30)}},
        include={"doctor": {"include": {"department": True}}},
        take=500,
    )
    dept_counts: dict[str, int] = defaultdict(int)
    for a in recent_appts:
        if a.doctor and a.doctor.department:
            dept_counts[a.doctor.department.name] += 1

    # ── Hourly Activity (today) ──
    todays_convos = await db.conversation.find_many(
        where={"timestamp": {"gte": today_start}},
    )
    hourly = [0] * 24
    for c in todays_convos:
        hourly[c.timestamp.hour] += 1

    return {
        "summary": {
            "total_patients": total_patients,
            "total_conversations": total_conversations,
            "total_appointments": total_appointments,
            "total_emergencies": total_emergencies,
            "active_emergencies": active_emergencies,
            "appointments_today": appointments_today,
        },
        "daily_trends": daily_data,
        "severity_distribution": severity_distribution,
        "appointment_status": appointment_status,
        "intent_distribution": dict(intent_counts),
        "department_load": dict(dept_counts),
        "hourly_activity": {
            "labels": [f"{h:02d}:00" for h in range(24)],
            "data": hourly,
        },
    }
