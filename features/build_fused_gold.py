import duckdb
import pandas as pd

DB_PATH = "data/telegram.duckdb"

# -------------------------
# DB CONNECTION
# -------------------------
def get_db():
    return duckdb.connect(DB_PATH, read_only=False)

# -------------------------
# MAIN PIPELINE
# -------------------------
def populate_fused_gold():
    db = get_db()

    # 1️ Find last processed timestamp
    last_ts = db.execute("""
        SELECT MAX(hour_ts) FROM fused_gold
    """).fetchone()[0]

    if last_ts is None:
        print("====== No existing fused_gold data → full backfill")
        ts_filter = ""
        params = []
    else:
        print(f"====== Incremental run after {last_ts}")
        ts_filter = "WHERE m.hour_ts > ?"
        params = [last_ts]

    # 2️ Load NEW market + social data
    query = f"""
        SELECT
            m.hour_ts,
            m.coin,

            -- market
            m.return,
            m.log_return,
            m.hl_range,
            m.if_score,

            -- social (may be NULL)
            s.hype_score,
            s.coin_reveal_score,
            s.entropy_mean,
            s.msg_velocity

        FROM market_gold_hourly m
        LEFT JOIN social_gold_hourly s
            ON m.coin = s.coin
           AND m.hour_ts = s.hour_ts
        {ts_filter}
        ORDER BY m.coin, m.hour_ts
    """

    df = db.execute(query, params).fetch_df()

    # 🔧 Rename reserved keyword column
    df = df.rename(columns={"return": "ret"})

    if df.empty:
        print("======= No new data to fuse")
    else:
        # 6️ Insert row-by-row (safe + idempotent)
        insert_sql = """
            INSERT OR REPLACE INTO fused_gold (
                hour_ts,
                coin,
                hype_score,
                coin_reveal_score,
                entropy_mean,
                msg_velocity,
                social_pressure,
                "return",
                log_return,
                hl_range,
                market_stress,
                if_score,
                if_score_lag1,
                if_score_lag3
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """

        rows = [
            (
                r.hour_ts,
                r.coin,
                r.hype_score,
                r.coin_reveal_score,
                r.entropy_mean,
                r.msg_velocity,
                r.social_pressure,
                r.ret,          # renamed column
                r.log_return,
                r.hl_range,
                r.market_stress,
                r.if_score,
                r.if_score_lag1,
                r.if_score_lag3,
            )
            for r in df.itertuples(index=False)
        ]

        db.executemany(insert_sql, rows)

        print(f" Inserted / updated {len(rows):,} fused rows")

    # 7️ UPDATE EXISTING ROWS WHERE SOCIAL DATA BECAME AVAILABLE LATER
    print(" Checking for existing rows that now have social data...")

    # Find fused_gold rows with zero social features that now have social data
    update_query = """
        SELECT
            f.hour_ts,
            f.coin,
            s.hype_score,
            s.coin_reveal_score,
            s.entropy_mean,
            s.msg_velocity,
            (s.hype_score + 2.0 * s.coin_reveal_score) * s.msg_velocity as social_pressure
        FROM fused_gold f
        JOIN social_gold_hourly s ON f.coin = s.coin AND f.hour_ts = s.hour_ts
        WHERE f.hype_score = 0.0  -- Only update rows that were missing social data
          AND s.hype_score > 0.0  -- And now have social data
    """

    update_df = db.execute(update_query).fetch_df()

    if not update_df.empty:
        update_sql = """
            UPDATE fused_gold
            SET hype_score = ?,
                coin_reveal_score = ?,
                entropy_mean = ?,
                msg_velocity = ?,
                social_pressure = ?
            WHERE hour_ts = ? AND coin = ?
        """

        update_rows = [
            (
                r.hype_score,
                r.coin_reveal_score,
                r.entropy_mean,
                r.msg_velocity,
                r.social_pressure,
                r.hour_ts,
                r.coin
            )
            for r in update_df.itertuples(index=False)
        ]

        db.executemany(update_sql, update_rows)
        print(f" Updated {len(update_rows):,} existing rows with newly available social data")
    else:
        print(" No existing rows needed social data updates")

    db.close()

# -------------------------
# ENTRY POINT
# -------------------------
if __name__ == "__main__":
    populate_fused_gold()
