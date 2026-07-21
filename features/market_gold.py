# scripts/gold/populate_market_gold_features.py

import duckdb
import numpy as np
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DB_PATH = PROJECT_ROOT / "data" / "telegram.duckdb"

con = duckdb.connect(DB_PATH)

# Watermark
con.execute("""
CREATE TEMP TABLE market_watermark AS
SELECT coin, exchange, MAX(hour_ts) AS last_hour
FROM market_gold_features_hourly
GROUP BY coin, exchange;
""")

df = con.execute("""
SELECT
    s.coin,
    s.exchange,
    s.hour_ts,
    s.close,
    s.high,
    s.low,
    s.volume
FROM market_silver_hourly s
LEFT JOIN market_watermark w
  ON s.coin = w.coin AND s.exchange = w.exchange
WHERE w.last_hour IS NULL OR s.hour_ts > w.last_hour
ORDER BY s.coin, s.exchange, s.hour_ts
""").df()

if df.empty:
    print("✓ No new market data")
    con.close()
    exit()

df["log_return"] = np.log(
    df["close"] / df.groupby(["coin", "exchange"])["close"].shift(1)
)
df["hl_range"] = (df["high"] - df["low"]) / df["close"]
df["volume_z"] = df.groupby(["coin", "exchange"])["volume"].transform(
    lambda x: (x - x.mean()) / (x.std() + 1e-6)
)
df["market_stress"] = df["hl_range"].abs() + df["volume_z"].abs()
df = df.dropna()

con.register("df", df)

con.execute("""
INSERT INTO market_gold_features_hourly
SELECT
    coin, exchange, hour_ts,
    log_return, hl_range, volume_z, market_stress
FROM df
ON CONFLICT (coin, exchange, hour_ts) DO UPDATE SET
    log_return = excluded.log_return,
    hl_range = excluded.hl_range,
    volume_z = excluded.volume_z,
    market_stress = excluded.market_stress;
""")

ans1= con.execute("SELECT COUNT(*) FROM market_gold_features_hourly;")
print(" Total rows in market_gold_features_hourly:", ans1.fetchall())
ans2 = con.execute("SELECT * FROM market_gold_features_hourly ORDER BY hour_ts DESC LIMIT 5;")
print(" Latest 5 rows in market_gold_features_hourly:", ans2.fetchall())
con.close()
print(f"market_gold_features_hourly updated ({len(df)})")
