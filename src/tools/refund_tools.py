"""
Refund & Return Tools with Autonomous Limits & Human-in-the-Loop Escalation:
- Check Refund Eligibility (Validates return window against delivery date & SKU)
- Process Refund (Auto-approves <= $150 within policy; Escalates > $150 or exceptions)
"""

import os
import sqlite3
from typing import Dict, Any, Optional
from datetime import datetime
import pandas as pd

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DB_PATH = os.path.join(BASE_DIR, "data", "support_system.db")
EXCEL_PATH = os.path.join(BASE_DIR, "data", "products_inventory.xlsx")

AUTO_REFUND_LIMIT_USD = 150.0

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def get_product_policy_from_catalog(sku: str) -> Optional[Dict[str, Any]]:
    """Fetches return window and restocking fee from the Excel inventory."""
    if not os.path.exists(EXCEL_PATH):
        return None
    df = pd.read_excel(EXCEL_PATH)
    match = df[df["SKU"] == sku]
    if match.empty:
        return None
    return match.iloc[0].to_dict()

def check_refund_eligibility(order_id: str, reason: str) -> Dict[str, Any]:
    """
    Evaluates order refund eligibility against delivery date, product return window, and policy limits.
    """
    order_id = order_id.strip().upper()
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT o.order_id, o.customer_id, c.full_name, c.tier,
               o.order_date, o.status, o.total_amount, o.delivered_date, o.payment_method
        FROM orders o
        JOIN customers c ON o.customer_id = c.customer_id
        WHERE o.order_id = ?
    """, (order_id,))
    order_row = cursor.fetchone()

    if not order_row:
        conn.close()
        return {"success": False, "error": f"Order '{order_id}' not found."}
    
    order = dict(order_row)

    cursor.execute("SELECT sku, product_name, quantity, total_price FROM order_items WHERE order_id = ?", (order_id,))
    items = [dict(r) for r in cursor.fetchall()]
    conn.close()

    # Rule: Must be delivered
    if order["status"] != "Delivered":
        return {
            "success": False,
            "order_id": order_id,
            "status": order["status"],
            "eligible": False,
            "reason": f"Order status is '{order['status']}'. Refunds can only be processed on delivered orders (or cancelled if Processing)."
        }

    # Calculate days since delivery
    delivered_date = datetime.strptime(order["delivered_date"], "%Y-%m-%d")
    days_since_delivery = (datetime.now() - delivered_date).days

    # Check return window (default 14 days for electronics, 30 days for accessories)
    sku = items[0]["sku"] if items else None
    product_policy = get_product_policy_from_catalog(sku) if sku else None
    allowed_window = product_policy.get("Return_Window_Days", 14) if product_policy else 14
    restocking_fee_pct = product_policy.get("Restocking_Fee_Pct", 0.0) if product_policy else 0.0

    # Waive restocking fee for VIP / Enterprise
    if order["tier"] in ["VIP", "Enterprise"]:
        restocking_fee_pct = 0.0

    restocking_deduction = round(order["total_amount"] * (restocking_fee_pct / 100.0), 2)
    estimated_refund = round(order["total_amount"] - restocking_deduction, 2)

    within_window = days_since_delivery <= allowed_window
    requires_human_approval = (estimated_refund > AUTO_REFUND_LIMIT_USD) or (not within_window)

    return {
        "success": True,
        "order_id": order_id,
        "customer_tier": order["tier"],
        "delivered_date": order["delivered_date"],
        "days_since_delivery": days_since_delivery,
        "allowed_window_days": allowed_window,
        "within_window": within_window,
        "total_amount": order["total_amount"],
        "restocking_fee_pct": restocking_fee_pct,
        "restocking_deduction": restocking_deduction,
        "estimated_refund": estimated_refund,
        "auto_approval_allowed": (estimated_refund <= AUTO_REFUND_LIMIT_USD) and within_window,
        "requires_human_approval": requires_human_approval,
        "policy_verdict": (
            "Eligible for immediate autonomous refund."
            if (estimated_refund <= AUTO_REFUND_LIMIT_USD and within_window)
            else f"Requires Human Supervisor Approval (Reason: {'Amount > $' + str(AUTO_REFUND_LIMIT_USD) if estimated_refund > AUTO_REFUND_LIMIT_USD else 'Past return window (' + str(days_since_delivery) + ' days vs ' + str(allowed_window) + ' days max)'})"
        )
    }

def process_refund(order_id: str, reason: str, human_approved: bool = False) -> Dict[str, Any]:
    """
    Executes refund. Enforces strict Guardrails:
    - If requires human approval and human_approved is False, creates a Pending_Human_Approval ticket.
    - If within autonomous threshold, updates DB and logs transaction.
    """
    eligibility = check_refund_eligibility(order_id, reason)
    if not eligibility["success"]:
        return eligibility

    order_id = eligibility["order_id"]
    refund_amount = eligibility["estimated_refund"]
    conn = get_db_connection()
    cursor = conn.cursor()

    if eligibility["requires_human_approval"] and not human_approved:
        # Create ticket for supervisor review
        ticket_id = f"TCK-ESC-{order_id[-4:]}"
        cursor.execute("""
            INSERT OR REPLACE INTO tickets (ticket_id, customer_id, order_id, category, priority, status, subject, description, assigned_agent, requires_human_approval, created_at, updated_at)
            VALUES (?, 
                    (SELECT customer_id FROM orders WHERE order_id = ?),
                    ?, 'Billing', 'High', 'Pending_Human_Approval',
                    ?, ?, 'AI_Action_Agent', 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        """, (
            ticket_id, order_id, order_id,
            f"Escalated Refund Request for Order {order_id} (${refund_amount:.2f})",
            f"Customer requested refund for order {order_id}. {eligibility['policy_verdict']}. Reason: {reason}"
        ))

        cursor.execute("""
            INSERT INTO audit_logs (ticket_id, action_name, actor, details)
            VALUES (?, 'REFUND_ESCALATED', 'AI_Action_Agent', ?)
        """, (ticket_id, f"Refund of ${refund_amount:.2f} held for Human Approval. Ticket {ticket_id} opened."))

        conn.commit()
        conn.close()

        return {
            "success": False,
            "escalated": True,
            "ticket_id": ticket_id,
            "refund_amount": refund_amount,
            "status": "Pending_Human_Approval",
            "message": f"Refund of ${refund_amount:.2f} exceeds autonomous approval limits. "
                       f"A priority ticket [{ticket_id}] has been forwarded to our Operations Supervisor for authorization."
        }

    # Autonomous execution
    cursor.execute("UPDATE orders SET status = 'Refunded' WHERE order_id = ?", (order_id,))
    cursor.execute("""
        INSERT INTO audit_logs (ticket_id, action_name, actor, details)
        VALUES (NULL, 'REFUND_PROCESSED', 'AI_Action_Agent', ?)
    """, (f"Autonomous refund of ${refund_amount:.2f} approved for {order_id}. Reason: {reason}",))

    conn.commit()
    conn.close()

    return {
        "success": True,
        "escalated": False,
        "order_id": order_id,
        "refund_amount": refund_amount,
        "status": "Refunded",
        "message": f"Refund of ${refund_amount:.2f} has been successfully approved and issued back to the customer's account."
    }
