"""
Point-level 0–1 quality scores for map coloring (aligns with certification grade bands).
Red (low) → Green (high).
"""

from __future__ import annotations

import pandas as pd


def quality_rsrp_dbm(value: float) -> float:
    if pd.isna(value):
        return 0.35
    v = float(value)
    if v > -80:
        return 1.0
    if v > -95:
        return 0.75
    if v > -105:
        return 0.5
    if v > -115:
        return 0.25
    return 0.05


def quality_sinr_db(value: float) -> float:
    if pd.isna(value):
        return 0.35
    v = float(value)
    if v > 20:
        return 1.0
    if v >= 13:
        return 0.75
    if v >= 5:
        return 0.5
    if v >= 0:
        return 0.25
    return 0.05


def quality_dl_mbps(value: float) -> float:
    if pd.isna(value):
        return 0.35
    v = float(value)
    if v > 500:
        return 1.0
    if v >= 250:
        return 0.75
    if v >= 100:
        return 0.5
    if v >= 50:
        return 0.25
    return 0.05


def pick_rsrp_series(row: pd.Series) -> float:
    for col in ["5G_SS_RSRP", "5G_CSI_RSRP", "LTE_RSRP", "RSRP"]:
        if col in row.index:
            val = pd.to_numeric(row.get(col), errors="coerce")
            if pd.notna(val):
                return float(val)
    return float("nan")


def pick_sinr_series(row: pd.Series) -> float:
    for col in ["5G_SS_RSSNR", "5G_CSI_RSSNR", "LTE_RSSNR", "RSSNR", "SINR", "5G_SINR"]:
        if col in row.index:
            val = pd.to_numeric(row.get(col), errors="coerce")
            if pd.notna(val):
                return float(val)
    return float("nan")


def row_dl_mbps_kbps_source(row: pd.Series) -> float:
    """Final_Test_Speed in CSV is Kbps; convert to Mbps for grading."""
    if "Final_Test_Speed" not in row.index:
        return float("nan")
    spd = pd.to_numeric(row.get("Final_Test_Speed"), errors="coerce")
    if pd.isna(spd):
        return float("nan")
    test = str(row.get("Test", "") or "")
    if "downlink" not in test.lower():
        return float("nan")
    return float(spd) / 1000.0
