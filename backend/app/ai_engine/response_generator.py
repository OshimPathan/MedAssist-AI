"""
MedAssist AI - Response Generator
Generates contextual AI responses based on classified intents
Uses multi-provider LLM (Ollama/Gemini/OpenAI) with guardrails, or falls back to template responses
"""

import logging
from typing import Optional

from app.config import settings
from app.models.schemas import AIClassification, IntentType, UrgencyLevel
from app.ai_engine.guardrails import check_guardrails, add_safety_disclaimer
from app.ai_engine.conversation_manager import ConversationContext
from app.ai_engine.llm_client import llm_client

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are MedAssist AI, a helpful and professional hospital assistant chatbot. You work 24/7 to help patients with hospital-related queries.

YOUR CAPABILITIES:
- Provide hospital information (departments, services, visiting hours)
- Help with appointment booking and scheduling
- Share doctor information and availability
- Guide patients to the right department based on symptoms
- Provide general health information and test preparation instructions
- Answer insurance and billing questions
- Detect emergencies and escalate immediately

STRICT RULES (NEVER VIOLATE):
1. NEVER diagnose diseases or conditions
2. NEVER prescribe or recommend specific medications
3. NEVER downplay potential emergencies
4. ALWAYS recommend consulting a healthcare professional for medical concerns
5. ALWAYS be empathetic and professional
6. If unsure, say so and recommend seeing a doctor
7. For emergencies, IMMEDIATELY advise calling 108 (emergency services)

RESPONSE STYLE:
- Be warm, professional, and concise
- Use clear language, avoiding medical jargon when possible
- Provide actionable next steps
- Keep responses under 150 words unless detail is needed
- Use relevant emojis sparingly for friendliness

HOSPITAL INFO:
- Name: City General Hospital
- Emergency: 108
- Departments: Cardiology, Neurology, Orthopedics, Pediatrics, General Medicine, Dermatology, ENT, Ophthalmology, Psychiatry, Gynecology
- Visiting Hours: 10 AM - 8 PM daily
- Emergency Department: 24/7"""


async def generate_response(
    message: str,
    classification: AIClassification,
    context: ConversationContext,
) -> str:
    """Generate an appropriate response based on intent classification"""

    # Emergency responses are always template-based for safety
    if classification.intent == IntentType.EMERGENCY:
        return _emergency_response(classification, message)

    # Symptom reports get triage-enhanced responses
    if classification.intent == IntentType.SYMPTOM_REPORT:
        return _triage_response(message, classification)

    # Retrieve RAG context for knowledge-enriched responses
    rag_context = _get_rag_context(message, classification)

    # Try LLM-based response (auto-detects Ollama → Gemini → OpenAI)
    try:
        system = SYSTEM_PROMPT
        if rag_context:
            system += f"\n\nRELEVANT HOSPITAL KNOWLEDGE:\n{rag_context}"

        llm_messages = context.to_llm_messages(system, max_messages=8)
        llm_messages.append({"role": "user", "content": message})

        ai_text = await llm_client.chat(
            messages=llm_messages,
            temperature=settings.TEMPERATURE,
            max_tokens=settings.MAX_TOKENS,
        )

        if ai_text is None:
            return _fallback_response(classification)

        # Apply guardrails
        filtered_text, was_modified = check_guardrails(ai_text)
        if was_modified:
            logger.warning("Guardrails modified AI response")

        return filtered_text

    except Exception as e:
        logger.error(f"LLM response generation failed: {e}")
        return _fallback_response(classification)


def _get_rag_context(message: str, classification: AIClassification) -> str:
    """Retrieve relevant knowledge from the RAG vector store"""
    try:
        from app.ai_engine.rag_engine import vector_store
        if vector_store.total_documents == 0:
            return ""
        results = vector_store.search(query=message, top_k=3)
        if not results:
            return ""
        context_parts = []
        for r in results:
            if r.get("score", 0) > 0.3:
                context_parts.append(f"- {r['title']}: {r['content'][:300]}")
        return "\n".join(context_parts)
    except Exception as e:
        logger.debug(f"RAG retrieval skipped: {e}")
        return ""


def _triage_response(message: str, classification: AIClassification) -> str:
    """Generate triage-enhanced response for symptom reports"""
    try:
        from app.triage.triage_engine import triage_engine
        result = triage_engine.assess(message)

        parts = []
        if result.severity_level == "CRITICAL":
            parts.append("🚨 **This requires immediate medical attention.**\n")
            parts.append("📞 **Call 108 (Emergency Services) NOW.**\n\n")
        elif result.severity_level == "URGENT":
            parts.append("⚠️ **Your symptoms suggest you should see a doctor soon.**\n\n")
        else:
            parts.append("Thank you for describing your symptoms. Here's my assessment:\n\n")

        parts.append(f"**Severity:** {result.severity_level}\n")
        parts.append(f"**Recommended Department:** {result.recommended_department}\n\n")

        if result.first_aid_tips:
            parts.append("**Helpful guidance:**\n")
            for tip in result.first_aid_tips[:4]:
                parts.append(f"• {tip}\n")
            parts.append("\n")

        parts.append(
            "Would you like me to **book an appointment** with our "
            f"{result.recommended_department} department?\n\n"
            "⚕️ *I cannot diagnose conditions. Please consult a healthcare professional.*"
        )
        return "".join(parts)

    except Exception as e:
        logger.error(f"Triage response failed: {e}")
        return _fallback_response(classification)


def _emergency_response(classification: AIClassification, message: str = "") -> str:
    """Generate emergency response with triage-based first-aid (always template-based for safety)"""
    dept = classification.department or "Emergency"

    # Run triage for first-aid tips
    first_aid_tips = []
    try:
        from app.triage.triage_engine import triage_engine
        result = triage_engine.assess(message)
        first_aid_tips = result.first_aid_tips
        if result.recommended_department != "General Medicine":
            dept = result.recommended_department
    except Exception:
        pass

    response = (
        f"🚨 **EMERGENCY ALERT** 🚨\n\n"
        f"This appears to be a medical emergency. Your safety is our top priority.\n\n"
        f"**IMMEDIATE ACTIONS:**\n"
        f"1. 📞 **Call 108 (Emergency Services) NOW**\n"
        f"2. If someone is with you, ask them to call while you stay with the patient\n"
        f"3. Do not move the patient unless they are in immediate danger\n\n"
        f"**Recommended Department:** {dept}\n\n"
    )

    if classification.needs_ambulance:
        response += (
            f"🚑 **Ambulance has been flagged.** Our emergency team has been notified.\n\n"
            f"Please provide:\n"
            f"- Your current location\n"
            f"- Contact phone number\n"
            f"- Brief description of the patient's condition\n\n"
        )

    if first_aid_tips:
        response += "⚠️ *While waiting for help:*\n"
        for tip in first_aid_tips[:5]:
            response += f"- {tip}\n"
        response += "\n"
    else:
        response += (
            "⚠️ *While waiting for help:*\n"
            "- Keep the patient calm and comfortable\n"
            "- Monitor their breathing\n"
            "- Do not give food or water\n"
            "- Note the time symptoms started\n\n"
        )

    response += "🏥 *Our emergency staff has been alerted and are standing by.*"
    return response


def _fallback_response(classification: AIClassification) -> str:
    """Template-based fallback when LLM is unavailable"""
    responses = {
        IntentType.GREETING: (
            "👋 Hello! Welcome to **MedAssist AI** - your hospital assistant.\n\n"
            "I can help you with:\n"
            "• 📅 Booking appointments\n"
            "• 👨‍⚕️ Doctor information\n"
            "• 🏥 Department guidance\n"
            "• 🩺 Symptom-based triage\n"
            "• 📋 Insurance & billing queries\n"
            "• 🚨 Emergency assistance\n\n"
            "How can I assist you today?"
        ),
        IntentType.FAREWELL: (
            "Thank you for using MedAssist AI! 🙏\n\n"
            "Remember:\n"
            "• For emergencies, always call **108**\n"
            "• Our hospital is open 24/7 for emergencies\n"
            "• Visiting hours: 10 AM - 8 PM\n\n"
            "Take care and stay healthy! 💙"
        ),
        IntentType.APPOINTMENT_REQUEST: (
            "📅 I'd be happy to help with your appointment!\n\n"
            "To book an appointment, I'll need:\n"
            "1. Your preferred **department** or **doctor**\n"
            "2. **Preferred date and time**\n"
            "3. Your **name** and **contact number**\n\n"
            "Which department or doctor would you like to see?"
        ),
        IntentType.DOCTOR_INFO: (
            "👨‍⚕️ I can help you find doctor information!\n\n"
            "Our hospital has specialists in:\n"
            "• Cardiology • Neurology • Orthopedics\n"
            "• Pediatrics • Dermatology • ENT\n"
            "• General Medicine • Ophthalmology\n\n"
            "Which department or doctor would you like to know about?"
        ),
        IntentType.SYMPTOM_REPORT: (
            "I understand you're not feeling well. I'm here to help guide you.\n\n"
            "Based on your description, I recommend:\n"
            "1. 🏥 **Visit our hospital** for a proper consultation\n"
            "2. 📞 **Call us** if symptoms worsen\n"
            "3. 🚨 **Call 108** if it becomes an emergency\n\n"
            "Would you like me to help book an appointment with a specialist?\n\n"
            "⚕️ *I'm an AI assistant and cannot diagnose conditions. "
            "Please consult a healthcare professional.*"
        ),
        IntentType.INSURANCE: (
            "📋 For insurance and billing questions:\n\n"
            "• **Insurance desk:** Available Mon-Sat, 9 AM - 5 PM\n"
            "• **Billing support:** Ground floor, counter 3\n"
            "• **Cashless claim:** Bring your insurance card and ID\n\n"
            "Would you like to know about a specific insurance plan or billing query?"
        ),
        IntentType.COMPLAINT: (
            "I'm sorry to hear about your experience. Your feedback is important to us.\n\n"
            "To help resolve this:\n"
            "1. Please describe your concern in detail\n"
            "2. Include any relevant dates, department, or staff names\n"
            "3. Our team will review and respond within 24 hours\n\n"
            "You can also reach our Patient Relations team at the front desk."
        ),
        IntentType.GENERAL_QUERY: (
            "Thank you for your question! Here's some useful hospital information:\n\n"
            "🏥 **City General Hospital**\n"
            "• Emergency: 24/7\n"
            "• OPD: 9 AM - 5 PM (Mon-Sat)\n"
            "• Visiting Hours: 10 AM - 8 PM\n"
            "• Pharmacy: 24/7\n\n"
            "Could you tell me more about what specific information you need?"
        ),
    }
    return responses.get(classification.intent, responses[IntentType.GENERAL_QUERY])
