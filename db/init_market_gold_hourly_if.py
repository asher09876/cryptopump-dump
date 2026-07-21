import duckdb
from pathlib import Path

DB_PATH = Path("C:\\Users\\asher\\Desktop\\projectlive\\data\\telegram.duckdb")

con = duckdb.connect(DB_PATH)

con.execute("""
CREATE TABLE IF NOT EXISTS market_gold_hourly (
    hour_ts TIMESTAMP,
    coin TEXT,
    exchange TEXT,

    open_first DOUBLE,
    high_max DOUBLE,
    low_min DOUBLE,
    close_last DOUBLE,
    volume_sum DOUBLE,

    return DOUBLE,
    log_return DOUBLE,
    hl_range DOUBLE,

    liquidity_bucket TEXT,
    log_volume DOUBLE,
    if_score DOUBLE,

    PRIMARY KEY (coin, exchange, hour_ts)
);
""")

con.close()
print("===== market_gold_hourly initialised")
