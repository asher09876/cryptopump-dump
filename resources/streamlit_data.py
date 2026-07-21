import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Coins to generate data for
coins = ['DOGE', 'SHIB', 'PEPE', 'SOL', 'ADA', '0G']

# Start and end dates
start_date = pd.Timestamp('2025-12-10 00:00:00+00:00')
end_date = pd.Timestamp('2025-12-20 23:00:00+00:00')

# Generate hourly timestamps
timestamps = pd.date_range(start=start_date, end=end_date, freq='H')

# Function to generate synthetic OHLCV data
def generate_ohlcv(coin, timestamps):
    # Starting prices (approximate from existing data)
    start_prices = {'DOGE': 0.26, 'SHIB': 0.00002, 'PEPE': 0.00001, 'SOL': 150, 'ADA': 0.5, '0G': 2.7}
    start_price = start_prices[coin]
    
    # Parameters for log returns (normal distribution)
    mu = 0.0001  # drift
    sigma = 0.02  # volatility
    
    log_returns = np.random.normal(mu, sigma, len(timestamps))
    prices = [start_price]
    for lr in log_returns[:-1]:
        prices.append(prices[-1] * np.exp(lr))
    
    # Generate OHLC from prices
    data = []
    for i, ts in enumerate(timestamps):
        close = prices[i]
        # Simulate open as previous close
        open_p = prices[i-1] if i > 0 else close
        # High and low around close
        volatility = 0.01
        high = close * (1 + np.random.uniform(0, volatility))
        low = close * (1 - np.random.uniform(0, volatility))
        # Volume
        volume = np.random.uniform(1e7, 1e9) if coin in ['DOGE', 'SOL'] else np.random.uniform(1e10, 1e12)
        
        # Compute return and log_return
        ret = (close - open_p) / open_p if open_p != 0 else 0
        log_ret = np.log(close / open_p) if open_p > 0 else 0
        hl_range = (high - low) / open_p if open_p != 0 else 0
        log_volume = np.log(volume) if volume > 0 else 0
        
        # Liquidity bucket (simplified)
        liquidity = 'high' if volume > 5e8 else 'medium' if volume > 1e8 else 'low'
        
        # IF score (anomaly score, random for synthetic)
        if_score = np.random.normal(0, 1)
        
        # LSTM predicted (synthetic)
        lstm_predicted = close * (1 + np.random.normal(0, 0.01))
        
        data.append({
            'hour_ts': ts,
            'coin': coin,
            'exchange': 'binance',
            'open_first': open_p,
            'high_max': high,
            'low_min': low,
            'close_last': close,
            'volume_sum': volume,
            'return': ret,
            'log_return': log_ret,
            'hl_range': hl_range,
            'liquidity_bucket': liquidity,
            'log_volume': log_volume,
            'if_score': if_score,
            'lstm_predicted': lstm_predicted
        })
    
    return data

# Generate data for all coins
all_data = []
for coin in coins:
    all_data.extend(generate_ohlcv(coin, timestamps))

# Create DataFrame
df = pd.DataFrame(all_data)

# Save to CSV
df.to_csv('test/synthetic_market_data.csv', index=False)

print("Synthetic data generated and saved to test/synthetic_market_data.csv")