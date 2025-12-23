# Trading Chart Service

A standalone microservice for generating trading signal charts with technical indicators. This service provides a REST API for rendering charts with candlesticks, Bollinger Bands, VWAP, and signal levels (entry, stop loss, take profit).

## Features

- **Chart Rendering**: Generate professional trading charts with candlesticks and technical indicators
- **Technical Indicators**: Bollinger Bands and VWAP with configurable parameters
- **Signal Visualization**: Display entry price, stop loss, and take profit levels
- **REST API**: FastAPI-based API with both base64 and direct image responses
- **Containerized**: Docker and Podman support for easy deployment
- **Health Checks**: Built-in health check endpoints

## Architecture

The service consists of two main components:

1. **ChartRenderer** (`chart_renderer.py`): Core chart generation logic
   - Calculates technical indicators (Bollinger Bands, VWAP)
   - Renders charts using matplotlib and mplfinance
   - Returns chart images as bytes

2. **API Server** (`api_server.py`): REST API wrapper
   - FastAPI-based HTTP server
   - Endpoints for chart generation
   - Returns charts as base64 or PNG images

## API Endpoints

### `GET /`
Root endpoint with API information

### `GET /health`
Health check endpoint

### `POST /chart/generate`
Generate a chart and return as base64-encoded JSON

**Request Body:**
```json
{
  "symbol": "EURUSD",
  "data": [
    {
      "timestamp": "2025-12-23T10:00:00Z",
      "open": 1.0500,
      "high": 1.0520,
      "low": 1.0490,
      "close": 1.0510,
      "volume": 1000
    }
  ],
  "signal_data": {  // Optional
    "entry_price": 1.0510,
    "stop_loss": 1.0490,
    "take_profit": 1.0550,
    "signal_type": "long"
  },
  "strategy_params": {  // Optional (defaults: bb_window=20, bb_std=2.0, vwap_std=2.0)
    "bb_window": 20,
    "bb_std": 2.0,
    "vwap_std": 2.0
  }
}
```

**Response:**
```json
{
  "success": true,
  "chart_base64": "iVBORw0KGgoAAAANS...",
  "generated_at": "2025-12-23T10:00:00"
}
```

### `POST /chart/generate/image`
Generate a chart and return as PNG image directly

Same request format as above, but returns PNG image with `Content-Type: image/png`

## Installation

### Local Development

1. **Install dependencies:**
```bash
cd chart-service
pip install -r requirements.txt
```

2. **Run the server:**
```bash
python api_server.py
```

The API will be available at `http://localhost:8000`

### Docker Deployment

1. **Build the image:**
```bash
docker build -t chart-service:latest .
```

2. **Run with Docker:**
```bash
docker run -d \
  --name chart-service \
  -p 8000:8000 \
  chart-service:latest
```

3. **Or use Docker Compose:**
```bash
docker-compose up -d
```

### Podman Deployment

1. **Build with Podman:**
```bash
podman build -t chart-service:latest .
```

2. **Run with Podman:**
```bash
podman run -d \
  --name chart-service \
  -p 8000:8000 \
  chart-service:latest
```

3. **Or use Makefile shortcuts:**
```bash
make build    # Build image
make run      # Run container
make logs     # View logs
make health   # Check health
make stop     # Stop container
make clean    # Clean up
```

## Usage Examples

### Python Client

```python
import requests
import base64
from io import BytesIO
from PIL import Image

# Minimal chart request (just price data)
chart_request = {
    "symbol": "EURUSD",
    "data": [
        # Your OHLCV data here
    ]
}

# Full chart request with signal and custom params
chart_request_with_signal = {
    "symbol": "EURUSD",
    "data": [
        # Your OHLCV data here
    ],
    "signal_data": {
        "entry_price": 1.0510,
        "stop_loss": 1.0490,
        "take_profit": 1.0550,
        "signal_type": "long"
    },
    "strategy_params": {
        "bb_window": 20,
        "bb_std": 2.0,
        "vwap_std": 2.0
    }
}

# Get chart as base64
response = requests.post(
    "http://localhost:8000/chart/generate",
    json=chart_request
)
data = response.json()
if data["success"]:
    chart_bytes = base64.b64decode(data["chart_base64"])
    # Save or use the chart
    with open("chart.png", "wb") as f:
        f.write(chart_bytes)

# Or get chart as direct image
response = requests.post(
    "http://localhost:8000/chart/generate/image",
    json=chart_request
)
with open("chart.png", "wb") as f:
    f.write(response.content)
```

### cURL

```bash
# Health check
curl http://localhost:8000/health

# Generate chart (save to file)
curl -X POST http://localhost:8000/chart/generate/image \
  -H "Content-Type: application/json" \
  -d @chart_request.json \
  --output chart.png
```

## Configuration

Environment variables:
- `LOG_LEVEL`: Logging level (default: INFO)
- `PYTHONUNBUFFERED`: Set to 1 for unbuffered output

Chart renderer settings (in `chart_renderer.py`):
- `candles_to_show`: Number of candles to display (default: 100)
- `figure_size`: Chart dimensions in inches (default: 12x8)
- `dpi`: Image resolution (default: 100)

## Health Monitoring

The service includes health check endpoints for container orchestration:

```bash
# Docker health check
docker inspect --format='{{.State.Health.Status}}' chart-service

# Manual health check
curl http://localhost:8000/health
```

## Logs

View container logs:
```bash
# Docker
docker logs -f chart-service

# Podman
podman logs -f chart-service

# Or with make
make logs
```

## Development

### Project Structure
```
chart-service/
├── chart_renderer.py      # Core chart rendering logic
├── api_server.py          # FastAPI REST API
├── requirements.txt       # Python dependencies
├── Dockerfile            # Docker configuration
├── docker-compose.yml    # Docker Compose configuration
├── Makefile             # Podman shortcuts
└── README.md            # This file
```

### Testing

Test the API endpoints:
```bash
# Test health
curl http://localhost:8000/health

# Test chart generation (with sample data)
python test_client.py
```

## Troubleshooting

### Charts not generating
- Check logs for matplotlib/mplfinance errors
- Ensure all required columns (timestamp, open, high, low, close) are present
- Verify timestamp format is ISO 8601 compatible

### Container fails to start
- Check port 8000 is not already in use
- Verify Docker/Podman is running
- Check logs with `docker logs chart-service`

### API returns 500 errors
- Check input data format matches schema
- Ensure data has enough points (at least 20+ for indicators)
- Verify timestamps are properly formatted

## License

Part of the mean-reversion-strat trading system.
