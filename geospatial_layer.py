"""
Geospatial Innovation Layer - Certification Compliance Map
"""

import streamlit as st
import pandas as pd
from io import BytesIO
import zipfile
from typing import Optional

from geo_anchors import (
    dataset_matches_seattle_preset,
    default_seattle_floorplan_relative_path,
    get_seattle_spatial_anchors,
    read_bytes_if_exists,
)
from indoor_floorplan import (
    CERT_MAP_METRIC_CHOICES,
    figure_to_png_bytes,
    render_all_operator_report_figure,
    REPORT_FIGURE_DPI,
)


def _cert_report_zip_name(map_metric: str) -> str:
    return (
        "All_Operator_"
        + map_metric.replace(" ", "_").replace("(", "").replace(")", "")
        + "_Report.png"
    )


class GeospatialLayer:
    """
    Renders interactive certification compliance maps with carrier filtering.
    """

    def __init__(self, raw_data: pd.DataFrame, metrics_df: pd.DataFrame, scores_df: pd.DataFrame):
        self.raw_data = raw_data.copy()
        self.metrics_df = metrics_df
        self.scores_df = scores_df

        self.carrier_badges = {}
        for _, row in scores_df.iterrows():
            carrier = row.get("Carrier", row.get("Network", "Unknown"))
            badge = row.get("Badge", "Fail")
            self.carrier_badges[carrier] = badge

    def _get_certification_status(self, row: pd.Series) -> str:
        try:
            carrier = row.get("Network", row.get("Carrier", "Unknown"))
            return self.carrier_badges.get(carrier, "Fail")
        except Exception:
            return "Fail"

    def _prepare_map_data(self, carrier_filter: str = None) -> pd.DataFrame:
        map_data = self.raw_data.copy()
        if carrier_filter and carrier_filter != "All Carriers":
            map_data = map_data[map_data["Network"] == carrier_filter]

        map_data = map_data[map_data["Latitude"].notna() & map_data["Longitude"].notna()]
        if len(map_data) == 0:
            return pd.DataFrame()

        map_data["Latitude"] = pd.to_numeric(map_data["Latitude"], errors="coerce")
        map_data["Longitude"] = pd.to_numeric(map_data["Longitude"], errors="coerce")
        map_data = map_data[map_data["Latitude"].notna() & map_data["Longitude"].notna()]
        if len(map_data) == 0:
            return pd.DataFrame()

        map_data["Certification"] = map_data.apply(self._get_certification_status, axis=1)
        return map_data

    def render_certification_map(self) -> None:
        st.header("🗺️ Compliance Map")
        st.markdown(
            "Upload your **floor plan** (or use **assets/image (3).png**). "
            "Alignment uses **seattle_anchors.json** automatically for Seattle venue data."
        )

        map_data = self._prepare_map_data(None)
        if len(map_data) == 0:
            st.warning("No location data with valid coordinates.")
            return

        venue_ok = dataset_matches_seattle_preset(self.raw_data)
        anchors: Optional[dict] = None
        anchor_err: Optional[str] = None
        if venue_ok:
            anchors, anchor_err = get_seattle_spatial_anchors()
        if venue_ok and anchor_err:
            st.error(anchor_err)
        elif not venue_ok:
            st.info(
                "All-operator reports are available when your dataset matches the **Seattle** venue "
                "(coordinates are checked automatically)."
            )

        st.subheader("Floor plan")
        up = st.file_uploader(
            "Upload floor plan (PNG or JPG)",
            type=["png", "jpg", "jpeg"],
            key="po_floorplan_uploader",
            help="e.g. image (3).png — used as the background in each carrier panel.",
        )
        if up is not None:
            st.session_state.po_floorplan_bytes = up.getvalue()

        fp_bytes: Optional[bytes] = st.session_state.get("po_floorplan_bytes")
        if fp_bytes is None and venue_ok:
            fp_bytes = read_bytes_if_exists(default_seattle_floorplan_relative_path())

        has_floor = fp_bytes is not None
        certified_ready = bool(venue_ok and anchors is not None and not anchor_err and has_floor)

        if venue_ok and not has_floor:
            st.caption(
                f"Add **{default_seattle_floorplan_relative_path()}** under **assets**, or upload above."
            )

        if "allop_report_bytes" not in st.session_state:
            st.session_state.allop_report_bytes = {}

        st.subheader("Olli all-operator reports")
        map_metric = st.selectbox(
            "Certified heatmap metric",
            options=list(CERT_MAP_METRIC_CHOICES),
            index=0,
            key="cert_heatmap_metric",
            help="Same 2×3 Olli grid, morphological building mask, and RBF blend for each metric.",
        )
        gen = st.button(
            "Generate all-operator report",
            key="cert_gen_allop_report",
            type="primary",
            disabled=not certified_ready,
            use_container_width=True,
        )

        if gen and certified_ready and fp_bytes is not None and anchors is not None:
            fig, err = render_all_operator_report_figure(
                fp_bytes,
                map_data,
                anchors["lon_west"],
                anchors["lon_east"],
                anchors["lat_south"],
                anchors["lat_north"],
                anchors["flip_north"],
                map_metric=map_metric,
                rsrp_colormap=None,
                metrics_df=self.metrics_df,
                venue_report_name=anchors.get("venue_report_name"),
            )
            if err:
                st.error(err)
            elif fig is not None:
                st.pyplot(fig, use_container_width=True)
                st.session_state.allop_report_bytes[map_metric] = figure_to_png_bytes(
                    fig, dpi=REPORT_FIGURE_DPI
                )

        pack = st.session_state.get("allop_report_bytes") or {}
        if any(pack.values()):
            zbuf = BytesIO()
            with zipfile.ZipFile(zbuf, "w", zipfile.ZIP_DEFLATED) as zf:
                for m, b in pack.items():
                    if b:
                        zf.writestr(_cert_report_zip_name(m), b)
            st.download_button(
                label="💾 Download All-Operator Report Pack (ZIP)",
                data=zbuf.getvalue(),
                file_name="Olli_All_Operator_Reports.zip",
                mime="application/zip",
                key="cert_allop_zip_dl",
                use_container_width=True,
            )
