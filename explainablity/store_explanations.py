import duckdb
import json

db = duckdb.connect("data/telegram.duckdb")

db.execute("""
CREATE TABLE IF NOT EXISTS explain_gold (
    hour_ts TIMESTAMP,
    coin TEXT,
    bert_explain JSON,
    if_explain JSON,
    lstm_explain JSON,
    fusion_explain JSON,
    PRIMARY KEY (coin, hour_ts)
)
""")

def store_explain(hour_ts, coin, bert, ifx, lstm, fusion):
    db.execute("""
        INSERT OR REPLACE INTO explain_gold
        VALUES (?, ?, ?, ?, ?, ?)
    """, [
        hour_ts,
        coin,
        json.dumps(bert),
        json.dumps(ifx),
        json.dumps(lstm),
        json.dumps(fusion)
    ])
db.close()