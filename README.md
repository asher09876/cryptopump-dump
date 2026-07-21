# crypto fraud detection 
# Crypto fraud Detection with Medallion Architecture

This project builds an early warning system for crypto pump and tail risk events by combining signals from unstructured Telegram data, structured market data, and several machine learning models. The pipeline is organized using a medallion-style data architecture (Bronze → Silver → Gold) and is backed by DuckDB for fast analytical processing.

## What this project does

The system is designed to:

- ingest unstructured Telegram messages and images,
- extract useful signals from text and OCR output,
- combine those social signals with structured market data,
- score risk using LSTM and Isolation Forest models,
- explain model outputs with SHAP,
- expose the results through a Streamlit dashboard.

The goal is to identify periods where social hype and abnormal market behavior suggest elevated risk or a potential pump event.

---

## Architecture overview

### 1. Bronze layer — raw ingestion
At the bronze stage, the project collects raw input data:

- Telegram messages and metadata from channels,
- Telegram images for OCR processing,
- market data such as OHLCV information.

This layer preserves the raw source material before cleaning and enrichment.

### 2. Silver layer — cleaning and feature extraction
The silver layer turns raw inputs into structured features:

- Telegram text is cleaned and normalized,
- OCR is run on images to extract text from screenshots or graphics,
- BERT-based scoring is used to produce probabilities and sentiment-like signals,
- market features such as returns, high-low range, volume-based stress, and log returns are derived.

This layer transforms messy, unstructured data into usable feature tables.

### 3. Gold layer — business-ready analytics
The gold layer aggregates and fuses the best features into production-style tables:

- social signals are aggregated into hourly social features,
- market features are engineered into hourly market features,
- both are fused into a unified feature set,
- risk predictions and explanation outputs are stored for analytics and dashboards.

---

## Core technologies used

### BERT
BERT is used to analyze Telegram text and produce signal scores such as:

- hype probability,
- coin reveal probability,
- outcome reflection,
- noise-related signals,
- entropy-based uncertainty measures.

These BERT-derived features are then used as part of the social signal stack.

### SHAP
SHAP is used to explain model decisions:

- LSTM risk explanations show which features contributed most to the predicted risk,
- Isolation Forest explanations help interpret why a point was flagged as anomalous,
- fusion explainability helps combine social and market factors into a single risk interpretation.

### LSTM A Long Short Term Memory network is used to model time-dependent risk behavior over sequences of hourly features. It helps capture patterns such as:

- escalating social pressure,
- abnormal market stress,
- increasing anomaly signals over time.

The LSTM produces risk estimates that are then stored in the gold tables.

### Isolation Forest
Isolation Forest is used for anomaly detection. It helps detect unusual market or feature behavior that may indicate stress or suspicious activity. Its score is stored as an anomaly-related signal and fused into the overall risk view.

### DuckDB
DuckDB serves as the analytical database backbone for the whole pipeline:

- it stores bronze/silver/gold tables,
- it powers feature engineering and joins,
- it allows fast SQL based transformations over large datasets,
- it is used by the Streamlit dashboard for querying risk and explanation tables.

### Streamlit
A Streamlit dashboard is included to visualize:

- LSTM risk scores,
- Isolation Forest scores,
- key social and market signals,
- SHAP-based explanations.

---

## Data flow

1. Telegram data is fetched and stored in the raw/bronze layer.
2. Telegram text and images are processed into silver-layer features.
3. Social signals are aggregated into hourly features.
4. Structured market data is transformed into market features.
5. The social and market features are fused into a combined gold dataset.
6. ML models generate risk scores and anomaly scores.
7. SHAP explanations are stored and visualized in the dashboard.

---

## Repository structure

- scripts/preprocess: text cleaning, OCR, and Telegram silver processing
- scripts/features: social and market feature engineering
- scripts/db: DuckDB table creation and gold-layer initialization
- scripts/fusion: fusion of social and market signals
- scripts/explainablity: SHAP based explanation pipelines
- scripts/dashboard: Streamlit dashboard app
- data: DuckDB database and supporting data files
- test: experimental or example dashboard versions

---

## Typical workflow

Run the pipeline in this order:

```bash
python scripts/preprocess/process_telegram_images_to_silver1.py
python scripts/features/build_social_gold_hourly_incremental.py
python scripts/features/market_gold.py
python scripts/db/init__fused_gold.py
python scripts/db/fusion_gold.py
```

Then launch the dashboard:

```bash
streamlit run dashboard.py
```

---

## Notes

This repository is an experimental analytics and modeling project for crypto risk monitoring. It combines NLP, time-series modeling, anomaly detection, explainability, and data warehousing concepts into a unified pipeline.

If you want, the next step could be to expand this README with:

- installation instructions,
- dependency lists,
- example SQL queries over DuckDB tables,
- a more detailed architecture diagram.
