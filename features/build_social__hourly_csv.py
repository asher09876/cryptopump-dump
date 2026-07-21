import duckdb
import pandas as pd
from pathlib import Path

# =========================
# PATHS
# =========================
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DB_PATH = PROJECT_ROOT / "data" / "telegram.duckdb"

OUTPUT_DIR = PROJECT_ROOT / "data" / "processed"
OUTPUT_CSV = OUTPUT_DIR / "social_hourly_features.csv"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# =========================
# CONNECT
# =========================
con = duckdb.connect(DB_PATH)

# =========================
# LOAD GOLD TABLE
# =========================
query = """
SELECT
    hour_ts,
    coin,
    hype_score,
    coin_reveal_score,
    outcome_score,
    noise_score,
    entropy_mean,
    total_msg_count,
    msg_velocity
FROM social_gold_hourly
ORDER BY coin, hour_ts
"""

df = con.execute(query).df()

con.close()

# =========================
# SAVE CSV
# =========================
df.to_csv(OUTPUT_CSV, index=False)

print("✓ Exported social_gold_hourly to CSV")
print(f"→ {OUTPUT_CSV}")
print("Shape:", df.shape)
print("\nSample:")
print(df.head())
