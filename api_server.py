#!/usr/bin/env python3
"""
Chart API Server

FastAPI-based REST API wrapper for the chart rendering service.
Provides endpoints for generating trading signal charts.
"""

import logging
import base64
from typing import Dict, Any, Optional
from datetime import datetime

from fastapi import FastAPI, HTTPException, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
import pandas as pd
import uvicorn

from chart_renderer import ChartRenderer

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Trading Chart API",
    description="API for generating trading signal charts with technical indicators",
    version="1.0.0"
)

# Initialize chart renderer
chart_renderer = ChartRenderer()


# Request models
class SignalData(BaseModel):
    """Signal information for chart generation"""
    entry_price: float = Field(..., description="Entry price for the signal")
    stop_loss: float = Field(..., description="Stop loss price")
    take_profit: float = Field(..., description="Take profit price")
    signal_type: str = Field(..., description="Signal type (long/short)")


class StrategyParams(BaseModel):
    """Strategy parameters for indicator calculation"""
    bb_window: int = Field(20, description="Bollinger Bands window")
    bb_std: float = Field(2.0, description="Bollinger Bands standard deviation")
    vwap_std: float = Field(2.0, description="VWAP standard deviation")


class ChartRequest(BaseModel):
    """Chart generation request"""
    symbol: str = Field(..., description="Trading symbol")
    data: list = Field(..., description="OHLCV data as list of dicts with timestamp, open, high, low, close, volume")
    signal_data: Optional[SignalData] = None
    strategy_params: Optional[StrategyParams] = None


class ChartResponse(BaseModel):
    """Chart generation response"""
    success: bool
    chart_base64: Optional[str] = None
    error: Optional[str] = None
    generated_at: str


# API endpoints
@app.get("/")
def root():
    """Root endpoint - API information"""
    return {
        "service": "Trading Chart API",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "health": "/health",
            "generate_chart": "/chart/generate (POST)",
            "generate_chart_image": "/chart/generate/image (POST)"
        }
    }


@app.get("/health")
def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat()
    }


@app.post("/chart/generate", response_model=ChartResponse)
async def generate_chart(request: ChartRequest):
    """
    Generate a trading chart and return as base64-encoded image
    
    Returns:
        JSON with base64-encoded chart image
    """
    try:
        logger.info(f"Generating chart for {request.symbol}")
        
        # Convert data list to DataFrame
        df = pd.DataFrame(request.data)
        
        # Ensure proper column names
        required_columns = ['timestamp', 'open', 'high', 'low', 'close']
        for col in required_columns:
            if col not in df.columns:
                raise HTTPException(
                    status_code=400,
                    detail=f"Missing required column: {col}"
                )
        
        # Set datetime index
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df.set_index('timestamp', inplace=True)
        df.sort_index(inplace=True)
        
        # Prepare signal data dict
        signal_dict = {
            'entry_price': request.signal_data.entry_price,
            'stop_loss': request.signal_data.stop_loss,
            'take_profit': request.signal_data.take_profit,
            'signal_type': request.signal_data.signal_type
        }
        
        # Prepare strategy params dict
        strategy_dict = {
            'bb_window': request.strategy_params.bb_window,
            'bb_std': request.strategy_params.bb_std,
            'vwap_std': request.strategy_params.vwap_std
        }
        
        # Generate chart
        chart_bytes = chart_renderer.generate_chart(
            data=df,
            signal_data=signal_dict,
            strategy_params=strategy_dict,
            symbol=request.symbol
        )
        
        if chart_bytes is None:
            return ChartResponse(
                success=False,
                error="Failed to generate chart",
                generated_at=datetime.now().isoformat()
            )
        
        # Encode to base64
        chart_base64 = base64.b64encode(chart_bytes).decode('utf-8')
        
        logger.info(f"Successfully generated chart for {request.symbol}")
        return ChartResponse(
            success=True,
            chart_base64=chart_base64,
            generated_at=datetime.now().isoformat()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating chart: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/chart/generate/image")
async def generate_chart_image(request: ChartRequest):
    """
    Generate a trading chart and return as PNG image
    
    Returns:
        PNG image directly
    """
    try:
        logger.info(f"Generating chart image for {request.symbol}")
        
        # Convert data list to DataFrame
        df = pd.DataFrame(request.data)
        
        # Ensure proper column names
        required_columns = ['timestamp', 'open', 'high', 'low', 'close']
        for col in required_columns:
            if col not in df.columns:
                raise HTTPException(
                    status_code=400,
                    detail=f"Missing required column: {col}"
                )
        
        # Set datetime index
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df.set_index('timestamp', inplace=True)
        df.sort_index(inplace=True)
        
        # Prepare signal data dict
        signal_dict = {
            'entry_price': request.signal_data.entry_price,
            'stop_loss': request.signal_data.stop_loss,
            'take_profit': request.signal_data.take_profit,
            'signal_type': request.signal_data.signal_type
        }
        
        # Prepare strategy params dict
        strategy_dict = {
            'bb_window': request.strategy_params.bb_window,
            'bb_std': request.strategy_params.bb_std,
            'vwap_std': request.strategy_params.vwap_std
        }
        
        # Generate chart
        chart_bytes = chart_renderer.generate_chart(
            data=df,
            signal_data=signal_dict,
            strategy_params=strategy_dict,
            symbol=request.symbol
        )
        
        if chart_bytes is None:
            raise HTTPException(
                status_code=500,
                detail="Failed to generate chart"
            )
        
        logger.info(f"Successfully generated chart image for {request.symbol}")
        return Response(content=chart_bytes, media_type="image/png")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating chart image: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    # Run server
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )
