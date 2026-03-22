# 📡 Cellular Certification ETL & Dashboard

A Streamlit application that automates the transition from raw Rootmetrics logs to a "Certified Cellular" audit with scoring and badge assignment.

## Overview

This application processes raw Rootmetrics CSV data and calculates **20+ certification metrics** per carrier, allowing Alan and Dan to make certification decisions with:

- **Automated Metric Calculation**: Extracts signal, performance, latency, and advanced radio metrics
- **Intelligent Scoring**: Weighted algorithm assigns Platinum/Gold/Silver/Fail badges
- **Manual Overrides**: Input non-CSV metrics (VPN usage, ISP redundancy, etc.)
- **Live Dashboard**: Real-time certification cards with instant score updates
- **CSV Export**: Generate final audit report in Excel format

## Features

### Part 1: Processing Logic (All-Detail CSV Aggregator)

Processes uploaded CSV and calculates per-carrier metrics:

#### Signal Strength/Quality
- **Logic**: Uses 5G columns if `Data_Network_Type` shows "NR", otherwise LTE
- **Metrics**: 
  - Median RSRP (Reference Signal Power)
  - Median RSRQ (Reference Signal Quality)
  - Median RSSNR (mapped as SINR)

#### Performance (Mbps)
- **Download**: Median and Peak of `Final_Test_Speed` where Test includes "Downlink"
- **Upload**: Median and Peak of `Final_Test_Speed` where Test includes "Uplink"

#### Latency/Jitter
- **Latency**: Median from UDP Echo tests
- **Jitter**: Variation in UDP Echo response times

#### Advanced Radio Metrics
- **CQI**: Median of `LTE_CQI` or `Average_LTE_CQI`
- **5G State**: "SA" (Standalone) or "NSA" (Non-Standalone)
- **CA Count**: Unique bands in `LTE_CA_Breakdown` or `NR_CA_Breakdown`
- **Coverage %**: Samples where RSRP > -110 dBm

### Part 2: Interactive Dashboard (Scoring View)

#### Certification Cards
For each carrier, displays:
- Badge (Platinum 🏆 | Gold ⭐ | Silver ✨ | Fail ❌)
- Composite score (0-100)
- Detailed metric breakdowns
- Score component analysis

#### Manual Overrides (Sidebar)
Alan can input non-CSV metrics:
- **VPN Usage**: Standard, VPN-Lite, VPN-Full
- **ISP Redundancy**: None, Fibre+1, Fibre+2, Diverse
- **ISP Diversity**: Single, Dual, Triple+
- **AP Model/Hardware Age**: Old (2020), Standard (2022), Modern (2024), Latest (2025)
- **Notes**: Free-form text for decisions

#### Live Math
As Alan changes inputs, carrier scores update instantly on screen.

### Part 3: Output

#### CSV Export
Generates 23-row format combining:
- Calculated Metrics (all 20+ metrics from Seattle CSV)
- Manual Inputs (from Alan)
- Final Badge Assignment
- Certification Scores

Export formats: CSV or Excel (.xlsx)

## Installation

### Prerequisites
- Python 3.8+
- pip package manager

### Setup

1. **Clone or navigate to project directory**
   ```bash
   cd "Cellular Scoring csv metric builder and scoring UI"
   ```

2. **Create virtual environment** (recommended)
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

## Usage

### Running the Application

```bash
streamlit run app.py
```

The application will open in your default browser at `http://localhost:8501`

### Workflow

**Tab 1: Data Processing**
1. Upload `Seattle-WA-SK2_2026-1H_All_Detail.csv` or similar
2. Verify data loads (shows record count and carriers found)
3. Click "Process Metrics" button
4. Review calculated metrics table

**Tab 2: Certification Review**
1. Metrics auto-populate from Tab 1
2. Use sidebar to select carriers and input manual metrics
3. View live certification cards with scores and badges
4. Review detailed metric breakdowns

**Tab 3: Export Results**
1. Review final certification table
2. Download as CSV or Excel
3. Summary shows badge distribution

## Scoring Algorithm

### Badge Thresholds
- **Platinum**: 90-100 points
- **Gold**: 75-89 points
- **Silver**: 60-74 points
- **Fail**: 0-59 points

### Weighted Components
- **Signal Quality** (25%): RSRP, RSRQ, SINR
- **Performance** (35%): Download/Upload speeds
- **Latency/Jitter** (20%): Network timing
- **Advanced Radio** (20%): 5G state, CA count, coverage

### Reference Thresholds

| Metric | Excellent | Good | Fair | Poor |
|--------|-----------|------|------|------|
| RSRP | > -95 dBm | -95 to -110 | -110 to -120 | < -120 |
| Download | > 150 Mbps | 100-150 | 50-100 | < 50 |
| Latency | < 20 ms | 20-50 | 50-100 | > 100 |
| Coverage | > 95% | 80-95% | 60-80% | < 60% |

## Data Requirements

The input CSV must contain these columns:

### Required Fields
- `Network`: Carrier name
- `Data_Network_Type`: Technology type (LTE, NR, etc.)
- `Test`: Test type identifier
- `Final_Test_Speed`: Speed measurement
- `Latency`: Latency in ms
- `Jitter`: Jitter in ms

### LTE Signal Columns
- `LTE_RSRP`: Reference Signal Power
- `LTE_RSRQ`: Reference Signal Quality
- `LTE_RSSNR`: Signal-to-Noise Ratio
- `LTE_CQI` or `Average_LTE_CQI`: Channel Quality
- `LTE_CA_Breakdown`: Carrier aggregation info

### 5G Signal Columns
- `5G_SS_RSRP`: 5G Signal Power
- `5G_SS_RSRQ`: 5G Signal Quality
- `5G_SS_RSSNR`: 5G Signal Ratio
- `NR_CA_Breakdown`: 5G carrier aggregation

## Output Format

### Export CSV Columns
```
Carrier
Signal_RSRP_Median
Signal_RSRQ_Median
Signal_SINR_Median
Download_Speed_Median
Download_Speed_Peak
Upload_Speed_Median
Upload_Speed_Peak
Latency_Median
Jitter_Median
CQI_Median
5G_State
CA_Count
Coverage_Percent
VPN_Usage
ISP_Redundancy
ISP_Diversity
AP_Model_Hardware
Certification_Score
Certification_Badge
Notes
```

## Architecture

### Modules

**app.py** - Main Streamlit application with UI
- File upload and preview
- Three-tab interface
- Session state management

**metrics_processor.py** - Metric calculation engine
- `MetricsProcessor` class
- Calculates 20+ metrics per carrier
- Handles LTE/5G detection
- Median aggregation logic

**certification_scorer.py** - Scoring and badging
- `CertificationScorer` class
- Weighted score algorithm
- Badge assignment logic
- Component-wise scoring

**dashboard_ui.py** - UI rendering
- `DashboardUI` class
- Certification cards
- Score visualization
- Summary tables

## Troubleshooting

### "No data found" error
- Verify CSV has `Network` column
- Check column names match expected format
- Ensure at least one carrier has data

### Scores not updating
- Verify Tab 1 (Data Processing) was completed
- Check manual inputs in sidebar
- Refresh browser if needed

### Export shows empty columns
- Verify metrics were calculated in Tab 1
- Check that carriers have valid data
- Ensure CSV had required columns

## Customization

### Adjusting Score Weights
Edit `certification_scorer.py`, line ~155:
```python
total_score = (
    scores['Signal_Score'] * 0.25 +      # Adjust percentages
    scores['Performance_Score'] * 0.35 +
    scores['Latency_Score'] * 0.20 +
    scores['Radio_Score'] * 0.20
)
```

### Adjusting Badge Thresholds
Edit `certification_scorer.py`, line ~26:
```python
BADGE_THRESHOLDS = {
    'Platinum': 90,    # Modify scores here
    'Gold': 75,
    'Silver': 60,
    'Fail': 0
}
```

### Reference Thresholds
See `_score_*` methods in `certification_scorer.py` for metric-specific thresholds.

## Support

For questions or issues:
1. Check data requirements section
2. Verify input CSV format
3. Review scoring methodology
4. Check error messages in Streamlit interface

## License

Internal use only - Cellular Certification Project
