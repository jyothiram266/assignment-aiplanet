#!/usr/bin/env python3
"""
Local GPU Fine-Tuning Script with LoRA (PyTorch + Hugging Face Transformers + PEFT)
Designed for ROCm AMD GPU environment (e.g. gfx1032 / RX 6000 series with HSA_OVERRIDE_GFX_VERSION=10.3.0).
"""

import os
import sys
import argparse
import json
import torch
from datasets import Dataset
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    TrainingArguments,
    Trainer,
    DataCollatorForLanguageModeling,
)
from peft import LoraConfig, get_peft_model, TaskType

# Sample instruction fine-tuning dataset for customer support QA
SAMPLE_DATASET = [
    {
        "instruction": "What is the return policy for electronic items?",
        "response": "Electronic items can be returned within 30 days of purchase provided they are in original packaging and condition."
    },
    {
        "instruction": "How do I reset my account password?",
        "response": "Navigate to the Login page, click 'Forgot Password', enter your registered email address, and follow the password reset link sent to your inbox."
    },
    {
        "instruction": "Where can I track my shipment order?",
        "response": "Log into your account dashboard, go to 'Order History', select your recent order, and click 'Track Package' to see real-time shipping updates."
    },
    {
        "instruction": "What payment methods do you accept?",
        "response": "We accept major credit cards (Visa, MasterCard, American Express), PayPal, Apple Pay, and Google Pay."
    },
    {
        "instruction": "How can I contact customer support?",
        "response": "Support is available 24/7 via live chat on our website or by emailing support@example.com."
    }
]

def format_prompt(example):
    return f"<|im_start|>user\n{example['instruction']}<|im_end|>\n<|im_start|>assistant\n{example['response']}<|im_end|>"

def main():
    parser = argparse.ArgumentParser(description="Local LoRA Fine-Tuning Pipeline for LLMOps Platform")
    parser.add_argument("--base_model", type=str, default="Qwen/Qwen2.5-0.5B-Instruct", help="Hugging Face base model ID")
    parser.add_argument("--output_dir", type=str, default="./checkpoints/qwen-lora-v1", help="Output directory for fine-tuned LoRA weights")
    parser.add_argument("--epochs", type=int, default=3, help="Number of training epochs")
    parser.add_argument("--batch_size", type=int, default=2, help="Per device train batch size")
    parser.add_argument("--lr", type=float, default=2e-4, help="Learning rate")
    parser.add_argument("--lora_r", type=int, default=8, help="LoRA rank")
    parser.add_argument("--lora_alpha", type=int, default=16, help="LoRA alpha")
    args = parser.parse_args()

    print(f"=== Starting LoRA Fine-Tuning ===")
    print(f"Base Model: {args.base_model}")
    print(f"CUDA/ROCm Available: {torch.cuda.is_available()}")
    if torch.cuda.is_available():
        print(f"Device Name: {torch.cuda.get_device_name(0)}")

    device = "cuda" if torch.cuda.is_available() else "cpu"

    print("Loading tokenizer and base model...")
    tokenizer = AutoTokenizer.from_pretrained(args.base_model, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    model = AutoModelForCausalLM.from_pretrained(
        args.base_model,
        torch_dtype=torch.float16 if device == "cuda" else torch.float32,
        device_map="auto" if device == "cuda" else None,
        trust_remote_code=True
    )

    lora_config = LoraConfig(
        task_type=TaskType.CAUSAL_LM,
        r=args.lora_r,
        lora_alpha=args.lora_alpha,
        lora_dropout=0.05,
        target_modules=["q_proj", "v_proj", "k_proj", "o_proj"]
    )

    model = get_peft_model(model, lora_config)
    model.print_trainable_parameters()

    print("Preparing training dataset...")
    formatted_texts = [format_prompt(item) for item in SAMPLE_DATASET]
    dataset = Dataset.from_dict({"text": formatted_texts})

    def tokenize_fn(examples):
        return tokenizer(examples["text"], truncation=True, max_length=512, padding="max_length")

    tokenized_dataset = dataset.map(tokenize_fn, batched=True, remove_columns=["text"])

    training_args = TrainingArguments(
        output_dir=args.output_dir,
        per_device_train_batch_size=args.batch_size,
        num_train_epochs=args.epochs,
        learning_rate=args.lr,
        logging_steps=1,
        save_strategy="epoch",
        fp16=(device == "cuda"),
        use_cpu=(device == "cpu"),
        report_to="none"
    )

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=tokenized_dataset,
        data_collator=DataCollatorForLanguageModeling(tokenizer=tokenizer, mlm=False)
    )

    print("Training LoRA model...")
    trainer.train()

    print(f"Saving fine-tuned LoRA weights and metadata to {args.output_dir}...")
    model.save_pretrained(args.output_dir)
    tokenizer.save_pretrained(args.output_dir)

    metadata = {
        "base_model": args.base_model,
        "lora_r": args.lora_r,
        "lora_alpha": args.lora_alpha,
        "epochs": args.epochs,
        "lr": args.lr,
        "dataset": "customer_support_qa"
    }

    with open(os.path.join(args.output_dir, "training_metadata.json"), "w") as f:
        json.dump(metadata, f, indent=2)

    print("LoRA Fine-tuning completed successfully!")

if __name__ == "__main__":
    main()
