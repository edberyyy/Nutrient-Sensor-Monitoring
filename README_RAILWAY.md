# Nutrient Sensor Monitoring System

## 📊 Overview

A 24/7 web-based sensor monitoring system that:
- Scrapes live data from Grafana dashboards every 10 minutes
- Stores historical data in CSV format
- Displays interactive real-time and historical charts
- Runs entirely in the cloud on Railway

---

## 🚀 Features

✅ **Live Dashboard** - Real-time sensor data display
✅ **Historical Data** - All readings stored in persistent CSV
✅ **Two Sensors** - Soil temperature, moisture, EC, pH, NPK
✅ **Interactive Charts** - Temperature, Moisture, EC, pH, NPK trends
✅ **24/7 Monitoring** - Automatic scraping every 10 minutes
✅ **No Cost** - Free Railway tier with unlimited uptime

---

## 📈 What Data Is Displayed

### Current Data (Latest Readings)
- Sensor 1 & 2 connection status
- Latest values for each sensor
- Real-time indicator cards

### Historical Data (Graphs)
- Charts built from ALL stored CSV records
- Sensor 1: Temperature, Moisture, EC, pH
- Sensor 2: Temperature, Moisture, EC, pH, Nitrogen, Phosphorus, Potassium
- Filterable by sensor and time range (24h, 7d, 30d, all)

---

## 🔄 How It Works on Railway

### Web Process
- Flask server runs on assigned port
- Serves dashboard.html as frontend
- Provides API endpoints:
  - `/api/latest` - Current readings
  - `/api/history` - All historical data
  - `/api/debug` - Diagnostic information

### Worker Process
- Headless browser with Playwright
- Accesses Grafana dashboards
- Extracts sensor readings every 10 minutes
- Appends new data to readings_history.csv
- Stores latest values in last_readings.json

### Data Persistence
- CSV file deployed from GitHub repository
- All new readings appended (not replaced)
- Persists across app restarts
- Data grows over time as scraper runs

---

## 📁 Key Files

```
├── server.py              # Flask backend + API endpoints
├── monitor.py             # Grafana scraper + data extraction
├── dashboard.html         # Interactive web interface
├── readings_history.csv   # All historical sensor data (PERSISTENT)
├── Procfile              # Two processes: web + worker
├── Dockerfile            # Container configuration
└── requirements.txt      # Python dependencies
```

---

## 📊 CSV File Structure

The `readings_history.csv` contains:
- timestamp_iso (when reading was taken)
- sensor (Sensor 1 or Sensor 2)
- temperature_c, moisture_pct, ec_us_cm, ph
- nitrogen, phosphorus, potassium (NPK)
- status fields (temperature_status, moisture_status, etc.)

**File grows continuously** as new readings are added.

---

## 🔗 How to Access

After deployment on Railway:

1. Visit your dashboard: `https://your-app-name.up.railway.app`
2. View live sensor status (Connected/Disconnected)
3. See current readings in cards
4. Scroll down to view historical charts
5. Filter charts by sensor and time range

---

## 🛠️ Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run server (with embedded scraper)
python server.py

# Access at http://localhost:5000
```

---

## 🚀 Deployment to Railway

1. Push to GitHub: `git push origin main`
2. Railway automatically detects changes
3. Rebuilds container from Dockerfile
4. Deploys web + worker processes
5. CSV data is carried over from git

---

## 📊 Expected Graph Display

- **First deployment**: Shows historical data from CSV in git + new data from scraper
- **Subsequent deployments**: Combines all old data + new data
- **Over time**: Charts get richer as more data accumulates

---

## 🔍 Troubleshooting

### "Disconnected" Status
- Check `/api/debug` endpoint
- Verify Grafana dashboards are accessible
- Check Railway logs for scraper errors

### No Historical Data
- CSV file should be deployed from git
- Check CSV file size: should be > 1KB
- Visit `/api/debug` to see data count

### Graphs are Empty
- Check browser console for JavaScript errors
- Ensure `/api/history` returns data
- Verify CSV file exists in Railway

---

## 📝 Notes

- Data is timestamped in ISO format
- Sensor 1 may show "NA" if not sending data to Grafana
- Sensor 2 is actively sending data
- Charts render with all available data
- Auto-refresh every 30 seconds

---

## 🎯 Next Steps

1. Monitor dashboard for data quality
2. Check graphs populate over time
3. Verify 10-minute scraper intervals
4. Watch CSV file grow in Railway storage
