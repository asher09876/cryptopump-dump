import duckdb

# =========================
# CONFIG
# =========================
DB_PATH = "data/telegram.duckdb"

# =========================
# APPLY SOCIAL HYPE BOOST TO EXISTING DATA
# =========================
def apply_social_boost():
    con = duckdb.connect(DB_PATH)

    # Apply social hype boost using lookback 3 hours max hype to all existing risk_gold data
    con.execute("""
        WITH recent_hype AS (
            SELECT
                coin,
                hour_ts,
                MAX(hype_score) OVER (
                    PARTITION BY coin
                    ORDER BY hour_ts
                    ROWS BETWEEN 3 PRECEDING AND CURRENT ROW
                ) AS max_hype_last_3h
            FROM fused_gold
        )
        UPDATE risk_gold r
        SET
            q50_1h  = q50_1h  * (1 + 0.6 * h.max_hype_last_3h),
            q50_3h  = q50_3h  * (1 + 0.7 * h.max_hype_last_3h),
            q50_6h  = q50_6h  * (1 + 0.8 * h.max_hype_last_3h),
            q90_1h  = q90_1h  * (1 + 0.8 * h.max_hype_last_3h),
            q90_3h  = q90_3h  * (1 + 0.9 * h.max_hype_last_3h),
            q90_6h  = q90_6h  * (1 + 1.0 * h.max_hype_last_3h)
        FROM recent_hype h
        WHERE r.coin = h.coin AND r.hour_ts = h.hour_ts
    """)

    con.close()
    print("===== Applied social hype boost to all existing risk_gold data")

# =========================
# RUN
# =========================
if __name__ == "__main__":
    apply_social_boost()