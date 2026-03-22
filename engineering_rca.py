"""
Engineering Insights & automated Root Cause Analysis (Innovation Phase 2).
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
import streamlit as st


RCA_RAW_THRESHOLD = 2.0  # Poor / Limited boundary (raw < 2)

# Total BW (MHz) below this suggests mid-band / CA review (aligns with scoring "Good" band)
SPECTRUM_BW_MHZ_HINT = 40.0


def _fmt_num(x: Any, suffix: str = "", nd: int = 1) -> str:
    try:
        if pd.isna(x):
            return "N/A"
        return f"{float(x):.{nd}f}{suffix}"
    except (TypeError, ValueError):
        return str(x)


def _metric_display_value(metric_label: str, metrics: pd.Series, manual: Dict[str, Any]) -> str:
    m = metrics
    if metric_label == "Peak DL (Mbps)":
        return _fmt_num(m.get("Peak_DL_Mbps"), " Mbps", 1)
    if metric_label == "Peak UL (Mbps)":
        return _fmt_num(m.get("Peak_UL_Mbps"), " Mbps", 1)
    if metric_label == "RSRP Summary":
        return _fmt_num(m.get("RSRP_Summary"), " dBm", 0)
    if metric_label == "SINR Summary":
        return _fmt_num(m.get("SINR_Summary"), " dB", 1)
    if metric_label == "Median Latency (ms)":
        return _fmt_num(m.get("Median_Latency_ms"), " ms", 0)
    if metric_label == "Primary Coverage %":
        return _fmt_num(m.get("Primary_Coverage_Pct"), "%", 1)
    if metric_label == "ISP Redundancy":
        return str(manual.get("isp_redundancy", "N/A"))
    if metric_label == "RSRQ (dB)":
        return _fmt_num(m.get("RSRQ_dB"), " dB", 1)
    if metric_label == "Median Jitter (ms)":
        return _fmt_num(m.get("Median_Jitter_ms"), " ms", 1)
    if metric_label == "Packet Loss %":
        return _fmt_num(m.get("Packet_Loss_Pct"), "%", 2)
    if metric_label == "Handover Success %":
        return _fmt_num(m.get("Handover_Success_Pct"), "%", 1)
    if metric_label == "Total BW (MHz)":
        return _fmt_num(m.get("Total_BW_MHz"), " MHz", 1)
    if metric_label == "ISP Diversity":
        return str(manual.get("isp_diversity", "N/A"))
    if metric_label == "TX Power (dBm)":
        return _fmt_num(m.get("TX_Power_dBm"), " dBm", 0)
    if metric_label == "MIMO Rank Max":
        v = m.get("MIMO_Rank_Max")
        return str(int(v)) if pd.notna(v) else "N/A"
    if metric_label == "CA Count":
        v = m.get("CA_Count")
        return str(int(v)) if pd.notna(v) else "N/A"
    if metric_label == "Band Diversity Count":
        v = m.get("Band_Diversity_Count")
        return str(int(v)) if pd.notna(v) else "N/A"
    if metric_label == "CQI":
        return _fmt_num(m.get("CQI_Tool"), "", 0)
    if metric_label == "Modulation":
        return str(m.get("Modulation_Tool", "N/A"))
    if metric_label in ("VPN Usage", "VPN Type"):
        return str(
            manual.get("vpn_type")
            or manual.get("vpn_usage")
            or "N/A"
        )
    if metric_label == "Hardware Age":
        return str(manual.get("hardware_age", "N/A"))
    return "N/A"


def _weak_issue_phrase(metric_label: str, grade: str, display_val: str) -> str:
    """Short clause for narrative."""
    g = (grade or "").lower()
    if metric_label == "ISP Redundancy":
        return f"lack of ISP redundancy ({display_val})"
    if metric_label == "ISP Diversity":
        return f"limited ISP diversity ({display_val})"
    if metric_label == "SINR Summary":
        return f"SINR interference ({display_val})"
    if metric_label == "RSRP Summary":
        return f"weak RSRP ({display_val})"
    if metric_label == "Median Latency (ms)":
        return f"elevated latency ({display_val})"
    if metric_label == "Peak DL (Mbps)":
        return f"limited download throughput ({display_val})"
    if metric_label == "Peak UL (Mbps)":
        return f"limited upload throughput ({display_val})"
    if metric_label == "Primary Coverage %":
        return f"coverage gaps ({display_val})"
    if metric_label == "TX Power (dBm)":
        return f"high UE TX power ({display_val})"
    if metric_label == "VPN Usage" or metric_label == "VPN Type":
        return f"VPN usage profile ({display_val})"
    if metric_label == "Packet Loss %":
        return f"packet loss ({display_val})"
    if metric_label == "Total BW (MHz)":
        return f"limited aggregated spectrum bandwidth ({display_val})"
    return f"{metric_label} at {g} levels ({display_val})"


def _spectrum_5g_insight(metrics: pd.Series) -> Optional[str]:
    """
    Flag likely 5G spectrum / mid-band gaps for RCA (n41/n77 style guidance).
    """
    bw = pd.to_numeric(metrics.get("Total_BW_MHz"), errors="coerce")
    state = str(metrics.get("Final_5G_State", "") or "").strip()
    if pd.notna(bw) and float(bw) < SPECTRUM_BW_MHZ_HINT:
        return (
            "**5G spectrum / bandwidth:** Low aggregated spectrum bandwidth detected "
            f"(**{_fmt_num(bw, ' MHz', 1)}**); suggest checking **5G mid-band (e.g. n41/n77)** "
            "availability, channel width, and carrier aggregation."
        )
    if state in ("None", "NSA") and pd.notna(bw) and float(bw) < 80:
        return (
            "**5G spectrum:** Deployment is **NSA** or **LTE-anchored** with moderate bandwidth "
            f"({_fmt_num(bw, ' MHz', 1)}); validate **n41/n77** layers and aggregation to improve capacity."
        )
    return None


def _positive_caveat(
    badge: str,
    metric_rows: List[Dict[str, Any]],
    metrics: pd.Series,
    weak_metric_names: List[str],
) -> Optional[str]:
    """For top badges, add engineering caveats (e.g. TX power) if not already flagged as weak."""
    if badge not in ("Platinum", "Gold"):
        return None
    if "TX Power (dBm)" in weak_metric_names:
        return None
    tx_raw = next(
        (r["Raw (0–4)"] for r in metric_rows if r["Metric"] == "TX Power (dBm)"),
        None,
    )
    tx_val = metrics.get("TX_Power_dBm")
    if tx_raw is not None and tx_raw >= 2 and pd.notna(tx_val) and float(tx_val) >= 18:
        return (
            f"However, elevated TX power ({_fmt_num(tx_val, ' dBm', 0)}) suggests "
            "potential long-term battery drain for mobile clients."
        )
    return None


def build_carrier_rca_summary(
    carrier: str,
    metrics: pd.Series,
    badge: str,
    detail: Dict[str, Any],
    manual: Dict[str, Any],
    raw_threshold: float = RCA_RAW_THRESHOLD,
) -> str:
    """Single-paragraph engineering narrative for one carrier."""
    rows = detail.get("metric_rows", [])
    weak = [r for r in rows if float(r.get("Raw (0–4)", 4)) < raw_threshold]
    weak_sorted = sorted(weak, key=lambda r: (r.get("Tier", ""), r["Metric"]))
    weak_names = [r["Metric"] for r in weak_sorted]

    parts: List[str] = []

    if detail.get("pmos_capped"):
        pmos = detail.get("pmos_score")
        if pmos is not None:
            parts.append(
                f"**{carrier}**: Certification grade is capped at **Silver** because the voice "
                f"**pMOS** score (**{pmos:.1f}**) is below **3.5** (with pMOS test enabled)."
            )
        else:
            parts.append(
                f"**{carrier}**: Certification grade is capped at **Silver** under the voice pMOS rule."
            )

    issue_clauses: List[str] = []
    for r in weak_sorted[:5]:
        label = r["Metric"]
        disp = _metric_display_value(label, metrics, manual)
        issue_clauses.append(_weak_issue_phrase(label, r.get("Grade", ""), disp))

    caveat = _positive_caveat(badge, rows, metrics, weak_names)

    if issue_clauses:
        joined = ", ".join(issue_clauses[:4])
        if len(issue_clauses) > 4:
            joined += ", and additional limiters"
        if detail.get("pmos_capped"):
            core = (
                f"**{carrier}**: At **the venue**, contributing RF / site factors "
                f"(raw < {raw_threshold}) include {joined}."
            )
        elif badge in ("Platinum", "Gold"):
            core = (
                f"**{carrier}**: {badge} status achieved at **the site**; focus areas include {joined}."
            )
        elif badge == "Silver":
            core = (
                f"**{carrier}**: **Silver** certification at **the venue**; drivers include {joined}."
            )
        else:
            core = f"**{carrier}**: Below target at **the site**; key gaps include {joined}."
        if caveat:
            core = core.rstrip(".") + f" {caveat}"
        parts.append(core)
    elif not parts:
        if badge in ("Platinum", "Gold"):
            msg = (
                f"**{carrier}**: **{badge}** status achieved; no metrics fell below the "
                f"RCA threshold (raw < {raw_threshold})."
            )
            if caveat:
                msg = msg.rstrip(".") + f" {caveat}"
            parts.append(msg)
        else:
            parts.append(
                f"**{carrier}**: **{badge}** — review detailed metrics and manual inputs for uplift opportunities."
            )

    if detail.get("pmos_capped") and not issue_clauses and len(parts) == 1:
        parts.append(
            f"No metrics fell below the RCA raw threshold ({raw_threshold}); "
            "the Silver cap is driven solely by the pMOS rule."
        )

    spec = _spectrum_5g_insight(metrics)
    if spec:
        parts.append(spec)

    return "\n\n".join(parts)


def render_engineering_insights_section(
    carriers,
    metrics_df: pd.DataFrame,
    scores_df: pd.DataFrame,
    scoring_details: Dict[str, Dict[str, Any]],
    manual_by_carrier: Dict[str, Dict[str, Any]],
) -> None:
    st.subheader("📊 Engineering Insights & Root Cause Analysis")
    st.caption(
        f"Automated RCA for **the venue** flags any scored metric with **raw points below {RCA_RAW_THRESHOLD}** "
        "(Poor/Limited), adds **5G spectrum / n41·n77** guidance when bandwidth is thin, "
        "and stitches a concise narrative with live values."
    )
    for carrier in carriers:
        mrow = metrics_df[metrics_df["Carrier"] == carrier].iloc[0]
        srow = scores_df[scores_df["Carrier"] == carrier].iloc[0]
        detail = scoring_details.get(carrier, {})
        manual = manual_by_carrier.get(carrier, {})
        text = build_carrier_rca_summary(
            carrier,
            mrow,
            srow.get("Badge", "Fail"),
            detail,
            manual,
        )
        with st.expander(f"🔎 {carrier} — Insights", expanded=False):
            st.markdown(text)
