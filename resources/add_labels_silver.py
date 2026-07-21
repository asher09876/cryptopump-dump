import duckdb
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / "data" / "telegram.duckdb"

con = duckdb.connect(DB_PATH)

alter_statements = [
    "ALTER TABLE telegram_silver ADD COLUMN IF NOT EXISTS gpt_label TEXT;",
    "ALTER TABLE telegram_silver ADD COLUMN IF NOT EXISTS gpt_reason TEXT;",
    "ALTER TABLE telegram_silver ADD COLUMN IF NOT EXISTS bert_probs JSON;",
    "ALTER TABLE telegram_silver ADD COLUMN IF NOT EXISTS bert_entropy DOUBLE;",
    "ALTER TABLE telegram_silver ADD COLUMN IF NOT EXISTS bert_label TEXT;",
]

for stmt in alter_statements:
    con.execute(stmt)

con.close()

print("[✓] telegram_silver schema updated with GPT + BERT columns")
