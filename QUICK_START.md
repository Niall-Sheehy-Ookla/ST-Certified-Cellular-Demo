# 📡 Cellular Certification ETL & Dashboard - Installation & Quick Start

## ✅ What's Been Created

Your complete Cellular Certification application is ready with:

### Core Application Files
- **app.py** - Main Streamlit application with 3-tab interface
- **metrics_processor.py** - Calculates 20+ metrics per carrier
- **certification_scorer.py** - Scoring algorithm and badge assignment
- **dashboard_ui.py** - Interactive UI components and visualizations
- **config.py** - Configuration, thresholds, and reference data

### Setup & Documentation
- **requirements.txt** - Python dependencies (streamlit, pandas, numpy, openpyxl)
- **README.md** - Comprehensive documentation
- **launch.sh** - Quick start script (macOS/Linux)
- **launch.bat** - Quick start script (Windows)
- **QUICK_START.md** - This file

---

## 🚀 Quick Start (Choose Your OS)

### macOS / Linux
```bash
# Navigate to project directory
cd "Cellular Scoring csv metric builder and scoring UI"

# Run the quick start script
chmod +x launch.sh
./launch.sh
```

### Windows
```bash
# Navigate to project directory
cd "Cellular Scoring csv metric builder and scoring UI"

# Run the quick start script
launch.bat
```

### Manual Setup (All Platforms)
```bash
# 1. Create virtual environment
python3 -m venv venv

# 2. Activate it
# macOS/Linux:
source venv/bin/activate
# Windows:
venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run the app
streamlit run app.py
```

---

## 📊 Using the Application

The dashboard opens in your browser at `http://localhost:8501`

### Tab 1: Data Processing
1. Upload your Seattle Full Detail CSV
2. Click "Process Metrics" to calculate all 20+ metrics
3. Review calculated metrics table

### Tab 2: Certification Review
1. View live certification cards for each carrier
2. Use sidebar to input manual metrics:
   - VPN Usage (Standard, VPN-Lite, VPN-Full)
   - ISP Redundancy (None, Fibre+1, Fibre+2, Diverse)
   - ISP Diversity (Single, Dual, Triple+)
   - AP Model/Hardware Age
   - Notes
3. Scores update instantly as you change inputs
4. View detailed metric breakdowns and score analysis

### Tab 3: Export Results
1. Preview final certification table
2. Download as CSV or Excel
3. See summary of badge distribution

---

## 📈 Metrics Calculated (20+ per Carrier)

### Signal Quality (25% weight)
- RSRP Median (dBm)
- RSRQ Median (dB)
- SINR/RSSNR Median (dB)

### Performance (35% weight)
- Download Speed Median & Peak (Mbps)
- Upload Speed Median & Peak (Mbps)

### Latency & Jitter (20% weight)
- Latency Median (ms)
- Jitter Median (ms)

### Advanced Radio (20% weight)
- CQI Median
- 5G State (SA/NSA/None)
- CA Count (carrier aggregation bands)
- Coverage % (RSRP > -110 dBm samples)

---

## 🏆 Certification Badges

| Badge | Score | Description |
|-------|-------|-------------|
| 🏆 Platinum | 90-100 | Exceptional performance |
| ⭐ Gold | 75-89 | Excellent performance |
| ✨ Silver | 60-74 | Good performance |
| ❌ Fail | 0-59 | Below standard |

---

## 📋 Scoring Logic

### Example Score Calculation
```
Signal Quality Score: 85 (Excellent RSRP, good RSRQ)
Performance Score: 92 (High download/upload speeds)
Latency Score: 78 (Good latency, acceptable jitter)
Radio Score: 88 (5G NSA, 3-CA, 92% coverage)

Total = (85 × 0.25) + (92 × 0.35) + (78 × 0.20) + (88 × 0.20)
      = 21.25 + 32.2 + 15.6 + 17.6
      = 86.65 → Gold Badge (75-89)
```

---

## 📥 Input Requirements

Your CSV must have:
- `Network` - Carrier name
- `Data_Network_Type` - "NR" for 5G, otherwise LTE
- `Test` - Test type (Downlink, Uplink, UDP Echo)
- `Final_Test_Speed` - Speed in Mbps
- `Latency` - Latency in ms
- `Jitter` - Jitter in ms
- `LTE_RSRP`, `LTE_RSRQ`, `LTE_RSSNR` - LTE metrics
- `5G_SS_RSRP`, `5G_SS_RSRQ`, `5G_SS_RSSNR` - 5G metrics
- `LTE_CQI` or `Average_LTE_CQI` - Channel quality
- `LTE_CA_Breakdown`, `NR_CA_Breakdown` - Carrier aggregation

✅ The Seattle CSV has all these columns!

---

## 📊 Export Output Format

Your CSV export includes:
1. Carrier name
2. All 20+ calculated metrics
3. Manual input values (VPN, ISP redundancy, etc.)
4. Final certification score (0-100)
5. Badge assignment
6. Certification notes

Perfect for Alan and Dan's decision-making!

---

## 🔧 Troubleshooting

### Issue: "Import streamlit could not be resolved"
**Solution:** This is just a VS Code warning. Install dependencies and run normally.
```bash
pip install -r requirements.txt
streamlit run app.py
```

### Issue: "No data found" when uploading CSV
**Solution:** 
- Verify `Network` column exists in CSV
- Check file is properly formatted CSV
- Ensure at least one row has data

### Issue: Scores show NaN or blank
**Solution:**
- Complete Tab 1 (Data Processing) first
- Verify CSV has required columns
- Check for empty/missing values in key columns

### Issue: Sidebar inputs not saving
**Solution:**
- Refresh browser page
- Re-select carrier in dropdown
- Clear browser cache if persists

---

## 📚 File Structure

```
Cellular Scoring csv metric builder and scoring UI/
├── app.py                          # Main Streamlit app
├── metrics_processor.py            # Metric calculation engine
├── certification_scorer.py         # Scoring algorithm
├── dashboard_ui.py                 # UI components
├── config.py                       # Configuration & thresholds
├── requirements.txt                # Python dependencies
├── launch.sh                       # Quick start (macOS/Linux)
├── launch.bat                      # Quick start (Windows)
├── README.md                       # Full documentation
├── QUICK_START.md                  # This file
└── Seattle-WA-SK2_2026-1H_All_Detail.csv  # Sample data
```

---

## 🎯 Next Steps

1. **Run the application**
   ```bash
   streamlit run app.py
   ```

2. **Upload your Seattle CSV**
   - Use Tab 1: Data Processing

3. **Process metrics**
   - Click "Process Metrics" button
   - Wait for calculation to complete

4. **Review & customize**
   - Go to Tab 2: Certification Review
   - Input manual metrics in sidebar
   - Watch scores update in real-time

5. **Export results**
   - Go to Tab 3: Export Results
   - Download CSV or Excel file
   - Share with Alan and Dan

---

## 💡 Key Features Implemented

✅ **Automated Metric Calculation**
- Processes 19,700+ raw data points
- Calculates 20+ metrics per carrier
- Handles LTE/5G automatically

✅ **Intelligent Scoring**
- Weighted algorithm (Signal 25%, Performance 35%, Latency 20%, Radio 20%)
- Evidence-based reference thresholds
- Four-tier badge system (Platinum/Gold/Silver/Fail)

✅ **Manual Overrides**
- VPN Usage, ISP Redundancy, ISP Diversity, AP Model
- Free-form notes field
- Per-carrier customization

✅ **Live Dashboard**
- Real-time score updates
- Interactive certification cards
- Detailed metric breakdowns
- Score component analysis

✅ **Professional Export**
- CSV and Excel formats
- 23-row certification format
- Combined calculated + manual metrics
- Badge assignment and notes

---

## 🤝 Support

For questions or customizations:
1. Review **README.md** for detailed documentation
2. Check **config.py** for all thresholds
3. Edit metric weights in **certification_scorer.py**
4. Modify reference thresholds in threshold functions

---

## 📅 Date Created

Generated: March 20, 2026

**Application Status**: ✅ Ready for Production

---

Enjoy your Cellular Certification Dashboard! 🚀📡
