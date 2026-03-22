"""
Certification Scorer - Assigns scores and badges based on detailed thresholds
"""

import pandas as pd
import numpy as np
from typing import Any, Dict, List, Optional, Tuple

from methodology_sandbox import (
    DEFAULT_WEIGHT_HIGH,
    DEFAULT_WEIGHT_LOW,
    DEFAULT_WEIGHT_MEDIUM,
)


class CertificationScorer:
    """
    Scores carriers based on detailed metric thresholds matching Baybrook structure.
    
    Badges:
    - Platinum: Exceptional performance (90+ points)
    - Gold: Excellent performance (75-89 points)
    - Silver: Good performance (60-74 points)
    - Fail: Below standard (<60 points)
    """
    
    # Score thresholds for badges
    BADGE_THRESHOLDS = {
        'Platinum': 90,
        'Gold': 75,
        'Silver': 60,
        'Fail': 0
    }
    
    def __init__(self, metrics_df: pd.DataFrame):
        """
        Initialize scorer with calculated metrics.
        
        Args:
            metrics_df: DataFrame from MetricsProcessor.calculate_all_metrics()
        """
        self.metrics_df = metrics_df.copy()
    
    # Grade-to-score conversion (0-4 scale, then to 0-100)
    GRADE_SCORES = {
        'Excellent': 4,
        'Great': 3,
        'Good': 2,
        'Limited': 1,
        'Poor': 0
    }
    
    def _grade_rsrp(self, value: float) -> Tuple[int, str]:
        """Grade RSRP (dBm) with 0-4 score."""
        if pd.isna(value):
            return 0, "Poor"
        if value > -80:
            return 4, "Excellent"
        elif value > -95:
            return 3, "Great"
        elif value > -105:
            return 2, "Good"
        elif value > -115:
            return 1, "Limited"
        else:
            return 0, "Poor"
    
    def _grade_rsrq(self, value: float) -> Tuple[int, str]:
        """Grade RSRQ (dB) with 0-4 score."""
        if pd.isna(value):
            return 0, "Poor"
        if value > -10:
            return 4, "Excellent"
        elif value > -12:
            return 3, "Great"
        elif value > -15:
            return 2, "Good"
        elif value > -18:
            return 1, "Limited"
        else:
            return 0, "Poor"
    
    def _grade_sinr(self, value: float) -> Tuple[int, str]:
        """Grade SINR (dB) with 0-4 score."""
        if pd.isna(value):
            return 0, "Poor"
        if value > 20:
            return 4, "Excellent"
        elif value >= 13:
            return 3, "Great"
        elif value >= 5:
            return 2, "Good"
        elif value >= 0:
            return 1, "Limited"
        else:
            return 0, "Poor"
    
    def _grade_rssi(self, value: float) -> Tuple[int, str]:
        """Grade RSSI (dBm) with 0-4 score."""
        if pd.isna(value):
            return 0, "Poor"
        if value > -70:
            return 4, "Excellent"
        elif value > -85:
            return 3, "Great"
        elif value > -95:
            return 2, "Good"
        elif value > -105:
            return 1, "Limited"
        else:
            return 0, "Poor"
    
    def _grade_noise_floor(self, value: float) -> Tuple[int, str]:
        """Grade Noise Floor (dBm) with 0-4 score."""
        if pd.isna(value):
            return 0, "Poor"
        if value < -110:
            return 4, "Excellent"
        elif value < -105:
            return 3, "Great"
        elif value < -100:
            return 2, "Good"
        elif value < -95:
            return 1, "Limited"
        else:
            return 0, "Poor"
    
    def _grade_tx_power(self, value: float) -> Tuple[int, str]:
        """Grade TX Power (dBm) with 0-4 score. Lower is better."""
        if pd.isna(value):
            return 0, "Poor"
        if value < 5:
            return 4, "Excellent"
        elif value < 12:
            return 3, "Great"
        elif value < 18:
            return 2, "Good"
        elif value < 21:
            return 1, "Limited"
        else:
            return 0, "Poor"
    
    def _grade_cqi(self, value: float) -> Tuple[int, str]:
        """Grade CQI Index with 0-4 score."""
        if pd.isna(value):
            return 0, "Poor"
        if value >= 13:
            return 4, "Excellent"
        elif value >= 10:
            return 3, "Great"
        elif value >= 7:
            return 2, "Good"
        elif value >= 4:
            return 1, "Limited"
        else:
            return 0, "Poor"
    
    def _grade_modulation(self, value: str) -> Tuple[int, str]:
        """Grade Modulation type with 0-4 score."""
        if pd.isna(value):
            return 0, "Poor"
        
        value_str = str(value).lower()
        
        if "256 qam" in value_str:
            return 4, "Excellent"
        elif "64 qam" in value_str:
            return 3, "Great"
        elif "16 qam" in value_str:
            return 2, "Good"
        elif "qpsk" in value_str:
            return 1, "Limited"
        else:  # Failed or unknown
            return 0, "Poor"
    
    def _grade_total_bw(self, value: float) -> Tuple[int, str]:
        """Grade Total Bandwidth (MHz) with 0-4 score."""
        if pd.isna(value):
            return 0, "Poor"
        if value > 100:
            return 4, "Excellent"
        elif value >= 60:
            return 3, "Great"
        elif value >= 40:
            return 2, "Good"
        elif value >= 20:
            return 1, "Limited"
        else:
            return 0, "Poor"
    
    def _grade_mimo_rank(self, value: float) -> Tuple[int, str]:
        """Grade MIMO Rank with 0-4 score."""
        if pd.isna(value):
            return 0, "Poor"
        if value >= 4:
            return 4, "Excellent"
        elif value >= 3:
            return 3, "Great"
        elif value >= 2:
            return 2, "Good"
        elif value >= 1:
            return 1, "Limited"
        else:
            return 0, "Poor"
    
    def _grade_5g_state(self, value: str) -> Tuple[int, str]:
        """Grade 5G State with 0-4 score."""
        if pd.isna(value):
            return 0, "Poor"
        
        value_str = str(value).lower()
        
        if "sa" in value_str:
            return 4, "Excellent"
        elif "nsa" in value_str and "clean" in value_str:
            return 3, "Great"
        elif "nsa" in value_str:
            return 2, "Good"
        elif "lte" in value_str or "anchor" in value_str:
            return 1, "Limited"
        else:
            return 0, "Poor"
    
    def _grade_band_diversity(self, value: float) -> Tuple[int, str]:
        """Grade Band Diversity with 0-4 score."""
        if pd.isna(value):
            return 0, "Poor"
        if value >= 3:
            return 4, "Excellent"
        elif value >= 2:
            return 3, "Great"
        elif value >= 1:
            return 2, "Good"
        else:
            return 0, "Poor"
    
    def _grade_ca_count(self, value: float) -> Tuple[int, str]:
        """Grade Carrier Aggregation Count with 0-4 score."""
        if pd.isna(value):
            return 0, "Poor"
        if value >= 4:
            return 4, "Excellent"
        elif value >= 3:
            return 3, "Great"
        elif value >= 2:
            return 2, "Good"
        elif value >= 1:
            return 1, "Limited"
        else:
            return 0, "Poor"
    
    def _grade_dl_speed(self, value: float) -> Tuple[int, str]:
        """Grade Download Speed (Mbps) with 0-4 score."""
        if pd.isna(value):
            return 0, "Poor"
        if value > 500:
            return 4, "Excellent"
        elif value >= 250:
            return 3, "Great"
        elif value >= 100:
            return 2, "Good"
        elif value >= 50:
            return 1, "Limited"
        else:
            return 0, "Poor"
    
    def _grade_ul_speed(self, value: float) -> Tuple[int, str]:
        """Grade Upload Speed (Mbps) with 0-4 score."""
        if pd.isna(value):
            return 0, "Poor"
        if value > 50:
            return 4, "Excellent"
        elif value >= 25:
            return 3, "Great"
        elif value >= 10:
            return 2, "Good"
        elif value >= 5:
            return 1, "Limited"
        else:
            return 0, "Poor"
    
    def _grade_jitter(self, value: float) -> Tuple[int, str]:
        """Grade Jitter (ms) with 0-4 score. Lower is better."""
        if pd.isna(value):
            return 0, "Poor"
        if value < 10:
            return 4, "Excellent"
        elif value < 20:
            return 3, "Great"
        elif value < 30:
            return 2, "Good"
        elif value < 50:
            return 1, "Limited"
        else:
            return 0, "Poor"
    
    def _grade_packet_loss(self, value: float) -> Tuple[int, str]:
        """Grade Packet Loss (%) with 0-4 score. Lower is better."""
        if pd.isna(value):
            return 0, "Poor"
        if value == 0:
            return 4, "Excellent"
        elif value < 0.1:
            return 3, "Great"
        elif value <= 0.5:
            return 2, "Good"
        elif value <= 1.0:
            return 1, "Limited"
        else:
            return 0, "Poor"
    
    def _grade_coverage(self, value: float) -> Tuple[int, str]:
        """Grade Coverage (%) with 0-4 score."""
        if pd.isna(value):
            return 0, "Poor"
        if value > 95:
            return 4, "Excellent"
        elif value >= 90:
            return 3, "Great"
        elif value >= 85:
            return 2, "Good"
        elif value >= 75:
            return 1, "Limited"
        else:
            return 0, "Poor"
    
    def _grade_latency(self, value: float) -> Tuple[int, str]:
        """Grade Latency (ms) with 0-4 score. Lower is better."""
        if pd.isna(value):
            return 0, "Poor"
        if value < 20:
            return 4, "Excellent"
        elif value < 40:
            return 3, "Great"
        elif value < 60:
            return 2, "Good"
        elif value < 100:
            return 1, "Limited"
        else:
            return 0, "Poor"
    
    def _grade_handover_success(self, value: float) -> Tuple[int, str]:
        """Grade Handover Success (%) with 0-4 score."""
        if pd.isna(value):
            return 0, "Poor"
        if value > 99.5:
            return 4, "Excellent"
        elif value >= 98:
            return 3, "Great"
        elif value >= 95:
            return 2, "Good"
        elif value >= 90:
            return 1, "Limited"
        else:
            return 0, "Poor"

    def _grade_manual_vpn_type(self, value: str) -> Tuple[int, str]:
        """VPN Usage (infrastructure): None = 0; Consumer mid; Corporate/IPSec = 4."""
        v = str(value or "").strip()
        m = {
            "None": (0, "Poor"),
            "Consumer": (2, "Good"),
            "Corporate/IPSec": (4, "Excellent"),
        }
        return m.get(v, (0, "Poor"))

    def _grade_manual_isp_redundancy(self, value: str) -> Tuple[int, str]:
        v = str(value or "").strip()
        m = {
            "None": (0, "Poor"),
            "Warm Standby": (2, "Good"),
            "Active/Active": (4, "Excellent"),
        }
        return m.get(v, (0, "Poor"))

    def _grade_manual_isp_diversity(self, value: str) -> Tuple[int, str]:
        v = str(value or "").strip()
        m = {
            "Single Entry": (0, "Poor"),
            "Dual Entry": (2, "Good"),
            "Diverse Paths": (4, "Excellent"),
        }
        return m.get(v, (0, "Poor"))

    def _grade_manual_hardware_age(self, value: str) -> Tuple[int, str]:
        v = str(value or "").strip()
        m = {
            "Legacy < 2 years": (1, "Limited"),
            "Modern 2-4 years": (3, "Great"),
            "State-of-the-art": (4, "Excellent"),
        }
        return m.get(v, (1, "Limited"))

    def _score_carrier(
        self,
        metrics_row: pd.Series,
        manual: Optional[Dict[str, Any]],
        methodology: Dict[str, Any],
    ) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """
        Tiered 90/8/2-style model: each metric is 0–4; per-tier weights apply.
        Final score = 100 * sum(p_i * w_i) / sum(4 * w_i).
        """
        manual = manual or {}
        w_h = float(methodology.get("weight_high", DEFAULT_WEIGHT_HIGH))
        w_m = float(methodology.get("weight_medium", DEFAULT_WEIGHT_MEDIUM))
        w_l = float(methodology.get("weight_low", DEFAULT_WEIGHT_LOW))
        pmos = bool(methodology.get("pmos_voice_test", False))
        pmos_score_input = methodology.get("pmos_score")

        metric_rows: List[Dict[str, Any]] = []

        def add_row(
            label: str,
            bucket: str,
            weight: float,
            raw: int,
            grade_label: str,
        ) -> float:
            wtd = float(raw) * weight
            metric_rows.append(
                {
                    "Metric": label,
                    "Tier": bucket,
                    "Raw (0–4)": raw,
                    "Grade": grade_label,
                    "Weight": weight,
                    "Raw × Weight": round(wtd, 6),
                }
            )
            return wtd

        high_wsum = 0.0
        med_wsum = 0.0
        low_wsum = 0.0
        high_raw_sum = 0
        med_raw_sum = 0
        low_raw_sum = 0
        high_n = med_n = low_n = 0
        sum_w = 0.0

        # --- HIGH (2.25 default) ---
        r, g = self._grade_dl_speed(
            pd.to_numeric(metrics_row.get("Peak_DL_Mbps"), errors="coerce")
        )
        high_wsum += add_row("Peak DL (Mbps)", "HIGH", w_h, r, g)
        high_raw_sum += r
        high_n += 1
        sum_w += w_h

        r, g = self._grade_ul_speed(
            pd.to_numeric(metrics_row.get("Peak_UL_Mbps"), errors="coerce")
        )
        high_wsum += add_row("Peak UL (Mbps)", "HIGH", w_h, r, g)
        high_raw_sum += r
        high_n += 1
        sum_w += w_h

        r, g = self._grade_rsrp(
            pd.to_numeric(metrics_row.get("RSRP_Summary"), errors="coerce")
        )
        high_wsum += add_row("RSRP Summary", "HIGH", w_h, r, g)
        high_raw_sum += r
        high_n += 1
        sum_w += w_h

        r, g = self._grade_sinr(
            pd.to_numeric(metrics_row.get("SINR_Summary"), errors="coerce")
        )
        high_wsum += add_row("SINR Summary", "HIGH", w_h, r, g)
        high_raw_sum += r
        high_n += 1
        sum_w += w_h

        r, g = self._grade_latency(
            pd.to_numeric(metrics_row.get("Median_Latency_ms"), errors="coerce")
        )
        high_wsum += add_row("Median Latency (ms)", "HIGH", w_h, r, g)
        high_raw_sum += r
        high_n += 1
        sum_w += w_h

        r, g = self._grade_coverage(
            pd.to_numeric(metrics_row.get("Primary_Coverage_Pct"), errors="coerce")
        )
        high_wsum += add_row("Primary Coverage %", "HIGH", w_h, r, g)
        high_raw_sum += r
        high_n += 1
        sum_w += w_h

        r, g = self._grade_manual_isp_redundancy(manual.get("isp_redundancy", "None"))
        high_wsum += add_row("ISP Redundancy", "HIGH", w_h, r, g)
        high_raw_sum += r
        high_n += 1
        sum_w += w_h

        # --- MEDIUM (0.25 default) ---
        r, g = self._grade_rsrq(
            pd.to_numeric(metrics_row.get("RSRQ_dB"), errors="coerce")
        )
        med_wsum += add_row("RSRQ (dB)", "MEDIUM", w_m, r, g)
        med_raw_sum += r
        med_n += 1
        sum_w += w_m

        r, g = self._grade_jitter(
            pd.to_numeric(metrics_row.get("Median_Jitter_ms"), errors="coerce")
        )
        med_wsum += add_row("Median Jitter (ms)", "MEDIUM", w_m, r, g)
        med_raw_sum += r
        med_n += 1
        sum_w += w_m

        r, g = self._grade_packet_loss(
            pd.to_numeric(metrics_row.get("Packet_Loss_Pct"), errors="coerce")
        )
        med_wsum += add_row("Packet Loss %", "MEDIUM", w_m, r, g)
        med_raw_sum += r
        med_n += 1
        sum_w += w_m

        r, g = self._grade_handover_success(
            pd.to_numeric(metrics_row.get("Handover_Success_Pct"), errors="coerce")
        )
        med_wsum += add_row("Handover Success %", "MEDIUM", w_m, r, g)
        med_raw_sum += r
        med_n += 1
        sum_w += w_m

        r, g = self._grade_total_bw(
            pd.to_numeric(metrics_row.get("Total_BW_MHz"), errors="coerce")
        )
        med_wsum += add_row("Total BW (MHz)", "MEDIUM", w_m, r, g)
        med_raw_sum += r
        med_n += 1
        sum_w += w_m

        r, g = self._grade_manual_isp_diversity(manual.get("isp_diversity", "Single Entry"))
        med_wsum += add_row("ISP Diversity", "MEDIUM", w_m, r, g)
        med_raw_sum += r
        med_n += 1
        sum_w += w_m

        # --- LOW (0.125 default) ---
        r, g = self._grade_tx_power(
            pd.to_numeric(metrics_row.get("TX_Power_dBm"), errors="coerce")
        )
        low_wsum += add_row("TX Power (dBm)", "LOW", w_l, r, g)
        low_raw_sum += r
        low_n += 1
        sum_w += w_l

        r, g = self._grade_mimo_rank(
            pd.to_numeric(metrics_row.get("MIMO_Rank_Max"), errors="coerce")
        )
        low_wsum += add_row("MIMO Rank Max", "LOW", w_l, r, g)
        low_raw_sum += r
        low_n += 1
        sum_w += w_l

        r, g = self._grade_ca_count(
            pd.to_numeric(metrics_row.get("CA_Count"), errors="coerce")
        )
        low_wsum += add_row("CA Count", "LOW", w_l, r, g)
        low_raw_sum += r
        low_n += 1
        sum_w += w_l

        r, g = self._grade_band_diversity(
            pd.to_numeric(metrics_row.get("Band_Diversity_Count"), errors="coerce")
        )
        low_wsum += add_row("Band Diversity Count", "LOW", w_l, r, g)
        low_raw_sum += r
        low_n += 1
        sum_w += w_l

        r, g = self._grade_cqi(
            pd.to_numeric(metrics_row.get("CQI_Tool"), errors="coerce")
        )
        low_wsum += add_row("CQI", "LOW", w_l, r, g)
        low_raw_sum += r
        low_n += 1
        sum_w += w_l

        r, g = self._grade_modulation(metrics_row.get("Modulation_Tool"))
        low_wsum += add_row("Modulation", "LOW", w_l, r, g)
        low_raw_sum += r
        low_n += 1
        sum_w += w_l

        vpn_sel = manual.get("vpn_type") or manual.get("vpn_usage") or "None"
        r, g = self._grade_manual_vpn_type(vpn_sel)
        low_wsum += add_row("VPN Usage", "LOW", w_l, r, g)
        low_raw_sum += r
        low_n += 1
        sum_w += w_l

        r, g = self._grade_manual_hardware_age(
            manual.get("hardware_age", "Modern 2-4 years")
        )
        low_wsum += add_row("Hardware Age", "LOW", w_l, r, g)
        low_raw_sum += r
        low_n += 1
        sum_w += w_l

        max_weighted = 4.0 * sum_w
        total_weighted = high_wsum + med_wsum + low_wsum
        score_100 = (total_weighted / max_weighted * 100.0) if max_weighted > 0 else 0.0

        weighted_avg_raw = (
            (total_weighted / sum_w) if sum_w > 0 else 0.0
        )

        if score_100 >= self.BADGE_THRESHOLDS["Platinum"]:
            badge = "Platinum"
        elif score_100 >= self.BADGE_THRESHOLDS["Gold"]:
            badge = "Gold"
        elif score_100 >= self.BADGE_THRESHOLDS["Silver"]:
            badge = "Silver"
        else:
            badge = "Fail"

        pmos_capped = False
        pmos_value_used: Optional[float] = None
        if pmos:
            try:
                pmos_value_used = (
                    float(pmos_score_input)
                    if pmos_score_input is not None and not pd.isna(pmos_score_input)
                    else float(weighted_avg_raw)
                )
            except (TypeError, ValueError):
                pmos_value_used = float(weighted_avg_raw)
            if pmos_value_used < 3.5 and badge in ("Platinum", "Gold"):
                badge = "Silver"
                pmos_capped = True

        high_max = 4.0 * w_h * high_n
        med_max = 4.0 * w_m * med_n
        low_max = 4.0 * w_l * low_n

        detail: Dict[str, Any] = {
            "metric_rows": metric_rows,
            "high_raw_sum": high_raw_sum,
            "high_weight": w_h,
            "high_metric_count": high_n,
            "high_weighted_sum": high_wsum,
            "high_max_weighted": high_max,
            "medium_raw_sum": med_raw_sum,
            "medium_weight": w_m,
            "medium_metric_count": med_n,
            "medium_weighted_sum": med_wsum,
            "medium_max_weighted": med_max,
            "low_raw_sum": low_raw_sum,
            "low_weight": w_l,
            "low_metric_count": low_n,
            "low_weighted_sum": low_wsum,
            "low_max_weighted": low_max,
            "total_weighted": total_weighted,
            "max_weighted": max_weighted,
            "score_100": score_100,
            "weighted_avg_raw": weighted_avg_raw,
            "pmos_voice_test": pmos,
            "pmos_capped": pmos_capped,
            "pmos_score": pmos_value_used,
        }

        scores: Dict[str, Any] = {
            "Score": score_100,
            "Badge": badge,
            "Bucket_HIGH_Weighted": high_wsum,
            "Bucket_MEDIUM_Weighted": med_wsum,
            "Bucket_LOW_Weighted": low_wsum,
            "Weighted_Avg_Raw": weighted_avg_raw,
            "PMOS_Capped": pmos_capped,
            "PMOS_Score_Used": pmos_value_used if pmos else None,
            "Signal_Score": high_wsum / high_max * 100 if high_max > 0 else 0,
            "Performance_Score": score_100,
            "Latency_Score": score_100,
            "Radio_Score": low_wsum / low_max * 100 if low_max > 0 else 0,
        }

        return scores, detail

    def calculate_scores(
        self,
        manual_by_carrier: Optional[Dict[str, Dict[str, Any]]] = None,
        methodology: Optional[Dict[str, Any]] = None,
    ) -> Tuple[pd.DataFrame, Dict[str, Dict[str, Any]]]:
        """
        Calculate certification scores for all carriers.

        Returns:
            scores_df: Carrier, Score, Badge, bucket totals
            details_by_carrier: Per-carrier breakdown for the Methodology Sandbox card
        """
        manual_by_carrier = manual_by_carrier or {}
        methodology = methodology or {}

        results: List[Dict[str, Any]] = []
        details_by_carrier: Dict[str, Dict[str, Any]] = {}

        for _, row in self.metrics_df.iterrows():
            carrier = row["Carrier"]
            manual = manual_by_carrier.get(carrier, {})
            score_data, detail = self._score_carrier(row, manual, methodology)
            score_data["Carrier"] = carrier
            detail["carrier"] = carrier
            results.append(score_data)
            details_by_carrier[carrier] = detail

        return pd.DataFrame(results), details_by_carrier
