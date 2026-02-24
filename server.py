from flask import Flask, jsonify, send_from_directory
import csv
from datetime import datetime
import os
import threading
import time

app = Flask(__name__, static_folder='.')

CSV_FILE = "readings_history.csv"

def ensure_csv_initialized():
    """Ensure CSV file exists with headers"""
    if not os.path.exists(CSV_FILE):
        print(f"   [*] Initializing {CSV_FILE}...")
        with open(CSV_FILE, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                'timestamp_iso', 'sensor', 'temperature_c', 'moisture_pct',
                'ec_us_cm', 'ph', 'nitrogen', 'phosphorus', 'potassium',
                'temperature_status', 'moisture_status',
                'ec_status', 'ph_status', 'overall_status'
            ])
        print(f"   [OK] CSV initialized with headers")
    else:
        # Check if CSV has headers (more than 0 lines)
        with open(CSV_FILE, 'r', newline='') as f:
            line_count = sum(1 for line in f)
        if line_count == 0:
            print(f"   [*] CSV file empty, adding headers...")
            with open(CSV_FILE, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([
                    'timestamp_iso', 'sensor', 'temperature_c', 'moisture_pct',
                    'ec_us_cm', 'ph', 'nitrogen', 'phosphorus', 'potassium',
                    'temperature_status', 'moisture_status',
                    'ec_status', 'ph_status', 'overall_status'
                ])
            print(f"   [OK] Headers added to CSV")

def read_csv_data():
    """Read all data from CSV file"""
    ensure_csv_initialized()
    data = []
    try:
        if os.path.exists(CSV_FILE):
            with open(CSV_FILE, 'r', newline='') as f:
                reader = csv.DictReader(f)
                if reader is not None:
                    for row in reader:
                        if row:  # Skip empty rows
                            # Ensure NPK fields exist (for backward compatibility)
                            row.setdefault('nitrogen', 'NA')
                            row.setdefault('phosphorus', 'NA')
                            row.setdefault('potassium', 'NA')
                            data.append(row)
    except Exception as e:
        print(f"   [!] Error reading CSV: {e}")
    return data

def get_latest_readings():
    """Get the most recent reading for each sensor"""
    data = read_csv_data()
    latest = {}
    
    for row in data:
        sensor = row.get('sensor', 'Unknown')
        latest[sensor] = row
    
    return latest

@app.route('/')
def index():
    return send_from_directory('.', 'dashboard.html')

@app.route('/api/latest')
def api_latest():
    """Get latest readings for all sensors"""
    latest = get_latest_readings()
    print(f"[API] /api/latest called, returning {len(latest)} sensors")
    return jsonify(latest)

@app.route('/api/history')
def api_history():
    """Get all historical readings"""
    data = read_csv_data()
    print(f"[API] /api/history called, returning {len(data)} rows")
    return jsonify(data)

@app.route('/api/history/<sensor>')
def api_sensor_history(sensor):
    """Get history for a specific sensor"""
    data = read_csv_data()
    filtered = [row for row in data if row.get('sensor') == sensor]
    return jsonify(filtered)

@app.route('/api/debug')
def api_debug():
    """Debug endpoint - returns diagnostic info"""
    try:
        latest = get_latest_readings()
        csv_data = read_csv_data()
        return jsonify({
            'status': 'OK',
            'csv_file_exists': os.path.exists(CSV_FILE),
            'csv_rows': len(csv_data),
            'sensors_in_api': list(latest.keys()),
            'latest_readings': latest,
            'last_row_sensor1': next((r for r in reversed(csv_data) if r.get('sensor') == 'Sensor 1'), None),
            'last_row_sensor2': next((r for r in reversed(csv_data) if r.get('sensor') == 'Sensor 2'), None),
        })
    except Exception as e:
        return jsonify({
            'status': 'ERROR',
            'error': str(e)
        }), 500


# ===== BACKGROUND SCRAPER =====
def start_background_scraper():
    """Run scraper in background thread"""
    import sys
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from monitor import run_watch_mode, run_single_check
    
    print("\n" + "="*60)
    print("STARTING BACKGROUND SCRAPER")
    print("="*60)
    
    # Run immediate first check to populate CSV
    print("   [*] Running initial scrape...")
    try:
        run_single_check()
        print("   [OK] Initial scrape complete")
    except Exception as e:
        print(f"   [!] Initial scrape failed: {e}")
    
    print("   Scraper will continue every 10 minutes")
    print("="*60 + "\n")
    
    try:
        run_watch_mode(interval=10, duration_minutes=None)
    except Exception as e:
        print(f"ERROR: Scraper error: {e}")
        import traceback
        traceback.print_exc()


def init_scraper():
    """Initialize background scraper thread"""
    scraper_thread = threading.Thread(target=start_background_scraper, daemon=True)
    scraper_thread.start()
    print("[OK] Scraper thread initialized")


if __name__ == '__main__':
    import os
    port = int(os.getenv('PORT', 5000))
    
    print("="*50)
    print("SENSOR DASHBOARD SERVER STARTING")
    print("="*50)
    print(f"   Port: 0.0.0.0:{port}")
    print("="*50)
    
    # Ensure CSV is initialized first
    ensure_csv_initialized()
    
    # Load and verify data from CSV
    initial_data = read_csv_data()
    print(f"   [OK] Loaded {len(initial_data)} historical data rows")
    
    # Start background scraper thread
    init_scraper()
    
    try:
        app.run(debug=False, host='0.0.0.0', port=port, threaded=True)
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
