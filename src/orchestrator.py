"""
Master Multi-Agent Orchestrator (Session 5 & Session 7):
Coordinates the full execution graph:
Customer Input -> Guardrails -> Memory Lookup -> Triage -> RAG -> Action Agent -> QA Supervisor -> Response Delivery
"""

from typing import Dict, Any, Optional
from src.security.guardrails import SecurityGuardrails
from src.memory.memory_manager import ConversationMemoryManager
from src.agents.triage_agent import TriageAgent, TriageResult
from src.agents.rag_agent import RAGAgent
from src.agents.action_agent import ActionAgent
from src.agents.qa_agent import QAAgent

class AutonomousSupportOrchestrator:
    def __init__(self):
        self.guardrails = SecurityGuardrails()
        self.memory = ConversationMemoryManager()
        self.triage_agent = TriageAgent()
        self.rag_agent = RAGAgent()
        self.action_agent = ActionAgent()
        self.qa_agent = QAAgent()

    def process_message(self, user_message: str) -> Dict[str, Any]:
        """
        Processes a single turn of interaction end-to-end.
        """
        # Step 1: Input Guardrails Check
        is_safe, sanitized_input, violation = self.guardrails.validate_input(user_message)
        if not is_safe:
            return {
                "success": False,
                "error": "GUARDRAIL_BLOCKED",
                "response": f"⚠️ Request Blocked: {violation}",
                "trace": {"guardrail_violation": violation}
            }

        # Step 2: Memory Context Recall
        active_order = self.memory.get_context("active_order_id")
        pending_action = self.memory.get_context("pending_action")

        # Step 3: Triage & Intent Analysis
        triage_res: TriageResult = self.triage_agent.analyze(
            sanitized_input, 
            chat_history=self.memory.get_chat_history_str()
        )

        # Context inheritance: If user didn't mention order ID in this turn, check memory
        if not triage_res.order_id and active_order:
            triage_res.order_id = active_order

        # Handle pending confirmation
        if pending_action == "CANCEL_CONFIRMATION" and triage_res.customer_confirmed:
            triage_res.intent = "CANCEL_ORDER"
            triage_res.customer_confirmed = True

        # Update active order in memory
        if triage_res.order_id:
            self.memory.set_context("active_order_id", triage_res.order_id)

        # Step 4: RAG Knowledge Retrieval
        rag_query = f"{triage_res.intent} {triage_res.category} {sanitized_input}"
        rag_data = self.rag_agent.retrieve_context(rag_query)

        # Step 5: Action Agent Execution
        action_data = self.action_agent.execute(
            triage=triage_res,
            rag_context=rag_data.get("grounded_context")
        )

        # Update pending state in memory
        if action_data.get("action_executed") == "CANCEL_ORDER":
            res = action_data.get("result", {})
            if res.get("action_required") == "CUSTOMER_CONFIRMATION_REQUIRED":
                self.memory.set_context("pending_action", "CANCEL_CONFIRMATION")
            elif res.get("success"):
                self.memory.set_context("pending_action", None)

        # Step 6: QA Supervisor Synthesis
        final_answer = self.qa_agent.format_final_response(
            customer_message=sanitized_input,
            triage_data=triage_res.model_dump(),
            rag_data=rag_data,
            action_data=action_data
        )

        # Step 7: Record in Memory
        self.memory.add_user_message(sanitized_input)
        self.memory.add_assistant_message(final_answer)

        return {
            "success": True,
            "response": final_answer,
            "trace": {
                "triage": triage_res.model_dump(),
                "rag_sources": rag_data.get("sources", []),
                "action_executed": action_data.get("action_executed"),
                "action_result": action_data.get("result", {})
            }
        }
