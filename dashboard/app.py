import streamlit as st
import duckdb
import pandas as pd
import plotly.graph_objects as go
import json

DB_PATH = "data/telegram.duckdb"

st.set_page_config(layout="wide")
st.title("🧠 Pump Early-Warning Dashboard")

con = duckdb.connect(DB_PATH)

# =========================
# LOAD DRIVER DATA (CRITICAL)
# =========================
risk_df = con.execute("""
    SELECT *
    FROM risk_gold
    ORDER BY hour_ts DESC
""").fetch_df()

if risk_df.empty:
    st.error("risk_gold is empty — nothing to display")
    st.stop()

# -------------------------
# COIN SELECTION
# -------------------------
coins = sorted(risk_df["coin"].unique())
coin = st.selectbox("Select coin", coins)

coin_risk = risk_df[risk_df["coin"] == coin].sort_values("hour_ts")

# =========================
# LSTM RISK TIME SERIES
# =========================
st.subheader("📈 LSTM Tail Risk (q90)")

fig_risk = go.Figure()

fig_risk.add_trace(go.Scatter(
    x=coin_risk["hour_ts"],
    y=coin_risk["q90_3h"],
    mode="lines+markers",
    name="LSTM q90 (3h)"
))

fig_risk.update_layout(
    height=300,
    xaxis_title="Time",
    yaxis_title="Risk",
)

st.plotly_chart(fig_risk, use_container_width=True)

# =========================
# IF CONTEXT (SAFE JOIN)
# =========================
if_df = con.execute("""
    SELECT hour_ts, if_score
    FROM fused_gold
    WHERE coin = ?
    ORDER BY hour_ts
""", [coin]).fetch_df()

if not if_df.empty:
    merged = pd.merge_asof(
        coin_risk.sort_values("hour_ts"),
        if_df.sort_values("hour_ts"),
        on="hour_ts",
        direction="backward"
    )

    st.subheader("⚠️ LSTM vs Isolation Forest")

    fig_if = go.Figure()

    fig_if.add_trace(go.Scatter(
        x=merged["hour_ts"],
        y=merged["q90_3h"],
        name="LSTM q90 (3h)",
        line=dict(width=2)
    ))

    fig_if.add_trace(go.Scatter(
        x=merged["hour_ts"],
        y=merged["if_score"],
        name="IF score",
        line=dict(dash="dot")
    ))

    fig_if.update_layout(height=300)
    st.plotly_chart(fig_if, use_container_width=True)
else:
    st.info("No IF data available for this coin")

# =========================
# SHAP EXPLANATION (TOP EVENT)
# =========================
st.subheader("🔍 SHAP Explanation (Top Risk Event)")

shap_df = con.execute("""
    SELECT *
    FROM lstm_explain_gold
    WHERE coin = ?
    ORDER BY hour_ts DESC
    LIMIT 1
""", [coin]).fetch_df()

if shap_df.empty:
    st.info("No SHAP explanation available yet")
else:
    shap_json = json.loads(shap_df.iloc[0]["feature_importance"])
    shap_vis = (
        pd.DataFrame(shap_json.items(), columns=["feature", "importance"])
        .sort_values("importance", ascending=True)
    )

    fig_shap = go.Figure(go.Bar(
        x=shap_vis["importance"],
        y=shap_vis["feature"],
        orientation="h"
    ))

    fig_shap.update_layout(
        height=400,
        xaxis_title="Impact on LSTM risk",
        yaxis_title=""
    )

    st.plotly_chart(fig_shap, use_container_width=True)
