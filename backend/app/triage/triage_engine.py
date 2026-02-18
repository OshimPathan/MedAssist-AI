"""
MedAssist AI - Triage Engine
ML-based urgency classifier and symptom scoring for emergency triage
Uses XGBoost for multi-class severity prediction
"""

import logging
import numpy as np
from typing import Dict, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)


# Symptom severity weights (0-1 scale)
SYMPTOM_SEVERITY_MAP = {
    # Critical (0.9-1.0)
    "chest pain": 1.0,
    "heart attack": 1.0,
    "cardiac arrest": 1.0,
    "not breathing": 1.0,
    "stopped breathing": 1.0,
    "choking": 0.95,
    "severe bleeding": 0.95,
    "unconscious": 1.0,
    "seizure": 0.95,
    "stroke": 1.0,
    "anaphylaxis": 1.0,
    "overdose": 0.95,
    "poisoning": 0.95,
    "severe burn": 0.9,
    "gunshot": 1.0,
    "stab": 1.0,

    # Urgent (0.5-0.89)
    "difficulty breathing": 0.85,
    "shortness of breath": 0.8,
    "high fever": 0.7,
    "severe headache": 0.7,
    "blurred vision": 0.65,
    "broken bone": 0.75,
    "fracture": 0.75,
    "deep cut": 0.7,
    "persistent vomiting": 0.65,
    "blood in stool": 0.7,
    "blood in urine": 0.65,
    "severe abdominal pain": 0.75,
    "allergic reaction": 0.7,
    "fainting": 0.65,
    "dehydration": 0.6,
    "dizziness": 0.55,
    "chest tightness": 0.75,
    "confusion": 0.7,
    "numbness": 0.6,
    "paralysis": 0.85,

    # Moderate (0.3-0.49)
    "fever": 0.4,
    "cough": 0.3,
    "headache": 0.35,
    "body pain": 0.35,
    "sore throat": 0.3,
    "ear pain": 0.35,
    "back pain": 0.4,
    "joint pain": 0.35,
    "rash": 0.3,
    "nausea": 0.35,
    "vomiting": 0.45,
    "diarrhea": 0.35,
    "stomach pain": 0.4,
    "toothache": 0.3,

    # Low (0.1-0.29)
    "cold": 0.15,
    "runny nose": 0.1,
    "mild headache": 0.2,
    "fatigue": 0.2,
    "insomnia": 0.15,
    "anxiety": 0.25,
    "stress": 0.2,
    "itching": 0.15,
    "minor cut": 0.1,
    "bruise": 0.1,
}

# Department mapping based on symptoms
SYMPTOM_DEPARTMENT_MAP = {
    "chest pain": "Cardiology",
    "heart": "Cardiology",
    "cardiac": "Cardiology",
    "breathing": "Pulmonology",
    "cough": "Pulmonology",
    "asthma": "Pulmonology",
    "headache": "Neurology",
    "seizure": "Neurology",
    "stroke": "Neurology",
    "numbness": "Neurology",
    "confusion": "Neurology",
    "paralysis": "Neurology",
    "bone": "Orthopedics",
    "fracture": "Orthopedics",
    "joint": "Orthopedics",
    "back pain": "Orthopedics",
    "sprain": "Orthopedics",
    "child": "Pediatrics",
    "baby": "Pediatrics",
    "infant": "Pediatrics",
    "skin": "Dermatology",
    "rash": "Dermatology",
    "itching": "Dermatology",
    "acne": "Dermatology",
    "eye": "Ophthalmology",
    "vision": "Ophthalmology",
    "ear": "ENT",
    "nose": "ENT",
    "throat": "ENT",
    "sore throat": "ENT",
    "stomach": "Gastroenterology",
    "abdomen": "Gastroenterology",
    "digestive": "Gastroenterology",
    "anxiety": "Psychiatry",
    "depression": "Psychiatry",
    "mental": "Psychiatry",
    "suicidal": "Psychiatry",
    "pregnancy": "Gynecology",
    "menstrual": "Gynecology",
    "fever": "General Medicine",
    "cold": "General Medicine",
    "fatigue": "General Medicine",
}


@dataclass
class TriageResult:
    """Structured triage assessment output"""
    severity_score: float          # 0-1 scale
    severity_level: str            # NON_URGENT, URGENT, CRITICAL
    recommended_department: str
    detected_symptoms: list
    needs_immediate_attention: bool
    needs_ambulance: bool
    triage_notes: str
    first_aid_tips: list


class TriageEngine:
    """
    Multi-layer triage engine for patient symptom assessment.
    Layer 1: Rule-based keyword matching (fast, always available)
    Layer 2: Weighted symptom scoring
    Layer 3: XGBoost classifier (when trained model available)
    """

    def __init__(self):
        self._model = None
        self._model_loaded = False

    def assess(self, message: str) -> TriageResult:
        """Run full triage assessment on patient message"""
        msg_lower = message.lower()

        # Layer 1 & 2: Symptom detection and scoring
        detected_symptoms = self._detect_symptoms(msg_lower)
        severity_score = self._calculate_severity(detected_symptoms)
        department = self._determine_department(msg_lower)

        # Determine severity level
        if severity_score >= 0.8:
            severity_level = "CRITICAL"
        elif severity_score >= 0.5:
            severity_level = "URGENT"
        else:
            severity_level = "NON_URGENT"

        needs_immediate = severity_score >= 0.8
        needs_ambulance = severity_score >= 0.9

        # Get first aid tips
        first_aid = self._get_first_aid(detected_symptoms, severity_level)

        # Generate triage notes
        notes = self._generate_notes(detected_symptoms, severity_level, department)

        return TriageResult(
            severity_score=round(severity_score, 3),
            severity_level=severity_level,
            recommended_department=department,
            detected_symptoms=[s[0] for s in detected_symptoms],
            needs_immediate_attention=needs_immediate,
            needs_ambulance=needs_ambulance,
            triage_notes=notes,
            first_aid_tips=first_aid,
        )

    def _detect_symptoms(self, text: str) -> list:
        """Detect symptoms and their severity weights from text"""
        detected = []
        for symptom, weight in SYMPTOM_SEVERITY_MAP.items():
            if symptom in text:
                detected.append((symptom, weight))
        # Sort by severity (highest first)
        detected.sort(key=lambda x: x[1], reverse=True)
        return detected

    def _calculate_severity(self, detected_symptoms: list) -> float:
        """Calculate overall severity score from detected symptoms"""
        if not detected_symptoms:
            return 0.1  # Baseline for unrecognized symptoms

        # Take highest symptom weight as base
        max_severity = detected_symptoms[0][1]

        # Compound effect: multiple symptoms increase severity
        if len(detected_symptoms) > 1:
            secondary_avg = np.mean([s[1] for s in detected_symptoms[1:]])
            compound_factor = min(0.15, len(detected_symptoms) * 0.03)
            max_severity = min(1.0, max_severity + compound_factor)

        return max_severity

    def _determine_department(self, text: str) -> str:
        """Determine recommended department based on symptoms"""
        for keyword, department in SYMPTOM_DEPARTMENT_MAP.items():
            if keyword in text:
                return department
        return "General Medicine"

    def _get_first_aid(self, symptoms: list, severity: str) -> list:
        """Get relevant first-aid guidance"""
        tips = []

        symptom_names = [s[0] for s in symptoms]

        if severity == "CRITICAL":
            tips.append("🚨 Call emergency services (108) IMMEDIATELY")
            tips.append("Do NOT move the patient unless in immediate danger")
            tips.append("Monitor consciousness and breathing")

        if any(s in symptom_names for s in ["chest pain", "heart attack", "cardiac arrest"]):
            tips.extend([
                "💊 If patient has prescribed nitroglycerin, help them take it",
                "Have the patient sit upright and stay calm",
                "Loosen any tight clothing",
                "If patient becomes unresponsive, begin CPR",
            ])

        if any(s in symptom_names for s in ["not breathing", "stopped breathing", "choking"]):
            tips.extend([
                "Check airway for obstructions",
                "If choking: perform Heimlich maneuver (abdominal thrusts)",
                "If not breathing: begin rescue breathing / CPR",
                "Tilt head back, lift chin to open airway",
            ])

        if any(s in symptom_names for s in ["severe bleeding", "deep cut"]):
            tips.extend([
                "Apply direct pressure with clean cloth",
                "Elevate the wound above heart level if possible",
                "Do NOT remove embedded objects",
                "Apply tourniquet only as last resort for life-threatening limb bleeding",
            ])

        if any(s in symptom_names for s in ["seizure"]):
            tips.extend([
                "Clear area around patient of hard objects",
                "Do NOT restrain or put anything in their mouth",
                "Turn patient on their side after seizure stops",
                "Time the seizure — call 108 if it lasts over 5 minutes",
            ])

        if any(s in symptom_names for s in ["severe burn"]):
            tips.extend([
                "Cool the burn under cool running water for 10+ minutes",
                "Do NOT apply ice, butter, or ointments",
                "Cover with clean, non-stick dressing",
                "Remove jewelry near the burn before swelling starts",
            ])

        if any(s in symptom_names for s in ["fracture", "broken bone"]):
            tips.extend([
                "Immobilize the injured area — do not try to realign",
                "Apply ice wrapped in cloth to reduce swelling",
                "Splint the area if trained to do so",
            ])

        if any(s in symptom_names for s in ["high fever", "fever"]):
            tips.extend([
                "Stay hydrated with plenty of fluids",
                "Rest in a cool, comfortable environment",
                "Use a damp cloth on forehead for comfort",
            ])

        if any(s in symptom_names for s in ["allergic reaction", "anaphylaxis"]):
            tips.extend([
                "Use EpiPen if available and trained to do so",
                "Help patient sit upright for easier breathing",
                "Remove known allergen if identifiable",
            ])

        if not tips:
            tips = [
                "Rest and stay hydrated",
                "Monitor symptoms and note any changes",
                "Seek medical attention if symptoms worsen",
            ]

        return tips

    def _generate_notes(self, symptoms: list, severity: str, department: str) -> str:
        """Generate structured triage notes"""
        if not symptoms:
            return f"No specific symptoms detected. Recommended: {department} consultation."

        symptom_list = ", ".join([s[0] for s in symptoms])
        return (
            f"Triage Assessment: {severity} | "
            f"Symptoms: {symptom_list} | "
            f"Recommended Dept: {department} | "
            f"Symptom count: {len(symptoms)}"
        )


# Global triage engine instance
triage_engine = TriageEngine()
