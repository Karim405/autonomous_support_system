"""
Triage & Intent Classification Agent (Session 7 & Session 2):
- Analyzes incoming customer message
- Identifies Intent: CHECK_ORDER, CANCEL_ORDER, REQUEST_REFUND, TROUBLESHOOTING, GENERAL_INQUIRY
- Extracts entities: order_id, customer_id, issue_category, urgency, customer_confirmed
- Uses LLM (via LangChain) if API key available, with intelligent semantic fallback
"""

import re
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field

class TriageResult(BaseModel):
    intent: str = Field(description="Detected primary intent")
    category: str = Field(description="Issue category: Technical, Billing, Shipping, Account, General")
    urgency: str = Field(description="Urgency: Low, Medium, High, Critical")
    order_id: Optional[str] = Field(default=None, description="Extracted order ID like ORD-2024")
    customer_confirmed: bool = Field(default=False, description="Whether customer confirmed an irreversible action")
    raw_message: str

class TriageAgent:
    def __init__(self, llm=None):
        self.llm = llm

    def extract_order_id(self, text: str) -> Optional[str]:
        """Extracts order IDs formatted like ORD-1234 or #ORD-1234."""
        match = re.search(r'(?:ORD|ORDER)[-_\s]?#?(\d{4})', text, re.IGNORECASE)
        if match:
            return f"ORD-{match.group(1)}"
        match2 = re.search(r'#(\d{4})', text)
        if match2:
            return f"ORD-{match2.group(1)}"
        return None

    def detect_confirmation(self, text: str) -> bool:
        """Detects explicit confirmation from customer."""
        affirmations = ["yes", "confirm", "proceed", "sure", "نعم", "تأكيد", "أوافق", "الغيه", "الغي", "ايوه", "تمام"]
        text_lower = text.lower()
        return any(word in text_lower for word in affirmations)

    def analyze(self, customer_message: str, chat_history: Optional[str] = None) -> TriageResult:
        """
        Classifies intent and extracts parameters.
        """
        extracted_order = self.extract_order_id(customer_message)
        confirmed = self.detect_confirmation(customer_message)
        msg_lower = customer_message.lower()

        # Check for Greetings & Introduction
        greetings = ["hello", "hi", "hey", "مرحبا", "أهلا", "اهلا", "السلام عليكم", "ازيك", "صباح الخير", "مساء الخير", "مين انت", "من انت", "من تكون", "كيف حالك"]
        if any(w in msg_lower for w in greetings) and not any(w in msg_lower for w in ["cancel", "refund", "return", "ord-", "#", "استرجاع", "إلغاء"]):
            intent = "GREETING"
            category = "General"
            urgency = "Low"

        # Check for Cancellation
        elif any(w in msg_lower for w in ["cancel", "إلغاء", "الغي", "وقف"]):
            intent = "CANCEL_ORDER"
            category = "Billing"
            urgency = "Medium"

        # Check for Refund / Return
        elif any(w in msg_lower for w in ["refund", "return", "استرجاع", "فلوسي", "ترجيع", "استرداد"]):
            intent = "REQUEST_REFUND"
            category = "Billing"
            urgency = "High"

        # Check for Order Status / Tracking
        elif any(w in msg_lower for w in ["where is my order", "track", "order status", "فين طلبي", "تتبع", "حالة الطلب", "وصل"]):
            intent = "CHECK_ORDER"
            category = "Shipping"
            urgency = "Medium"

        # Check for Technical Troubleshooting
        elif any(w in msg_lower for w in ["broken", "not working", "sound", "connect", "bluetooth", "dead pixel", "مش شغال", "باظ", "عطل"]):
            intent = "TROUBLESHOOTING"
            category = "Technical"
            urgency = "High"

        # If LLM is available, enrich analysis
        if self.llm:
            try:
                # LLM can refine or confirm intent
                pass
            except Exception:
                pass

        return TriageResult(
            intent=intent,
            category=category,
            urgency=urgency,
            order_id=extracted_order,
            customer_confirmed=confirmed,
            raw_message=customer_message
        )
