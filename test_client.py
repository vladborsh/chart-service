#!/usr/bin/env python3
"""
Example client for testing the chart service API
"""

import requests
import json
import base64
from datetime import datetime, timedelta

# Generate sample OHLCV data
def generate_sample_data(num_candles=100):
    """Generate sample OHLCV data for testing"""
    data = []
    base_price = 1.0500
    start_time = datetime.now() - timedelta(hours=num_candles)
    
    for i in range(num_candles):
        timestamp = start_time + timedelta(hours=i)
        open_price = base_price + (i * 0.0001)
        high_price = open_price + 0.0005
        low_price = open_price - 0.0003
        close_price = open_price + 0.0002
        
        data.append({
            "timestamp": timestamp.isoformat(),
            "open": round(open_price, 5),
            "high": round(high_price, 5),
            "low": round(low_price, 5),
            "close": round(close_price, 5),
            "volume": 1000
        })
    
    return data


def test_chart_generation():
    """Test chart generation endpoint"""
    
    # Prepare request with full options
    chart_request_full = {
        "symbol": "EURUSD",
        "data": generate_sample_data(100),
        "signal_data": {
            "entry_price": 1.0600,
            "stop_loss": 1.0550,
            "take_profit": 1.0700,
            "signal_type": "long"
        },
        "strategy_params": {
            "bb_window": 20,
            "bb_std": 2.0,
            "vwap_std": 2.0
        }
    }
    
    # Minimal request (optional fields omitted)
    chart_request_minimal = {
        "symbol": "GBPUSD",
        "data": generate_sample_data(100)
    }
    
    print("Testing Chart Service API...")
    print("=" * 60)
    
    # Test 1: Health check
    print("\n1. Testing health check endpoint...")
    try:
        response = requests.get("http://localhost:8000/health")
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.json()}")
    except Exception as e:
        print(f"   Error: {e}")
        return
    
    # Test 2: Generate chart as base64
    print("\n2. Testing chart generation (base64)...")
    try:
        response = requests.post(
            "http://localhost:8000/chart/generate",
            json=chart_request_full
        )
        print(f"   Status: {response.status_code}")
        result = response.json()
        
        if result["success"]:
            print(f"   Success! Chart generated at {result['generated_at']}")
            
            # Save chart to file
            chart_bytes = base64.b64decode(result["chart_base64"])
            filename = "test_chart_base64.png"
            with open(filename, "wb") as f:
                f.write(chart_bytes)
            print(f"   Chart saved to {filename}")
        else:
            print(f"   Error: {result['error']}")
    except Exception as e:
        print(f"   Error: {e}")
    
    # Test 3: Generate chart as direct image
    print("\n3. Testing chart generation (direct image)...")
    try:
        response = requests.post(
            "http://localhost:8000/chart/generate/image",
            json=chart_request_full
        )
        print(f"   Status: {response.status_code}")
        
        if response.status_code == 200:
            filename = "test_chart_image.png"
            with open(filename, "wb") as f:
                f.write(response.content)
            print(f"   Success! Chart saved to {filename}")
        else:
            print(f"   Error: {response.text}")
    except Exception as e:
        print(f"   Error: {e}")
    
    # Test 4: Generate minimal chart (no signal data)
    print("\n4. Testing minimal chart generation (no signal)...")
    try:
        response = requests.post(
            "http://localhost:8000/chart/generate/image",
            json=chart_request_minimal
        )
        print(f"   Status: {response.status_code}")
        
        if response.status_code == 200:
            filename = "test_chart_minimal.png"
            with open(filename, "wb") as f:
                f.write(response.content)
            print(f"   Success! Minimal chart saved to {filename}")
        else:
            print(f"   Error: {response.text}")
    except Exception as e:
        print(f"   Error: {e}")
    
    print("\n" + "=" * 60)
    print("Testing complete!")


if __name__ == "__main__":
    test_chart_generation()
