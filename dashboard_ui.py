"""
Dashboard UI - Renders certification cards and interactive elements
"""

import streamlit as st
import pandas as pd
from typing import Dict, Any

from display_formatting import (
    format_cert_score_whole,
    format_latency_ms_whole,
    format_signal_whole,
    format_speed_mbps_gbps_line,
)


class DashboardUI:
    """
    Renders interactive certification cards and scoring visualization.
    """
    
    BADGE_COLORS = {
        'Platinum': '#E5E4E2',  # Platinum
        'Gold': '#FFD700',      # Gold
        'Silver': '#C0C0C0',    # Silver
        'Fail': '#DC143C',      # Crimson red
    }
    
    BADGE_EMOJIS = {
        'Platinum': '🏆',
        'Gold': '⭐',
        'Silver': '✨',
        'Fail': '❌',
    }
    
    def __init__(self, metrics_df: pd.DataFrame, scores_df: pd.DataFrame, manual_inputs: Dict[str, Dict]):
        """
        Initialize dashboard UI.
        
        Args:
            metrics_df: DataFrame with calculated metrics
            scores_df: DataFrame with certification scores
            manual_inputs: Dictionary of manual input values per carrier
        """
        self.metrics_df = metrics_df
        self.scores_df = scores_df
        self.manual_inputs = manual_inputs
    
    def render_certification_card(
        self,
        carrier: str,
        carrier_metrics: pd.DataFrame,
        carrier_score: pd.Series,
        carrier_manual: Dict[str, str]
    ) -> None:
        """
        Render a certification card for a single carrier.
        
        Args:
            carrier: Carrier name
            carrier_metrics: Metrics for this carrier
            carrier_score: Score data for this carrier
            carrier_manual: Manual inputs for this carrier
        """
        metrics = carrier_metrics.iloc[0] if len(carrier_metrics) > 0 else {}
        
        badge = carrier_score.get('Badge', 'Fail')
        score = carrier_score.get('Score', 0)
        
        # Card styling
        color = self.BADGE_COLORS.get(badge, '#cccccc')
        emoji = self.BADGE_EMOJIS.get(badge, '?')
        
        with st.container():
            # Card border
            st.markdown(f"""
                <div style="
                    border: 3px solid {color};
                    border-radius: 10px;
                    padding: 20px;
                    background-color: rgba(255, 255, 255, 0.9);
                    margin-bottom: 20px;
                ">
                    <h3 style="margin: 0; color: {color};">{emoji} {carrier}</h3>
                    <div style="
                        font-size: 36px;
                        font-weight: bold;
                        color: {color};
                        margin: 10px 0;
                    ">
                        {badge}
                    </div>
                    <div style="
                        font-size: 24px;
                        color: #666;
                        margin-bottom: 15px;
                    ">
                        Score: {format_cert_score_whole(score)}/100
                    </div>
                </div>
                """, unsafe_allow_html=True)
            
            # Detailed metrics in expandable section
            with st.expander("📊 Detailed Metrics"):
                col1, col2 = st.columns(2)

                def safe_format(value, unit="", decimals=1):
                    if pd.isna(value) or value == "N/A":
                        return "N/A"
                    try:
                        return f"{float(value):.{decimals}f}{unit}"
                    except (ValueError, TypeError):
                        return str(value)

                def _signal_metric(value, unit: str) -> str:
                    s = format_signal_whole(value)
                    return f"{s} {unit}" if s != "N/A" else "N/A"

                def _latency_metric(value) -> str:
                    s = format_latency_ms_whole(value)
                    return f"{s} ms" if s != "N/A" else "N/A"

                with col1:
                    st.metric(
                        "Signal Quality (RSRP)",
                        _signal_metric(metrics.get("RSRP_Summary", "N/A"), "dBm"),
                    )
                    st.metric(
                        "Download Speed (Peak)",
                        format_speed_mbps_gbps_line(metrics.get("Peak_DL_Mbps", "N/A")),
                    )
                    st.metric(
                        "Latency",
                        _latency_metric(metrics.get("Median_Latency_ms", "N/A")),
                    )

                with col2:
                    st.metric(
                        "Signal Quality (RSRQ)",
                        _signal_metric(metrics.get("RSRQ_dB", "N/A"), "dB"),
                    )
                    st.metric(
                        "Upload Speed (Peak)",
                        format_speed_mbps_gbps_line(metrics.get("Peak_UL_Mbps", "N/A")),
                    )
                    st.metric(
                        "Jitter",
                        _latency_metric(metrics.get("Median_Jitter_ms", "N/A")),
                    )
                
                # Advanced metrics
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("5G State", metrics.get('Final_5G_State', 'N/A'))
                    st.metric("Band Diversity", metrics.get('Band_Diversity_Count', 'N/A'))
                with col2:
                    st.metric(
                        "Coverage %",
                        safe_format(metrics.get('Primary_Coverage_Pct', 'N/A'), '%')
                    )
                    st.metric("CQI", safe_format(metrics.get('CQI_Tool', 'N/A'), decimals=0))
            
            # Score breakdown (methodology tiers)
            with st.expander("📈 Score Breakdown"):
                col1, col2 = st.columns(2)

                with col1:
                    st.metric(
                        "HIGH tier (weighted sum)",
                        f"{float(carrier_score.get('Bucket_HIGH_Weighted', 0) or 0):.2f}",
                    )
                    st.metric(
                        "MEDIUM tier (weighted sum)",
                        f"{float(carrier_score.get('Bucket_MEDIUM_Weighted', 0) or 0):.2f}",
                    )

                with col2:
                    st.metric(
                        "LOW tier (weighted sum)",
                        f"{float(carrier_score.get('Bucket_LOW_Weighted', 0) or 0):.2f}",
                    )
                    st.metric(
                        "Weighted avg raw (0–4)",
                        f"{float(carrier_score.get('Weighted_Avg_Raw', 0) or 0):.3f}",
                    )
                if carrier_score.get("PMOS_Capped"):
                    ps = carrier_score.get("PMOS_Score_Used")
                    st.warning(
                        f"pMOS rule: certification capped at **Silver** (pMOS **{ps:.1f}** < 3.5)."
                        if ps is not None and not pd.isna(ps)
                        else "pMOS rule: certification capped at **Silver**."
                    )

                try:
                    bar_score = float(score)
                except (TypeError, ValueError):
                    bar_score = 0.0
                if pd.isna(bar_score):
                    bar_score = 0.0
                st.progress(max(0.0, min(1.0, bar_score / 100.0)))
            
            # Manual inputs summary
            with st.expander("⚙️ Manual Inputs"):
                col1, col2 = st.columns(2)

                with col1:
                    st.info(
                        f"**VPN Usage**: {carrier_manual.get('vpn_type', carrier_manual.get('vpn_usage', 'N/A'))}"
                    )
                    st.info(f"**ISP Redundancy**: {carrier_manual.get('isp_redundancy', 'N/A')}")

                with col2:
                    st.info(f"**ISP Diversity**: {carrier_manual.get('isp_diversity', 'N/A')}")
                    st.info(
                        f"**Hardware Age**: {carrier_manual.get('hardware_age', carrier_manual.get('ap_model', 'N/A'))}"
                    )
                
                if carrier_manual.get('notes'):
                    st.text_area(
                        "Notes",
                        carrier_manual.get('notes', ''),
                        disabled=True,
                        height=100
                    )
    
    def render_summary_table(self) -> pd.DataFrame:
        """
        Render a summary table of all carriers and their scores.
        
        Returns:
            Summary DataFrame
        """
        summary_data = []
        
        for _, score_row in self.scores_df.iterrows():
            carrier = score_row['Carrier']
            metrics_row = self.metrics_df[
                self.metrics_df['Carrier'] == carrier
            ]
            
            if len(metrics_row) == 0:
                continue
            
            metrics = metrics_row.iloc[0]
            manual = self.manual_inputs.get(carrier, {})
            
            summary_data.append({
                'Carrier': carrier,
                'Badge': score_row['Badge'],
                'Score': score_row['Score'],
                'HIGH_Σw': score_row.get('Bucket_HIGH_Weighted', ''),
                'MED_Σw': score_row.get('Bucket_MEDIUM_Weighted', ''),
                'LOW_Σw': score_row.get('Bucket_LOW_Weighted', ''),
                'AvgRaw': score_row.get('Weighted_Avg_Raw', ''),
                'RSRP': metrics.get('RSRP_Summary', ''),
                'DL Peak': metrics.get('Peak_DL_Mbps', ''),
                'Redundancy': manual.get('isp_redundancy', ''),
            })
        
        return pd.DataFrame(summary_data)
    
    @staticmethod
    def render_certification_legend() -> None:
        """Render badge legend."""
        st.subheader("📋 Certification Levels")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.markdown("""
                <div style="text-align: center; padding: 10px;">
                    <div style="font-size: 32px;">🏆</div>
                    <div style="font-weight: bold;">Platinum</div>
                    <div style="font-size: 12px; color: gray;">90-100</div>
                </div>
                """, unsafe_allow_html=True)
        
        with col2:
            st.markdown("""
                <div style="text-align: center; padding: 10px;">
                    <div style="font-size: 32px;">⭐</div>
                    <div style="font-weight: bold;">Gold</div>
                    <div style="font-size: 12px; color: gray;">75-89</div>
                </div>
                """, unsafe_allow_html=True)
        
        with col3:
            st.markdown("""
                <div style="text-align: center; padding: 10px;">
                    <div style="font-size: 32px;">✨</div>
                    <div style="font-weight: bold;">Silver</div>
                    <div style="font-size: 12px; color: gray;">60-74</div>
                </div>
                """, unsafe_allow_html=True)
        
        with col4:
            st.markdown("""
                <div style="text-align: center; padding: 10px;">
                    <div style="font-size: 32px;">❌</div>
                    <div style="font-weight: bold;">Fail</div>
                    <div style="font-size: 12px; color: gray;">0-59</div>
                </div>
                """, unsafe_allow_html=True)
    
    @staticmethod
    def render_methodology_info() -> None:
        """Render scoring methodology information."""
        st.subheader("📊 Scoring Methodology")
        
        with st.expander("View Scoring Details"):
            st.markdown("""
            ### Methodology Sandbox (tiered weights)

            Each metric maps to **0–4 raw points** (Poor → Excellent). Tier weights default to
            **HIGH 2.25**, **MEDIUM 0.25**, **LOW 0.125** per metric (tunable in the sidebar).

            **HIGH tier:** Peak DL/UL Mbps, RSRP, SINR, median latency, primary coverage %, ISP redundancy (manual).

            **MEDIUM tier:** RSRQ, jitter, packet loss, handover success %, total bandwidth MHz, ISP diversity (manual).

            **LOW tier:** TX power, MIMO rank, CA count, band diversity count, CQI, modulation, **VPN Usage** (None=0, Consumer=2, Corporate=4), hardware age (manual).

            Final **0–100 score** = 100 × Σ(raw × weight) / Σ(4 × weight). **pMOS** voice toggle caps the badge at **Silver**
            when the weighted average raw score is below **3.5**.
            """)
