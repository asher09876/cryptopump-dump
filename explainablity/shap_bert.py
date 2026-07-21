import shap
import numpy as np
import pandas as pd
import joblib
from transformers import AutoTokenizer, AutoModelForSequenceClassification
import torch
from transformers import AutoTokenizer, AutoModel

MODEL_NAME = "scripts/models/bert_pump_classifier_4labels"

tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME, local_files_only=True)
model = AutoModel.from_pretrained(MODEL_NAME, local_files_only=True)


model.eval()

def bert_predict(texts):
    inputs = tokenizer(
        texts,
        padding=True,
        truncation=True,
        return_tensors="pt"
    )
    with torch.no_grad():
        logits = model(**inputs).logits
    probs = torch.softmax(logits, dim=1)
    return probs.numpy()

explainer = shap.Explainer(bert_predict, tokenizer)

def explain_bert(text):
    shap_values = explainer([text])

    token_importance = list(
        zip(
            shap_values.data[0],
            shap_values.values[0].sum(axis=1)
        )
    )

    token_importance = sorted(
        token_importance,
        key=lambda x: abs(x[1]),
        reverse=True
    )[:10]

    return token_importance
