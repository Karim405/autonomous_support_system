"""
Security & Guardrails Module (Session 10 & Session 8):
- Input Sanitization & Anti-Prompt Injection Defense
- Sensitive Data Redaction (Credit Cards, Secret Keys)
- Financial Boundary Guardrails
"""

import re
from typing import Dict, Any, Tuple

INJECTION_PATTERNS = [
    r"ignore (?:all )?(?:previous|above) (?:instructions|rules)",
    r"you are now (?:dan|developer mode|unrestricted)",
    r"system prompt",
    r"reveal (?:your|the) (?:instructions|prompt|api key)",
    r"override policy",
    r"disregard safety"
]

CREDIT_CARD_PATTERN = r'\b(?:\d{4}[ -]?){3}\d{4}\b'

class SecurityGuardrails:
    @staticmethod
    def validate_input(user_text: str) -> Tuple[bool, str, str]:
        """
        Validates user input.
        Returns: (is_safe, sanitized_text, violation_reason)
        """
        if not user_text or not user_text.strip():
            return False, "", "Empty input provided."

        text_lower = user_text.lower()
        for pattern in INJECTION_PATTERNS:
            if re.search(pattern, text_lower):
                return False, user_text, "Security Alert: Prompt injection or system override detected."

        # Redact credit card numbers for privacy/PCI-DSS compliance
        sanitized = re.sub(CREDIT_CARD_PATTERN, "[REDACTED_CARD_NUMBER]", user_text)

        return True, sanitized, ""

    @staticmethod
    def enforce_financial_limit(refund_amount: float, max_auto_limit: float = 150.0) -> bool:
        """Ensures refund does not exceed auto-approval limit without human review."""
        return refund_amount <= max_auto_limit
