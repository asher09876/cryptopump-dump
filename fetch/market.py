import ccxt
import json
import time
import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta, timezone

# =========================
# CONFIG
# =========================
SOCIAL_JSONL = Path("data/processed/labeled_messages_bert1.jsonl")
OUTPUT_DIR = Path("data/market/raw_ohlcv")

TIMEFRAME = "1m"
LOOKBACK_DAYS = 60
RATE_LIMIT_SLEEP = 0.25

EXCHANGES = [
    ("binance", ccxt.binance),
    ("bybit", ccxt.bybit),
    ("kucoin", ccxt.kucoin),
]

# =========================
# LOAD COINS
# =========================
coins = set()
with SOCIAL_JSONL.open("r", encoding="utf-8") as f:
    for line in f:
        if not line.strip():
            continue
        msg = json.loads(line)
        for c in msg.get("coins", []):
            coins.add(c.upper())

coins = sorted(coins)
print(f"Found {len(coins)} unique coins in social data")

# =========================
# INIT EXCHANGES
# =========================
exchanges = {}
for name, cls in EXCHANGES:
    ex = cls({"enableRateLimit": True})
    ex.load_markets()
    exchanges[name] = ex

# =========================
# FETCH FUNCTION
# =========================
def fetch_ohlcv(exchange, symbol, since_ms):
    rows = []
    since = since_ms

    while True:
        try:
            batch = exchange.fetch_ohlcv(
                symbol,
                timeframe=TIMEFRAME,
                since=since,
                limit=1000
            )
        except Exception as e:
            print(f"[ERROR] {exchange.id} {symbol}: {e}")
            break

        if not batch:
            break

        rows.extend(batch)
        since = batch[-1][0] + 1

        if len(batch) < 1000:
            break

        time.sleep(RATE_LIMIT_SLEEP)

    return rows

# =========================
# MAIN LOOP
# =========================
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

end_time = datetime.now(timezone.utc)
start_time = end_time - timedelta(days=LOOKBACK_DAYS)
since_ms = int(start_time.timestamp() * 1000)

for coin in coins:
    symbol = f"{coin}/USDT"
    fetched = False

    for ex_name, ex in exchanges.items():
        if symbol not in ex.markets:
            continue

        print(f"[FETCHING] {symbol} from {ex_name}")

        rows = fetch_ohlcv(ex, symbol, since_ms)

        if not rows:
            print(f"[EMPTY] {symbol} on {ex_name}")
            continue

        df = pd.DataFrame(
            rows,
            columns=["timestamp", "open", "high", "low", "close", "volume"]
        )

        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)
        df["coin"] = coin
        df["exchange"] = ex_name

        out_path = OUTPUT_DIR / f"{coin}_{ex_name}_1m.csv"
        df.to_csv(out_path, index=False)

        print(f"[SAVED] {out_path} ({len(df)} rows)")
        fetched = True
        break

    if not fetched:
        print(f"[SKIP] {coin} not found on any exchange")

    if not fetched:
        print(f"[SKIP] {coin} not found on any exchange")
