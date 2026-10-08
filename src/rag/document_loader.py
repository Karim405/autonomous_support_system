"""
Document Loaders for RAG Engine:
- Extracts policy text from PDF with chunking
- Extracts product catalog from Excel with structured metadata
"""

import os
from typing import List, Dict, Any
import pandas as pd
from pypdf import PdfReader
from langchain_text_splitters import RecursiveCharacterTextSplitter

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PDF_PATH = os.path.join(BASE_DIR, "data", "refund_policy.pdf")
EXCEL_PATH = os.path.join(BASE_DIR, "data", "products_inventory.xlsx")

def load_pdf_policy(pdf_path: str = PDF_PATH) -> List[Dict[str, Any]]:
    """Loads PDF and splits into chunks with metadata."""
    if not os.path.exists(pdf_path):
        return []

    reader = PdfReader(pdf_path)
    full_text = ""
    for page_idx, page in enumerate(reader.pages):
        text = page.extract_text()
        if text:
            full_text += f"\n--- Page {page_idx + 1} ---\n" + text

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=400,
        chunk_overlap=60,
        separators=["\n\n", "\n", ".", " ", ""]
    )
    chunks = splitter.split_text(full_text)

    docs = []
    for idx, chunk in enumerate(chunks):
        docs.append({
            "content": chunk.strip(),
            "metadata": {
                "source": "refund_policy.pdf",
                "chunk_id": idx,
                "type": "policy_rule"
            }
        })
    return docs

def load_excel_products(excel_path: str = EXCEL_PATH) -> List[Dict[str, Any]]:
    """Loads Excel catalog and serializes each product into an informative knowledge chunk."""
    if not os.path.exists(excel_path):
        return []

    df = pd.read_excel(excel_path)
    docs = []

    for _, row in df.iterrows():
        content = (
            f"Product: {row['Product_Name']} (SKU: {row['SKU']})\n"
            f"Category: {row['Category']} | Price: ${row['Price_USD']:.2f}\n"
            f"Return Window: {row['Return_Window_Days']} days | Warranty: {row['Warranty_Months']} months\n"
            f"Restocking Fee: {row['Restocking_Fee_Pct']}%\n"
            f"Troubleshooting Guide: {row['Troubleshooting_Guide']}"
        )
        docs.append({
            "content": content,
            "metadata": {
                "source": "products_inventory.xlsx",
                "sku": row["SKU"],
                "product_name": row["Product_Name"],
                "category": row["Category"],
                "type": "product_catalog"
            }
        })
    return docs

def load_all_knowledge_documents() -> List[Dict[str, Any]]:
    """Aggregates all enterprise unstructured and structured documents."""
    pdf_docs = load_pdf_policy()
    excel_docs = load_excel_products()
    return pdf_docs + excel_docs
