"""
Setup realistic enterprise demo data for the Autonomous Support System:
1. SQLite Database: Customers, Orders, Order Items, Support Tickets, Audit Logs.
2. PDF Policy Document: Official Enterprise Return & Warranty Policy.
3. Excel Product Inventory: Electronics & Gadgets Catalog with SKU, Warranty, Price, Return Window.
"""

import os
import sqlite3
from datetime import datetime, timedelta
import pandas as pd
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
os.makedirs(DATA_DIR, exist_ok=True)

DB_PATH = os.path.join(DATA_DIR, "support_system.db")
PDF_PATH = os.path.join(DATA_DIR, "refund_policy.pdf")
EXCEL_PATH = os.path.join(DATA_DIR, "products_inventory.xlsx")

def init_database():
    print(" initializing SQLite Database...")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Drop existing tables to have fresh clean state
    cursor.executescript("""
    DROP TABLE IF EXISTS audit_logs;
    DROP TABLE IF EXISTS tickets;
    DROP TABLE IF EXISTS order_items;
    DROP TABLE IF EXISTS orders;
    DROP TABLE IF EXISTS customers;

    CREATE TABLE customers (
        customer_id TEXT PRIMARY KEY,
        full_name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        phone TEXT,
        tier TEXT DEFAULT 'Standard', -- Standard, VIP, Enterprise
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE orders (
        order_id TEXT PRIMARY KEY,
        customer_id TEXT NOT NULL,
        order_date DATE NOT NULL,
        status TEXT NOT NULL, -- Processing, Shipped, Delivered, Cancelled, Refunded
        shipping_address TEXT,
        payment_method TEXT,
        total_amount REAL NOT NULL,
        delivered_date DATE,
        FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
    );

    CREATE TABLE order_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_id TEXT NOT NULL,
        sku TEXT NOT NULL,
        product_name TEXT NOT NULL,
        quantity INTEGER NOT NULL,
        unit_price REAL NOT NULL,
        total_price REAL NOT NULL,
        FOREIGN KEY (order_id) REFERENCES orders(order_id)
    );

    CREATE TABLE tickets (
        ticket_id TEXT PRIMARY KEY,
        customer_id TEXT NOT NULL,
        order_id TEXT,
        category TEXT NOT NULL, -- Technical, Billing, Shipping, Account, General
        priority TEXT NOT NULL, -- Low, Medium, High, Critical
        status TEXT DEFAULT 'Open', -- Open, In_Progress, Pending_Human_Approval, Resolved, Closed
        subject TEXT NOT NULL,
        description TEXT NOT NULL,
        assigned_agent TEXT DEFAULT 'AI_Support_Agent',
        resolution_notes TEXT,
        requires_human_approval BOOLEAN DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
    );

    CREATE TABLE audit_logs (
        log_id INTEGER PRIMARY KEY AUTOINCREMENT,
        ticket_id TEXT,
        action_name TEXT NOT NULL,
        actor TEXT NOT NULL, -- AI_Action_Agent, Human_Supervisor, Customer
        details TEXT,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # Seed Customers
    customers = [
        ("CUST-1001", "Ahmed Mansour", "ahmed.mansour@example.com", "+201012345678", "VIP"),
        ("CUST-1002", "Sarah Jenkins", "sarah.j@example.com", "+14155552671", "Standard"),
        ("CUST-1003", "Omar Khaled", "omar.k@example.com", "+201198765432", "Standard"),
        ("CUST-1004", "TechCorp Solutions (Rami)", "ops@techcorp.io", "+971501234567", "Enterprise")
    ]
    cursor.executemany("INSERT INTO customers VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)", customers)

    # Calculate realistic dates relative to today
    today = datetime.now()
    d_3_days_ago = (today - timedelta(days=3)).strftime("%Y-%m-%d")
    d_10_days_ago = (today - timedelta(days=10)).strftime("%Y-%m-%d")
    d_20_days_ago = (today - timedelta(days=20)).strftime("%Y-%m-%d")
    d_45_days_ago = (today - timedelta(days=45)).strftime("%Y-%m-%d")
    d_yesterday = (today - timedelta(days=1)).strftime("%Y-%m-%d")

    # Seed Orders
    # ORD-2024: Delivered 10 days ago (within 14-day refund window)
    # ORD-2025: Processing (eligible for immediate cancellation)
    # ORD-2026: Delivered 45 days ago (OUTSIDE 14-day refund window, warranty applies)
    # ORD-2027: Shipped (in transit, cancellation requires return process)
    orders = [
        ("ORD-2024", "CUST-1001", d_10_days_ago, "Delivered", "24 Nile Corniche, Maadi, Cairo", "Credit_Card", 349.99, d_3_days_ago),
        ("ORD-2025", "CUST-1002", d_yesterday, "Processing", "742 Evergreen Terrace, Springfield", "PayPal", 89.50, None),
        ("ORD-2026", "CUST-1003", d_45_days_ago, "Delivered", "15 Tahrir Square, Downtown, Cairo", "Debit_Card", 1200.00, (today - timedelta(days=40)).strftime("%Y-%m-%d")),
        ("ORD-2027", "CUST-1004", d_3_days_ago, "Shipped", "Building 4, Internet City, Dubai", "Bank_Wire", 4500.00, None)
    ]
    cursor.executemany("INSERT INTO orders VALUES (?, ?, ?, ?, ?, ?, ?, ?)", orders)

    # Seed Order Items
    order_items = [
        (1, "ORD-2024", "SKU-HEADSET-PRO", "Nova Wireless Noise-Cancelling Headphones", 1, 349.99, 349.99),
        (2, "ORD-2025", "SKU-CHARGER-65W", "UltraFast 65W GaN Multi-Port Charger", 1, 49.50, 49.50),
        (3, "ORD-2025", "SKU-CABLE-USB4", "Braided USB-C to USB-C Cable (2m)", 1, 40.00, 40.00),
        (4, "ORD-2026", "SKU-MONITOR-4K", "UltraView 32-inch 4K HDR Gaming Monitor", 1, 1200.00, 1200.00),
        (5, "ORD-2027", "SKU-LAPTOP-DEV", "ApexBook Pro M3 Max (32GB, 1TB SSD)", 2, 2250.00, 4500.00)
    ]
    cursor.executemany("INSERT INTO order_items VALUES (?, ?, ?, ?, ?, ?, ?)", order_items)

    # Seed 2 realistic tickets
    tickets = [
        ("TCK-9001", "CUST-1001", "ORD-2024", "Technical", "Medium", "Resolved", 
         "Bluetooth connection drops intermittently", 
         "Customer reported audio stuttering on macOS.", 
         "AI_Support_Agent", 
         "Provided firmware 2.1 update instructions. Customer confirmed issue resolved.", 
         0, d_3_days_ago, d_yesterday),
        ("TCK-9002", "CUST-1003", "ORD-2026", "Billing", "High", "Pending_Human_Approval", 
         "Customer requested full refund after 40 days", 
         "Customer claims monitor developed dead pixels. Outside standard 14-day refund window but within 2-year warranty.", 
         "AI_Support_Agent", 
         "Escalated to human supervisor: Refund amount ($1200) exceeds auto-approval threshold ($150) and exceeds 14 days.", 
         1, d_yesterday, d_yesterday)
    ]
    cursor.executemany("INSERT INTO tickets VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", tickets)

    # Seed Audit Log
    cursor.execute("""
    INSERT INTO audit_logs (ticket_id, action_name, actor, details) 
    VALUES ('TCK-9002', 'ESCALATE_REFUND_APPROVAL', 'AI_Action_Agent', 'Refund of $1200.00 for order ORD-2026 held for human review.')
    """)

    conn.commit()
    conn.close()
    print(" SQLite Database initialized with realistic demo data at:", DB_PATH)


def init_excel_inventory():
    print(" initializing Excel Product Catalog...")
    products = [
        {
            "SKU": "SKU-HEADSET-PRO",
            "Product_Name": "Nova Wireless Noise-Cancelling Headphones",
            "Category": "Audio & Wearables",
            "Price_USD": 349.99,
            "Stock_Quantity": 45,
            "Return_Window_Days": 14,
            "Warranty_Months": 12,
            "Restocking_Fee_Pct": 0.0,
            "Troubleshooting_Guide": "Hold power button 7s to reset Bluetooth pairing. Update firmware via NovaCompanion App."
        },
        {
            "SKU": "SKU-CHARGER-65W",
            "Product_Name": "UltraFast 65W GaN Multi-Port Charger",
            "Category": "Accessories & Power",
            "Price_USD": 49.50,
            "Stock_Quantity": 150,
            "Return_Window_Days": 30,
            "Warranty_Months": 24,
            "Restocking_Fee_Pct": 0.0,
            "Troubleshooting_Guide": "Ensure using 100W rated cable for full fast-charging speed. Unplug for 10s if thermal protection triggers."
        },
        {
            "SKU": "SKU-CABLE-USB4",
            "Product_Name": "Braided USB-C to USB-C Cable (2m)",
            "Category": "Cables & Adapters",
            "Price_USD": 40.00,
            "Stock_Quantity": 320,
            "Return_Window_Days": 30,
            "Warranty_Months": 36,
            "Restocking_Fee_Pct": 0.0,
            "Troubleshooting_Guide": "Inspect cable pins for physical debris. Supports 40Gbps data and 240W Power Delivery."
        },
        {
            "SKU": "SKU-MONITOR-4K",
            "Product_Name": "UltraView 32-inch 4K HDR Gaming Monitor",
            "Category": "Displays & Monitors",
            "Price_USD": 1200.00,
            "Stock_Quantity": 12,
            "Return_Window_Days": 14,
            "Warranty_Months": 24,
            "Restocking_Fee_Pct": 10.0,
            "Troubleshooting_Guide": "For dead pixels test, run built-in diagnostic pattern in OSD menu. Requires DisplayPort 1.4 for 144Hz."
        },
        {
            "SKU": "SKU-LAPTOP-DEV",
            "Product_Name": "ApexBook Pro M3 Max (32GB, 1TB SSD)",
            "Category": "Laptops & Computers",
            "Price_USD": 2250.00,
            "Stock_Quantity": 8,
            "Return_Window_Days": 14,
            "Warranty_Months": 12,
            "Restocking_Fee_Pct": 15.0,
            "Troubleshooting_Guide": "Boot diagnostics: Hold 'D' during power-up. Contact enterprise hardware dispatch for board-level repairs."
        },
        {
            "SKU": "SKU-SMART-PLUG",
            "Product_Name": "SmartPower Wi-Fi Energy Monitoring Plug",
            "Category": "Smart Home",
            "Price_USD": 24.99,
            "Stock_Quantity": 200,
            "Return_Window_Days": 30,
            "Warranty_Months": 12,
            "Restocking_Fee_Pct": 0.0,
            "Troubleshooting_Guide": "Requires 2.4GHz Wi-Fi band. Press side button for 5 seconds until LED blinks amber to reset Wi-Fi."
        }
    ]

    df = pd.DataFrame(products)
    df.to_excel(EXCEL_PATH, index=False, engine="openpyxl")
    print(" Excel Inventory created at:", EXCEL_PATH)


def init_pdf_policy():
    print(" initializing Official PDF Policy Document...")
    doc = SimpleDocTemplate(PDF_PATH, pagesize=letter, rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40)
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontSize=20,
        leading=24,
        textColor=colors.HexColor('#1E3A8A'),
        spaceAfter=14
    )
    h2_style = ParagraphStyle(
        'H2',
        parent=styles['Heading2'],
        fontSize=13,
        leading=17,
        textColor=colors.HexColor('#2563EB'),
        spaceBefore=10,
        spaceAfter=6
    )
    body_style = ParagraphStyle(
        'Body',
        parent=styles['Normal'],
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#1F2937'),
        spaceAfter=6
    )

    story = []
    story.append(Paragraph("OmniTech Global: Customer Operations & Returns Policy", title_style))
    story.append(Paragraph("<b>Document Version:</b> 3.2 | <b>Effective Date:</b> January 2026 | <b>Applicable To:</b> All Customer Channels", body_style))
    story.append(Spacer(1, 10))

    story.append(Paragraph("1. General Return Window & Conditions", h2_style))
    story.append(Paragraph(
        "Customers are entitled to return unopened or defective merchandise within the designated return window starting from the verified delivery date. "
        "Standard items (accessories, cables, chargers) have a <b>30-calendar-day return window</b>. High-tier electronics (laptops, monitors, headphones) "
        "have a strict <b>14-calendar-day return window</b>.", body_style
    ))
    story.append(Paragraph(
        "Returned items must be in original condition with all accessories, cables, and packaging intact. "
        "Items damaged through user negligence or unauthorized disassembly are ineligible for refund.", body_style
    ))

    story.append(Paragraph("2. Order Cancellation Rules", h2_style))
    story.append(Paragraph(
        "• <b>Status 'Processing':</b> Orders can be cancelled instantly with an immediate 100% full refund to original payment method.<br/>"
        "• <b>Status 'Shipped':</b> Orders in transit CANNOT be cancelled directly. The customer must receive the parcel and initiate a standard Return Merchandise Authorization (RMA).<br/>"
        "• <b>Status 'Delivered':</b> Subject to standard return policies.", body_style
    ))

    story.append(Paragraph("3. Refund Approval Matrix & AI Guardrails", h2_style))
    story.append(Paragraph(
        "To safeguard operations, all refunds and financial disbursements adhere to strict operational limits:<br/>"
        "• <b>Tier 1 - Autonomous AI Approval:</b> Full refunds for defective or returned items up to <b>$150.00 USD</b> within valid return window.<br/>"
        "• <b>Tier 2 - Human Supervisor Escalation Required:</b> Any refund claim <b>greater than $150.00 USD</b>, or claims initiated outside the standard return window, "
        "MUST be flagged as <code>Pending_Human_Approval</code> and transferred to a Human Lead.<br/>"
        "• <b>VIP / Enterprise Customers:</b> Restocking fees are automatically waived.", body_style
    ))

    # Table of return rules
    data = [
        ["Product Category", "Return Window", "Restocking Fee", "Warranty Coverage", "AI Auto-Refund Limit"],
        ["Accessories & Cables", "30 Days", "0%", "24 - 36 Months", "$150.00 Max"],
        ["Audio & Headphones", "14 Days", "0%", "12 Months", "$150.00 Max"],
        ["Gaming Monitors & Displays", "14 Days", "10%", "24 Months", "Requires Supervisor (>$150)"],
        ["Laptops & Workstations", "14 Days", "15%", "12 Months", "Requires Supervisor (>$150)"]
    ]
    t = Table(data, colWidths=[130, 85, 80, 105, 130])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1E3A8A')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,0), 9),
        ('BOTTOMPADDING', (0,0), (-1,0), 6),
        ('BACKGROUND', (0,1), (-1,-1), colors.HexColor('#F8FAFC')),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
        ('FONTSIZE', (0,1), (-1,-1), 8),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    story.append(t)
    story.append(Spacer(1, 10))

    story.append(Paragraph("4. Technical Troubleshooting Requirement", h2_style))
    story.append(Paragraph(
        "Prior to initiating an RMA for technical defects, the support system MUST provide the standard troubleshooting steps (e.g., reset instructions, firmware verification) "
        "from the Product Knowledge Base. If troubleshooting fails, an RMA replacement or refund ticket is authorized.", body_style
    ))

    doc.build(story)
    print(" PDF Policy Document created at:", PDF_PATH)


if __name__ == "__main__":
    init_database()
    init_excel_inventory()
    init_pdf_policy()
    print("\n Phase 1 Demo Data Generation Complete!")
