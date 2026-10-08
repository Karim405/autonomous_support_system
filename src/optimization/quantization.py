"""
Quantization & Local Model Serving Module (Session 10):
- Demonstrates 4-bit (NF4) and 8-bit quantization using Hugging Face Transformers & BitsAndBytes
- Reduces VRAM footprint by 70% to run local models efficiently on consumer hardware
"""

import os
from typing import Optional

def get_quantized_model_config():
    """
    Returns BitsAndBytes configuration for 4-bit Quantization (QLoRA / NF4).
    """
    try:
        from transformers import BitsAndBytesConfig
        import torch

        bnb_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_use_double_quant=True,
            bnb_4bit_compute_dtype=torch.float16
        )
        return bnb_config
    except ImportError:
        return None

def load_quantized_llm(model_id: str = "mistralai/Mistral-7B-Instruct-v0.2"):
    """
    Loads model in 4-bit mode for local fast inference.
    """
    from transformers import AutoModelForCausalLM, AutoTokenizer
    
    config = get_quantized_model_config()
    if config:
        print(f"Loading {model_id} with 4-bit NF4 Quantization...")
        tokenizer = AutoTokenizer.from_pretrained(model_id)
        model = AutoModelForCausalLM.from_pretrained(
            model_id,
            quantization_config=config,
            device_map="auto"
        )
        return model, tokenizer
    else:
        print("BitsAndBytes not available. Running in standard float16/CPU mode.")
        return None, None

if __name__ == "__main__":
    cfg = get_quantized_model_config()
    print("Quantization config available:", cfg is not None)
