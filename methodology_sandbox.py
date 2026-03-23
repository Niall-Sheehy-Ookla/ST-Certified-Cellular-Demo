"""
Methodology Sandbox — defaults and UI helpers for Product Owner tuning (Alan).
"""

from __future__ import annotations

from typing import Any, Dict, List

import pandas as pd

# Default per-metric weights by tier (tunable in sidebar)
DEFAULT_WEIGHT_HIGH = 2.25
DEFAULT_WEIGHT_MEDIUM = 0.25
DEFAULT_WEIGHT_LOW = 0.125

# Manual input option sets (must match app sidebar)
VPN_TYPE_OPTIONS = ("None", "Consumer", "Corporate/IPSec")
ISP_REDUNDANCY_OPTIONS = ("None", "Warm Standby", "Active/Active")
ISP_DIVERSITY_OPTIONS = ("Single Entry", "Dual Entry", "Diverse Paths")
HARDWARE_AGE_OPTIONS = ("Legacy < 2 years", "Modern 2-4 years", "State-of-the-art")


def default_manual_inputs() -> Dict[str, Any]:
    return {
        "vpn_type": "None",
        "vpn_usage": "None",
        "isp_redundancy": "None",
        "isp_diversity": "Single Entry",
        "hardware_age": "Modern 2-4 years",
        "notes": "",
    }


def migrate_manual_dict(manual: Dict[str, Any]) -> Dict[str, Any]:
    """Map legacy session keys to Methodology Sandbox fields."""
    out = default_manual_inputs()
    if not manual:
        return out
    if "vpn_type" in manual:
        out["vpn_type"] = manual["vpn_type"]
    elif "vpn_usage" in manual:
        mapping = {
            "Standard": "None",
            "VPN-Lite": "Consumer",
            "VPN-Full": "Corporate/IPSec",
        }
        vu = manual.get("vpn_usage", "None")
        out["vpn_type"] = mapping.get(vu, vu if vu in VPN_TYPE_OPTIONS else "None")
        out["vpn_usage"] = out["vpn_type"]
    if "isp_redundancy" in manual:
        lr = manual["isp_redundancy"]
        rmap = {
            "None": "None",
            "Fibre+1": "Warm Standby",
            "Fibre+2": "Warm Standby",
            "Diverse": "Diverse Paths",
            "Warm Standby": "Warm Standby",
            "Active/Active": "Active/Active",
        }
        out["isp_redundancy"] = rmap.get(lr, "None")
    if "isp_diversity" in manual:
        d = manual["isp_diversity"]
        dmap = {
            "Single": "Single Entry",
            "Dual": "Dual Entry",
            "Triple+": "Diverse Paths",
            "Single Entry": "Single Entry",
            "Dual Entry": "Dual Entry",
            "Diverse Paths": "Diverse Paths",
        }
        out["isp_diversity"] = dmap.get(d, "Single Entry")
    if "hardware_age" in manual:
        out["hardware_age"] = manual["hardware_age"]
    elif "ap_model" in manual:
        amap = {
            "Old (2020)": "Legacy < 2 years",
            "Standard (2022)": "Modern 2-4 years",
            "Modern (2024)": "Modern 2-4 years",
            "Latest (2025)": "State-of-the-art",
        }
        out["hardware_age"] = amap.get(manual.get("ap_model"), "Modern 2-4 years")
    if "notes" in manual:
        out["notes"] = manual["notes"]
    out["vpn_usage"] = out["vpn_type"]
    return out


def coerce_metrics_column_to_str(df: pd.DataFrame) -> pd.DataFrame:
    """
    PyArrow / st.dataframe: bucket summaries use int counts and '' in ``Metrics`` — force str.
    """
    if df is None or len(df) == 0 or "Metrics" not in df.columns:
        return df
    out = df.copy()
    out["Metrics"] = out["Metrics"].astype(str)
    return out


def build_bucket_scoring_card_df(detail: Dict[str, Any]) -> pd.DataFrame:
    """
    Summary rows: [Raw Points] × [Weight] = [Weighted Score] per tier + total.
    Uses sum(raw_i) * w_tier == sum(raw_i * w_tier) when all metrics in tier share w.
    """
    rows: List[Dict[str, Any]] = []
    for tier in ("HIGH", "MEDIUM", "LOW"):
        key = tier.lower()
        rs = detail.get(f"{key}_raw_sum", 0)
        w = detail.get(f"{key}_weight", 0.0)
        ws = detail.get(f"{key}_weighted_sum", 0.0)
        wmax = detail.get(f"{key}_max_weighted", 0.0)
        n = detail.get(f"{key}_metric_count", 0)
        rows.append(
            {
                "Tier": tier,
                "Metrics": n,
                "Σ Raw points (0–4)": rs,
                "Weight / metric": w,
                "Σ(Raw × Weight)": round(ws, 4),
                "Max Σ for tier": round(wmax, 4),
            }
        )
    rows.append(
        {
            "Tier": "TOTAL (0–100)",
            "Metrics": "",
            "Σ Raw points (0–4)": "",
            "Weight / metric": "normalized",
            "Σ(Raw × Weight)": round(detail.get("score_100", 0), 2),
            "Max Σ for tier": "100 (points scale)",
        }
    )
    return pd.DataFrame(rows)


def build_metric_scoring_card_df(detail: Dict[str, Any]) -> pd.DataFrame:
    """Per-metric lines for the sandbox."""
    mrows = detail.get("metric_rows", [])
    if not mrows:
        return pd.DataFrame()
    return pd.DataFrame(mrows)
