
import json
from pathlib import Path
from typing import List, Dict
import torch
import numpy as np
from transformers import BertTokenizer, BertForSequenceClassification
from torch.utils.data import Dataset, DataLoader
import tqdm

# =========================
# CONFIGURATION
# =========================
MODEL_DIR = Path("models/bert_pump_classifier_4labels")
INPUT_JSONL = Path("data/processed/telegram_messages_with_coins.jsonl")
OUTPUT_JSONL = Path("data/processed/labeled_messages_bert1.jsonl")

BATCH_SIZE = 32
MAX_LENGTH = 128
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# TEMPERATURE SCALING to Fix Overconfidence/ overfitting
TEMPERATURE = 3.0  

ID_TO_LABEL = {
    0: "hype_signal",
    1: "coin_reveal",
    2: "outcome_reflection",
    3: "noise"
}

# =========================
# DATASET
# =========================
class MessageDataset(Dataset):
    def __init__(self, messages: List[Dict], tokenizer):
        self.messages = messages
        self.tokenizer = tokenizer

    def __len__(self):
        return len(self.messages)

    def __getitem__(self, idx):
        msg = self.messages[idx]
        text = msg.get("text", "") or " "
        encoding = self.tokenizer(
            text,
            truncation=True,
            padding="max_length",
            max_length=MAX_LENGTH,
            return_tensors="pt"
        )
        item = {k: v.squeeze(0) for k, v in encoding.items()}
        item["original_data"] = msg
        return item

def collate_fn(batch):
    return {
        "input_ids": torch.stack([b["input_ids"] for b in batch]),
        "attention_mask": torch.stack([b["attention_mask"] for b in batch]),
        "metadata": [b["original_data"] for b in batch]
    }

# =========================
# LOAD MODEL
# =========================
print("Loading tokenizer and model...")
tokenizer = BertTokenizer.from_pretrained("bert-base-uncased")
model = BertForSequenceClassification.from_pretrained(MODEL_DIR)
model.to(DEVICE)
model.eval()
print(f"Model loaded on {DEVICE}")

# =========================
# LOAD DATA
# =========================
print(f"Loading messages from {INPUT_JSONL}...")
with INPUT_JSONL.open("r", encoding="utf-8") as f:
    messages = [json.loads(line) for line in f if line.strip()]

print(f"Loaded {len(messages)} messages")

dataset = MessageDataset(messages, tokenizer)
dataloader = DataLoader(
    dataset,
    batch_size=BATCH_SIZE,
    shuffle=False,
    collate_fn=collate_fn
)

# =========================
# INFERENCE WITH TEMPERATURE SCALING
# =========================
labeled_messages = []
print(f"Running probabilistic inference with temperature scaling (T={TEMPERATURE})...")

with torch.no_grad():
    for batch in tqdm.tqdm(dataloader):
        input_ids = batch["input_ids"].to(DEVICE)
        attention_mask = batch["attention_mask"].to(DEVICE)

        outputs = model(input_ids=input_ids, attention_mask=attention_mask)
        logits = outputs.logits

        #  APPLY TEMPERATURE SCALING
        scaled_logits = logits / TEMPERATURE

        # Softmax over scaled logits
        probs = torch.softmax(scaled_logits, dim=-1).cpu().numpy()

        for prob_vec, original_msg in zip(probs, batch["metadata"]):
            bert_probs = {
                ID_TO_LABEL[i]: float(prob_vec[i])
                for i in range(len(prob_vec))
            }

            # Soft label (for inspection only — still argmax on scaled probs)
            original_msg["label"] = max(bert_probs, key=bert_probs.get)

            # REQUIRED downstream features
            original_msg["bert_probs"] = bert_probs
            original_msg["bert_entropy"] = float(
                -np.sum(prob_vec * np.log(prob_vec + 1e-9))
            )

            labeled_messages.append(original_msg)

# =========================
# SAVE OUTPUT
# =========================
OUTPUT_JSONL.parent.mkdir(parents=True, exist_ok=True)
with OUTPUT_JSONL.open("w", encoding="utf-8") as f:
    for msg in labeled_messages:
        f.write(json.dumps(msg) + "\n")

print(f"\nDone! Saved {len(labeled_messages)} messages → {OUTPUT_JSONL}")


import pandas as pd

df = pd.DataFrame([
    {
        "hype_signal": m["bert_probs"]["hype_signal"],
        "coin_reveal": m["bert_probs"]["coin_reveal"],
        "outcome_reflection": m["bert_probs"]["outcome_reflection"],
        "noise": m["bert_probs"]["noise"],
        "entropy": m["bert_entropy"]
    }
    for m in labeled_messages
])

print(f"\nMean BERT Probabilities (Temperature = {TEMPERATURE}):")
print(df.mean().round(4))

print("\nEntropy Statistics:")
print(df["entropy"].describe().round(4))
