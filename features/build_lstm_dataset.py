import pandas as pd
import numpy as np
from pathlib import Path

# =========================
# CONFIG
# =========================
SOCIAL_CSV = Path("data/processed/social_hourly_features.csv")
MARKET_IF_CSV = Path("data/market/market_hourly_with_if.csv")

OUTPUT_DIR = Path("data/lstm")

SEQ_LEN = 24
FUTURE_HORIZON = 4

# =========================
# LOAD DATA
# =========================
social = pd.read_csv(SOCIAL_CSV, parse_dates=["hour_ts"])
market = pd.read_csv(MARKET_IF_CSV, parse_dates=["hour_ts"])
print("social dtype:", social["hour_ts"].dtype)
print("market dtype:", market["hour_ts"].dtype)


# --- Normalize timestamps to UTC (avoid tz mismatch) ---

social["hour_ts"] = social["hour_ts"].dt.tz_localize("UTC")
# market is already UTC-aware, so just leave it
print("social dtype:", social["hour_ts"].dtype)
print("market dtype:", market["hour_ts"].dtype)
# =========================
# MERGE (MARKET-ANCHORED)
# =========================
df = (
    market
    .merge(
        social,
        on=["coin", "hour_ts"],
        how="left"
    )
    .sort_values(["coin", "hour_ts"])
    .reset_index(drop=True)
)

# Fill missing social signals (no messages that hour)
social_cols = [
    "hype_score",
    "coin_reveal_score",
    "outcome_score",
    "noise_score",
    "entropy_mean",
    "msg_velocity",
    "total_msg_count"
]
df[social_cols] = df[social_cols].fillna(0)

print("Merged dataset shape:", df.shape)

# =========================
# DERIVED FEATURES
# =========================
df["social_pressure"] = (
    df["hype_score"] +
    2.0 * df["coin_reveal_score"]
) * df["msg_velocity"]

df["market_stress"] = df["hl_range"].abs() + df["log_return"].abs()

df["if_score_lag1"] = df.groupby("coin")["if_score"].shift(1)
df["if_score_lag3"] = df.groupby("coin")["if_score"].shift(3)
df[["if_score_lag1", "if_score_lag3"]] = df[["if_score_lag1", "if_score_lag3"]].fillna(0)

# =========================
# FUTURE RISK TARGET (CONTINUOUS)
# =========================
df["future_if_max"] = (
    df.groupby("coin")["if_score"]
    .rolling(FUTURE_HORIZON)
    .max()
    .shift(-FUTURE_HORIZON + 1)
    .reset_index(level=0, drop=True)
)
df["future_if_max"] = df["future_if_max"].fillna(0)

# =========================
# FEATURE SET
# =========================
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
# PAST-ONLY NORMALIZATION (NO LEAKAGE)
# =========================
for coin, g in df.groupby("coin"):
    idx = g.index
    for col in FEATURE_COLS:
        mean = g[col].expanding().mean()
        std = g[col].expanding().std().fillna(1)
        df.loc[idx, col] = (g[col] - mean) / (std + 1e-6)

# =========================
# BUILD SEQUENCES
# =========================
X, y = [], []

for coin, g in df.groupby("coin"):
    g = g.reset_index(drop=True)

    if len(g) < SEQ_LEN + FUTURE_HORIZON:
        continue

    for i in range(len(g) - SEQ_LEN - FUTURE_HORIZON):
        X.append(g.loc[i:i + SEQ_LEN - 1, FEATURE_COLS].values)
        y.append(g.loc[i + SEQ_LEN, "future_if_max"])

X = np.array(X, dtype=np.float32)
y = np.array(y, dtype=np.float32)

print("LSTM input shape:", X.shape)
print("Target stats:")
print("  mean:", y.mean())
print("  std :", y.std())
print("  max :", y.max())

# =========================
# SANITY CHECKS
# =========================
assert not np.isnan(X).any(), "NaNs found in X"
assert not np.isnan(y).any(), "NaNs found in y"

# =========================
# SAVE
# =========================
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
np.save(OUTPUT_DIR / "X.npy", X)
np.save(OUTPUT_DIR / "y.npy", y)

print(f"\nSaved LSTM dataset → {OUTPUT_DIR}")
