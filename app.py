"""
Cellular Certification ETL & Dashboard
Processes Rootmetrics logs and generates certified cellular audit with scoring.
"""

import streamlit as st
import pandas as pd
from io import BytesIO
import warnings
warnings.filterwarnings('ignore')

from metrics_processor import MetricsProcessor
from certification_scorer import CertificationScorer
from dashboard_ui import DashboardUI
from geospatial_layer import GeospatialLayer
from geo_anchors import dataset_matches_seattle_preset
from display_formatting import (
    build_column_config_for_metrics_display,
    build_detailed_metrics_display_dataframe,
    format_cert_score_whole,
    format_speed_mbps,
)
from engineering_rca import render_engineering_insights_section
from methodology_sandbox import (
    DEFAULT_WEIGHT_HIGH,
    DEFAULT_WEIGHT_LOW,
    DEFAULT_WEIGHT_MEDIUM,
    HARDWARE_AGE_OPTIONS,
    ISP_DIVERSITY_OPTIONS,
    ISP_REDUNDANCY_OPTIONS,
    VPN_TYPE_OPTIONS,
    build_bucket_scoring_card_df,
    build_metric_scoring_card_df,
    coerce_metrics_column_to_str,
    default_manual_inputs,
    migrate_manual_dict,
)


def run_metrics_pipeline(df: pd.DataFrame) -> None:
    """Normalize speeds, compute per-carrier metrics, and cache for maps / export."""
    processor = MetricsProcessor(df)
    st.session_state.metrics_data = processor.calculate_all_metrics()
    st.session_state.processed_df = df
    st.session_state.raw_data = df
    st.session_state.venue_preset = (
        "seattle" if dataset_matches_seattle_preset(df) else None
    )


# ============================================================================
# PAGE CONFIGURATION
# ============================================================================
st.set_page_config(
    page_title="Cellular Certification Dashboard",
    page_icon="📡",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
    <style>
        .main {
            padding: 0rem 1rem;
        }
        h1 {
            color: #1f77b4;
        }
        .metric-card {
            background-color: #f0f2f6;
            border-radius: 0.5rem;
            padding: 1rem;
            margin: 0.5rem 0;
        }
    </style>
    """, unsafe_allow_html=True)

# ============================================================================
# SESSION STATE INITIALIZATION
# ============================================================================
if 'processed_df' not in st.session_state:
    st.session_state.processed_df = None
if 'metrics_data' not in st.session_state:
    st.session_state.metrics_data = None
if 'manual_inputs' not in st.session_state:
    st.session_state.manual_inputs = {}
if 'final_output' not in st.session_state:
    st.session_state.final_output = None
if "pmos_score_val" not in st.session_state:
    st.session_state.pmos_score_val = 4.5

# ============================================================================
# MAIN APPLICATION
# ============================================================================
st.title("📡 Cellular Certification ETL & Dashboard")

if st.session_state.get("pmos_voice") and float(st.session_state.get("pmos_score_val", 4.5)) < 3.5:
    st.markdown(
        """
        <div style="background:linear-gradient(90deg,#7f1d1d,#b91c1c);color:#fff;padding:18px 22px;
        border-radius:10px;font-size:1.2rem;font-weight:800;text-align:center;
        letter-spacing:0.02em;margin:0 0 16px 0;box-shadow:0 4px 14px rgba(127,29,29,0.35);">
        ⚠️ CERTIFICATION CAPPED AT SILVER (Voice Quality Failure)
        </div>
        """,
        unsafe_allow_html=True,
    )

# ----------------------------------------------------------------------------
# Sidebar: voice + site audit (tier weights fixed at defaults in the engine)
# ----------------------------------------------------------------------------
with st.sidebar:
    st.header("Certification inputs")
    st.checkbox(
        "pMOS (Voice) Test Performed",
        value=False,
        key="pmos_voice",
        help="When enabled, enter pMOS (1–5). If pMOS < 3.5, certification badge cannot exceed Silver.",
    )
    if st.session_state.get("pmos_voice"):
        st.number_input(
            "pMOS score (1.0 – 5.0)",
            min_value=1.0,
            max_value=5.0,
            step=0.1,
            key="pmos_score_val",
            help="Mean Opinion Score style voice quality. Capped at Silver when below 3.5.",
        )
        if float(st.session_state.get("pmos_score_val", 4.5)) < 3.5:
            st.markdown(
                """
                <div style="background:#7f1d1d;color:#fff;padding:12px 14px;border-radius:8px;
                font-size:1.05rem;font-weight:700;text-align:center;line-height:1.35;margin:8px 0 0 0;">
                ⚠️ CERTIFICATION CAPPED AT SILVER<br/>
                <span style="font-weight:500;font-size:0.95rem;">(Voice Quality Failure)</span>
                </div>
                """,
                unsafe_allow_html=True,
            )

    carriers_sidebar = (
        st.session_state.metrics_data["Carrier"].unique()
        if st.session_state.metrics_data is not None
        else []
    )
    if len(carriers_sidebar) > 0:
        st.divider()
        with st.expander("Site Infrastructure Audit", expanded=True):
            st.caption(
                "These settings apply to **every** processed RootMetrics dataset. "
                "VPN Usage (LOW tier), ISP Redundancy (HIGH), ISP Diversity (MEDIUM), Hardware Age (LOW)."
            )
            for c in carriers_sidebar:
                st.session_state.manual_inputs[c] = migrate_manual_dict(
                    st.session_state.manual_inputs.get(c, default_manual_inputs())
                )

            selected_carrier = st.selectbox(
                "Carrier",
                list(carriers_sidebar),
                key="carrier_select",
            )

            mi = st.session_state.manual_inputs[selected_carrier]

            def _opt_index(options, current):
                cur = str(current)
                return options.index(cur) if cur in options else 0

            mi["vpn_type"] = st.selectbox(
                "VPN Usage",
                list(VPN_TYPE_OPTIONS),
                index=_opt_index(list(VPN_TYPE_OPTIONS), mi.get("vpn_type", "None")),
                key=f"vpn_type_sb_{selected_carrier}",
            )
            mi["vpn_usage"] = mi["vpn_type"]
            mi["isp_redundancy"] = st.selectbox(
                "ISP Redundancy",
                list(ISP_REDUNDANCY_OPTIONS),
                index=_opt_index(
                    list(ISP_REDUNDANCY_OPTIONS), mi.get("isp_redundancy", "None")
                ),
                key=f"isp_red_sb_{selected_carrier}",
            )
            mi["isp_diversity"] = st.selectbox(
                "ISP Diversity",
                list(ISP_DIVERSITY_OPTIONS),
                index=_opt_index(
                    list(ISP_DIVERSITY_OPTIONS), mi.get("isp_diversity", "Single Entry")
                ),
                key=f"isp_div_sb_{selected_carrier}",
            )
            mi["hardware_age"] = st.selectbox(
                "Hardware Age",
                list(HARDWARE_AGE_OPTIONS),
                index=_opt_index(
                    list(HARDWARE_AGE_OPTIONS),
                    mi.get("hardware_age", "Modern 2-4 years"),
                ),
                key=f"hw_age_sb_{selected_carrier}",
            )
            mi["notes"] = st.text_area(
                "Notes",
                mi.get("notes", ""),
                height=80,
                key=f"notes_sb_{selected_carrier}",
            )
            st.session_state.manual_inputs[selected_carrier] = mi
    else:
        st.caption("Process data in **Data Processing** to enable inputs and scoring.")

methodology = {
    "weight_high": float(DEFAULT_WEIGHT_HIGH),
    "weight_medium": float(DEFAULT_WEIGHT_MEDIUM),
    "weight_low": float(DEFAULT_WEIGHT_LOW),
    "pmos_voice_test": bool(st.session_state.get("pmos_voice", False)),
    "pmos_score": (
        float(st.session_state.get("pmos_score_val", 4.5))
        if st.session_state.get("pmos_voice")
        else None
    ),
}

scores_df = None
scoring_details = {}
if st.session_state.metrics_data is not None:
    _scorer = CertificationScorer(st.session_state.metrics_data)
    scores_df, scoring_details = _scorer.calculate_scores(
        st.session_state.manual_inputs,
        methodology,
    )
    st.session_state.scoring_details = scoring_details
    st.session_state.final_output = {
        "metrics": st.session_state.metrics_data,
        "scores": scores_df,
        "manual_inputs": st.session_state.manual_inputs,
        "methodology": methodology,
        "scoring_details": scoring_details,
    }

with st.sidebar:
    if (
        st.session_state.metrics_data is not None
        and scoring_details
        and st.session_state.get("carrier_select")
    ):
        st.divider()
        st.subheader("Scoring Card")
        _sel = st.session_state.carrier_select
        _detail = scoring_details.get(_sel, {})
        if _detail:
            st.markdown(
                f"**{_sel}** — weighted avg raw (0–4): "
                f"`{_detail.get('weighted_avg_raw', 0):.3f}`"
            )
            if _detail.get("pmos_voice_test") and _detail.get("pmos_score") is not None:
                st.caption(f"Voice pMOS entered: **{_detail.get('pmos_score'):.1f}**")
            if _detail.get("pmos_capped"):
                st.error(
                    "⚠️ CERTIFICATION CAPPED AT SILVER (Voice Quality Failure)."
                )
            st.caption(
                "Per tier: Σ(Raw×Weight) = weight × Σ(Raw) when all metrics in the tier share the same weight."
            )
            _bucket_df = coerce_metrics_column_to_str(build_bucket_scoring_card_df(_detail))
            st.dataframe(
                _bucket_df,
                width="stretch",
                hide_index=True,
            )
            with st.expander("Per-metric breakdown"):
                st.dataframe(
                    build_metric_scoring_card_df(_detail),
                    width="stretch",
                    hide_index=True,
                    height=320,
                )

tab1, tab2, tab3, tab4, tab5 = st.tabs(
    [
        "📊 Data Processing",
        "📋 Certification Review",
        "📥 Export Results",
        "🗺️ Compliance Map",
        "🧪 Methodology Sandbox",
    ]
)

# ============================================================================
# TAB 1: DATA PROCESSING
# ============================================================================
with tab1:
    st.header("Step 1: Upload and Process Raw Data")

    uploaded_file = st.file_uploader(
        "Upload RootMetrics Detail CSV",
        type=['csv'],
        help="Upload a valid RootMetrics All_Detail (or equivalent) CSV with Network, coordinates, and RF columns.",
    )

    df_active = None
    df_label = None
    if uploaded_file is not None:
        df_active = pd.read_csv(uploaded_file)
        df_label = uploaded_file.name
    elif st.session_state.get("raw_data") is not None:
        df_active = st.session_state.raw_data
        df_label = "Cached session data"

    if df_active is not None:
        st.success(f"✓ Active dataset: **{df_label}** — **{len(df_active):,}** rows")

        col1, col2 = st.columns(2)
        with col1:
            st.metric("Total Records", f"{len(df_active):,}")
        with col2:
            st.metric("Carriers Found", df_active["Network"].nunique())

        st.subheader("Data Preview")
        st.dataframe(df_active.head(10), width="stretch", height=300)

        if st.button("🔄 Process Metrics", key="process_btn", type="primary"):
            with st.spinner("Processing metrics..."):
                run_metrics_pipeline(df_active)
            st.success("✓ Metrics calculated successfully!")
            st.rerun()

    if st.session_state.metrics_data is not None:
        st.subheader("Calculated Metrics by Carrier")
        _mdisp = build_detailed_metrics_display_dataframe(
            st.session_state.metrics_data.copy()
        )
        st.dataframe(
            _mdisp,
            width="stretch",
            height=400,
            column_config=build_column_config_for_metrics_display(_mdisp),
        )

    with st.expander("📚 Data Columns Reference"):
        st.write("""
        **Key Columns Used:**
        - `Network`: Carrier name
        - `Data_Network_Type`: "NR" for 5G, otherwise LTE
        - `LTE_RSRP`, `LTE_RSRQ`, `LTE_RSSNR`: LTE signal metrics
        - `5G_SS_RSRP`, `5G_SS_RSRQ`, `5G_SS_RSSNR`: 5G signal metrics
        - `LTE_CQI`, `Average_LTE_CQI`: Channel quality indicator
        - `Final_Test_Speed`: Speed in **Kbps** in the CSV (converted to Mbps in-app)
        - `Latency`, `Jitter`: Network timing metrics
        - `LTE_CA_Breakdown`, `NR_CA_Breakdown`: Carrier aggregation info
        - `Test`: Test type (Downlink, Uplink, UDP Echo)
        """)

# ============================================================================
# TAB 2: CERTIFICATION REVIEW & MANUAL INPUTS
# ============================================================================
with tab2:
    st.header("Step 2: Certification Scoring & Manual Inputs")
    st.caption(
        "Use the sidebar for **pMOS (Voice)**, **Site Infrastructure Audit**, and the live **Scoring Card**."
    )

    if st.session_state.metrics_data is None or scores_df is None:
        st.info("👈 Please process data in the 'Data Processing' tab first.")
    else:
        carriers = st.session_state.metrics_data["Carrier"].unique()

        st.subheader("Certification Scorecards")

        dashboard = DashboardUI(
            st.session_state.metrics_data,
            scores_df,
            st.session_state.manual_inputs,
        )

        cols = st.columns(min(3, len(carriers)))
        for idx, carrier in enumerate(carriers):
            with cols[idx % len(cols)]:
                carrier_metrics = st.session_state.metrics_data[
                    st.session_state.metrics_data["Carrier"] == carrier
                ]
                carrier_score = scores_df[scores_df["Carrier"] == carrier].iloc[0]

                dashboard.render_certification_card(
                    carrier,
                    carrier_metrics,
                    carrier_score,
                    st.session_state.manual_inputs[carrier],
                )

        render_engineering_insights_section(
            carriers,
            st.session_state.metrics_data,
            scores_df,
            scoring_details,
            st.session_state.manual_inputs,
        )

        st.subheader("Detailed Metrics Table")
        detailed_view = build_detailed_metrics_display_dataframe(
            st.session_state.metrics_data.copy()
        )
        st.dataframe(
            detailed_view,
            width="stretch",
            height=400,
            column_config=build_column_config_for_metrics_display(detailed_view),
        )

# ============================================================================
# TAB 3: EXPORT RESULTS
# ============================================================================
with tab3:
    st.header("Step 3: Export Final Certification CSV")
    
    if st.session_state.final_output is None:
        st.info("👈 Please complete the certification review in the previous tab.")
    else:
        st.success("✓ Ready to export final certification data")
        
        # Create export CSV
        export_df = pd.DataFrame()
        
        for carrier in st.session_state.final_output['metrics']['Carrier'].unique():
            carrier_metrics = st.session_state.final_output['metrics'][
                st.session_state.final_output['metrics']['Carrier'] == carrier
            ].iloc[0]
            
            carrier_score = st.session_state.final_output['scores'][
                st.session_state.final_output['scores']['Carrier'] == carrier
            ].iloc[0]
            
            manual_input = st.session_state.final_output['manual_inputs'].get(
                carrier, {}
            )
            
            row = {
                'Carrier': carrier,
                # RF Health Pillar (4 metrics)
                'RSRP_Summary': carrier_metrics.get('RSRP_Summary', ''),
                'RSRQ_dB': carrier_metrics.get('RSRQ_dB', ''),
                'SINR_Summary': carrier_metrics.get('SINR_Summary', ''),
                'RSSI_dBm': carrier_metrics.get('RSSI_dBm', ''),
                # Derived (1 metric)
                'Noise_Floor': carrier_metrics.get('Noise_Floor', ''),
                # Capacity Pillar (5 metrics)
                'Total_BW_MHz': carrier_metrics.get('Total_BW_MHz', ''),
                'Final_5G_State': carrier_metrics.get('Final_5G_State', ''),
                'Handover_Success_Pct': carrier_metrics.get('Handover_Success_Pct', ''),
                'CQI_Tool': carrier_metrics.get('CQI_Tool', ''),
                'Modulation_Tool': carrier_metrics.get('Modulation_Tool', ''),
                # Infrastructure Pillar (4 metrics)
                'TX_Power_dBm': carrier_metrics.get('TX_Power_dBm', ''),
                'MIMO_Rank_Max': carrier_metrics.get('MIMO_Rank_Max', ''),
                'Band_Diversity_Count': carrier_metrics.get('Band_Diversity_Count', ''),
                'CA_Count': carrier_metrics.get('CA_Count', ''),
                # Experience & QoS Pillar (6 metrics)
                'Primary_Coverage_Pct': carrier_metrics.get('Primary_Coverage_Pct', ''),
                'Peak_DL_Mbps': carrier_metrics.get('Peak_DL_Mbps', ''),
                'Peak_UL_Mbps': carrier_metrics.get('Peak_UL_Mbps', ''),
                'Peak_DL_Gbps': carrier_metrics.get('Peak_DL_Gbps', ''),
                'Peak_UL_Gbps': carrier_metrics.get('Peak_UL_Gbps', ''),
                'Peak_DL_Mbps_Median_Gbps': carrier_metrics.get(
                    'Peak_DL_Mbps_Median_Gbps', ''
                ),
                'Median_Jitter_ms': carrier_metrics.get('Median_Jitter_ms', ''),
                'Packet_Loss_Pct': carrier_metrics.get('Packet_Loss_Pct', ''),
                'Median_Latency_ms': carrier_metrics.get('Median_Latency_ms', ''),
                # Methodology / manual (Alan)
                'VPN_Usage': manual_input.get('vpn_type')
                or manual_input.get('vpn_usage', ''),
                'ISP_Redundancy': manual_input.get('isp_redundancy', ''),
                'ISP_Diversity': manual_input.get('isp_diversity', ''),
                'Hardware_Age': manual_input.get('hardware_age', ''),
                # Scoring Results
                'Certification_Badge': carrier_score.get('Badge', 'N/A'),
                'Certification_Score': carrier_score.get('Score', 0),
                'Weighted_Avg_Raw_0_4': carrier_score.get('Weighted_Avg_Raw', ''),
                'PMOS_Score_Used': carrier_score.get('PMOS_Score_Used', ''),
                'PMOS_Capped': carrier_score.get('PMOS_Capped', False),
                'Bucket_HIGH_Weighted': carrier_score.get('Bucket_HIGH_Weighted', ''),
                'Bucket_MEDIUM_Weighted': carrier_score.get('Bucket_MEDIUM_Weighted', ''),
                'Bucket_LOW_Weighted': carrier_score.get('Bucket_LOW_Weighted', ''),
            }
            
            export_df = pd.concat([export_df, pd.DataFrame([row])], ignore_index=True)
        
        # Display preview
        st.subheader("Export Preview")
        
        # Format display copy (keep numeric in actual export)
        display_df = export_df.copy()
        speed_cols = ['Peak_DL_Mbps', 'Peak_UL_Mbps']
        for col in speed_cols:
            if col in display_df.columns:
                display_df[col] = display_df[col].apply(
                    lambda x: format_speed_mbps(x)
                    if pd.notna(x) and x != ''
                    else x
                )
        gbps_cols = [
            'Peak_DL_Gbps',
            'Peak_UL_Gbps',
            'Peak_DL_Mbps_Median_Gbps',
        ]
        for col in gbps_cols:
            if col in display_df.columns:
                display_df[col] = display_df[col].apply(
                    lambda x: f"{float(x):.2f} Gbps"
                    if pd.notna(x) and x != ''
                    else x
                )
        if 'Certification_Score' in display_df.columns:
            display_df['Certification_Score'] = display_df['Certification_Score'].apply(
                lambda x: format_cert_score_whole(x) if pd.notna(x) and x != '' else x
            )

        st.dataframe(
            display_df,
            width="stretch",
            height=300,
            column_config=build_column_config_for_metrics_display(display_df),
        )
        
        # Export buttons
        col1, col2 = st.columns(2)
        
        with col1:
            csv_data = export_df.to_csv(index=False)
            st.download_button(
                label="📥 Download as CSV",
                data=csv_data,
                file_name="Cellular_Certification_Results.csv",
                mime="text/csv",
                type="primary"
            )
        
        with col2:
            excel_buffer = BytesIO()
            export_df.to_excel(excel_buffer, index=False)
            excel_data = excel_buffer.getvalue()
            st.download_button(
                label="📥 Download as Excel",
                data=excel_data,
                file_name="Cellular_Certification_Results.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        
        # Summary statistics
        st.subheader("Certification Summary")
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            platinum = len(export_df[export_df['Certification_Badge'] == 'Platinum'])
            st.metric("Platinum", platinum)
        with col2:
            gold = len(export_df[export_df['Certification_Badge'] == 'Gold'])
            st.metric("Gold", gold)
        with col3:
            silver = len(export_df[export_df['Certification_Badge'] == 'Silver'])
            st.metric("Silver", silver)
        with col4:
            fail = len(export_df[export_df['Certification_Badge'] == 'Fail'])
            st.metric("Fail", fail)

# ============================================================================
# TAB 4: GEOSPATIAL COMPLIANCE MAP
# ============================================================================
with tab4:
    if st.session_state.final_output is None:
        st.info("👈 Please complete the data processing and certification review in the previous tabs.")
    else:
        try:
            # Get raw data from session (need to re-read since it was loaded in tab1)
            if 'raw_data' not in st.session_state:
                st.warning("Raw data not available. Please re-upload the file in Tab 1 and process again.")
            else:
                # Create geospatial layer
                geo_layer = GeospatialLayer(
                    st.session_state.raw_data,
                    st.session_state.final_output['metrics'],
                    st.session_state.final_output['scores']
                )
                st.caption(
                    "**All-operator reports:** **RSRP**, **SINR**, **Download Speed** (`Access_Speed_Mean`), **Latency**, **Jitter** — "
                    "same **2×3** Olli grid (combined tech, morphological footprint, vertical legend; Mbps / ms / dBm on colorbars). "
                    "ZIP packs each metric you generate this session (high-resolution PNG)."
                )
                geo_layer.render_certification_map()
        
        except Exception as e:
            st.error(f"Error rendering map: {str(e)}")
            st.info("Please ensure your data contains Latitude and Longitude columns.")

# ============================================================================
# TAB 5: METHODOLOGY SANDBOX (PRODUCT OWNER)
# ============================================================================
with tab5:
    st.header("🧪 Methodology Sandbox")
    st.markdown(
        """
        **For Alan (Product Owner):** tier weights are fixed at **HIGH 2.25 / MEDIUM 0.25 / LOW 0.125** in the engine.
        Use the sidebar for **Site Infrastructure Audit** and **pMOS (Voice)**. Inspect how **raw points (0–4)** flow
        through the tiers into the **0–100** score. If **pMOS < 3.5**, certification **cannot exceed Silver**.
        """
    )

    if st.session_state.metrics_data is None or not scoring_details:
        st.info("Process data in **Data Processing** to explore methodology outputs.")
    else:
        carriers_ms = list(st.session_state.metrics_data["Carrier"].unique())
        pick = st.selectbox(
            "Carrier to analyze",
            carriers_ms,
            key="methodology_sandbox_carrier",
        )
        det = scoring_details.get(pick, {})
        if det:
            c1, c2, c3 = st.columns(3)
            with c1:
                st.metric("Score (0–100)", f"{det.get('score_100', 0):.2f}")
            with c2:
                st.metric("Weighted avg raw (0–4)", f"{det.get('weighted_avg_raw', 0):.3f}")
            with c3:
                st.metric("pMOS cap applied", "Yes" if det.get("pmos_capped") else "No")

            st.subheader("Bucket scoring card")
            st.caption(
                "Each row: count of metrics in the tier, sum of raw points, shared weight per metric, "
                "and Σ(Raw×Weight) (equals weight × Σ Raw within the tier)."
            )
            _bucket_tab5 = coerce_metrics_column_to_str(build_bucket_scoring_card_df(det))
            st.dataframe(
                _bucket_tab5,
                width="stretch",
                hide_index=True,
            )

            st.subheader("Per-metric contributions")
            st.dataframe(
                build_metric_scoring_card_df(det),
                width="stretch",
                hide_index=True,
                height=400,
            )

            with st.expander("Active methodology parameters"):
                st.json(methodology)
