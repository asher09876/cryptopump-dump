import duckdb
from pathlib import Path

# =========================
# CONFIG
# =========================
DB_PATH = Path("data/telegram.duckdb")

# =========================
# CONNECT
# =========================
con = duckdb.connect(DB_PATH)

# =========================
# CREATE TABLE
# =========================
con.execute("""
CREATE TABLE IF NOT EXISTS lstm_explain_gold (
    hour_ts TIMESTAMP,
    coin TEXT,
    feature_importance JSON,
    PRIMARY KEY (hour_ts, coin)
);
""")

print("✓ Table lstm_explain_gold is ready")

# =========================
# CLOSE
# =========================
con.close()
