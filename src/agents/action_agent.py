"""
Constrained Action Agent (Session 2, 7 & 8):
- Executes backend operations with strict safety rules:
  * Only cancels orders in 'Processing' status AND with explicit confirmation.
  * Only auto-approves refunds <= $150.00 within valid return window.
  * Escalates any exception or high-value claim to human supervisor with a formal ticket.
"""

from typing import Dict, Any, Optional
from src.tools.order_tools import get_order_details, cancel_order
from src.tools.refund_tools import check_refund_eligibility, process_refund
from src.tools.ticket_tools import create_support_ticket
from src.agents.triage_agent import TriageResult

class ActionAgent:
    def __init__(self):
        pass

    def execute(self, triage: TriageResult, rag_context: Optional[str] = None) -> Dict[str, Any]:
        """
        Executes operations based on intent and hard constraints.
        """
        intent = triage.intent
        order_id = triage.order_id

        # 1. Order Status Check
        if intent == "CHECK_ORDER":
            if not order_id:
                return {
                    "action_executed": "NONE",
                    "status": "MISSING_INFO",
                    "message": "Please provide your Order ID (e.g., ORD-2024) to look up the status."
                }
            res = get_order_details(order_id)
            return {
                "action_executed": "GET_ORDER_DETAILS",
                "result": res
            }

        # 2. Cancel Order (Strict Guardrail: Confirmation + Processing status)
        elif intent == "CANCEL_ORDER":
            if not order_id:
                return {
                    "action_executed": "NONE",
                    "status": "MISSING_INFO",
                    "message": "Please specify the Order ID you wish to cancel (e.g., ORD-2025)."
                }
            res = cancel_order(
                order_id=order_id,
                reason=triage.raw_message,
                customer_confirmed=triage.customer_confirmed
            )
            return {
                "action_executed": "CANCEL_ORDER",
                "result": res
            }

        # 3. Refund / Return Claim
        elif intent == "REQUEST_REFUND":
            if not order_id:
                return {
                    "action_executed": "NONE",
                    "status": "MISSING_INFO",
                    "message": "Please provide your Order ID (e.g., ORD-2024) so we can evaluate your refund eligibility."
                }
            # Check eligibility and execute according to threshold
            res = process_refund(
                order_id=order_id,
                reason=triage.raw_message,
                human_approved=False  # Automated path cannot self-approve > $150
            )
            return {
                "action_executed": "PROCESS_REFUND",
                "result": res
            }

        # 4. Technical Troubleshooting / Defect
        elif intent == "TROUBLESHOOTING":
            # If an order is mentioned, check items
            order_info = get_order_details(order_id) if order_id else None
            return {
                "action_executed": "TROUBLESHOOTING_LOOKUP",
                "order_info": order_info,
                "rag_guidance": rag_context
            }

        # 5. General Inquiry
        return {
            "action_executed": "KNOWLEDGE_LOOKUP",
            "rag_guidance": rag_context
        }
