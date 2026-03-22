"""
Metrics Processor - Calculates all 20+ metrics from raw Rootmetrics data
"""

import pandas as pd
import numpy as np
from typing import Dict, List


class MetricsProcessor:
    """
    Processes raw Rootmetrics logs and calculates aggregated metrics per carrier.
    
    Metrics calculated:
    1. Signal Strength: RSRP, RSRQ, SINR (from RSSNR) medians
    2. Performance: Download/Upload speeds (median & peak)
    3. Latency/Jitter: Network timing metrics
    4. Advanced Radio: CQI, 5G State, CA Count, Coverage %
    """
    
    def __init__(self, df: pd.DataFrame):
        """
        Initialize processor with raw data.
        
        Args:
            df: DataFrame from CSV with all Rootmetrics columns
        """
        self.df = df.copy()
        self.df['Network'] = self.df['Network'].fillna('Unknown')
        self._normalize_final_test_speed_kbps_to_mbps()
        
    def calculate_all_metrics(self) -> pd.DataFrame:
        """
        Calculate all metrics per carrier.
        
        Returns:
            DataFrame with one row per carrier containing all metrics
        """
        carriers = self.df['Network'].unique()
        results = []
        
        for carrier in carriers:
            carrier_df = self.df[self.df['Network'] == carrier]
            metrics = self._calculate_carrier_metrics(carrier, carrier_df)
            results.append(metrics)
        
        return pd.DataFrame(results)

    def _normalize_final_test_speed_kbps_to_mbps(self) -> None:
        """RootMetrics Detail CSV stores Final_Test_Speed in Kbps; convert to Mbps."""
        if 'Final_Test_Speed' not in self.df.columns:
            return
        speeds = pd.to_numeric(self.df['Final_Test_Speed'], errors='coerce')
        self.df['Final_Test_Speed'] = speeds / 1000.0

    def _get_median_latency_ms(self, df: pd.DataFrame, columns: List[str]) -> float:
        """Median Latency excluding 0.0 ms (invalid test artifacts)."""
        values = []
        for col in columns:
            if col not in df.columns:
                continue
            col_values = pd.to_numeric(df[col], errors='coerce').dropna()
            col_values = col_values[np.abs(col_values) > 1e-9]
            values.extend(col_values.tolist())
        if len(values) == 0:
            return np.nan
        return float(np.median(values))

    def _calculate_carrier_metrics(self, carrier: str, carrier_df: pd.DataFrame) -> Dict:
        """
        Calculate all 21 metrics for a single carrier matching Baybrook structure.
        
        Args:
            carrier: Carrier name
            carrier_df: DataFrame subset for this carrier
        
        Returns:
            Dictionary with all 21 metrics
        """
        metrics = {'Carrier': carrier}
        
        # ====================================================================
        # 1-4: SIGNAL STRENGTH/QUALITY METRICS (RF Health Pillar)
        # ====================================================================
        # Determine technology type: NR (5G) if any "NR" in Data_Network_Type
        has_5g = (carrier_df['Data_Network_Type'] == 'NR').any()
        
        if has_5g:
            # Use 5G metrics
            metrics['RSRP_Summary'] = self._get_median(
                carrier_df, ['5G_SS_RSRP', '5G_CSI_RSRP']
            )
            metrics['RSRQ_dB'] = self._get_median(
                carrier_df, ['5G_SS_RSRQ', '5G_CSI_RSRQ']
            )
            metrics['SINR_Summary'] = self._get_median(
                carrier_df, ['5G_SS_RSSNR', '5G_CSI_RSSNR']
            )
        else:
            # Use LTE metrics
            metrics['RSRP_Summary'] = self._get_median(carrier_df, ['LTE_RSRP'])
            metrics['RSRQ_dB'] = self._get_median(carrier_df, ['LTE_RSRQ'])
            metrics['SINR_Summary'] = self._get_median(carrier_df, ['LTE_RSSNR'])
        
        # 4: RSSI (Received Signal Strength Indicator)
        metrics['RSSI_dBm'] = self._get_median(
            carrier_df, ['LTE_RSSI']
        )
        
        # 5: Noise Floor (RSRP - SINR)
        metrics['Noise_Floor'] = metrics['RSRP_Summary'] - metrics['SINR_Summary'] if not pd.isna(metrics['RSRP_Summary']) and not pd.isna(metrics['SINR_Summary']) else np.nan
        
        # ====================================================================
        # 6-10: CAPACITY PILLAR
        # ====================================================================
        # 6: Total Bandwidth MHz
        metrics['Total_BW_MHz'] = self._calculate_total_bandwidth(carrier_df, has_5g)
        
        # 7: Final 5G State (SA/NSA/LTE)
        metrics['Final_5G_State'] = self._determine_5g_state(carrier_df)
        
        # 8: Handover Success %
        handover_df = carrier_df[carrier_df['LTE_Handover'].notna()] if 'LTE_Handover' in carrier_df.columns else pd.DataFrame()
        metrics['Handover_Success_Pct'] = float(
            (handover_df['LTE_Handover'].str.contains('Success', na=False).sum() / len(handover_df) * 100)
            if len(handover_df) > 0 else 100.0
        )
        
        # 9: CQI Tool Input (mapped from SINR)
        cqi_val = self._map_cqi(metrics['SINR_Summary'])
        metrics['CQI_Tool'] = float(cqi_val) if pd.notna(cqi_val) else np.nan
        
        # 10: Modulation Tool (mapped from SINR)
        metrics['Modulation_Tool'] = self._map_modulation(metrics['SINR_Summary'])
        
        # ====================================================================
        # 11-14: INFRASTRUCTURE PILLAR
        # ====================================================================
        # 11: TX Power (from RootMetrics detail CSV when present)
        metrics['TX_Power_dBm'] = self._get_median(
            carrier_df, ['Average_LTE_UE_PUSCH_Tx_Power']
        )
        
        # 12: MIMO Rank Max
        metrics['MIMO_Rank_Max'] = self._get_max_mimo_rank(carrier_df)
        
        # 13: Band Diversity Count (unique bands)
        metrics['Band_Diversity_Count'] = self._count_unique_bands(carrier_df, has_5g)
        
        # 14: CA Count (Carrier Aggregation layers)
        metrics['CA_Count'] = self._count_carrier_aggregation(carrier_df)
        
        # ====================================================================
        # 15-21: EXPERIENCE & QoS PILLAR
        # ====================================================================
        # 15: Primary Coverage %
        metrics['Primary_Coverage_Pct'] = self._calculate_coverage(carrier_df, has_5g)
        
        # 16-17: Download Performance
        downlink_df = carrier_df[
            carrier_df['Test'].str.contains('Downlink', na=False, case=False)
        ]
        dl_max = downlink_df['Final_Test_Speed'].max() if len(downlink_df) > 0 else np.nan
        metrics['Peak_DL_Mbps'] = float(dl_max) if pd.notna(dl_max) else np.nan
        metrics['Peak_DL_Gbps'] = (
            metrics['Peak_DL_Mbps'] / 1000.0 if pd.notna(metrics['Peak_DL_Mbps']) else np.nan
        )
        metrics['Peak_DL_Mbps_Median'] = self._get_median(downlink_df, ['Final_Test_Speed'])
        metrics['Peak_DL_Mbps_Median_Gbps'] = (
            metrics['Peak_DL_Mbps_Median'] / 1000.0
            if pd.notna(metrics['Peak_DL_Mbps_Median'])
            else np.nan
        )

        # 18-19: Upload Performance
        uplink_df = carrier_df[
            carrier_df['Test'].str.contains('Uplink', na=False, case=False)
        ]
        ul_max = uplink_df['Final_Test_Speed'].max() if len(uplink_df) > 0 else np.nan
        metrics['Peak_UL_Mbps'] = float(ul_max) if pd.notna(ul_max) else np.nan
        metrics['Peak_UL_Gbps'] = (
            metrics['Peak_UL_Mbps'] / 1000.0 if pd.notna(metrics['Peak_UL_Mbps']) else np.nan
        )
        
        # 20: Jitter Median (clipped to 0 minimum)
        jitter_val = self._get_median(
            carrier_df[carrier_df['Test'].str.contains('UDP Echo', na=False, case=False)],
            ['Jitter']
        )
        metrics['Median_Jitter_ms'] = float(max(0, jitter_val)) if not pd.isna(jitter_val) else np.nan
        
        # 21: Packet Loss %
        packet_loss_val = self._get_median(
            carrier_df[carrier_df['Test'].str.contains('UDP Echo', na=False, case=False)],
            ['Drop_rate']
        )
        metrics['Packet_Loss_Pct'] = float(packet_loss_val) if pd.notna(packet_loss_val) else np.nan
        
        # Additional: Median Latency (for export); drop 0 ms artifacts
        udp_df = carrier_df[
            carrier_df['Test'].str.contains('UDP Echo', na=False, case=False)
        ]
        latency_val = self._get_median_latency_ms(udp_df, ['Latency'])
        metrics['Median_Latency_ms'] = float(latency_val) if pd.notna(latency_val) else np.nan
        
        return metrics
    
    def _get_median(self, df: pd.DataFrame, columns: List[str]) -> float:
        """
        Get median value from one or more columns, handling missing data.
        
        Args:
            df: DataFrame subset
            columns: List of column names to consider
        
        Returns:
            Median value or NaN if no data
        """
        values = []
        for col in columns:
            if col in df.columns:
                col_values = pd.to_numeric(df[col], errors='coerce').dropna()
                values.extend(col_values.tolist())
        
        if len(values) == 0:
            return np.nan
        
        return float(np.median(values))
    
    def _determine_5g_state(self, df: pd.DataFrame) -> str:
        """
        Determine if 5G is SA (Standalone) or NSA (Non-Standalone).
        
        Args:
            df: DataFrame for carrier
        
        Returns:
            'SA', 'NSA', or 'None'
        """
        # Check Data_Network_Type for NSA indicators
        network_types = df['Data_Network_Type'].fillna('').astype(str)
        
        # NSA typically shows "NR NSA, LTE" or similar
        has_nsa = network_types.str.contains('NSA', case=False).any()
        # SA shows "NR" alone
        has_sa = network_types.str.contains('NR', case=False).any() and not has_nsa
        
        if has_sa:
            return 'SA'
        elif has_nsa:
            return 'NSA'
        else:
            return 'None'
    
    def _count_carrier_aggregation(self, df: pd.DataFrame) -> int:
        """
        Count unique bands in carrier aggregation breakdown.
        
        Args:
            df: DataFrame for carrier
        
        Returns:
            Number of unique CA bands
        """
        bands = set()
        
        # Check LTE CA
        if 'LTE_CA_Breakdown' in df.columns:
            ca_values = df['LTE_CA_Breakdown'].dropna().astype(str)
            for val in ca_values:
                if val and val != 'nan':
                    # Parse format like "B48-0.000,W/oB48-1.000"
                    parts = str(val).split(',')
                    for part in parts:
                        band = part.split('-')[0].strip()
                        if band:
                            bands.add(band)
        
        # Check NR CA
        if 'NR_CA_Breakdown' in df.columns:
            ca_values = df['NR_CA_Breakdown'].dropna().astype(str)
            for val in ca_values:
                if val and val != 'nan':
                    # Parse format like "1cc-0.000,2cc-1.000"
                    parts = str(val).split(',')
                    for part in parts:
                        band = part.split('-')[0].strip()
                        if band:
                            bands.add(band)
        
        return len(bands)
    
    def _calculate_coverage(self, df: pd.DataFrame, has_5g: bool) -> float:
        """
        Calculate coverage percentage (% of samples where RSRP > -110 dBm).
        
        Args:
            df: DataFrame for carrier
            has_5g: Whether carrier has 5G
        
        Returns:
            Coverage percentage (0-100)
        """
        if has_5g:
            # Use 5G RSRP
            rsrp_col = '5G_SS_RSRP'
            if rsrp_col not in df.columns:
                rsrp_col = '5G_CSI_RSRP'
        else:
            # Use LTE RSRP
            rsrp_col = 'LTE_RSRP'
        
        if rsrp_col not in df.columns:
            return np.nan
        
        rsrp_values = pd.to_numeric(df[rsrp_col], errors='coerce').dropna()
        
        if len(rsrp_values) == 0:
            return np.nan
        
        # RSRP > -110 is considered good coverage
        coverage_count = (rsrp_values > -110).sum()
        coverage_percent = (coverage_count / len(rsrp_values)) * 100
        
        return float(coverage_percent)
    
    def _map_cqi(self, sinr: float) -> int:
        """
        Map SINR value to CQI Index (matching Baybrook logic).
        
        Args:
            sinr: SINR value in dB
        
        Returns:
            CQI Index (6-15)
        """
        if pd.isna(sinr) or sinr <= 0:
            return 6
        if sinr > 15:
            return 15
        if sinr > 10:
            return 12
        return 9
    
    def _map_modulation(self, sinr: float) -> str:
        """
        Map SINR value to modulation type (matching Baybrook logic).
        
        Args:
            sinr: SINR value in dB
        
        Returns:
            Modulation string
        """
        if pd.isna(sinr) or sinr <= 0:
            return "Modulation Failed"
        if sinr > 18:
            return "256 QAM (Excellent)"
        if sinr > 12:
            return "64 QAM (Good)"
        if sinr > 6:
            return "16 QAM (Average)"
        return "QPSK (Fair)"
    
    def _calculate_total_bandwidth(self, df: pd.DataFrame, has_5g: bool) -> float:
        """
        Calculate total bandwidth MHz by summing unique carrier frequencies.
        
        Args:
            df: DataFrame for carrier
            has_5g: Whether carrier has 5G
        
        Returns:
            Total bandwidth in MHz
        """
        bw_values = set()
        
        if has_5g:
            # Sum 5G bandwidths (CC1-CC8)
            for i in range(1, 9):
                col = f'5G_Bandwidth_CC{i}'
                if col in df.columns:
                    vals = pd.to_numeric(df[col], errors='coerce').dropna().unique()
                    bw_values.update(vals)
        else:
            # Sum LTE bandwidths (Pcell + Scells)
            bw_cols = ['LTE_Bandwidth_Pcell', 'LTE_Bandwidth_Scell1', 'LTE_Bandwidth_Scell2', 
                       'LTE_Bandwidth_Scell3', 'LTE_Bandwidth_Scell4']
            for col in bw_cols:
                if col in df.columns:
                    vals = pd.to_numeric(df[col], errors='coerce').dropna().unique()
                    bw_values.update(vals)
        
        total_bw = sum(bw_values) if bw_values else 20.0
        return float(total_bw) if total_bw > 0 else 20.0
    
    def _count_unique_bands(self, df: pd.DataFrame, has_5g: bool) -> int:
        """
        Count unique bands (Band Diversity).
        
        Args:
            df: DataFrame for carrier
            has_5g: Whether carrier has 5G
        
        Returns:
            Number of unique bands
        """
        bands = set()
        
        if has_5g:
            # Check 5G bands (CC1-CC8)
            for i in range(1, 9):
                col = f'5G_Band_CC{i}'
                if col in df.columns:
                    band_vals = df[col].dropna().unique()
                    for b in band_vals:
                        if pd.notna(b):
                            try:
                                bands.add(str(int(b)))
                            except (ValueError, TypeError):
                                # Handle string band names like 'AWS-3'
                                bands.add(str(b))
        else:
            # Check LTE bands (Pcell + Scells)
            band_cols = ['LTE_Band_Pcell', 'LTE_Band_Scell1', 'LTE_Band_Scell2',
                        'LTE_Band_Scell3', 'LTE_Band_Scell4']
            for col in band_cols:
                if col in df.columns:
                    band_vals = df[col].dropna().unique()
                    for b in band_vals:
                        if pd.notna(b):
                            try:
                                bands.add(str(int(b)))
                            except (ValueError, TypeError):
                                # Handle string band names like 'AWS-3'
                                bands.add(str(b))
        
        return len(bands)
    
    def _get_max_mimo_rank(self, df: pd.DataFrame) -> int:
        """
        Get maximum MIMO Rank from the data.
        
        Args:
            df: DataFrame for carrier
        
        Returns:
            Maximum MIMO Rank (1-4)
        """
        # Check for MIMO rank indicators in Average_LTE_DL_RBs, NR_RI_Mode, or LTE_RI_Mode
        # For now, infer from CA count as a proxy (more CA = better MIMO typically)
        ca_count = self._count_carrier_aggregation(df)
        
        if ca_count >= 4:
            return 4
        elif ca_count >= 2:
            return 2
        else:
            return 1
