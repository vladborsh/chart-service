#!/usr/bin/env python3
"""
Technical Indicators Calculator

This module provides technical indicator calculations for trading analysis.
Indicators include Bollinger Bands, VWAP, and other common technical analysis tools.
"""

import logging
from typing import Dict, Any
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


class IndicatorCalculator:
    """Calculate technical indicators for trading analysis"""
    
    def __init__(self):
        """Initialize the indicator calculator"""
        logger.info("Indicator calculator initialized")
    
    def calculate_bollinger_bands(self, df: pd.DataFrame, window: int = 20, num_std: float = 2.0) -> pd.DataFrame:
        """
        Calculate Bollinger Bands
        
        Args:
            df: OHLCV DataFrame
            window: Moving average window
            num_std: Number of standard deviations
            
        Returns:
            DataFrame with ma, upper, lower columns
        """
        close = df['close']
        ma = close.rolling(window=window).mean()
        std = close.rolling(window=window).std()
        upper = ma + (std * num_std)
        lower = ma - (std * num_std)
        
        return pd.DataFrame({
            'ma': ma,
            'upper': upper,
            'lower': lower
        }, index=df.index)
    
    def calculate_vwap(self, df: pd.DataFrame, num_std: float = 2.0) -> pd.DataFrame:
        """
        Calculate VWAP with daily reset
        
        Args:
            df: OHLCV DataFrame with datetime index
            num_std: Number of standard deviations for bands
            
        Returns:
            DataFrame with vwap, upper, lower columns
        """
        # Typical price
        typical_price = (df['high'] + df['low'] + df['close']) / 3
        
        # Handle volume - use default if not present
        if 'volume' in df.columns:
            volume = df['volume']
        else:
            # For forex without volume, use equal weighting
            volume = pd.Series(1, index=df.index)
        
        # Group by date for daily reset
        df_with_date = df.copy()
        df_with_date['date'] = df_with_date.index.date
        
        # Calculate cumulative for each day
        vwap_list = []
        vwap_upper_list = []
        vwap_lower_list = []
        
        for date, group in df_with_date.groupby('date'):
            group_tp = typical_price.loc[group.index]
            group_vol = volume.loc[group.index]
            
            # Cumulative VWAP for the day
            cum_vol = group_vol.cumsum()
            cum_tp_vol = (group_tp * group_vol).cumsum()
            group_vwap = cum_tp_vol / cum_vol
            
            # Calculate standard deviation for bands
            squared_diff = (group_tp - group_vwap) ** 2
            cum_squared_diff = (squared_diff * group_vol).cumsum()
            variance = cum_squared_diff / cum_vol
            std_dev = np.sqrt(variance)
            
            group_upper = group_vwap + (std_dev * num_std)
            group_lower = group_vwap - (std_dev * num_std)
            
            vwap_list.append(group_vwap)
            vwap_upper_list.append(group_upper)
            vwap_lower_list.append(group_lower)
        
        vwap = pd.concat(vwap_list)
        vwap_upper = pd.concat(vwap_upper_list)
        vwap_lower = pd.concat(vwap_lower_list)
        
        return pd.DataFrame({
            'vwap': vwap,
            'upper': vwap_upper,
            'lower': vwap_lower
        }, index=df.index)
    
    def calculate_indicators(self, df: pd.DataFrame, strategy_params: Dict[str, Any]) -> Dict[str, pd.DataFrame]:
        """
        Calculate technical indicators for the chart
        
        Args:
            df: OHLCV DataFrame
            strategy_params: Strategy parameters containing indicator settings
            
        Returns:
            Dictionary with calculated indicators
        """
        indicators = {}
        
        # Calculate Bollinger Bands
        bb_window = strategy_params.get('bb_window', 20)
        bb_std = strategy_params.get('bb_std', 2)
        
        try:
            indicators['bb'] = self.calculate_bollinger_bands(df, window=bb_window, num_std=bb_std)
        except Exception as e:
            logger.error(f"Error calculating Bollinger Bands: {e}")
            return {}
        
        # Calculate VWAP with daily reset
        vwap_std = strategy_params.get('vwap_std', 2)
        
        try:
            indicators['vwap'] = self.calculate_vwap(df, num_std=vwap_std)
        except Exception as e:
            logger.error(f"Error calculating VWAP: {e}")
            return {}
        
        logger.debug("Indicators calculated successfully")
        return indicators
