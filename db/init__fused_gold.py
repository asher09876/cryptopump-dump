import duckdb
from pathlib import Path

DB_PATH = Path("data/telegram.duckdb")
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

con = duckdb.connect(DB_PATH)

con.execute("""
CREATE TABLE IF NOT EXISTS fused_gold (
    hour_ts TIMESTAMP NOT NULL,
    coin TEXT NOT NULL,

    -- Social signals
    hype_score DOUBLE,
    coin_reveal_score DOUBLE,
    entropy_mean DOUBLE,
    msg_velocity DOUBLE,

    -- Derived social
    social_pressure DOUBLE,

    -- Market signals
    return DOUBLE,
    log_return DOUBLE,
    hl_range DOUBLE,
    market_stress DOUBLE,

    -- Anomaly features
    if_score DOUBLE,
    if_score_lag1 DOUBLE,
    if_score_lag3 DOUBLE,

    PRIMARY KEY (coin, hour_ts)
);
""")

con.execute("""
CREATE TABLE IF NOT EXISTS risk_gold (
    hour_ts TIMESTAMP NOT NULL,
    coin TEXT NOT NULL,

    -- Median risk
    q50_1h DOUBLE,
    q50_3h DOUBLE,
    q50_6h DOUBLE,

    -- Tail risk
    q90_1h DOUBLE,
    q90_3h DOUBLE,
    q90_6h DOUBLE,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (coin, hour_ts)
);
""")

con.execute("""
CREATE INDEX IF NOT EXISTS idx_fused_gold_coin_ts
ON fused_gold (coin, hour_ts);
""")

con.execute("""
CREATE INDEX IF NOT EXISTS idx_risk_gold_coin_ts
ON risk_gold (coin, hour_ts);
""")

print(con.execute("SHOW TABLES").fetchall())
con.close()
print("===== fused_gold and risk_gold initialised")