"""
Shared numeric display formatting for certification UI (Streamlit metrics, tables, popups).
"""

from __future__ import annotations

from typing import Any, Dict, Optional

import pandas as pd


def mbps_to_gbps(mbps: Any) -> Optional[float]:
    """Convert Mbps to Gbps (Mbps / 1000). Returns None if not numeric."""
    if pd.isna(mbps) or mbps == "" or mbps == "N/A":
        return None
    try:
        v = float(mbps)
    except (TypeError, ValueError):
        return None
    return v / 1000.0


def format_cert_score_whole(value: Any) -> str:
    """Certification scores as whole numbers (no trailing decimals)."""
    if pd.isna(value) or value == "" or value == "N/A":
        return "N/A"
    try:
        return str(int(round(float(value))))
    except (TypeError, ValueError):
        return str(value)


def format_speed_mbps(value: Any) -> str:
    """Speed in Mbps: thousands separator, exactly 2 decimal places."""
    if pd.isna(value) or value == "" or value == "N/A":
        return "N/A"
    try:
        return f"{float(value):,.2f} Mbps"
    except (TypeError, ValueError):
        return str(value)


def format_speed_gbps(value: Any) -> str:
    """Gbps from Mbps/1000, 2 decimal places."""
    g = mbps_to_gbps(value)
    if g is None:
        return "N/A"
    return f"{g:.2f} Gbps"


def format_speed_mbps_gbps_line(mbps_value: Any) -> str:
    """Single line for st.metric: Mbps and Gbps alongside."""
    if pd.isna(mbps_value) or mbps_value == "" or mbps_value == "N/A":
        return "N/A"
    try:
        m = float(mbps_value)
    except (TypeError, ValueError):
        return str(mbps_value)
    g = m / 1000.0
    return f"{m:,.2f} Mbps · {g:.2f} Gbps"


def format_signal_whole(value: Any) -> str:
    """RSRP / RSRQ style: whole number only (unit supplied by st.metric label)."""
    if pd.isna(value) or value == "" or value == "N/A":
        return "N/A"
    try:
        return str(int(round(float(value))))
    except (TypeError, ValueError):
        return str(value)


def format_latency_ms_whole(value: Any) -> str:
    """Latency / jitter in ms as whole numbers."""
    if pd.isna(value) or value == "" or value == "N/A":
        return "N/A"
    try:
        return str(int(round(float(value))))
    except (TypeError, ValueError):
        return str(value)


def _is_mbps_speed_column(name: str) -> bool:
    if name.endswith("_Gbps"):
        return False
    return "Mbps" in name


def _is_signal_whole_column(name: str) -> bool:
    return name in (
        "RSRP_Summary",
        "RSRQ_dB",
        "SINR_Summary",
        "RSSI_dBm",
        "TX_Power_dBm",
        "Noise_Floor",
    )


def _is_latency_ms_column(name: str) -> bool:
    return name in ("Median_Latency_ms", "Median_Jitter_ms")


def build_detailed_metrics_display_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Return a copy of metrics suitable for st.dataframe: formatted strings and rules
    from the spec (speed / signal / latency). Gbps columns are formatted next to Mbps sources.
    """
    out = df.copy()
    for col in list(out.columns):
        if col == "Carrier":
            continue
        series = out[col]
        if not pd.api.types.is_numeric_dtype(series):
            continue
        if _is_mbps_speed_column(col):
            out[col] = series.map(lambda x: format_speed_mbps(x) if pd.notna(x) else "N/A")
        elif col.endswith("_Gbps"):
            out[col] = series.map(
                lambda x: f"{float(x):.2f} Gbps" if pd.notna(x) else "N/A"
            )
        elif _is_signal_whole_column(col):
            if col == "RSRQ_dB" or col == "SINR_Summary":
                suffix = " dB"
            elif col in ("RSRP_Summary", "RSSI_dBm", "TX_Power_dBm", "Noise_Floor"):
                suffix = " dBm"
            else:
                suffix = ""
            out[col] = series.map(
                lambda x, s=suffix: (
                    f"{format_signal_whole(x)}{s}" if pd.notna(x) else "N/A"
                )
            )
        elif _is_latency_ms_column(col):
            out[col] = series.map(
                lambda x: f"{format_latency_ms_whole(x)} ms" if pd.notna(x) else "N/A"
            )
    return out


def build_column_config_for_metrics_display(df: pd.DataFrame) -> Dict[str, Any]:
    """TextColumn only for object/string columns (formatted strings), leave true numeric as default."""
    import streamlit as st

    cfg: Dict[str, Any] = {}
    for col in df.columns:
        if col == "Carrier":
            continue
        s = df[col]
        if pd.api.types.is_object_dtype(s) or pd.api.types.is_string_dtype(s):
            cfg[col] = st.column_config.TextColumn(col)
    return cfg


def format_popup_dl_speed(mbps_val: Any) -> str:
    """Folium popup: Mbps (grouped) + Gbps."""
    if pd.isna(mbps_val):
        return "No data"
    try:
        m = float(mbps_val)
    except (TypeError, ValueError):
        return "No data"
    if m <= 0:
        return "No data"
    g = m / 1000.0
    return f"{m:,.2f} Mbps ({g:.2f} Gbps)"


def format_popup_signal_dbm(val: Any) -> str:
    if pd.isna(val):
        return "No data"
    try:
        return f"{int(round(float(val)))} dBm"
    except (TypeError, ValueError):
        return "No data"


def format_popup_sinr_db(val: Any) -> str:
    if pd.isna(val):
        return "No data"
    try:
        return f"{int(round(float(val)))} dB"
    except (TypeError, ValueError):
        return "No data"
