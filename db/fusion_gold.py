import duckdb

con = duckdb.connect("data/telegram.duckdb")

con.execute("""
CREATE TABLE IF NOT EXISTS fusion_gold (
    hour_ts TIMESTAMP NOT NULL,
    coin TEXT NOT NULL,

    q90_3h DOUBLE,
    if_score DOUBLE,
    social_pressure DOUBLE,

    fusion_risk DOUBLE,

    PRIMARY KEY (coin, hour_ts)
);
""")

con.execute("""
CREATE INDEX IF NOT EXISTS idx_fusion_gold_coin_ts
ON fusion_gold (coin, hour_ts);
""")

print("fusion_gold initialised")


con.execute("""
INSERT OR REPLACE INTO fusion_gold
SELECT
    r.hour_ts,
    r.coin,

    r.q90_3h,
    f.if_score,
    f.social_pressure,

    0.5 * r.q90_3h
  + 0.3 * f.if_score
  + 0.2 * f.social_pressure AS fusion_risk

FROM risk_gold r
JOIN fused_gold f
  ON r.coin = f.coin
 AND r.hour_ts = f.hour_ts;
""")

print("fusion_gold populated")
con.close()
