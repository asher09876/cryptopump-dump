import shap
import numpy as np
import keras
import duckdb

MODEL_PATH = r"scripts\models\lstm_multi_final.keras"
SEQ_LEN = 24

FEATURE_COLS = [
    "hype_score",
    "coin_reveal_score",
    "entropy_mean",
    "msg_velocity",
    "social_pressure",
    "return",
    "log_return",
    "hl_range",
    "market_stress",
    "if_score",
    "if_score_lag1",
    "if_score_lag3"
]

model = keras.models.load_model(MODEL_PATH, compile=False)

def build_sequence(db, coin):
    df = db.execute(f"""
        SELECT {",".join(FEATURE_COLS)}
        FROM fused_gold
        WHERE coin = ?
        ORDER BY hour_ts DESC
        LIMIT {SEQ_LEN}
    """, [coin]).fetch_df()

    if len(df) < SEQ_LEN:
        return None

    df = df.sort_index()
    return df.values.reshape(1, SEQ_LEN, -1)

def explain_lstm(db, coin):
    background = np.zeros((20, SEQ_LEN, len(FEATURE_COLS)))

    explainer = shap.KernelExplainer(
        lambda x: model.predict(x)[4],  # q90_3h head
        background
    )

    X = build_sequence(db, coin)
    shap_vals = explainer.shap_values(X, nsamples=150)

    # Aggregate time → feature
    contrib = np.abs(shap_vals[0]).mean(axis=1).mean(axis=0)

    return dict(zip(FEATURE_COLS, contrib))
