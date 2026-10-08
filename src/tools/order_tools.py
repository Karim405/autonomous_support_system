"""
Order Operations Tools with Strict Business Rules & Guardrails:
- Retrieve Order Details (Structured)
- Check Order Status
- Cancel Order (Only if 'Processing', strictly requires customer confirmation)
"""

import os
import sqlite3
from typing import Dict, Any, Optional
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DB_PATH = os.path.join(BASE_DIR, "data", "support_system.db")

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def get_order_details(order_id: str) -> Dict[str, Any]:
    """
    Fetches full structured details of a customer order including items.
    """
    order_id = order_id.strip().upper()
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT o.order_id, o.customer_id, c.full_name, c.email, c.tier,
               o.order_date, o.status, o.total_amount, o.shipping_address,
               o.payment_method, o.delivered_date
        FROM orders o
        JOIN customers c ON o.customer_id = c.customer_id
        WHERE o.order_id = ?
    """, (order_id,))
    
    order = cursor.fetchone()
    if not order:
        conn.close()
        return {"success": False, "error": f"Order '{order_id}' was not found in the database."}

    cursor.execute("""
        SELECT sku, product_name, quantity, unit_price, total_price
        FROM order_items
        WHERE order_id = ?
    """, (order_id,))
    items = [dict(row) for row in cursor.fetchall()]

    conn.close()

    return {
        "success": True,
        "order": dict(order),
        "items": items
    }

def cancel_order(order_id: str, reason: str, customer_confirmed: bool = False) -> Dict[str, Any]:
    """
    Cancels an order if it is in 'Processing' state.
    Strict Business Rules:
    1. If status is NOT 'Processing', cancellation is forbidden.
    2. Requires customer_confirmed=True to prevent accidental or hallucinated cancellations.
    """
    order_id = order_id.strip().upper()
    order_info = get_order_details(order_id)
    if not order_info["success"]:
        return order_info

    order = order_info["order"]
    current_status = order["status"]

    # Rule 1: Check status
    if current_status == "Cancelled":
        return {
            "success": False,
            "error": f"Order '{order_id}' is already cancelled."
        }
    
    if current_status in ["Shipped", "Delivered"]:
        return {
            "success": False,
            "error": f"Cannot cancel order '{order_id}' directly because its status is '{current_status}'. "
                     f"Orders in transit or delivered must follow the return/refund procedure after delivery."
        }

    if current_status != "Processing":
        return {
            "success": False,
            "error": f"Order status is '{current_status}'. Only 'Processing' orders can be cancelled."
        }

    # Rule 2: Explicit Confirmation Check (Human/Customer validation guardrail)
    if not customer_confirmed:
        return {
            "success": False,
            "action_required": "CUSTOMER_CONFIRMATION_REQUIRED",
            "message": f"Order '{order_id}' is eligible for cancellation with a full refund of ${order['total_amount']:.2f}. "
                       f"Please ask the customer to confirm: 'Are you sure you want to cancel order {order_id}?'"
        }

    # Execute Cancellation in DB
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE orders 
        SET status = 'Cancelled'
        WHERE order_id = ?
    """, (order_id,))

    # Log action in audit logs
    cursor.execute("""
        INSERT INTO audit_logs (ticket_id, action_name, actor, details)
        VALUES (NULL, 'ORDER_CANCELLED', 'AI_Action_Agent', ?)
    """, (f"Cancelled order {order_id} (Reason: {reason}). Refund of ${order['total_amount']:.2f} queued.",))

    conn.commit()
    conn.close()

    return {
        "success": True,
        "order_id": order_id,
        "new_status": "Cancelled",
        "refund_amount": order["total_amount"],
        "message": f"Order '{order_id}' has been successfully cancelled. A full refund of ${order['total_amount']:.2f} has been processed back to {order['payment_method']}."
    }
