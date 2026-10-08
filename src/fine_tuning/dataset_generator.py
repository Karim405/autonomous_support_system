"""
Fine-Tuning Module (Session 3):
- Generates instruction-tuning dataset (JSONL format) from support policies & ticket histories
- Prepares LoRA (Parameter-Efficient Fine-Tuning) script for domain-specific tone & classification
"""

import os
import json

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
FT_DATA_DIR = os.path.join(BASE_DIR, "data", "fine_tuning")
os.makedirs(FT_DATA_DIR, exist_ok=True)

DATASET_FILE = os.path.join(FT_DATA_DIR, "support_instructions.jsonl")

def generate_lora_dataset():
    """Generates instruction-response pairs for fine-tuning on customer support tone & classification."""
    samples = [
        {
            "instruction": "Classify customer issue and assess urgency: 'My monitor has dead pixels and I want my money back.'",
            "context": "Enterprise Return Policy: Monitors have 14 days return window and 10% restocking fee.",
            "response": '{"intent": "REQUEST_REFUND", "category": "Technical", "urgency": "High", "product_category": "Displays"}'
        },
        {
            "instruction": "Respond to an angry customer demanding an unauthorized refund exceeding $150.",
            "context": "Guardrails Rule: AI cannot auto-refund > $150. Must escalate to Human Supervisor.",
            "response": "I completely understand your frustration and want to make sure this is handled properly. Because your refund claim exceeds our standard automated limit, I have personally opened a priority ticket for our Operations Supervisor to review and authorize your request promptly."
        },
        {
            "instruction": "Evaluate cancellation eligibility for order status 'Shipped'.",
            "context": "Policy Rule: Shipped orders cannot be cancelled in transit.",
            "response": "Orders that have already shipped cannot be cancelled in transit. Once the package arrives at your address, you can initiate a standard return for a full refund."
        }
    ]

    with open(DATASET_FILE, "w", encoding="utf-8") as f:
        for item in samples:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")

    print(f" LoRA Fine-Tuning dataset generated: {len(samples)} samples at {DATASET_FILE}")

if __name__ == "__main__":
    generate_lora_dataset()
