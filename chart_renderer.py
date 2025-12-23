#!/usr/bin/env python3
"""
Chart Renderer

This module provides core chart rendering functionality for trading signals.
It generates chart images with candlesticks and technical indicators.
"""

import io
import logging
from typing import Dict, Any, Optional
import pandas as pd
import numpy as np
from datetime import datetime

try:
    import matplotlib
    # Use non-interactive backend to avoid GUI dependencies
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import mplfinance as mpf
    MPLFINANCE_AVAILABLE = True
except ImportError as e:
    logger = logging.getLogger(__name__)
    logger.warning(f"mplfinance not available for chart generation: {e}")
    MPLFINANCE_AVAILABLE = False

logger = logging.getLogger(__name__)


class ChartRenderer:
    """Render trading signal charts with indicators"""
    
    def __init__(self):
        """Initialize the chart renderer with style settings"""
        if not MPLFINANCE_AVAILABLE:
            logger.warning("ChartRenderer initialized but mplfinance not available - charts will not be generated")
            return
            
        # Define custom style for professional appearance
        self.chart_style = mpf.make_mpf_style(
            base_mpf_style='charles',
            marketcolors=mpf.make_marketcolors(
                up='#26a69a',      # Green for up candles
                down='#ef5350',    # Red for down candles
                edge='inherit',
                wick={'up': '#26a69a', 'down': '#ef5350'},
                volume='inherit',
                alpha=0.9
            ),
            gridstyle='--',
            gridcolor='#e0e0e0',
            facecolor='#ffffff',
            edgecolor='#000000',
            figcolor='#ffffff',
            y_on_right=True
        )
        
        # Chart settings
        self.candles_to_show = 100  # Show last 100 candles for better context
        self.figure_size = (12, 8)  # Size in inches for good mobile readability
        self.dpi = 100  # Resolution
        
        logger.info("Chart renderer initialized")
    
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
    
    def _prepare_chart_data(self, data: pd.DataFrame, signal_data: Optional[Dict[str, Any]]) -> pd.DataFrame:
        """
        Prepare chart data with optimal range for SL/TP visibility
        
        Args:
            data: Full OHLCV DataFrame
            signal_data: Optional signal information with entry, stop_loss, take_profit
            
        Returns:
            Optimized DataFrame for chart display
        """
        # Use last N candles as base
        plot_data = data.tail(self.candles_to_show).copy()
        
        # Calculate optimal y-axis range to include SL/TP with some padding if signal_data provided
        if signal_data:
            entry_price = signal_data.get('entry_price', 0)
            stop_loss = signal_data.get('stop_loss', 0)
            take_profit = signal_data.get('take_profit', 0)
        else:
            entry_price = stop_loss = take_profit = 0
        
        if entry_price > 0 and stop_loss > 0 and take_profit > 0:
            # Find min/max of signal levels
            signal_min = min(entry_price, stop_loss, take_profit)
            signal_max = max(entry_price, stop_loss, take_profit)
            
            # Get price range from data
            data_min = plot_data[['low']].min().min()
            data_max = plot_data[['high']].max().max()
            
            # Extend range to ensure SL/TP are visible
            chart_min = min(data_min, signal_min)
            chart_max = max(data_max, signal_max)
            
            # Add padding (5% of range)
            price_range = chart_max - chart_min
            padding = price_range * 0.05
            
            # Store the optimal y-limits for later use
            plot_data.attrs['y_limits'] = (chart_min - padding, chart_max + padding)
            
            logger.debug(f"Chart range optimized for SL/TP visibility: {chart_min - padding:.5f} - {chart_max + padding:.5f}")
        
        return plot_data
    
    def generate_chart(self, 
                      data: pd.DataFrame,
                      signal_data: Optional[Dict[str, Any]],
                      strategy_params: Dict[str, Any],
                      symbol: str) -> Optional[bytes]:
        """
        Generate a chart image for the trading signal
        
        Args:
            data: OHLCV DataFrame with datetime index
            signal_data: Optional signal information (entry, stop_loss, take_profit, etc.)
            strategy_params: Strategy parameters for indicators
            symbol: Trading symbol name
            
        Returns:
            Chart image as bytes buffer or None if generation fails
        """
        if not MPLFINANCE_AVAILABLE:
            logger.debug("Chart generation skipped - mplfinance not available")
            return None
            
        try:
            # Prepare data with smart selection for better SL/TP visibility
            plot_data = self._prepare_chart_data(data, signal_data)
            
            # Ensure data has proper format for mplfinance
            if not isinstance(plot_data.index, pd.DatetimeIndex):
                plot_data.index = pd.to_datetime(plot_data.index)
            
            # Calculate indicators
            indicators = self.calculate_indicators(plot_data, strategy_params)
            
            # Check if indicators calculation failed
            if not indicators:
                logger.error(f"Indicators calculation failed for {symbol} - cannot generate chart")
                return None
            
            # Prepare additional plot lines for indicators
            additional_plots = []
            
            # Add Bollinger Bands (upper and lower only)
            bb_data = indicators['bb']
            additional_plots.extend([
                mpf.make_addplot(bb_data['upper'], color='#808080', width=1, linestyle='--', alpha=0.7),
                mpf.make_addplot(bb_data['lower'], color='#808080', width=1, linestyle='--', alpha=0.7)
            ])
            
            # Add VWAP bands (upper and lower only)
            vwap_data = indicators['vwap']
            additional_plots.extend([
                mpf.make_addplot(vwap_data['upper'], color='#9932cc', width=1, linestyle=':', alpha=0.6),
                mpf.make_addplot(vwap_data['lower'], color='#9932cc', width=1, linestyle=':', alpha=0.6)
            ])
            
            # Add signal levels (entry, stop loss, take profit) as horizontal lines if provided
            if signal_data:
                entry_price = signal_data.get('entry_price', 0)
                stop_loss = signal_data.get('stop_loss', 0)
                take_profit = signal_data.get('take_profit', 0)
                
                if entry_price > 0:
                    # Create horizontal lines for signal levels with better visibility
                    entry_line = pd.Series([entry_price] * len(plot_data), index=plot_data.index)
                    additional_plots.append(
                        mpf.make_addplot(entry_line, color='#1f77b4', width=2.5, linestyle='-', alpha=0.9)
                    )
                
                if stop_loss > 0:
                    sl_line = pd.Series([stop_loss] * len(plot_data), index=plot_data.index)
                    additional_plots.append(
                        mpf.make_addplot(sl_line, color='#d62728', width=2, linestyle='--', alpha=0.8)
                    )
                
                if take_profit > 0:
                    tp_line = pd.Series([take_profit] * len(plot_data), index=plot_data.index)
                    additional_plots.append(
                        mpf.make_addplot(tp_line, color='#2ca02c', width=2, linestyle='-.', alpha=0.8)
                    )
            
            # Clean symbol name for display
            clean_symbol = symbol
            if clean_symbol and clean_symbol.endswith('X'):
                # Keep X only for indices like 'DAX', 'FTMX'
                if clean_symbol not in ['DAX', 'FTMX', 'SPX', 'NDX']:
                    clean_symbol = clean_symbol[:-1]
            
            # Create the chart with optimized settings
            signal_type_text = ""
            if signal_data and signal_data.get('signal_type'):
                signal_type_text = f" - {signal_data.get('signal_type', '').upper()} Signal"
            
            fig, axes = mpf.plot(
                plot_data,
                type='candle',
                style=self.chart_style,
                addplot=additional_plots,
                figsize=self.figure_size,
                title=dict(
                    title=f'{clean_symbol}{signal_type_text}',
                    fontsize=16,
                    fontweight='bold'
                ),
                returnfig=True,
                volume=False,  # Don't show volume subplot
                tight_layout=True,
                scale_padding={'left': 0.05, 'right': 0.15, 'top': 0.25, 'bottom': 0.05}
            )
            
            # Apply y-axis limits if available for better SL/TP visibility
            if hasattr(plot_data, 'attrs') and 'y_limits' in plot_data.attrs:
                y_min, y_max = plot_data.attrs['y_limits']
                axes[0].set_ylim(y_min, y_max)
                logger.debug(f"Applied y-axis limits: {y_min:.5f} - {y_max:.5f}")
            
            # Add timestamp
            timestamp_text = f'Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")}'
            axes[0].text(0.98, 0.02, timestamp_text,
                        transform=axes[0].transAxes,
                        fontsize=8,
                        horizontalalignment='right',
                        alpha=0.6)
            
            # Save to bytes buffer
            buffer = io.BytesIO()
            fig.savefig(buffer, format='png', dpi=self.dpi, bbox_inches='tight', 
                       facecolor='white', edgecolor='none')
            buffer.seek(0)
            
            # Clean up
            plt.close(fig)
            
            signal_info = f"{signal_data.get('signal_type')} signal" if signal_data else "chart"
            logger.info(f"Chart generated for {symbol} {signal_info}")
            return buffer.getvalue()
            
        except Exception as e:
            logger.error(f"Failed to generate chart for {symbol}: {e}")
            return None
