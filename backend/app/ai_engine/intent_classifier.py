"""
MedAssist AI - Intent Classifier
Classifies user messages into structured intents using LLM
"""

import json
import logging
from typing import Optional

from app.config import settings
from app.models.schemas import AIClassification, IntentType, UrgencyLevel
from app.ai_engine.llm_client import llm_client

logger = logging.getLogger(__name__)

CLASSIFICATION_PROMPT = """You are an AI assistant for a hospital communication system. Your job is to classify the patient's message into a structured intent.

CLASSIFY the message into one of these intents:
- general_query: General questions about the hospital, departments, services, visiting hours
- appointment_request: Wants to book, reschedule, or cancel an appointment
- doctor_info: Asking about a specific doctor, their schedule, specialization
- symptom_report: Describing symptoms or health concerns
- emergency: Reporting an emergency situation (chest pain, difficulty breathing, severe bleeding, seizures, unconsciousness, stroke symptoms)
- insurance: Questions about insurance, billing, payments, policies
- complaint: Filing a complaint or expressing dissatisfaction
- greeting: Simple hello or greeting
- farewell: Goodbye or end of conversation

URGENCY LEVELS:
- non_urgent: Normal query, no health risk
- urgent: Health concern that should be addressed soon
- critical: Immediate medical attention needed (always for emergency intent)

⚠️ SAFETY RULES:
- If ANY emergency keywords are present (chest pain, can't breathe, bleeding heavily, seizure, unconscious, stroke), ALWAYS classify as emergency with critical urgency
- When in doubt about severity, escalate to higher urgency
- NEVER provide medical diagnosis or prescriptions
- NEVER downplay potential emergencies

Respond ONLY in this JSON format:
{
    "intent": "<intent_type>",
    "urgency": "<urgency_level>",
    "department": "<relevant department or null>",
    "needs_ambulance": <true/false>,
    "confidence": <0.0 to 1.0>,
    "entities": {"key": "value"}
}"""


async def classify_intent(message: str) -> AIClassification:
    """Classify a patient message into a structured intent using LLM"""
    
    # First check rule-based emergency detection (safety net)
    emergency_result = _check_emergency_rules(message)
    if emergency_result:
        logger.warning(f"Rule-based emergency detected: {message[:100]}")
        return emergency_result

    # Use LLM for classification if available
    try:
        response_text = await llm_client.chat(
            messages=[
                {"role": "system", "content": CLASSIFICATION_PROMPT},
                {"role": "user", "content": message},
            ],
            temperature=0.1,
            max_tokens=200,
        )

        if response_text is None:
            return _fallback_classification(message)

        # Parse JSON from response (handle markdown code blocks)
        clean_text = response_text.strip()
        if clean_text.startswith("```"):
            clean_text = clean_text.split("\n", 1)[-1].rsplit("```", 1)[0]

        result = json.loads(clean_text)

        classification = AIClassification(
            intent=IntentType(result.get("intent", "general_query")),
            urgency=UrgencyLevel(result.get("urgency", "non_urgent")),
            department=result.get("department"),
            needs_ambulance=result.get("needs_ambulance", False),
            confidence=result.get("confidence", 0.8),
            entities=result.get("entities"),
        )

        logger.info(f"Classified intent: {classification.intent} (urgency: {classification.urgency})")
        return classification

    except Exception as e:
        logger.error(f"LLM classification failed: {e}")
        return _fallback_classification(message)


def _check_emergency_rules(message: str) -> Optional[AIClassification]:
    """Rule-based emergency keyword detection (Layer 1 safety net)"""
    msg_lower = message.lower()
    
    emergency_triggers = {
        "chest pain": "cardiology",
        "heart attack": "cardiology",
        "can't breathe": "pulmonology",
        "cannot breathe": "pulmonology",
        "difficulty breathing": "pulmonology",
        "choking": "emergency",
        "severe bleeding": "emergency",
        "bleeding heavily": "emergency",
        "seizure": "neurology",
        "convulsion": "neurology",
        "unconscious": "emergency",
        "not conscious": "emergency",
        "passed out": "emergency",
        "stroke": "neurology",
        "slurred speech": "neurology",
        "face drooping": "neurology",
        "severe burn": "emergency",
        "poisoning": "emergency",
        "overdose": "emergency",
        "suicidal": "psychiatry",
        "suicide": "psychiatry",
        "anaphylaxis": "emergency",
        "allergic reaction severe": "emergency",
    }

    for trigger, department in emergency_triggers.items():
        if trigger in msg_lower:
            return AIClassification(
                intent=IntentType.EMERGENCY,
                urgency=UrgencyLevel.CRITICAL,
                department=department,
                needs_ambulance=True,
                confidence=1.0,
                entities={"trigger": trigger},
            )
    return None


def _fallback_classification(message: str) -> AIClassification:
    """Keyword-based fallback classification when LLM is unavailable"""
    msg_lower = message.lower()

    # Simple keyword matching
    if any(w in msg_lower for w in ["hello", "hi", "hey", "good morning", "good evening"]):
        return AIClassification(intent=IntentType.GREETING, confidence=0.9)

    if any(w in msg_lower for w in ["bye", "goodbye", "thank", "thanks"]):
        return AIClassification(intent=IntentType.FAREWELL, confidence=0.9)

    if any(w in msg_lower for w in ["appointment", "book", "schedule", "slot", "reschedule", "cancel appointment"]):
        return AIClassification(intent=IntentType.APPOINTMENT_REQUEST, confidence=0.7)

    if any(w in msg_lower for w in ["doctor", "dr.", "specialist", "surgeon"]):
        return AIClassification(intent=IntentType.DOCTOR_INFO, confidence=0.7)

    if any(w in msg_lower for w in ["insurance", "bill", "payment", "cost", "charge", "policy"]):
        return AIClassification(intent=IntentType.INSURANCE, confidence=0.7)

    if any(w in msg_lower for w in ["complaint", "unhappy", "bad experience", "rude"]):
        return AIClassification(intent=IntentType.COMPLAINT, confidence=0.7)

    if any(w in msg_lower for w in ["pain", "fever", "headache", "cough", "vomit", "nausea", "dizzy", "symptom", "sick", "ill", "hurts"]):
        return AIClassification(
            intent=IntentType.SYMPTOM_REPORT,
            urgency=UrgencyLevel.URGENT,
            confidence=0.6,
        )

    return AIClassification(intent=IntentType.GENERAL_QUERY, confidence=0.5)
