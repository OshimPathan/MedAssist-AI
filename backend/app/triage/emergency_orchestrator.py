"""
MedAssist AI - Emergency Orchestrator
Coordinates emergency detection, triage, alerts, and response workflows
"""

import logging
from datetime import datetime
from typing import Optional, Dict
from dataclasses import dataclass

from app.triage.triage_engine import triage_engine, TriageResult
from app.ai_engine.conversation_manager import ConversationContext
from app.database.connection import get_db
from app.utils.audit_logger import log_action

logger = logging.getLogger(__name__)


@dataclass
class EmergencyAction:
    """Describes the action to take for a detected emergency"""
    is_emergency: bool
    triage: TriageResult
    dispatch_ambulance: bool
    alert_staff: bool
    escalation_message: str
    patient_guidance: str
    emergency_case_id: Optional[str] = None


class EmergencyOrchestrator:
    """
    Central coordinator for emergency response workflows.
    Integrates triage engine, alert system, and case management.
    """

    async def evaluate_and_respond(
        self,
        message: str,
        context: ConversationContext,
    ) -> EmergencyAction:
        """
        Full emergency evaluation pipeline:
        1. Run triage engine
        2. Determine response level
        3. Create emergency case if needed
        4. Prepare staff alerts
        5. Generate patient guidance
        """
        # Run triage
        triage = triage_engine.assess(message)

        is_emergency = triage.severity_level == "CRITICAL"
        is_urgent = triage.severity_level == "URGENT"

        # Build patient guidance
        guidance = self._build_patient_guidance(triage)

        # Create emergency case if critical/urgent
        emergency_id = None
        if is_emergency or is_urgent:
            emergency_id = await self._create_emergency_case(
                triage, context, message
            )

        # Build escalation message for staff
        escalation = self._build_escalation_message(
            triage, context, emergency_id
        ) if is_emergency else ""

        return EmergencyAction(
            is_emergency=is_emergency,
            triage=triage,
            dispatch_ambulance=triage.needs_ambulance,
            alert_staff=is_emergency,
            escalation_message=escalation,
            patient_guidance=guidance,
            emergency_case_id=emergency_id,
        )

    async def _create_emergency_case(
        self,
        triage: TriageResult,
        context: ConversationContext,
        message: str,
    ) -> Optional[str]:
        """Create an emergency case record in the database"""
        try:
            db = get_db()

            # Map severity level to schema enum
            severity_map = {
                "CRITICAL": "CRITICAL",
                "URGENT": "URGENT",
                "NON_URGENT": "NON_URGENT",
            }

            case = await db.emergencycase.create(data={
                "patientId": context.patient_id,
                "severity": severity_map.get(triage.severity_level, "URGENT"),
                "symptoms": ", ".join(triage.detected_symptoms) or message[:500],
                "contactNumber": context.patient_phone or "UNKNOWN",
                "notes": triage.triage_notes,
            })

            await log_action(
                "EMERGENCY_CASE_CREATED",
                "emergency_cases",
                details={
                    "case_id": case.id,
                    "severity": triage.severity_level,
                    "score": triage.severity_score,
                    "department": triage.recommended_department,
                    "session_id": context.session_id,
                }
            )

            logger.critical(
                f"Emergency case created: {case.id} | "
                f"Severity: {triage.severity_level} ({triage.severity_score}) | "
                f"Dept: {triage.recommended_department}"
            )

            return case.id

        except Exception as e:
            logger.error(f"Failed to create emergency case: {e}")
            return None

    def _build_patient_guidance(self, triage: TriageResult) -> str:
        """Build comprehensive patient-facing guidance message"""
        parts = []

        if triage.severity_level == "CRITICAL":
            parts.append(
                "🚨 **EMERGENCY — IMMEDIATE ACTION REQUIRED**\n\n"
                "**Call 108 (Emergency Services) NOW.**\n"
            )
        elif triage.severity_level == "URGENT":
            parts.append(
                "⚠️ **URGENT — Please seek medical attention soon.**\n"
            )

        # Triage info
        parts.append(
            f"**Severity Assessment:** {triage.severity_level}\n"
            f"**Recommended Department:** {triage.recommended_department}\n"
        )

        if triage.needs_ambulance:
            parts.append(
                "\n🚑 **Ambulance recommended.** "
                "Our team has been alerted. Please share your location.\n"
            )

        # First aid
        if triage.first_aid_tips:
            parts.append("\n**While waiting for help:**\n")
            for tip in triage.first_aid_tips[:5]:
                parts.append(f"• {tip}\n")

        # Safety disclaimer
        parts.append(
            "\n⚕️ *This is an automated triage assessment. "
            "A healthcare professional will confirm the evaluation.*"
        )

        return "".join(parts)

    def _build_escalation_message(
        self,
        triage: TriageResult,
        context: ConversationContext,
        emergency_id: Optional[str],
    ) -> str:
        """Build staff-facing escalation alert"""
        return (
            f"🚨 EMERGENCY ALERT — Case #{emergency_id or 'PENDING'}\n"
            f"Severity: {triage.severity_level} (Score: {triage.severity_score})\n"
            f"Symptoms: {', '.join(triage.detected_symptoms)}\n"
            f"Department: {triage.recommended_department}\n"
            f"Patient: {context.patient_name or 'Unknown'}\n"
            f"Phone: {context.patient_phone or 'Unknown'}\n"
            f"Session: {context.session_id}\n"
            f"Ambulance Required: {'YES' if triage.needs_ambulance else 'No'}\n"
            f"Time: {datetime.utcnow().isoformat()}"
        )


# Global orchestrator instance
emergency_orchestrator = EmergencyOrchestrator()
