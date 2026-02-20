from flask import Flask, jsonify, send_from_directory
import csv
from datetime import datetime
import os

app = Flask(__name__, static_folder='.')

CSV_FILE = "readings_history.csv"

def read_csv_data():
    """Read all data from CSV file"""
    data = []
    if os.path.exists(CSV_FILE):
        with open(CSV_FILE, 'r', newline='') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Ensure NPK fields exist (for backward compatibility)
                row.setdefault('nitrogen', 'NA')
                row.setdefault('phosphorus', 'NA')
                row.setdefault('potassium', 'NA')
                data.append(row)
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
    return jsonify(get_latest_readings())

@app.route('/api/history')
def api_history():
    """Get all historical readings"""
    return jsonify(read_csv_data())

@app.route('/api/history/<sensor>')
def api_sensor_history(sensor):
    """Get history for a specific sensor"""
    data = read_csv_data()
    filtered = [row for row in data if row.get('sensor') == sensor]
    return jsonify(filtered)

if __name__ == '__main__':
    import os
    port = int(os.getenv('PORT', 5000))
    
    print("="*50)
    print("🌐 SENSOR DASHBOARD SERVER")
    print("="*50)
    print(f"   Server running on 0.0.0.0:{port}")
    print("="*50)
    
    try:
        app.run(debug=False, host='0.0.0.0', port=port, threaded=True)
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
