"""
MedAssist AI - Triage API
Patient triage assessment endpoint and first-aid guidance
"""

from fastapi import APIRouter, Query
from typing import Optional
import logging

from app.triage.triage_engine import triage_engine

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/assess")
async def assess_symptoms(
    message: str,
):
    """
    Run triage assessment on a symptom description.
    Returns severity score, recommended department, and first-aid tips.
    """
    result = triage_engine.assess(message)
    return {
        "severity_score": result.severity_score,
        "severity_level": result.severity_level,
        "recommended_department": result.recommended_department,
        "detected_symptoms": result.detected_symptoms,
        "needs_immediate_attention": result.needs_immediate_attention,
        "needs_ambulance": result.needs_ambulance,
        "triage_notes": result.triage_notes,
        "first_aid_tips": result.first_aid_tips,
    }


@router.get("/first-aid/{condition}")
async def get_first_aid(condition: str):
    """Get first-aid guidance for a specific condition"""
    # Run triage with the condition as input
    result = triage_engine.assess(condition)

    if not result.first_aid_tips:
        return {
            "condition": condition,
            "tips": [
                "For this condition, please consult a healthcare professional.",
                "If symptoms are severe, call emergency services (108).",
            ],
            "severity": result.severity_level,
        }

    return {
        "condition": condition,
        "tips": result.first_aid_tips,
        "severity": result.severity_level,
        "recommended_department": result.recommended_department,
    }


@router.get("/departments")
async def get_triage_departments():
    """Get available departments for symptom-based routing"""
    departments = {
        "Cardiology": "Heart and cardiovascular conditions",
        "Pulmonology": "Breathing and lung conditions",
        "Neurology": "Brain, nerve, and neurological conditions",
        "Orthopedics": "Bone, joint, and muscle injuries",
        "Pediatrics": "Children's health",
        "Dermatology": "Skin conditions",
        "Ophthalmology": "Eye conditions",
        "ENT": "Ear, nose, and throat",
        "Gastroenterology": "Digestive system",
        "Psychiatry": "Mental health",
        "Gynecology": "Women's health",
        "General Medicine": "General health concerns",
        "Emergency": "Life-threatening emergencies",
    }
    return {"departments": departments}
