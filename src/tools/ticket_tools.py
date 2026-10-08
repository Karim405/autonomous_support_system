"""
Support Ticket Management Tools:
- Create Ticket (Categorized: Technical, Billing, Shipping, Account, General)
- Retrieve Tickets for Customer
- Update Ticket Status & Resolution Notes
"""

import os
import sqlite3
import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DB_PATH = os.path.join(BASE_DIR, "data", "support_system.db")

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def create_support_ticket(
    customer_id: str,
    category: str,
    priority: str,
    subject: str,
    description: str,
    order_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Creates an official support ticket in the database.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    # Verify customer exists
    cursor.execute("SELECT customer_id, full_name, email FROM customers WHERE customer_id = ?", (customer_id,))
    customer = cursor.fetchone()
    if not customer:
        conn.close()
        return {"success": False, "error": f"Customer '{customer_id}' not found."}

    ticket_id = f"TCK-{uuid.uuid4().hex[:6].upper()}"
    valid_priorities = ["Low", "Medium", "High", "Critical"]
    valid_categories = ["Technical", "Billing", "Shipping", "Account", "General"]

    priority = priority.capitalize() if priority.capitalize() in valid_priorities else "Medium"
    category = category.capitalize() if category.capitalize() in valid_categories else "General"

    cursor.execute("""
        INSERT INTO tickets (ticket_id, customer_id, order_id, category, priority, status, subject, description, assigned_agent)
        VALUES (?, ?, ?, ?, ?, 'Open', ?, ?, 'AI_Support_Agent')
    """, (ticket_id, customer_id, order_id, category, priority, subject, description))

    cursor.execute("""
        INSERT INTO audit_logs (ticket_id, action_name, actor, details)
        VALUES (?, 'TICKET_CREATED', 'AI_Triage_Agent', ?)
    """, (ticket_id, f"Created {priority} priority ticket for category '{category}'."))

    conn.commit()
    conn.close()

    return {
        "success": True,
        "ticket_id": ticket_id,
        "customer_id": customer_id,
        "category": category,
        "priority": priority,
        "status": "Open",
        "subject": subject,
        "message": f"Support Ticket [{ticket_id}] has been logged successfully."
    }

def get_customer_tickets(customer_id: str) -> List[Dict[str, Any]]:
    """Retrieves all past and open tickets for a customer."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT ticket_id, order_id, category, priority, status, subject, created_at, resolution_notes
        FROM tickets
        WHERE customer_id = ?
        ORDER BY created_at DESC
    """, (customer_id,))
    tickets = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return tickets
