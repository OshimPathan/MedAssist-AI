"""
MedAssist AI - Guardrails Filter
Prevents unsafe medical responses: no diagnosis, no prescriptions, no unsafe claims
"""

import re
import logging
from typing import Tuple

logger = logging.getLogger(__name__)

# Keywords that indicate the AI is trying to give medical advice
DIAGNOSIS_PATTERNS = [
    r"you have \w+",
    r"you are suffering from",
    r"diagnosed with",
    r"this is (likely|probably|definitely) \w+",
    r"it sounds like you have",
    r"you might have",
    r"this could be \w+ disease",
]

PRESCRIPTION_PATTERNS = [
    r"take \d+ mg",
    r"you should take \w+ medication",
    r"prescribe",
    r"dosage",
    r"take (aspirin|ibuprofen|paracetamol|acetaminophen)",
    r"medication for \w+",
    r"i recommend taking",
]

UNSAFE_CLAIM_PATTERNS = [
    r"don't worry.{0,20}not serious",
    r"nothing to worry about",
    r"this is not an emergency",
    r"you don't need to see a doctor",
    r"no need for hospital",
    r"home remedy will cure",
    r"guaranteed to work",
]

# Safe disclaimers to append
MEDICAL_DISCLAIMER = (
    "\n\n⚕️ *Please note: I'm an AI hospital assistant and cannot provide "
    "medical diagnosis or prescriptions. For medical concerns, please consult "
    "with a healthcare professional or visit the hospital.*"
)

EMERGENCY_DISCLAIMER = (
    "\n\n🚨 *If you are experiencing a medical emergency, please call "
    "emergency services (108) immediately or go to the nearest emergency room.*"
)


def check_guardrails(response: str) -> Tuple[str, bool]:
    """
    Check AI response against guardrails.
    Returns (filtered_response, was_modified).
    """
    was_modified = False
    filtered = response

    # Check for diagnosis patterns
    for pattern in DIAGNOSIS_PATTERNS:
        if re.search(pattern, response, re.IGNORECASE):
            logger.warning(f"Guardrail: Diagnosis pattern detected: {pattern}")
            filtered = re.sub(
                pattern,
                "[I cannot make diagnoses - please consult a doctor]",
                filtered,
                flags=re.IGNORECASE,
            )
            was_modified = True

    # Check for prescription patterns
    for pattern in PRESCRIPTION_PATTERNS:
        if re.search(pattern, response, re.IGNORECASE):
            logger.warning(f"Guardrail: Prescription pattern detected: {pattern}")
            filtered = re.sub(
                pattern,
                "[I cannot prescribe medications - please consult a doctor]",
                filtered,
                flags=re.IGNORECASE,
            )
            was_modified = True

    # Check for unsafe claims
    for pattern in UNSAFE_CLAIM_PATTERNS:
        if re.search(pattern, response, re.IGNORECASE):
            logger.warning(f"Guardrail: Unsafe claim detected: {pattern}")
            filtered = re.sub(
                pattern,
                "[Please seek professional medical advice]",
                filtered,
                flags=re.IGNORECASE,
            )
            was_modified = True

    # Always add disclaimer if symptoms are discussed
    symptom_keywords = ["pain", "fever", "bleeding", "symptom", "condition", "suffer"]
    if any(kw in response.lower() for kw in symptom_keywords):
        if MEDICAL_DISCLAIMER not in filtered:
            filtered += MEDICAL_DISCLAIMER
            was_modified = True

    return filtered, was_modified


def add_safety_disclaimer(response: str, is_emergency: bool = False) -> str:
    """Add appropriate safety disclaimer to response"""
    if is_emergency:
        if EMERGENCY_DISCLAIMER not in response:
            return response + EMERGENCY_DISCLAIMER
    return response
