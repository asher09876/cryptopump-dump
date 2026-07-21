import duckdb
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DB_PATH = PROJECT_ROOT / "data" / "telegram.duckdb"

con = duckdb.connect(DB_PATH)

con.execute("""
DROP TABLE IF EXISTS model_gold_lstm_predictions;
   
""")
con.execute("""SELECT COUNT(*) FROM model_gold_lstm_predictions;""").fetchall()
con.close()
print(" model_gold_lstm_predictions initialized")
