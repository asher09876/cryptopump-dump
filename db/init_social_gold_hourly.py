import duckdb
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DB_PATH = PROJECT_ROOT / "data" / "telegram.duckdb"

con = duckdb.connect(DB_PATH)

con.execute("""
CREATE TABLE IF NOT EXISTS social_gold_hourly (
    hour_ts TIMESTAMP,
    coin TEXT,

    hype_score DOUBLE,
    coin_reveal_score DOUBLE,
    outcome_score DOUBLE,
    noise_score DOUBLE,

    entropy_mean DOUBLE,
    total_msg_count INTEGER,
    msg_velocity DOUBLE,

    PRIMARY KEY (coin, hour_ts)
);
""")

con.close()

print(" social_gold_hourly table initialized")
