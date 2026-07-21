import shap
import joblib
import pandas as pd

IF_MODEL_PATH = r"scripts\models\if.pkl"
FEATURE_COLS = [
    "return", "log_return", "hl_range", "log_volume"
]

model_data = joblib.load(IF_MODEL_PATH)
models = model_data['models']
scalers = model_data['scalers']
explainers = {bucket: shap.TreeExplainer(model) for bucket, model in models.items()}

def explain_iforest(df_row):
    bucket = df_row['liquidity_bucket']
    scaler = scalers[bucket]
    features = df_row[FEATURE_COLS].values.reshape(1, -1)
    features_scaled = scaler.transform(features)
    explainer = explainers[bucket]
    shap_vals = explainer.shap_values(features_scaled)
    return dict(zip(FEATURE_COLS, shap_vals[0]))
