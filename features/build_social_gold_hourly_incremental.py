import duckdb
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DB_PATH = PROJECT_ROOT / "data" / "telegram.duckdb"

con = duckdb.connect(DB_PATH)

# -------------------------------------------------
# Find last processed hour per coin
# -------------------------------------------------
con.execute("""
CREATE TEMP TABLE last_gold_hour AS
SELECT
    coin,
    MAX(hour_ts) AS last_hour
FROM social_gold_hourly
GROUP BY coin;
""")

# -------------------------------------------------
# Build new hourly aggregates from SILVER
# -------------------------------------------------
con.execute("""
CREATE TEMP TABLE new_social_gold AS
SELECT
    date_trunc('hour', s.message_ts) AS hour_ts,
    c AS coin,

    AVG(CAST(s.bert_probs ->> 'hype_signal' AS DOUBLE)) AS hype_score,
    AVG(CAST(s.bert_probs ->> 'coin_reveal' AS DOUBLE)) AS coin_reveal_score,
    AVG(CAST(s.bert_probs ->> 'outcome_reflection' AS DOUBLE)) AS outcome_score,
    AVG(CAST(s.bert_probs ->> 'noise' AS DOUBLE)) AS noise_score,

    AVG(s.bert_entropy) AS entropy_mean,
    COUNT(*) AS total_msg_count,
    COUNT(*) / 60.0 AS msg_velocity

FROM telegram_silver s
CROSS JOIN UNNEST(s.detected_coins) AS t(c)
LEFT JOIN last_gold_hour lg
  ON lg.coin = c
WHERE
    s.bert_probs IS NOT NULL
    AND (
        lg.last_hour IS NULL
        OR s.message_ts >= lg.last_hour
    )
GROUP BY c, hour_ts;
""")

# -------------------------------------------------
# UPSERT into GOLD (no duplicates)
# -------------------------------------------------
con.execute("""
INSERT INTO social_gold_hourly
SELECT * FROM new_social_gold
ON CONFLICT (coin, hour_ts) DO UPDATE SET
    hype_score = excluded.hype_score,
    coin_reveal_score = excluded.coin_reveal_score,
    outcome_score = excluded.outcome_score,
    noise_score = excluded.noise_score,
    entropy_mean = excluded.entropy_mean,
    total_msg_count = excluded.total_msg_count,
    msg_velocity = excluded.msg_velocity;
""")

# -------------------------------------------------
# Cleanup
# -------------------------------------------------
con.execute("DROP TABLE last_gold_hour;")
con.execute("DROP TABLE new_social_gold;")

con.close()

print("====== social_gold_hourly updated incrementally")
