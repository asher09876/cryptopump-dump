import duckdb
import numpy as np
import pandas as pd
from pathlib import Path
from scipy.special import expit  # sigmoid

# =========================
# CONFIG
# =========================
DB_PATH = "data/telegram.duckdb"

# weights (can be tuned later)
W_LSTM = 1.8
W_IF = 1.2
W_SOCIAL = 1.0

# =========================
# DB
# =========================
def get_db():
    return duckdb.connect(DB_PATH)

# =========================
# ROBUST Z-SCORE (PER COIN)
# =========================
def robust_z(series):
    med = series.median()
    mad = np.median(np.abs(series - med)) + 1e-6
    return (series - med) / (1.4826 * mad)

# =========================
# MAIN FUSION
# =========================
def fuse_latest():
    db = get_db()

    df = db.execute("""
        SELECT
            f.hour_ts,
            f.coin,
            f.social_pressure,
            m.if_score,
            r.q90_3h,
            r.q90_6h
        FROM fused_gold f
        JOIN market_gold_hourly m USING (coin, hour_ts)
        JOIN risk_gold r USING (coin, hour_ts)
    """).fetch_df()

    if df.empty:
        print("No data to fuse.")
        return

    # --- Per-coin normalization ---
    df["z_lstm"] = df.groupby("coin")["q90_3h"].transform(robust_z)
    df["z_if"] = df.groupby("coin")["if_score"].transform(robust_z)
    df["z_social"] = df.groupby("coin")["social_pressure"].transform(robust_z)

    # --- Fusion ---
    df["pump_logit"] = (
        W_LSTM * df["z_lstm"] +
        W_IF * df["z_if"] +
        W_SOCIAL * df["z_social"]
    )

    df["pump_probability"] = expit(df["pump_logit"])

    # --- Store (idempotent) ---
    db.execute("""
        CREATE TABLE IF NOT EXISTS pump_risk_gold (
            hour_ts TIMESTAMP,
            coin TEXT,
            pump_probability DOUBLE,
            z_lstm DOUBLE,
            z_if DOUBLE,
            z_social DOUBLE,
            PRIMARY KEY (coin, hour_ts)
        )
    """)

    db.execute("""
        INSERT OR REPLACE INTO pump_risk_gold
        SELECT
            hour_ts,
            coin,
            pump_probability,
            z_lstm,
            z_if,
            z_social
        FROM df
    """)

    db.close()
    print("====== Pump risk fused & stored")

# =========================
if __name__ == "__main__":
    fuse_latest()
