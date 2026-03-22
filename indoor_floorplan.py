"""
Indoor floor-plan heatmaps: 2×3 Olli-style certification reports (5G / LTE × three carriers),
liquid RBF field, building footprint mask, multiply blend, vertical legend, and display axes.
"""

from __future__ import annotations

from io import BytesIO
from typing import List, Optional, Sequence, Tuple

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.cm import ScalarMappable
from matplotlib.colors import LinearSegmentedColormap, Normalize
from matplotlib.figure import Figure
from PIL import Image
from scipy.interpolate import RBFInterpolator, Rbf
from scipy.ndimage import binary_closing, binary_erosion, gaussian_filter, zoom

from map_metric_quality import pick_rsrp_series, pick_sinr_series

# Certification RSRP colorbar / paint normalization (Olli: −120 … −60 dBm)
RSRP_CERT_MIN = -120.0
RSRP_CERT_MAX = -60.0
# Back-compat aliases
RSRP_OLLI_MIN = RSRP_CERT_MIN
RSRP_OLLI_MAX = RSRP_CERT_MAX

# SINR field range (dB) for normalization — Olli legend −10 … +40
SINR_PAINT_MIN = -10.0
SINR_PAINT_MAX = 40.0

# Certified heatmap metric keys (dropdown / paint pipeline)
CERT_METRIC_RSRP = "RSRP (Coverage)"
CERT_METRIC_SINR = "SINR (Quality)"
CERT_METRIC_DOWNLOAD_SPEED = "Download Speed"
CERT_METRIC_LATENCY = "Latency"
CERT_METRIC_JITTER = "Jitter"
CERT_MAP_METRIC_CHOICES: Tuple[str, ...] = (
    CERT_METRIC_RSRP,
    CERT_METRIC_SINR,
    CERT_METRIC_DOWNLOAD_SPEED,
    CERT_METRIC_LATENCY,
    CERT_METRIC_JITTER,
)

# Download speed (Mbps): higher → better; legend 0 … 500 (values above clip to best green)
DL_SPEED_PAINT_MIN = 0.0
DL_SPEED_PAINT_MAX = 500.0

# Latency (ms): 20 = good (emerald), 100 = poor (red); linear z01 + reversed liquid ramp
LATENCY_PAINT_MIN = 20.0
LATENCY_PAINT_MAX = 100.0

# Jitter (ms): 0 = good, 20 = poor; linear z01 + reversed liquid ramp
JITTER_PAINT_MIN = 0.0
JITTER_PAINT_MAX = 20.0

# High-fidelity grid (RBF evaluated on this mesh)
CERT_INDOOR_GRID_NX = 600
CERT_INDOOR_GRID_NY = 600
# Multiply cap — strong office glow; airy/pw tame street paper only
CERT_INDOOR_HEAT_ALPHA = 0.88

# Keep ≤800 points so global RBF fits quickly and extrapolates across the whole floor
RBF_MAX_SAMPLES = 800
# RBF smoothing — liquid with visible peaks/valleys
RBF_SMOOTH = 0.15
# Wide multiquadric influence on unit plan square
RBF_MULTIQUADRIC_EPSILON = 0.58

# Post-RBF Gaussian — local variation without flat sheet
POST_RBF_GAUSSIAN_SIGMA = 3.0

# Heat panels require at least this many points; below → white "No Data" (1 ⇒ only len==0)
CERT_REPORT_MIN_POINTS_FOR_HEATMAP = 1

# Multiply composite: keep near-black ink and gray floor labels readable vs heat
FLOOR_LINE_PRESERVE_MAX_CH = 0.30
FLOOR_TEXT_LUM_MIN = 0.20
FLOOR_TEXT_LUM_MAX = 0.82
FLOOR_TEXT_MAX_CH_SPREAD = 0.14

# Geographic inclusion buffer (fraction of anchor span)
GEO_INCLUSION_BUFFER_FRAC = 0.05

# PNG export DPI for certification reports (high-res handoff)
REPORT_FIGURE_DPI = 200

# Building footprint: ink threshold + morphological solid blob + border flood (no luma punch-out)
FOOTPRINT_INK_LUMA_MAX = 0.92
FOOTPRINT_PAPER_LUMA_MIN = 0.88
# Legacy 15×15 path kept only for rare empty-interior fallback
FOOTPRINT_CLOSING_KERNEL = 15
FOOTPRINT_CLOSING_ITERATIONS = 2
# Heavy closing: bridge desks + walls into one solid blob before exterior flood
BUILDING_SOLID_BLOB_KERNEL = 25
# One erosion pass on interior mask to trim outer-wall halo after closing
FOOTPRINT_EDGE_EROSION_ITERATIONS = 1

# Room / desk labels: ink stays clean; gray numerals keep heat tint for through-emerald legibility
FLOOR_LABEL_SHOW_THROUGH_FLOOR = 0.42

# Airy / pure-white: keep exterior margins light without killing office heat
AIRY_WHITE_LUMA_START = 0.93
AIRY_WHITE_LUMA_END = 0.992
AIRY_LUM_CRUSH_STRENGTH = 0.38
PURE_WHITE_BLEND_START = 0.968
PURE_WHITE_FLOOR_FRACTION = 0.95
PURE_WHITE_PW_SCALE = 0.42

# If habitable mask covers <10% of grid (>90% empty), use full footprint
HABITABLE_MIN_COVERAGE_FRAC = 0.10

# Olli RSRP colorbar tick positions (dBm)
RSRP_CBAR_TICKS_DBM: Tuple[float, ...] = (-120.0, -110.0, -100.0, -90.0, -80.0, -70.0, -60.0)

# Olli report axes (arbitrary plan units matching reference PNGs)
OLLI_DISP_X_MAX = 45.0
OLLI_DISP_Y_MAX = 35.0


def _olli_imshow_extent() -> Tuple[float, float, float, float]:
    """left, right, bottom, top for ``imshow(..., origin='upper')``."""
    return (0.0, float(OLLI_DISP_X_MAX), 0.0, float(OLLI_DISP_Y_MAX))


def _set_olli_panel_title(ax: plt.Axes, carrier: str, subtitle: str) -> None:
    ax.set_title(
        f"{carrier}\n{subtitle}",
        fontsize=10.5,
        fontweight="normal",
        fontfamily="sans-serif",
        color="#222222",
        pad=5,
        linespacing=1.15,
    )


def _style_olli_map_axes(ax: plt.Axes) -> None:
    ax.tick_params(axis="both", which="major", labelsize=8, colors="#333333")
    ax.set_xlabel("")
    ax.set_ylabel("")
    xt = np.array([0, 10, 20, 30, 40, int(OLLI_DISP_X_MAX)], dtype=np.int32)
    yt = np.array([0, 10, 20, 30, int(OLLI_DISP_Y_MAX)], dtype=np.int32)
    ax.set_xticks(xt.astype(float))
    ax.set_yticks(yt.astype(float))
    ax.set_xlim(0.0, float(OLLI_DISP_X_MAX))
    ax.set_ylim(float(OLLI_DISP_Y_MAX), 0.0)


def _rsrp_t01(dbm: float) -> float:
    return (float(dbm) - RSRP_CERT_MIN) / (RSRP_CERT_MAX - RSRP_CERT_MIN)


def olli_branded_liquid_cmap() -> LinearSegmentedColormap:
    """
    Olli RSRP ramp (0→1 = −120 → −60 dBm): blood red → orange → yellow-green → emerald.
    """
    t110 = _rsrp_t01(-110.0)
    t95 = _rsrp_t01(-95.0)
    t80 = _rsrp_t01(-80.0)
    return LinearSegmentedColormap.from_list(
        "olli_brand_liquid",
        [
            (0.0, "#8B0000"),
            (float(t110), "#FFA500"),
            (float(t95), "#ADFF2F"),
            (float(t80), "#006400"),
            (1.0, "#006400"),
        ],
        N=512,
    )


def olli_latency_jitter_inverted_ramp_cmap() -> LinearSegmentedColormap:
    """
    Reversed Olli liquid ramp: normalized t=0 → **#006400** emerald (good / low ms),
    t=1 → **#8B0000** deep red (bad / high ms). Use with linear z01 where **lower** raw ms → **lower** t.
    """
    return olli_branded_liquid_cmap().reversed()


def olli_sinr_branded_cmap() -> LinearSegmentedColormap:
    """Olli SINR ramp −10 … +40 dB: deep red → orange → yellow → light green → emerald."""
    span = SINR_PAINT_MAX - SINR_PAINT_MIN
    t10 = (10.0 - SINR_PAINT_MIN) / span
    t20 = (20.0 - SINR_PAINT_MIN) / span
    t30 = (30.0 - SINR_PAINT_MIN) / span
    t0db = (0.0 - SINR_PAINT_MIN) / span
    return LinearSegmentedColormap.from_list(
        "olli_sinr_brand",
        [
            (0.0, "#8B0000"),
            (float(t0db), "#FF6600"),
            (float(t10), "#FFCC00"),
            (float(t20), "#ADFF2F"),
            (float(t30), "#228B22"),
            (1.0, "#006400"),
        ],
        N=512,
    )


def olli_rsrp_colormap() -> LinearSegmentedColormap:
    """Legacy multi-stop ramp; reports use olli_branded_liquid_cmap()."""
    return LinearSegmentedColormap.from_list(
        "olli_rsrp",
        ["#1a0000", "#8B0000", "#FF4500", "#FFCC00", "#ADFF2F", "#00FF88", "#00FF66"],
        N=512,
    )


def certified_rsrp_colormap_from_reference_png(path: str) -> Optional[LinearSegmentedColormap]:
    try:
        img = np.asarray(Image.open(path).convert("RGB"), dtype=np.float64)
    except (OSError, ValueError):
        return None
    if img.size == 0:
        return None
    h, w, _ = img.shape
    y0 = int(h * 0.72)
    strip = img[y0:, :, :]
    if strip.shape[0] < 2 or strip.shape[1] < 8:
        strip = img[int(h * 0.55) :, :, :]
    col_med = np.median(strip, axis=0) / 255.0
    step = max(1, w // 56)
    samples = col_med[::step, :]
    if samples.shape[0] < 4:
        return None
    colors = [tuple(np.clip(row, 0.0, 1.0)) for row in samples]
    return LinearSegmentedColormap.from_list("cert_rsrp_ref_png", colors, N=512)


def paint_value_for_row(row: pd.Series, map_metric: str) -> float:
    if map_metric == CERT_METRIC_RSRP:
        v = pick_rsrp_series(row)
        if pd.isna(v):
            return float("nan")
        return float(v)
    if map_metric == CERT_METRIC_SINR:
        v = pick_sinr_series(row)
        if pd.isna(v):
            return float("nan")
        return float(v)
    if map_metric == CERT_METRIC_DOWNLOAD_SPEED:
        if "Access_Speed_Mean" not in row.index:
            return float("nan")
        v = pd.to_numeric(row.get("Access_Speed_Mean"), errors="coerce")
        if pd.isna(v):
            return float("nan")
        return float(v)
    if map_metric == CERT_METRIC_LATENCY:
        if "Latency" not in row.index:
            return float("nan")
        v = pd.to_numeric(row.get("Latency"), errors="coerce")
        if pd.isna(v):
            return float("nan")
        return float(v)
    if map_metric == CERT_METRIC_JITTER:
        if "Jitter" not in row.index:
            return float("nan")
        v = pd.to_numeric(row.get("Jitter"), errors="coerce")
        if pd.isna(v):
            return float("nan")
        return float(v)
    return float("nan")


def _geo_span_floor(
    lon_west: float, lon_east: float, lat_south: float, lat_north: float
) -> Tuple[float, float]:
    lon_span = float(lon_east - lon_west)
    lat_span = float(lat_north - lat_south)
    if abs(lon_span) < 1e-10:
        lon_span = 1e-6
    if abs(lat_span) < 1e-10:
        lat_span = 1e-6
    return lon_span, lat_span


def lonlat_to_plan_coords(
    lon: np.ndarray,
    lat: np.ndarray,
    lon_west: float,
    lon_east: float,
    lat_south: float,
    lat_north: float,
    flip_north: bool,
) -> Tuple[np.ndarray, np.ndarray]:
    lon_span, lat_span = _geo_span_floor(lon_west, lon_east, lat_south, lat_north)
    px = (lon - lon_west) / lon_span
    py = (lat - lat_south) / lat_span
    if flip_north:
        py = 1.0 - py
    return px, py


def mask_lonlat_inside_buffered_extent(
    lon: np.ndarray,
    lat: np.ndarray,
    lon_west: float,
    lon_east: float,
    lat_south: float,
    lat_north: float,
    buffer_frac: float = GEO_INCLUSION_BUFFER_FRAC,
) -> np.ndarray:
    lon_span, lat_span = _geo_span_floor(lon_west, lon_east, lat_south, lat_north)
    bw = float(buffer_frac) * lon_span
    bh = float(buffer_frac) * lat_span
    return (
        (lon >= lon_west - bw)
        & (lon <= lon_east + bw)
        & (lat >= lat_south - bh)
        & (lat <= lat_north + bh)
    )


def _vector_paint_to_01(paint: np.ndarray, map_metric: str) -> np.ndarray:
    z = np.full(len(paint), np.nan, dtype=np.float64)
    for i, p in enumerate(paint):
        if pd.isna(p) or not np.isfinite(p):
            continue
        fp = float(p)
        if map_metric == CERT_METRIC_SINR:
            t = (fp - SINR_PAINT_MIN) / (SINR_PAINT_MAX - SINR_PAINT_MIN)
        elif map_metric == CERT_METRIC_RSRP:
            t = (fp - RSRP_OLLI_MIN) / (RSRP_OLLI_MAX - RSRP_OLLI_MIN)
        elif map_metric == CERT_METRIC_DOWNLOAD_SPEED:
            t = (fp - DL_SPEED_PAINT_MIN) / (DL_SPEED_PAINT_MAX - DL_SPEED_PAINT_MIN)
        elif map_metric == CERT_METRIC_LATENCY:
            t = (fp - LATENCY_PAINT_MIN) / (LATENCY_PAINT_MAX - LATENCY_PAINT_MIN)
        elif map_metric == CERT_METRIC_JITTER:
            t = (fp - JITTER_PAINT_MIN) / (JITTER_PAINT_MAX - JITTER_PAINT_MIN)
        else:
            t = (fp - RSRP_OLLI_MIN) / (RSRP_OLLI_MAX - RSRP_OLLI_MIN)
        z[i] = float(np.clip(t, 0.0, 1.0))
    return z


def _subsample_xy_z(
    px: np.ndarray, py: np.ndarray, z01: np.ndarray, max_samples: int, seed: int = 42
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    n = len(px)
    if n <= max_samples:
        return px, py, z01
    rng = np.random.default_rng(seed)
    idx = rng.choice(n, size=max_samples, replace=False)
    return px[idx], py[idx], z01[idx]


def build_rbf_surface_grid(
    px: np.ndarray,
    py: np.ndarray,
    z01: np.ndarray,
    grid_nx: int,
    grid_ny: int,
    max_samples: int = RBF_MAX_SAMPLES,
    smooth: float = RBF_SMOOTH,
    epsilon: float = RBF_MULTIQUADRIC_EPSILON,
) -> np.ndarray:
    """
    Multiquadric RBF (``RBFInterpolator`` / thin-plate + legacy ``Rbf`` fallback) → full-floor [0,1] field.
    Light smoothing + post-Gaussian for liquid glow with local peaks/valleys (not a flat sheet).
    """
    finite = np.isfinite(z01) & np.isfinite(px) & np.isfinite(py)
    px = px[finite].astype(np.float64, copy=False)
    py = py[finite].astype(np.float64, copy=False)
    z01 = z01[finite].astype(np.float64, copy=False)
    if len(px) == 0:
        return np.zeros((grid_ny, grid_nx), dtype=np.float64)

    gx = np.linspace(0.0, 1.0, grid_nx, dtype=np.float64)
    gy = np.linspace(0.0, 1.0, grid_ny, dtype=np.float64)
    Gx, Gy = np.meshgrid(gx, gy)

    px_t, py_t, z_t = _subsample_xy_z(px, py, z01, max_samples)
    # Tiny jitter removes exact duplicate sites that break Rbf
    rng = np.random.default_rng(43)
    jitter = rng.normal(0.0, 1e-9, size=(len(px_t), 2))
    px_t = px_t + jitter[:, 0]
    py_t = py_t + jitter[:, 1]

    pts = np.column_stack([px_t, py_t])
    q = np.column_stack([Gx.ravel(), Gy.ravel()])
    zi = None
    eps = float(epsilon)
    sm = max(float(smooth), 1e-4)
    if len(px_t) <= 800:
        neigh_tries: Tuple[Optional[int], ...] = (None, 110, 80)
    else:
        neigh_tries = (128, 100, 80, 64)
    for neigh in neigh_tries:
        try:
            kw = dict(kernel="multiquadric", smoothing=sm, epsilon=eps)
            if neigh is not None and len(px_t) > neigh + 2:
                kw["neighbors"] = int(neigh)
            interp = RBFInterpolator(pts, z_t, **kw)
            zi = interp(q).reshape(grid_ny, grid_nx)
            break
        except Exception:
            continue
    if zi is None:
        for neigh in neigh_tries:
            try:
                kw = dict(kernel="thin_plate_spline", smoothing=sm)
                if neigh is not None and len(px_t) > neigh + 2:
                    kw["neighbors"] = int(neigh)
                interp = RBFInterpolator(pts, z_t, **kw)
                zi = interp(q).reshape(grid_ny, grid_nx)
                break
            except Exception:
                continue
    if zi is None:
        try:
            rbf = Rbf(
                px_t,
                py_t,
                z_t,
                function="multiquadric",
                smooth=float(smooth),
                epsilon=eps,
            )
            zi = np.asarray(rbf(Gx, Gy), dtype=np.float64)
        except Exception:
            try:
                rbf = Rbf(px_t, py_t, z_t, function="thin_plate", smooth=float(smooth))
                zi = np.asarray(rbf(Gx, Gy), dtype=np.float64)
            except Exception:
                fill = float(np.nanmean(z_t)) if len(z_t) else 0.0
                zi = np.full((grid_ny, grid_nx), np.clip(fill, 0.0, 1.0), dtype=np.float64)

    zi = np.clip(zi, 0.0, 1.0)
    if POST_RBF_GAUSSIAN_SIGMA > 0.05:
        zi = gaussian_filter(zi, sigma=float(POST_RBF_GAUSSIAN_SIGMA), mode="nearest")
    return np.clip(zi, 0.0, 1.0)


def ordered_three_carrier_slots(network_values: Sequence[str]) -> List[Optional[str]]:
    """
    Prefer AT&T, T-Mobile, Verizon (in that order), then any other names, up to 3 slots.
    Unused slots are None (floor-only placeholder panel).
    """
    raw = sorted({str(x) for x in network_values if x is not None and str(x).strip() != ""})
    if not raw:
        return [None, None, None]

    def is_att(n: str) -> bool:
        u = n.upper()
        return "AT&T" in u or u.startswith("ATT") or "AT AND T" in u

    def is_tmo(n: str) -> bool:
        u = n.upper()
        compact = u.replace(" ", "").replace("-", "")
        return "T-MOBILE" in u or "TMOBILE" in compact or compact.startswith("TMO")

    def is_vzw(n: str) -> bool:
        return "VERIZON" in n.upper()

    matchers = [
        ("AT&T", is_att),
        ("T-Mobile", is_tmo),
        ("Verizon", is_vzw),
    ]
    picked: List[str] = []
    used = set()
    for _label, pred in matchers:
        for n in raw:
            if n not in used and pred(n):
                picked.append(n)
                used.add(n)
                break
    for n in raw:
        if n not in used and len(picked) < 3:
            picked.append(n)
            used.add(n)
    while len(picked) < 3:
        picked.append(None)
    return picked[:3]


def _sample_floor_rgb_on_grid(
    img_rgb_u8: np.ndarray, grid_ny: int, grid_nx: int
) -> np.ndarray:
    """Bilinear-friendly cell-center sampling: floor RGB in [0,1], shape (grid_ny, grid_nx, 3)."""
    h, w = img_rgb_u8.shape[:2]
    jj, ii = np.meshgrid(
        np.arange(grid_nx, dtype=np.float64),
        np.arange(grid_ny, dtype=np.float64),
    )
    x_frac = (jj + 0.5) / float(grid_nx)
    y_frac = (ii + 0.5) / float(grid_ny)
    col = np.clip((x_frac * (w - 1)).astype(np.int32), 0, w - 1)
    row = np.clip((y_frac * (h - 1)).astype(np.int32), 0, h - 1)
    return img_rgb_u8[row, col].astype(np.float64) / 255.0


def hard_anchor_mask_grid(grid_ny: int, grid_nx: int) -> np.ndarray:
    """
    Binary mask for the spatial anchor box in plan space: heat is fully on inside [0,1]×[0,1]
    (entire rendered floor extent) and zero outside. No edge feather — hard “outer wall” clip
    at the plot boundary only (matplotlib imshow crops the rectangle).
    """
    return np.ones((grid_ny, grid_nx), dtype=np.float64)


def _floodfill_exterior_on_paper(paper: np.ndarray) -> np.ndarray:
    """True for pixels connected to the image border through ``paper`` (exterior / margins)."""
    h, w = paper.shape
    exterior = np.zeros((h, w), dtype=bool)
    stack: List[Tuple[int, int]] = []

    def push(y: int, x: int) -> None:
        if 0 <= y < h and 0 <= x < w and paper[y, x] and not exterior[y, x]:
            exterior[y, x] = True
            stack.append((y, x))

    for x in range(w):
        push(0, x)
        push(h - 1, x)
    for y in range(h):
        push(y, 0)
        push(y, w - 1)
    while stack:
        y, x = stack.pop()
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            push(y + dy, x + dx)
    return exterior


def _legacy_luminance_footprint_bool_fullres(
    img_rgb_u8: np.ndarray,
    ink_luma_max: float = FOOTPRINT_INK_LUMA_MAX,
    paper_luma_min: float = FOOTPRINT_PAPER_LUMA_MIN,
    closing_kernel: int = FOOTPRINT_CLOSING_KERNEL,
    closing_iterations: int = FOOTPRINT_CLOSING_ITERATIONS,
) -> np.ndarray:
    """Fallback only: bright-paper punch-out + sealed ink (older path)."""
    rgb = img_rgb_u8.astype(np.float64) / 255.0
    lum = 0.299 * rgb[:, :, 0] + 0.587 * rgb[:, :, 1] + 0.114 * rgb[:, :, 2]
    ink_raw = lum < float(ink_luma_max)
    k = max(3, int(closing_kernel) | 1)
    struct = np.ones((k, k), dtype=bool)
    ink_sealed = binary_closing(
        ink_raw,
        structure=struct,
        iterations=int(max(1, closing_iterations)),
    )
    paper = (lum >= float(paper_luma_min)) & (~ink_sealed)
    exterior = _floodfill_exterior_on_paper(paper)
    return ~exterior


def _morphological_building_interior_bool_fullres(
    img_rgb_u8: np.ndarray,
    ink_luma_max: float = FOOTPRINT_INK_LUMA_MAX,
    blob_kernel: int = BUILDING_SOLID_BLOB_KERNEL,
) -> np.ndarray:
    """
    Solid building mask: ink → heavy binary closing (building blob) → flood from border on
    ``~blob`` → interior = not exterior (rooms wall-to-wall; stops at outer perimeter).
    """
    rgb = img_rgb_u8.astype(np.float64) / 255.0
    lum = 0.299 * rgb[:, :, 0] + 0.587 * rgb[:, :, 1] + 0.114 * rgb[:, :, 2]
    ink_raw = lum < float(ink_luma_max)
    bk = max(3, int(blob_kernel) | 1)
    blob_struct = np.ones((bk, bk), dtype=bool)
    ink_blob = binary_closing(
        ink_raw.astype(bool),
        structure=blob_struct,
        iterations=1,
    ).astype(bool)
    traversable = ~ink_blob
    exterior = _floodfill_exterior_on_paper(traversable)
    interior = ~exterior
    if int(FOOTPRINT_EDGE_EROSION_ITERATIONS) > 0:
        interior = binary_erosion(
            interior,
            structure=np.ones((3, 3), dtype=bool),
            iterations=int(FOOTPRINT_EDGE_EROSION_ITERATIONS),
            border_value=0,
        )
    return interior


def _bool_mask_downsample_to_grid(mask_bool: np.ndarray, grid_ny: int, grid_nx: int) -> np.ndarray:
    h, w = mask_bool.shape[:2]
    zf_y = float(grid_ny) / float(h)
    zf_x = float(grid_nx) / float(w)
    down = zoom(mask_bool.astype(np.float32), (zf_y, zf_x), order=0)
    out = (down >= 0.5).astype(np.float64)
    if out.shape != (grid_ny, grid_nx):
        fix = np.zeros((grid_ny, grid_nx), dtype=np.float64)
        mh, mw = min(out.shape[0], grid_ny), min(out.shape[1], grid_nx)
        fix[:mh, :mw] = out[:mh, :mw]
        return fix
    return out


def building_footprint_mask_grid(
    img_rgb_u8: np.ndarray,
    grid_ny: int,
    grid_nx: int,
    ink_luma_max: float = FOOTPRINT_INK_LUMA_MAX,
    paper_luma_min: float = FOOTPRINT_PAPER_LUMA_MIN,
    closing_kernel: int = FOOTPRINT_CLOSING_KERNEL,
    closing_iterations: int = FOOTPRINT_CLOSING_ITERATIONS,
    blob_kernel: int = BUILDING_SOLID_BLOB_KERNEL,
) -> np.ndarray:
    """
    Morphological solid footprint: 25×25 ink closing + border flood (see
    ``_morphological_building_interior_bool_fullres``).
    ``paper_luma_min`` is ignored (kept for API compatibility).
    """
    _ = paper_luma_min
    h, w = img_rgb_u8.shape[:2]
    if h < 8 or w < 8:
        return np.ones((grid_ny, grid_nx), dtype=np.float64)
    footprint = _morphological_building_interior_bool_fullres(
        img_rgb_u8, ink_luma_max, blob_kernel=blob_kernel
    )
    if not np.any(footprint):
        footprint = _legacy_luminance_footprint_bool_fullres(
            img_rgb_u8, ink_luma_max, FOOTPRINT_PAPER_LUMA_MIN, closing_kernel, closing_iterations
        )
    if not np.any(footprint):
        return np.ones((grid_ny, grid_nx), dtype=np.float64)
    return _bool_mask_downsample_to_grid(footprint, grid_ny, grid_nx)


def habitable_office_mask_grid(
    img_rgb_u8: np.ndarray,
    grid_ny: int,
    grid_nx: int,
    ink_luma_max: float = FOOTPRINT_INK_LUMA_MAX,
    paper_luma_min: float = FOOTPRINT_PAPER_LUMA_MIN,
    blob_kernel: int = BUILDING_SOLID_BLOB_KERNEL,
    closing_kernel: int = FOOTPRINT_CLOSING_KERNEL,
    closing_iterations: int = FOOTPRINT_CLOSING_ITERATIONS,
) -> np.ndarray:
    """
    Same morphological solid as footprint: ink → 25×25 closing → border flood on ``~blob``.
    ``paper_luma_min`` is ignored (kept for API compatibility).
    """
    _ = paper_luma_min
    h, w = img_rgb_u8.shape[:2]
    if h < 8 or w < 8:
        return np.ones((grid_ny, grid_nx), dtype=np.float64)
    interior = _morphological_building_interior_bool_fullres(
        img_rgb_u8, ink_luma_max, blob_kernel=blob_kernel
    )
    if not np.any(interior):
        return np.ones((grid_ny, grid_nx), dtype=np.float64)
    grid = _bool_mask_downsample_to_grid(interior, grid_ny, grid_nx)
    if float(np.mean(grid)) < float(HABITABLE_MIN_COVERAGE_FRAC):
        return building_footprint_mask_grid(
            img_rgb_u8,
            grid_ny,
            grid_nx,
            ink_luma_max,
            FOOTPRINT_PAPER_LUMA_MIN,
            closing_kernel,
            closing_iterations,
            blob_kernel=blob_kernel,
        )
    return grid


def merge_final_5g_state_column(
    map_data: pd.DataFrame, metrics_df: Optional[pd.DataFrame]
) -> pd.DataFrame:
    out = map_data.copy()
    if metrics_df is None or len(metrics_df) == 0:
        out["_Final_5G_State"] = np.nan
        return out
    if "Final_5G_State" not in metrics_df.columns:
        out["_Final_5G_State"] = np.nan
        return out
    key = "Carrier" if "Carrier" in metrics_df.columns else "Network"
    if key not in metrics_df.columns:
        out["_Final_5G_State"] = np.nan
        return out
    sub = metrics_df[[key, "Final_5G_State"]].drop_duplicates(subset=[key])
    m = {str(row[key]): row["Final_5G_State"] for _, row in sub.iterrows()}
    out["_Final_5G_State"] = out["Network"].map(lambda n: m.get(str(n), np.nan))
    return out


def _normalized_5g_token(val) -> str:
    if val is None or (isinstance(val, float) and np.isnan(val)):
        return ""
    s = str(val).strip().upper()
    if s in ("", "NAN", "NONE", "NULL"):
        return "NONE"
    return s


def _combined_data_network_type_series(df: pd.DataFrame) -> pd.Series:
    """
    Per-row tech label: ``Data_Network_Type`` when present and non-empty; else
    ``Data_Network_Type_OS_Reported`` (recovers T-Mobile LTE when primary is NaN).
    """
    idx = df.index
    n = len(df)
    if "Data_Network_Type" in df.columns:
        dnt = df["Data_Network_Type"]
    else:
        dnt = pd.Series(pd.NA, index=idx, dtype=object)
    if "Data_Network_Type_OS_Reported" in df.columns:
        dnt_os = df["Data_Network_Type_OS_Reported"]
    else:
        dnt_os = pd.Series(pd.NA, index=idx, dtype=object)
    as_str = dnt.astype(str)
    valid_main = dnt.notna() & as_str.str.strip().ne("") & ~as_str.str.strip().str.upper().isin(
        ("NAN", "NONE", "NULL", "<NA>")
    )
    combined = dnt.where(valid_main, dnt_os)
    return combined.fillna("").astype(str).str.strip()


def _infer_5g_state_from_points(carrier_df: pd.DataFrame) -> str:
    if carrier_df is None or len(carrier_df) == 0:
        return "NONE"
    if (
        "Data_Network_Type" not in carrier_df.columns
        and "Data_Network_Type_OS_Reported" not in carrier_df.columns
    ):
        return "NONE"
    nt = _combined_data_network_type_series(carrier_df)
    if nt.str.contains("NSA", case=False, na=False).any():
        return "NSA"
    if nt.str.contains("NR", case=False, na=False).any():
        return "SA"
    return "NONE"


def _carrier_effective_5g_state(sub_all: pd.DataFrame) -> str:
    tok = ""
    if "_Final_5G_State" in sub_all.columns and len(sub_all) > 0:
        tok = _normalized_5g_token(sub_all["_Final_5G_State"].iloc[0])
    if tok in ("", "NONE"):
        return _infer_5g_state_from_points(sub_all)
    if tok in ("SA", "NSA", "LTE"):
        return tok
    return _infer_5g_state_from_points(sub_all)


def _row_is_lte_tech(network_type: object) -> bool:
    """LTE-class on a single combined-tech string: contains ``LTE`` or ``EUTRAN`` (case-insensitive)."""
    u = str(network_type).upper()
    return bool(str(network_type).strip()) and (
        "LTE" in u or "EUTRAN" in u
    )


def filter_subframe_for_tech(sub_all: pd.DataFrame, tech: str, state_norm: str) -> pd.DataFrame:
    """
    Tech labels use **combined** primary + OS-reported columns (see ``_combined_data_network_type_series``).

    **5G** = combined string contains ``NR``; ``Final_5G_State`` SA/NSA only.
    **LTE** = combined contains ``LTE`` or ``EUTRAN``, and **no** ``NR`` (NR / LTE-NR → 5G only).
    LTE path **never** uses ``Final_5G_State``.
    """
    if len(sub_all) == 0:
        return sub_all
    if (
        "Data_Network_Type" not in sub_all.columns
        and "Data_Network_Type_OS_Reported" not in sub_all.columns
    ):
        return sub_all.iloc[0:0]
    nt = _combined_data_network_type_series(sub_all)
    is_lte_class = nt.str.contains("LTE", case=False, na=False, regex=False) | nt.str.contains(
        "EUTRAN", case=False, na=False, regex=False
    )
    is_nr = nt.str.contains("NR", case=False, na=False, regex=False)
    if tech == "5g":
        if state_norm not in ("SA", "NSA"):
            return sub_all.iloc[0:0]
        return sub_all[is_nr]
    is_lte_panel = is_lte_class & (~is_nr)
    return sub_all[is_lte_panel]


def _multiply_blend_heat_on_floor(
    floor_rgb: np.ndarray,
    grid_z01: np.ndarray,
    cmap: LinearSegmentedColormap,
    norm: Normalize,
    interior_mask: np.ndarray,
    heat_cap: float,
) -> np.ndarray:
    """
    Airy multiply: transparent neon on lease space; near-white paper stays bright; ink/text preserved.
    """
    z = np.clip(grid_z01, 0.0, 1.0)
    heat_rgba = cmap(norm(z))
    heat_rgb = np.asarray(heat_rgba[..., :3], dtype=np.float64)
    r = floor_rgb[..., 0]
    gch = floor_rgb[..., 1]
    bch = floor_rgb[..., 2]
    lum = 0.299 * r + 0.587 * gch + 0.114 * bch
    spread = np.maximum(np.maximum(r, gch), bch) - np.minimum(np.minimum(r, gch), bch)

    airy = np.clip(
        (lum - float(AIRY_WHITE_LUMA_START))
        / (float(AIRY_WHITE_LUMA_END) - float(AIRY_WHITE_LUMA_START) + 1e-9),
        0.0,
        1.0,
    )
    s = np.clip(z, 0.0, 1.0) ** 0.98
    s = s * interior_mask * float(heat_cap)
    s = s * (1.0 - float(AIRY_LUM_CRUSH_STRENGTH) * airy)
    s = np.clip(s, 0.0, 1.0)
    vivid = np.clip(heat_rgb * 1.08, 0.0, 1.0)
    blend = s[..., np.newaxis] * vivid + (1.0 - s[..., np.newaxis])
    floor_lift = np.clip(floor_rgb ** 0.985, 1e-4, 1.0)
    out = np.clip(floor_lift * blend, 0.0, 1.0)

    line_preserve = np.min(floor_rgb, axis=-1) < float(FLOOR_LINE_PRESERVE_MAX_CH)
    text_preserve = (
        (lum >= float(FLOOR_TEXT_LUM_MIN))
        & (lum <= float(FLOOR_TEXT_LUM_MAX))
        & (spread <= float(FLOOR_TEXT_MAX_CH_SPREAD))
    )
    # Walls/ink: hard passthrough. Room numbers (#12, …): tint so numerals read through emerald heat.
    ft = float(FLOOR_LABEL_SHOW_THROUGH_FLOOR)
    label_blend = np.clip(ft * floor_rgb + (1.0 - ft) * out, 0.0, 1.0)
    out = np.where(line_preserve[..., np.newaxis], floor_rgb, out)
    text_only = text_preserve & (~line_preserve)
    out = np.where(text_only[..., np.newaxis], label_blend, out)

    pw = np.clip(
        (lum - float(PURE_WHITE_BLEND_START)) / (0.998 - float(PURE_WHITE_BLEND_START) + 1e-9),
        0.0,
        1.0,
    ) * float(PURE_WHITE_PW_SCALE)
    frac = float(PURE_WHITE_FLOOR_FRACTION)
    whitened = frac * floor_rgb + (1.0 - frac) * out
    out = out * (1.0 - pw[..., np.newaxis]) + whitened * pw[..., np.newaxis]
    return np.clip(out, 0.0, 1.0)


def _prepare_points_from_subframe(
    sub: pd.DataFrame,
    metric: str,
    lon_west: float,
    lon_east: float,
    lat_south: float,
    lat_north: float,
    flip_north: bool,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    if len(sub) == 0:
        return np.array([]), np.array([]), np.array([])
    lon = pd.to_numeric(sub["Longitude"], errors="coerce").values
    lat = pd.to_numeric(sub["Latitude"], errors="coerce").values
    paint = np.array(
        [paint_value_for_row(sub.iloc[i], metric) for i in range(len(sub))],
        dtype=np.float64,
    )
    valid = ~(np.isnan(lon) | np.isnan(lat))
    lon, lat, paint = lon[valid], lat[valid], paint[valid]
    if len(lon) == 0:
        return np.array([]), np.array([]), np.array([])
    inside = mask_lonlat_inside_buffered_extent(
        lon, lat, lon_west, lon_east, lat_south, lat_north, GEO_INCLUSION_BUFFER_FRAC
    )
    lon, lat, paint = lon[inside], lat[inside], paint[inside]
    if len(lon) == 0:
        return np.array([]), np.array([]), np.array([])
    px, py = lonlat_to_plan_coords(lon, lat, lon_west, lon_east, lat_south, lat_north, flip_north)
    px = np.clip(px, 0.0, 1.0)
    py = np.clip(py, 0.0, 1.0)
    z01 = _vector_paint_to_01(paint, metric)
    return px, py, z01


def _prepare_points_for_carrier(
    map_data: pd.DataFrame,
    carrier: Optional[str],
    metric: str,
    lon_west: float,
    lon_east: float,
    lat_south: float,
    lat_north: float,
    flip_north: bool,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    if carrier is None or len(map_data) == 0:
        return np.array([]), np.array([]), np.array([])
    sub = map_data[map_data["Network"] == carrier].copy()
    return _prepare_points_from_subframe(
        sub, metric, lon_west, lon_east, lat_south, lat_north, flip_north
    )


def _prepare_points_for_carrier_tech(
    map_data: pd.DataFrame,
    carrier: Optional[str],
    metric: str,
    tech: str,
    lon_west: float,
    lon_east: float,
    lat_south: float,
    lat_north: float,
    flip_north: bool,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    if carrier is None or len(map_data) == 0:
        return np.array([]), np.array([]), np.array([])
    sub_all = map_data[map_data["Network"] == carrier].copy()
    if len(sub_all) == 0:
        return np.array([]), np.array([]), np.array([])
    if tech == "lte":
        sub = filter_subframe_for_tech(sub_all, tech, "")
    else:
        state_norm = _carrier_effective_5g_state(sub_all)
        sub = filter_subframe_for_tech(sub_all, tech, state_norm)
    return _prepare_points_from_subframe(
        sub, metric, lon_west, lon_east, lat_south, lat_north, flip_north
    )


def _cert_colormap_for_metric(map_metric: str) -> LinearSegmentedColormap:
    if map_metric == CERT_METRIC_SINR:
        return olli_sinr_branded_cmap()
    if map_metric in (CERT_METRIC_LATENCY, CERT_METRIC_JITTER):
        return olli_latency_jitter_inverted_ramp_cmap()
    return olli_branded_liquid_cmap()


def _cert_suptitle_metric_phrase(map_metric: str) -> str:
    if map_metric == CERT_METRIC_RSRP:
        return "RSRP"
    if map_metric == CERT_METRIC_SINR:
        return "SINR"
    if map_metric == CERT_METRIC_DOWNLOAD_SPEED:
        return "download speed"
    if map_metric == CERT_METRIC_LATENCY:
        return "latency"
    if map_metric == CERT_METRIC_JITTER:
        return "jitter"
    return "RSRP"


def render_all_operator_report_figure(
    image_bytes: bytes,
    map_data: pd.DataFrame,
    lon_west: float,
    lon_east: float,
    lat_south: float,
    lat_north: float,
    flip_north: bool,
    map_metric: str = CERT_METRIC_RSRP,
    grid_nx: int = CERT_INDOOR_GRID_NX,
    grid_ny: int = CERT_INDOOR_GRID_NY,
    heatmap_alpha: float = CERT_INDOOR_HEAT_ALPHA,
    rsrp_colormap: Optional[LinearSegmentedColormap] = None,
    metrics_df: Optional[pd.DataFrame] = None,
    venue_report_name: Optional[str] = None,
) -> Tuple[Optional[Figure], Optional[str]]:
    """
    2×3 Olli-layout grid: vertical colorbar, plan axes 0–45 × 0–35, two-line ``Carrier`` / technology titles,
    5G/LTE tech from combined ``Data_Network_Type`` + OS-reported fallback; morphological mask + edge erosion.
    ``rsrp_colormap`` is ignored (API compatibility).
    """
    _ = rsrp_colormap
    try:
        img = Image.open(BytesIO(image_bytes)).convert("RGB")
    except Exception as exc:
        return None, f"Could not read image: {exc}"

    if len(map_data) == 0:
        return None, "No rows with coordinates."

    map_enriched = merge_final_5g_state_column(map_data, metrics_df)
    slots = ordered_three_carrier_slots(map_enriched["Network"].dropna().unique().tolist())
    metric = map_metric if map_metric in CERT_MAP_METRIC_CHOICES else CERT_METRIC_RSRP
    cmap = _cert_colormap_for_metric(metric)
    img_arr = np.asarray(img)
    venue = (venue_report_name or "Seattle Office New").strip() or "Seattle Office New"
    extent = _olli_imshow_extent()

    fig, axes = plt.subplots(2, 3, figsize=(20.5, 12.8), dpi=120, constrained_layout=False)
    fig.subplots_adjust(
        left=0.06, right=0.865, top=0.84, bottom=0.06, wspace=0.22, hspace=0.36
    )

    norm = Normalize(vmin=0.0, vmax=1.0)
    floor_grid = _sample_floor_rgb_on_grid(img_arr, grid_ny, grid_nx)
    interior_mask = habitable_office_mask_grid(img_arr, grid_ny, grid_nx)
    white_panel = np.full_like(img_arr, 255, dtype=np.uint8)

    row_specs = [("5g", "5G"), ("lte", "LTE")]

    for row_idx, (tech_key, tech_label) in enumerate(row_specs):
        for col_idx, carrier in enumerate(slots):
            ax = axes[row_idx, col_idx]
            label = carrier if carrier else "—"

            if carrier is None:
                _set_olli_panel_title(ax, label, tech_label)
                ax.imshow(
                    img_arr,
                    extent=extent,
                    origin="upper",
                    aspect="auto",
                    interpolation="bilinear",
                )
                _style_olli_map_axes(ax)
                continue

            px, py, z01 = _prepare_points_for_carrier_tech(
                map_enriched,
                carrier,
                metric,
                tech_key,
                lon_west,
                lon_east,
                lat_south,
                lat_north,
                flip_north,
            )
            if len(px) < int(CERT_REPORT_MIN_POINTS_FOR_HEATMAP):
                _set_olli_panel_title(ax, label, f"No {tech_label} Data")
                ax.imshow(
                    white_panel,
                    extent=extent,
                    origin="upper",
                    aspect="auto",
                    interpolation="nearest",
                )
                _style_olli_map_axes(ax)
                continue

            _set_olli_panel_title(ax, label, tech_label)
            grid = build_rbf_surface_grid(px, py, z01, grid_nx, grid_ny)
            composite = _multiply_blend_heat_on_floor(
                floor_grid,
                grid,
                cmap,
                norm,
                interior_mask,
                heat_cap=float(heatmap_alpha),
            )
            ax.imshow(
                composite,
                extent=extent,
                origin="upper",
                aspect="auto",
                interpolation="bicubic",
            )
            _style_olli_map_axes(ax)

    sm = ScalarMappable(norm=norm, cmap=cmap)
    sm.set_array([])
    cbar_ax = fig.add_axes([0.885, 0.12, 0.022, 0.68])
    cb = fig.colorbar(sm, cax=cbar_ax, orientation="vertical")
    cb.ax.tick_params(labelsize=8, length=2, width=0.6)
    ticks_u = np.linspace(0.0, 1.0, 7)
    if metric == CERT_METRIC_SINR:
        db = SINR_PAINT_MIN + ticks_u * (SINR_PAINT_MAX - SINR_PAINT_MIN)
        cb.set_ticks(ticks_u)
        cb.set_ticklabels([f"{v:.0f}" for v in db])
        cb.set_label("SINR (dB)", fontsize=10, labelpad=10)
    elif metric == CERT_METRIC_DOWNLOAD_SPEED:
        db = DL_SPEED_PAINT_MIN + ticks_u * (DL_SPEED_PAINT_MAX - DL_SPEED_PAINT_MIN)
        cb.set_ticks(ticks_u)
        cb.set_ticklabels([f"{v:.0f}" for v in db])
        cb.set_label("Download speed (Mbps)", fontsize=10, labelpad=10)
    elif metric == CERT_METRIC_LATENCY:
        db = LATENCY_PAINT_MIN + ticks_u * (LATENCY_PAINT_MAX - LATENCY_PAINT_MIN)
        cb.set_ticks(ticks_u)
        cb.set_ticklabels([f"{v:.0f}" for v in db])
        cb.set_label("Latency (ms)", fontsize=10, labelpad=10)
    elif metric == CERT_METRIC_JITTER:
        db = JITTER_PAINT_MIN + ticks_u * (JITTER_PAINT_MAX - JITTER_PAINT_MIN)
        cb.set_ticks(ticks_u)
        cb.set_ticklabels([f"{v:.0f}" for v in db])
        cb.set_label("Jitter (ms)", fontsize=10, labelpad=10)
    else:
        tick_dbm = np.asarray(RSRP_CBAR_TICKS_DBM, dtype=np.float64)
        span = float(RSRP_CERT_MAX - RSRP_CERT_MIN)
        ticks_n = (tick_dbm - float(RSRP_CERT_MIN)) / span
        cb.set_ticks(ticks_n)
        cb.set_ticklabels([str(int(t)) for t in tick_dbm])
        cb.set_label("RSRP (dBm)", fontsize=10, labelpad=10)

    metric_phrase = _cert_suptitle_metric_phrase(metric)
    fig.suptitle(
        f"Cellular {metric_phrase} by operator and technology\n\n{venue}",
        fontsize=13.5,
        fontweight="normal",
        fontfamily="sans-serif",
        color="#1a1a1a",
        x=0.5,
        y=0.98,
        ha="center",
        linespacing=1.22,
    )

    return fig, None


def figure_to_png_bytes(fig: Figure, dpi: int = REPORT_FIGURE_DPI) -> bytes:
    buf = BytesIO()
    fig.savefig(buf, format="png", dpi=dpi, bbox_inches="tight", pad_inches=0.12)
    plt.close(fig)
    return buf.getvalue()


def olli_color_range_rgba() -> list:
    return [
        [35, 0, 0, 255],
        [120, 0, 20, 255],
        [220, 60, 0, 255],
        [255, 200, 0, 255],
        [180, 255, 80, 255],
        [0, 255, 120, 255],
    ]
