"""
Verification and Test Suite for Phase 1:
- Database connectivity & mock data integrity
- Tools execution & guardrails (order check, cancellation, refund limits)
- RAG Document Loading & Semantic Search accuracy
"""

import sys
import os

# Add parent directory to path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

if sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

from src.tools.order_tools import get_order_details, cancel_order
from src.tools.refund_tools import check_refund_eligibility, process_refund
from src.tools.ticket_tools import create_support_ticket, get_customer_tickets
from src.rag.document_loader import load_all_knowledge_documents
from src.rag.vector_store import get_vector_store

def run_tests():
    print("=" * 60)
    print("🚀 RUNNING PHASE 1 VERIFICATION TESTS")
    print("=" * 60)

    # 1. Test Order Tools
    print("\n[1] Testing Order Details Retrieval...")
    res = get_order_details("ORD-2024")
    assert res["success"] is True, f"Failed to get ORD-2024: {res}"
    print(f" Found Order {res['order']['order_id']} for customer {res['order']['full_name']} (${res['order']['total_amount']})")

    # 2. Test Cancellation Guardrails
    print("\n[2] Testing Cancellation Guardrail (Unconfirmed vs Confirmed)...")
    unconfirmed = cancel_order("ORD-2025", "Customer changed mind", customer_confirmed=False)
    assert unconfirmed["success"] is False and unconfirmed.get("action_required") == "CUSTOMER_CONFIRMATION_REQUIRED", "Guardrail failed to require confirmation!"
    print(f" Guardrail Active: System correctly halted unconfirmed cancellation -> '{unconfirmed['message']}'")

    confirmed = cancel_order("ORD-2025", "Customer changed mind", customer_confirmed=True)
    assert confirmed["success"] is True and confirmed["new_status"] == "Cancelled", "Confirmed cancellation failed!"
    print(f" Order Cancelled Safely: Status={confirmed['new_status']}, Refund={confirmed['refund_amount']}")

    # 3. Test Refund Eligibility & Autonomous Limits
    print("\n[3] Testing Refund Limits & Human Escalation Guardrail...")
    # ORD-2024 ($349.99 > $150 limit)
    refund_res = check_refund_eligibility("ORD-2024", "Headphones sound distorted")
    assert refund_res["success"] is True
    print(f" Refund Evaluation for ORD-2024: Amount=${refund_res['estimated_refund']}, Verdict: {refund_res['policy_verdict']}")
    assert refund_res["requires_human_approval"] is True, "High amount (> $150) should require human approval!"

    # Process refund without approval -> Should escalate
    exec_res = process_refund("ORD-2024", "Distorted audio", human_approved=False)
    assert exec_res["escalated"] is True, "Failed to escalate high-value refund!"
    print(f" Safe Escalation Executed: Created Ticket [{exec_res['ticket_id']}] for supervisor approval.")

    # 4. Test Support Ticket Creation
    print("\n[4] Testing Support Ticket Creation...")
    tck = create_support_ticket(
        customer_id="CUST-1001",
        category="Technical",
        priority="Medium",
        subject="Headset firmware inquiry",
        description="Customer asking how to update to firmware 2.2"
    )
    assert tck["success"] is True
    print(f" Ticket Created: ID={tck['ticket_id']}, Priority={tck['priority']}")

    # 5. Test RAG Document Indexing and Search
    print("\n[5] Testing RAG Ingestion & Vector Search...")
    docs = load_all_knowledge_documents()
    print(f" Loaded {len(docs)} documents (PDF policies + Excel products)")
    assert len(docs) > 0, "No documents loaded!"

    vs = get_vector_store()
    query = "What is the return window for headphones and what is the auto refund limit?"
    search_results = vs.search(query, top_k=2)
    assert len(search_results) > 0, "Search returned 0 results!"
    print(f" Search Query: '{query}'")
    for idx, r in enumerate(search_results):
        print(f"   Match #{idx+1} [Score: {r.get('relevance_score', 0):.3f}]: {r['content'][:120]}...")

    print("\n" + "=" * 60)
    print(" ALL PHASE 1 TESTS PASSED SUCCESSFULLY! ")
    print("=" * 60)

if __name__ == "__main__":
    run_tests()
