"""
Configuration and Reference Guide for Cellular Certification Dashboard
"""

# ============================================================================
# SCORING THRESHOLDS
# ============================================================================

# Badge thresholds (adjust in certification_scorer.py if needed)
BADGE_THRESHOLDS = {
    'Platinum': 90,     # 90-100: Exceptional performance
    'Gold': 75,         # 75-89: Excellent performance
    'Silver': 60,       # 60-74: Good performance
    'Fail': 0           # 0-59: Below standard
}

# ============================================================================
# SIGNAL STRENGTH THRESHOLDS (dBm)
# ============================================================================

RSRP_THRESHOLDS = {
    'Excellent': -95,       # RSRP > -95 dBm
    'Good': -110,           # RSRP -95 to -110 dBm
    'Fair': -120,           # RSRP -110 to -120 dBm
    'Poor': float('-inf')   # RSRP < -120 dBm
}

RSRQ_THRESHOLDS = {
    'Excellent': -5,        # RSRQ > -5 dB
    'Good': -15,            # RSRQ -5 to -15 dB
    'Fair': -20,            # RSRQ -15 to -20 dB
    'Poor': float('-inf')   # RSRQ < -20 dB
}

# ============================================================================
# PERFORMANCE THRESHOLDS (Mbps)
# ============================================================================

DOWNLOAD_SPEED_THRESHOLDS = {
    'Excellent': 150,       # > 150 Mbps
    'Good': 100,            # 100-150 Mbps
    'Fair': 50,             # 50-100 Mbps
    'Poor': 0               # < 50 Mbps
}

UPLOAD_SPEED_THRESHOLDS = {
    'Excellent': 50,        # > 50 Mbps
    'Good': 30,             # 30-50 Mbps
    'Fair': 10,             # 10-30 Mbps
    'Poor': 0               # < 10 Mbps
}

# ============================================================================
# LATENCY/JITTER THRESHOLDS (milliseconds)
# ============================================================================

LATENCY_THRESHOLDS = {
    'Excellent': 20,        # < 20 ms (ideal for VoIP/gaming)
    'Good': 50,             # 20-50 ms (acceptable)
    'Fair': 100,            # 50-100 ms (noticeable)
    'Poor': float('inf')    # > 100 ms (poor)
}

JITTER_THRESHOLDS = {
    'Excellent': 5,         # < 5 ms variance
    'Good': 15,             # 5-15 ms variance
    'Fair': 30,             # 15-30 ms variance
    'Poor': float('inf')    # > 30 ms variance
}

# ============================================================================
# COVERAGE THRESHOLDS (percentage)
# ============================================================================

COVERAGE_THRESHOLDS = {
    'Excellent': 95,        # > 95% (comprehensive)
    'Good': 80,             # 80-95% (solid)
    'Fair': 60,             # 60-80% (acceptable)
    'Poor': 0               # < 60% (gaps exist)
}

# RSRP threshold for coverage calculation
COVERAGE_RSRP_MINIMUM = -110  # dBm (strong signal threshold)

# ============================================================================
# CARRIER AGGREGATION (CA) SCORING
# ============================================================================

CA_SCORE_MAPPING = {
    1: 25,      # Single band: 25%
    2: 50,      # Dual band: 50%
    3: 75,      # Triple band: 75%
    4: 90,      # Quad band: 90%
    5: 100,     # 5+ bands: 100%
}

# ============================================================================
# 5G STATE SCORING
# ============================================================================

G5_STATE_SCORE = {
    'SA': 100,          # Standalone: Full score
    'NSA': 75,          # Non-standalone: Good but not optimal
    'None': 50          # No 5G: Baseline
}

# ============================================================================
# WEIGHTED SCORE COMPONENTS
# ============================================================================

SCORE_WEIGHTS = {
    'Signal_Quality': 0.25,      # 25% of total
    'Performance': 0.35,         # 35% of total
    'Latency_Jitter': 0.20,      # 20% of total
    'Advanced_Radio': 0.20       # 20% of total
}

# Within Signal Quality (25% of total)
SIGNAL_WEIGHTS = {
    'RSRP': 0.40,       # 40% of signal score
    'RSRQ': 0.35,       # 35% of signal score
    'SINR': 0.25        # 25% of signal score
}

# Within Performance (35% of total)
PERFORMANCE_WEIGHTS = {
    'Download': 0.70,   # 70% of performance score
    'Upload': 0.30      # 30% of performance score
}

# Within Latency/Jitter (20% of total)
LATENCY_WEIGHTS = {
    'Latency': 0.70,    # 70% of latency score
    'Jitter': 0.30      # 30% of latency score
}

# Within Advanced Radio (20% of total)
RADIO_WEIGHTS = {
    '5G_State': 0.30,       # 30% of radio score
    'CA_Count': 0.35,       # 35% of radio score
    'Coverage': 0.35        # 35% of radio score
}

# ============================================================================
# MANUAL INPUT OPTIONS
# ============================================================================

VPN_USAGE_OPTIONS = [
    'Standard',
    'VPN-Lite',
    'VPN-Full'
]

ISP_REDUNDANCY_OPTIONS = [
    'None',
    'Fibre+1',
    'Fibre+2',
    'Diverse'
]

ISP_DIVERSITY_OPTIONS = [
    'Single',
    'Dual',
    'Triple+'
]

AP_MODEL_OPTIONS = [
    'Old (2020)',
    'Standard (2022)',
    'Modern (2024)',
    'Latest (2025)'
]

# ============================================================================
# DATA COLUMN MAPPING
# ============================================================================

# Required columns in input CSV
REQUIRED_COLUMNS = [
    'Network',                  # Carrier name
    'Data_Network_Type',        # LTE/NR/etc
    'Test',                     # Test type
    'Final_Test_Speed',         # Speed in Mbps
    'Latency',                  # Latency in ms
    'Jitter'                    # Jitter in ms
]

# LTE Signal columns
LTE_SIGNAL_COLUMNS = {
    'RSRP': 'LTE_RSRP',
    'RSRQ': 'LTE_RSRQ',
    'RSSNR': 'LTE_RSSNR',
    'CQI': 'LTE_CQI',
    'CQI_AVG': 'Average_LTE_CQI',
    'CA': 'LTE_CA_Breakdown'
}

# 5G Signal columns
G5_SIGNAL_COLUMNS = {
    'SS_RSRP': '5G_SS_RSRP',
    'SS_RSRQ': '5G_SS_RSRQ',
    'SS_RSSNR': '5G_SS_RSSNR',
    'CSI_RSRP': '5G_CSI_RSRP',
    'CSI_RSRQ': '5G_CSI_RSRQ',
    'CSI_RSSNR': '5G_CSI_RSSNR',
    'CA': 'NR_CA_Breakdown'
}

# ============================================================================
# EXPORT COLUMNS
# ============================================================================

EXPORT_COLUMNS = [
    'Carrier',
    # Calculated Metrics
    'Signal_RSRP_Median',
    'Signal_RSRQ_Median',
    'Signal_SINR_Median',
    'Download_Speed_Median',
    'Download_Speed_Peak',
    'Upload_Speed_Median',
    'Upload_Speed_Peak',
    'Latency_Median',
    'Jitter_Median',
    'CQI_Median',
    '5G_State',
    'CA_Count',
    'Coverage_Percent',
    # Manual Metrics
    'VPN_Usage',
    'ISP_Redundancy',
    'ISP_Diversity',
    'AP_Model_Hardware',
    # Score Results
    'Certification_Score',
    'Certification_Badge',
    'Notes'
]

# ============================================================================
# TEST TYPE FILTERS
# ============================================================================

TEST_TYPES = {
    'Downlink': 'Download speed test',
    'Uplink': 'Upload speed test',
    'UDP Echo': 'Latency and jitter test',
    'Video': 'Video streaming test'
}

# ============================================================================
# BADGE CONFIGURATION
# ============================================================================

BADGE_CONFIG = {
    'Platinum': {
        'emoji': '🏆',
        'color': '#E5E4E2',
        'description': 'Exceptional Performance',
        'min_score': 90
    },
    'Gold': {
        'emoji': '⭐',
        'color': '#FFD700',
        'description': 'Excellent Performance',
        'min_score': 75
    },
    'Silver': {
        'emoji': '✨',
        'color': '#C0C0C0',
        'description': 'Good Performance',
        'min_score': 60
    },
    'Fail': {
        'emoji': '❌',
        'color': '#DC143C',
        'description': 'Below Standard',
        'min_score': 0
    }
}

# ============================================================================
# QUALITY OF SERVICE (QoS) TARGETS
# ============================================================================

QOS_TARGETS = {
    'VoIP': {
        'latency': 50,      # ms
        'jitter': 10,       # ms
        'bandwidth': 0.1    # Mbps
    },
    'Video Conferencing': {
        'latency': 100,     # ms
        'jitter': 20,       # ms
        'bandwidth': 2.5    # Mbps
    },
    'Video Streaming': {
        'latency': 200,     # ms
        'jitter': 30,       # ms
        'bandwidth': 5      # Mbps
    },
    'Web Browsing': {
        'latency': 300,     # ms
        'jitter': 50,       # ms
        'bandwidth': 1      # Mbps
    }
}

# ============================================================================
# DOCUMENTATION
# ============================================================================

"""
METRIC DEFINITIONS

Signal Strength/Quality:
  - RSRP (Reference Signal Receive Power): Actual power level received
  - RSRQ (Reference Signal Receive Quality): Quality of signal (SINR + RSRP)
  - RSSNR (Reference Signal Signal-to-Noise Ratio): Signal vs noise ratio
  - CQI (Channel Quality Indicator): 0-15 scale for LTE

Performance:
  - Download Speed: Median of downlink test speeds (Mbps)
  - Upload Speed: Median of uplink test speeds (Mbps)
  - Peak Speed: Maximum speed observed in tests

Latency/Jitter:
  - Latency: Round-trip time in milliseconds
  - Jitter: Variance in round-trip times (ms)

Advanced Radio:
  - 5G State: SA (Standalone) or NSA (Non-Standalone) mode
  - CA Count: Number of unique carrier aggregation bands
  - Coverage: % of samples meeting RSRP > -110 dBm threshold
"""
