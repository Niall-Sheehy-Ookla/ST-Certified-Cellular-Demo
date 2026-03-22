"""
Hidden geospatial presets: venue anchors loaded from JSON (no PO-facing controls).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import pandas as pd

_CONFIG_PATH = Path(__file__).resolve().parent / "seattle_anchors.json"


def _project_root() -> Path:
    return Path(__file__).resolve().parent


def load_seattle_anchor_config() -> Optional[Dict[str, Any]]:
    if not _CONFIG_PATH.is_file():
        return None
    try:
        with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


def _bbox_from_df(df: pd.DataFrame) -> Optional[Tuple[float, float, float, float]]:
    if df is None or len(df) == 0:
        return None
    if "Latitude" not in df.columns or "Longitude" not in df.columns:
        return None
    lat = pd.to_numeric(df["Latitude"], errors="coerce")
    lon = pd.to_numeric(df["Longitude"], errors="coerce")
    ok = lat.notna() & lon.notna()
    if not ok.any():
        return None
    return (
        float(lat[ok].min()),
        float(lat[ok].max()),
        float(lon[ok].min()),
        float(lon[ok].max()),
    )


def dataset_matches_seattle_preset(df: pd.DataFrame) -> bool:
    """
    True when the dataset's geographic midpoint (valid lat/lon rows) lies inside
    the `detect` bounds in seattle_anchors.json (enables the Seattle venue preset).
    """
    cfg = load_seattle_anchor_config()
    if not cfg:
        return False
    bb = _bbox_from_df(df)
    if bb is None:
        return False
    lat_lo, lat_hi, lon_lo, lon_hi = bb
    det = cfg.get("detect") or {}
    try:
        lat_min = float(det["lat_min"])
        lat_max = float(det["lat_max"])
        lon_min = float(det["lon_min"])
        lon_max = float(det["lon_max"])
    except (KeyError, TypeError, ValueError):
        return False
    lat_mid = 0.5 * (lat_lo + lat_hi)
    lon_mid = 0.5 * (lon_lo + lon_hi)
    return (
        lat_min <= lat_mid <= lat_max
        and lon_min <= lon_mid <= lon_max
    )


def read_bytes_if_exists(relative_path: str) -> Optional[bytes]:
    p = _project_root() / relative_path
    if not p.is_file():
        return None
    try:
        return p.read_bytes()
    except OSError:
        return None


def get_seattle_spatial_anchors() -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """
    Anchors from seattle_anchors.json only (no floor-plan file required).
    Used when the CSV matches Seattle; floor image may come from upload or assets.
    """
    cfg = load_seattle_anchor_config()
    if not cfg:
        return None, "Missing or invalid seattle_anchors.json"
    spa = cfg.get("spatial_anchors") or {}
    try:
        anchors = {
            "lon_west": float(spa["lon_west"]),
            "lon_east": float(spa["lon_east"]),
            "lat_south": float(spa["lat_south"]),
            "lat_north": float(spa["lat_north"]),
            "flip_north": bool(spa.get("flip_north", True)),
            "venue_report_name": str(cfg.get("venue_report_name") or "Seattle Office New"),
        }
    except (KeyError, TypeError, ValueError):
        return None, "Invalid spatial_anchors in seattle_anchors.json"
    if anchors["lon_east"] <= anchors["lon_west"] or anchors["lat_north"] <= anchors["lat_south"]:
        return None, "Invalid anchor ordering (east≤west or north≤south)."
    return anchors, None


def get_seattle_certified_assets() -> Tuple[
    Optional[Dict[str, Any]],
    Optional[bytes],
    Optional[str],
]:
    """
    Returns (anchors dict, floorplan bytes, error message).
    anchors includes: lon_west, lon_east, lat_south, lat_north, flip_north
    """
    cfg = load_seattle_anchor_config()
    if not cfg:
        return None, None, "Missing or invalid seattle_anchors.json"
    spa = cfg.get("spatial_anchors") or {}
    try:
        anchors = {
            "lon_west": float(spa["lon_west"]),
            "lon_east": float(spa["lon_east"]),
            "lat_south": float(spa["lat_south"]),
            "lat_north": float(spa["lat_north"]),
            "flip_north": bool(spa.get("flip_north", True)),
            "venue_report_name": str(cfg.get("venue_report_name") or "Seattle Office New"),
        }
    except (KeyError, TypeError, ValueError):
        return None, None, "Invalid spatial_anchors in seattle_anchors.json"
    rel = cfg.get("floorplan_relative_path") or "assets/image (3).png"
    data = read_bytes_if_exists(rel)
    if not data:
        return None, None, f"Floor plan image not found at {rel} (place file under project root)."
    if anchors["lon_east"] <= anchors["lon_west"] or anchors["lat_north"] <= anchors["lat_south"]:
        return None, None, "Invalid anchor ordering (east≤west or north≤south)."
    return anchors, data, None


def default_seattle_floorplan_relative_path() -> str:
    cfg = load_seattle_anchor_config()
    if cfg and cfg.get("floorplan_relative_path"):
        return str(cfg["floorplan_relative_path"])
    return "assets/image (3).png"


def get_rsrp_reference_png_path() -> Optional[Path]:
    cfg = load_seattle_anchor_config()
    if not cfg:
        return None
    rel = cfg.get("rsrp_legend_png_relative_path") or "assets/cellular_rsrp_all_operators_4g_5g.png"
    p = _project_root() / rel
    return p if p.is_file() else None
