import duckdb
import numpy as np
import pandas as pd
import tensorflow as tf
from datetime import timezone

# =========================
# CONFIG
# =========================
DB_PATH = "data/telegram.duckdb"
MODEL_PATH = "scripts/models/lstm_multi_final.keras"

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
    "if_score_lag3",
]

# =========================
# LOAD MODEL
# =========================
model = tf.keras.models.load_model(
    MODEL_PATH,
    compile=False
)

# =========================
# HELPERS
# =========================
def build_latest_sequence(con, coin):
    df = con.execute(f"""
        SELECT hour_ts, {", ".join(FEATURE_COLS)}
        FROM fused_gold
        WHERE coin = ?
        ORDER BY hour_ts DESC
        LIMIT ?
    """, [coin, SEQ_LEN]).fetch_df()

    if len(df) < SEQ_LEN:
        return None, None

    df = df.sort_values("hour_ts")
    hour_ts = df["hour_ts"].iloc[-1]

    X = df[FEATURE_COLS].values.astype("float32")
    X = X.reshape(1, SEQ_LEN, len(FEATURE_COLS))

    return hour_ts, X

# =========================
# MAIN INFERENCE LOOP
# =========================
def run_inference():
    con = duckdb.connect(DB_PATH)

    # Ensure table exists
    con.execute("""
        CREATE TABLE IF NOT EXISTS risk_gold (
            hour_ts TIMESTAMP,
            coin TEXT,
            q50_1h DOUBLE,
            q50_3h DOUBLE,
            q50_6h DOUBLE,
            q90_1h DOUBLE,
            q90_3h DOUBLE,
            q90_6h DOUBLE,
            created_at TIMESTAMP DEFAULT now(),
            PRIMARY KEY (coin, hour_ts)
        )
    """)

    coins = con.execute("""
        SELECT DISTINCT coin FROM fused_gold
    """).fetch_df()["coin"].tolist()

    inserted = 0

    for coin in coins:
        hour_ts, X = build_latest_sequence(con, coin)
        if X is None:
            continue

        # Skip if already predicted
        exists = con.execute("""
            SELECT 1 FROM risk_gold
            WHERE coin = ? AND hour_ts = ?
            LIMIT 1
        """, [coin, hour_ts]).fetchone()

        if exists:
            continue

        preds = model.predict(X, verbose=0)

        row = {
            "hour_ts": hour_ts,
            "coin": coin,
            "q50_1h": preds[0][0].item(),
            "q50_3h": preds[1][0].item(),
            "q50_6h": preds[2][0].item(),
            "q90_1h": preds[3][0].item(),
            "q90_3h": preds[4][0].item(),
            "q90_6h": preds[5][0].item(),
            
        }

        con.execute("""
            INSERT INTO risk_gold VALUES (
                ?, ?, ?, ?, ?, ?, ?, ?, now()
            )
        """, list(row.values()))

        inserted += 1

    # Apply social hype boost using lookback 3 hours max hype
    con.execute("""
        WITH recent_hype AS (
            SELECT 
                coin,
                hour_ts,
                MAX(hype_score) OVER (
                    PARTITION BY coin 
                    ORDER BY hour_ts 
                    ROWS BETWEEN 3 PRECEDING AND CURRENT ROW
                ) AS max_hype_last_3h
            FROM fused_gold
        )
        UPDATE risk_gold r
        SET 
            q50_1h  = q50_1h  * (1 + 0.6 * h.max_hype_last_3h),
            q50_3h  = q50_3h  * (1 + 0.7 * h.max_hype_last_3h),
            q50_6h  = q50_6h  * (1 + 0.8 * h.max_hype_last_3h),
            q90_1h  = q90_1h  * (1 + 0.8 * h.max_hype_last_3h),
            q90_3h  = q90_3h  * (1 + 0.9 * h.max_hype_last_3h),
            q90_6h  = q90_6h  * (1 + 1.0 * h.max_hype_last_3h)
        FROM recent_hype h
        WHERE r.coin = h.coin AND r.hour_ts = h.hour_ts
    """)

    con.close()
    print(f"===== Inserted {inserted} new LSTM predictions with social hype boost applied")

# =========================
# RUN
# =========================
if __name__ == "__main__":
    run_inference()
