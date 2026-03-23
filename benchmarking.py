"""
Benchmarking Module - Carrier Head-to-Head Comparison
Visualizes carrier performance across key dimensions using radar charts
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from typing import Dict


class CarrierBenchmark:
    """
    Provides benchmarking and comparison capabilities for cellular carriers.
    """
    
    def __init__(self, metrics_df: pd.DataFrame, scores_df: pd.DataFrame):
        """
        Initialize benchmarking module.
        
        Args:
            metrics_df: DataFrame with calculated metrics per carrier
            scores_df: DataFrame with certification scores per carrier
        """
        self.metrics_df = metrics_df
        self.scores_df = scores_df
    
    def _normalize_value(self, value: float, min_val: float, max_val: float) -> float:
        """
        Normalize a value to 0-100 scale.
        
        Args:
            value: The value to normalize
            min_val: Minimum value in the dataset
            max_val: Maximum value in the dataset
        
        Returns:
            Normalized value (0-100)
        """
        if pd.isna(value):
            return 0
        if max_val == min_val:
            return 50  # Middle value if all values are the same
        normalized = ((value - min_val) / (max_val - min_val)) * 100
        return max(0, min(100, normalized))  # Clamp to 0-100
    
    def _normalize_inverse(self, value: float, min_val: float, max_val: float) -> float:
        """
        Normalize a value inversely (lower is better, like latency).
        
        Args:
            value: The value to normalize
            min_val: Minimum value (best)
            max_val: Maximum value (worst)
        
        Returns:
            Normalized value (0-100, where 100 is best/lowest)
        """
        if pd.isna(value):
            return 0
        if max_val == min_val:
            return 50
        # Inverse: lower values get higher scores
        normalized = ((max_val - value) / (max_val - min_val)) * 100
        return max(0, min(100, normalized))
    
    def _get_benchmark_data(self) -> Dict[str, Dict[str, float]]:
        """
        Extract and normalize benchmark metrics for each carrier.
        
        Returns:
            Dictionary with carrier names and their normalized metrics
        """
        benchmark_data = {}
        
        # Get all carriers
        carriers = self.metrics_df['Carrier'].tolist()
        
        # Extract metrics for normalization
        rsrp_values = self.metrics_df['RSRP_Summary'].dropna().values
        rsrq_values = self.metrics_df['RSRQ_dB'].dropna().values
        sinr_values = self.metrics_df['SINR_Summary'].dropna().values
        dl_values = self.metrics_df['Peak_DL_Mbps'].dropna().values
        latency_values = self.metrics_df['Median_Latency_ms'].dropna().values
        coverage_values = self.metrics_df['Primary_Coverage_Pct'].dropna().values
        
        # Set min/max for normalization (with reasonable defaults)
        rsrp_min, rsrp_max = rsrp_values.min() if len(rsrp_values) > 0 else -120, rsrp_values.max() if len(rsrp_values) > 0 else -50
        rsrq_min, rsrq_max = rsrq_values.min() if len(rsrq_values) > 0 else -20, rsrq_values.max() if len(rsrq_values) > 0 else 0
        sinr_min, sinr_max = sinr_values.min() if len(sinr_values) > 0 else 0, sinr_values.max() if len(sinr_values) > 0 else 30
        dl_min, dl_max = dl_values.min() if len(dl_values) > 0 else 0, dl_values.max() if len(dl_values) > 0 else 500
        latency_min, latency_max = latency_values.min() if len(latency_values) > 0 else 0, latency_values.max() if len(latency_values) > 0 else 200
        coverage_min, coverage_max = coverage_values.min() if len(coverage_values) > 0 else 0, coverage_values.max() if len(coverage_values) > 0 else 100
        
        for _, row in self.metrics_df.iterrows():
            carrier = row['Carrier']
            
            # Signal Strength: Average of RSRP and RSRQ (both higher is better)
            rsrp_norm = self._normalize_value(row['RSRP_Summary'], rsrp_min, rsrp_max)
            rsrq_norm = self._normalize_value(row['RSRQ_dB'], rsrq_min, rsrq_max)
            signal_strength = (rsrp_norm + rsrq_norm) / 2
            
            # Signal Quality: SINR (higher is better)
            signal_quality = self._normalize_value(row['SINR_Summary'], sinr_min, sinr_max)
            
            # Download Speed (higher is better)
            download_speed = self._normalize_value(row['Peak_DL_Mbps'], dl_min, dl_max)
            
            # Latency (lower is better, so inverse normalization)
            latency = self._normalize_inverse(row['Median_Latency_ms'], latency_min, latency_max)
            
            # Coverage (higher is better)
            coverage = self._normalize_value(row['Primary_Coverage_Pct'], coverage_min, coverage_max)
            
            benchmark_data[carrier] = {
                'Signal Strength': signal_strength,
                'Signal Quality': signal_quality,
                'Download Speed': download_speed,
                'Latency': latency,
                'Coverage': coverage
            }
        
        return benchmark_data
    
    def create_radar_chart(self) -> go.Figure:
        """
        Create an interactive radar chart comparing all carriers.
        
        Returns:
            Plotly figure object with radar chart
        """
        benchmark_data = self._get_benchmark_data()
        
        # Define colors for each carrier
        colors = {
            'AT&T': '#1f77b4',      # Blue
            'T-Mobile': '#ff7f0e',  # Orange
            'Verizon': '#2ca02c'    # Green
        }
        
        # Create figure
        fig = go.Figure()
        
        # Add a trace for each carrier
        for carrier, metrics in benchmark_data.items():
            categories = list(metrics.keys())
            values = list(metrics.values())
            
            # Close the radar by repeating the first value
            categories_closed = categories + [categories[0]]
            values_closed = values + [values[0]]
            
            fig.add_trace(go.Scatterpolar(
                r=values_closed,
                theta=categories_closed,
                fill='toself',
                name=carrier,
                line=dict(color=colors.get(carrier, '#95a5a6')),
                fillcolor=colors.get(carrier, '#95a5a6'),
                opacity=0.5,
                hoverinfo='all',
                hovertemplate='<b>%{fullData.name}</b><br>%{theta}: %{r:.1f}<extra></extra>'
            ))
        
        # Update layout
        fig.update_layout(
            polar=dict(
                radialaxis=dict(
                    visible=True,
                    range=[0, 100],
                    tickfont=dict(size=11),
                    gridcolor='#e0e0e0'
                ),
                angularaxis=dict(
                    tickfont=dict(size=12)
                ),
                bgcolor='rgba(240, 240, 240, 0.5)'
            ),
            hovermode='closest',
            font=dict(size=12),
            showlegend=True,
            legend=dict(
                x=1.1,
                y=1,
                bgcolor='rgba(255, 255, 255, 0.8)',
                bordercolor='#e0e0e0',
                borderwidth=1
            ),
            title=dict(
                text='<b>Carrier Benchmarking: Head-to-Head Comparison</b><br><sub>Normalized Score (0-100)</sub>',
                x=0.5,
                xanchor='center',
                font=dict(size=16)
            ),
            margin=dict(l=80, r=200, t=100, b=80),
            paper_bgcolor='white',
            plot_bgcolor='rgba(240, 240, 240, 0.5)',
            width=1000,
            height=600
        )
        
        return fig
    
    def render_benchmarking_view(self) -> None:
        """
        Render the full benchmarking view with charts and analysis.
        """
        st.header("📊 Carrier Benchmarking")
        
        st.markdown("""
        This view provides a head-to-head comparison of the three carriers across five key performance dimensions:
        
        - **Signal Strength**: Combined RSRP and RSRQ metrics (higher is better)
        - **Signal Quality**: SINR/RSSNR measurements (higher is better)
        - **Download Speed**: Peak DL performance in Mbps (higher is better)
        - **Latency**: Median latency in milliseconds (lower is better)
        - **Coverage**: Primary coverage percentage (higher is better)
        
        All metrics are normalized to a 0-100 scale for easy comparison.
        """)
        
        # Display radar chart
        fig = self.create_radar_chart()
        st.plotly_chart(fig, width="stretch")
        
        # Display detailed metrics table
        st.subheader("Detailed Metrics by Carrier")
        
        benchmark_data = self._get_benchmark_data()
        
        # Create a comparison table
        comparison_df = pd.DataFrame(benchmark_data).T
        comparison_df = comparison_df.round(1)
        
        # Color code the table values
        st.dataframe(
            comparison_df,
            width="stretch",
            height=250
        )
        
        # Show raw metrics for reference
        st.subheader("Raw Metrics Reference")
        
        raw_metrics = self.metrics_df[[
            'Carrier', 'RSRP_Summary', 'RSRQ_dB', 'SINR_Summary',
            'Peak_DL_Mbps', 'Median_Latency_ms', 'Primary_Coverage_Pct'
        ]].copy()
        
        raw_metrics = raw_metrics.round(2)
        st.dataframe(raw_metrics, width="stretch")
        
        # Summary insights
        st.subheader("Key Insights")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            # Signal Strength leader
            signal_leader = max(benchmark_data.items(), key=lambda x: x[1]['Signal Strength'])
            st.metric(
                "Signal Strength Leader",
                signal_leader[0],
                f"{signal_leader[1]['Signal Strength']:.1f}/100"
            )
        
        with col2:
            # Speed leader
            speed_leader = max(benchmark_data.items(), key=lambda x: x[1]['Download Speed'])
            st.metric(
                "Download Speed Leader",
                speed_leader[0],
                f"{speed_leader[1]['Download Speed']:.1f}/100"
            )
        
        with col3:
            # Latency leader (lower latency = higher score)
            latency_leader = max(benchmark_data.items(), key=lambda x: x[1]['Latency'])
            st.metric(
                "Latency Leader",
                latency_leader[0],
                f"{latency_leader[1]['Latency']:.1f}/100"
            )
