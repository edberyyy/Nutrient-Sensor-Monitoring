from playwright.sync_api import sync_playwright, TimeoutError
import time
import json
from datetime import datetime, timedelta
import re
import os
import requests
import csv
import argparse

# Dashboard URLs
DASHBOARDS = {
    "Sensor 1": "https://solisolcap.grafana.net/public-dashboards/5f813ad60cfd4d5495ee33fbac349c34",
    "Sensor 2": "https://solisolcap.grafana.net/public-dashboards/36aa33cfd13c44d5a43422afa6fa1235",
}

DATA_FILE = "last_readings.json"
ALERT_LOG = "alerts.log"
CSV_FILE = "readings_history.csv"
POLL_INTERVAL_MINUTES = 10

TEMP_CRITICAL_LOW = 10.0
TEMP_CRITICAL_HIGH = 38.0


# -------- DASHBOARD SCRAPE --------

def get_dashboard_data(url, name="Dashboard"):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1920, "height": 1080})

        print(f"\n📡 Loading {name}...")
        page.goto(url, timeout=60000)

        try:
            page.wait_for_load_state("networkidle", timeout=45000)
        except TimeoutError:
            page.wait_for_load_state("domcontentloaded", timeout=20000)
            page.wait_for_timeout(3000)

        print("⏳ Waiting for panels to render...")
        time.sleep(10)

        try:
            for _ in range(5):
                page.evaluate("window.scrollBy(0, document.body.scrollHeight)")
                time.sleep(1)
                page.wait_for_load_state("networkidle")
        except:
            pass

        all_text = page.locator("body").inner_text()
        browser.close()
        
        # Check for "No data" indicators
        if "no data" in all_text.lower():
            no_data_count = all_text.lower().count("no data")
            print(f"   ⚠️  WARNING: Found {no_data_count} 'No data' indicator(s) on dashboard")
        
        return all_text


# -------- FIXED PARAMETER EXTRACTION --------

def extract_parameters(page_text):
    results = {
        'Growing Parameters': 'N/A',
        'Temperature': 'N/A',
        'Moisture': 'N/A',
        'Electric Conductivity': 'N/A',
        'Acidity': 'N/A',
        'Nitrogen': 'N/A',
        'Phosphorus': 'N/A',
        'Potassium': 'N/A',
        '_data_quality': 'GOOD'  # Track data quality
    }

    # Check for global "No data" or offline indicators
    if "no data" in page_text.lower() or "field not found" in page_text.lower():
        no_data_indicators = page_text.lower().count("no data") + page_text.lower().count("field not found")
        if no_data_indicators > 3:
            results['_data_quality'] = 'POOR_NO_DATA'
            print(f"   ⚠️  Data quality warning: {no_data_indicators} 'no data'/'field not found' indicators detected")

    if re.search(r'GROWING\s*PARAMETERS', page_text, re.IGNORECASE):
        results['Growing Parameters'] = '✓ Section Found'

    # EC
    ec_patterns = [
        r'(\d{1,5})\s*[µuμ]S/cm',
        r'Electric\s*Conductivity[:\s]*(\d{1,5})',
        r'\bEC\b[:\s]*(\d{1,5})',
    ]

    for p in ec_patterns:
        m = re.search(p, page_text, re.IGNORECASE)
        if m:
            results['Electric Conductivity'] = f"{m.group(1)} µS/cm"
            break

    # Temperature
    temp_patterns = [
        r'(\d+\.?\d*)\s*°C',
        r'\bTemperature\b[:\s]*(\d+\.?\d*)',
    ]

    for p in temp_patterns:
        m = re.search(p, page_text, re.IGNORECASE)
        if m:
            results['Temperature'] = f"{m.group(1)} °C"
            break

    # Moisture
    moisture_patterns = [
        r'\bMoisture\b[:\s]*(\d+\.?\d*)\s*%',
        r'(\d+\.?\d*)\s*%\s*\bMoisture\b',
    ]

    for p in moisture_patterns:
        m = re.search(p, page_text, re.IGNORECASE)
        if m:
            results['Moisture'] = f"{m.group(1)} %"
            break

    # pH with fallback logic
    ph_patterns = [
        r'\bpH\b[:\s]*([0-9]+(?:\.[0-9]{1,2})?)',
        r'([0-9]+(?:\.[0-9]{1,2})?)\s*\bpH\b',
        r'\bAcidity\b[:\s]*([0-9]+(?:\.[0-9]{1,2})?)',
        r'\bACIDITY\b[:\s]*([0-9]+(?:\.[0-9]{1,2})?)',
    ]

    ph_value = None

    for p in ph_patterns:
        m = re.search(p, page_text, re.IGNORECASE)
        if m:
            try:
                v = float(m.group(1))
                if 0 < v <= 14:
                    ph_value = v
                    break
            except:
                pass

    if ph_value is None:
        for tag in ['pH', 'Acidity', 'ACIDITY']:
            for hit in re.finditer(tag, page_text, re.IGNORECASE):
                window = page_text[max(0, hit.start()-40):hit.end()+40]
                num = re.search(r'([0-9]+(?:\.[0-9]{1,2})?)', window)
                if num:
                    try:
                        v = float(num.group(1))
                        if 0 < v <= 14:
                            ph_value = v
                            break
                    except:
                        pass
            if ph_value is not None:
                break

    if ph_value is not None:
        results['Acidity'] = f"{ph_value:.2f} pH"

    # Special handling for Grafana NPK layout: N, K, values, P pattern
    # Look for pattern where N/K/P letters appear near mg/L values
    npk_section = re.search(r'GROWING PARAMETERS.*?(?=TEMPERATURE|$)', page_text, re.DOTALL | re.IGNORECASE)
    if npk_section:
        npk_text = npk_section.group()
        # Extract all mg/L values in order
        mg_values = re.findall(r'(\d+\.?\d*)\s*mg/L', npk_text, re.IGNORECASE)
        
        print(f"   🧪 NPK extraction: Found {len(mg_values)} mg/L values: {mg_values}")
        
        # Grafana layout: N label, K label, [N_val], [K_val], [P_val], P label
        # Map values based on position: 1st=N, 2nd=K, 3rd=P
        if len(mg_values) >= 3:
            results['Nitrogen'] = f"{mg_values[0]} mg/kg"
            results['Potassium'] = f"{mg_values[1]} mg/kg"
            results['Phosphorus'] = f"{mg_values[2]} mg/kg"
            print(f"   ✓ NPK extracted: N={mg_values[0]}, K={mg_values[1]}, P={mg_values[2]}")
        elif len(mg_values) == 2:
            results['Nitrogen'] = f"{mg_values[0]} mg/kg"
            results['Phosphorus'] = f"{mg_values[1]} mg/kg"
            print(f"   ℹ️  Only 2 NPK values found")
        elif len(mg_values) == 1:
            results['Nitrogen'] = f"{mg_values[0]} mg/kg"
            print(f"   ⚠️  Only 1 NPK value found")
        else:
            print(f"   ⚠️  No NPK values found in GROWING PARAMETERS section")

    # Fallback: Nitrogen (N) patterns
    if results['Nitrogen'] == 'N/A':
        n_patterns = [
            r'\bNitrogen\b[:\s]*(\d+\.?\d*)\s*(?:mg/kg|ppm|mg/L)?',
            r'NITROGEN[:\s]*(\d+\.?\d*)',
            r'i_nitrogen.*?(\d+\.?\d*)\s*(?:mg/kg|ppm|mg/L)',
            r'(\d+\.?\d*)\s*(?:mg/kg|ppm|mg/L)?\s*Nitrogen',
        ]
        for p in n_patterns:
            m = re.search(p, page_text, re.IGNORECASE)
            if m:
                try:
                    val = float(m.group(1))
                    if 0 < val < 10000:
                        results['Nitrogen'] = f"{val} mg/kg"
                        break
                except:
                    pass

    # Fallback: search near "i_nitrogen" label
    if results['Nitrogen'] == 'N/A':
        for hit in re.finditer(r'i_nitrogen|Nitrogen|NITROGEN', page_text, re.IGNORECASE):
            window = page_text[max(0, hit.start()-80):hit.end()+80]
            nums = re.findall(r'(\d+\.?\d*)\s*mg/L', window, re.IGNORECASE)
            if nums:
                try:
                    val = float(nums[0])
                    if 0 < val < 10000:
                        results['Nitrogen'] = f"{val} mg/kg"
                        break
                except:
                    pass

    # Fallback: Phosphorus (P) patterns
    if results['Phosphorus'] == 'N/A':
        p_patterns = [
            r'\bPhosphorus\b[:\s]*(\d+\.?\d*)\s*(?:mg/kg|ppm|mg/L)?',
            r'PHOSPHORUS[:\s]*(\d+\.?\d*)',
            r'j_phosphorus.*?(\d+\.?\d*)\s*(?:mg/kg|ppm|mg/L)',
            r'(\d+\.?\d*)\s*(?:mg/kg|ppm|mg/L)?\s*Phosphorus',
        ]
        for p in p_patterns:
            m = re.search(p, page_text, re.IGNORECASE)
            if m:
                try:
                    val = float(m.group(1))
                    if 0 < val < 10000:
                        results['Phosphorus'] = f"{val} mg/kg"
                        break
                except:
                    pass

    # Fallback: search near "j_phosphorus" label
    if results['Phosphorus'] == 'N/A':
        for hit in re.finditer(r'j_phosphorus|Phosphorus|PHOSPHORUS', page_text, re.IGNORECASE):
            window = page_text[max(0, hit.start()-80):hit.end()+80]
            nums = re.findall(r'(\d+\.?\d*)\s*mg/L', window, re.IGNORECASE)
            if nums:
                try:
                    val = float(nums[0])
                    if 0 < val < 10000:
                        results['Phosphorus'] = f"{val} mg/kg"
                        break
                except:
                    pass

    # Fallback: Potassium (K) patterns
    if results['Potassium'] == 'N/A':
        k_patterns = [
            r'\bPotassium\b[:\s]*(\d+\.?\d*)\s*(?:mg/kg|ppm|mg/L)?',
            r'POTASSIUM[:\s]*(\d+\.?\d*)',
            r'k_potassium.*?(\d+\.?\d*)\s*(?:mg/kg|ppm|mg/L)',
            r'(\d+\.?\d*)\s*(?:mg/kg|ppm|mg/L)?\s*Potassium',
        ]
        for p in k_patterns:
            m = re.search(p, page_text, re.IGNORECASE)
            if m:
                try:
                    val = float(m.group(1))
                    if 0 < val < 10000:
                        results['Potassium'] = f"{val} mg/kg"
                        break
                except:
                    pass

    # Fallback: search near "k_potassium" label
    if results['Potassium'] == 'N/A':
        for hit in re.finditer(r'k_potassium|Potassium|POTASSIUM', page_text, re.IGNORECASE):
            window = page_text[max(0, hit.start()-80):hit.end()+80]
            nums = re.findall(r'(\d+\.?\d*)\s*mg/L', window, re.IGNORECASE)
            if nums:
                try:
                    val = float(nums[0])
                    if 0 < val < 10000:
                        results['Potassium'] = f"{val} mg/kg"
                        break
                except:
                    pass

    return results


# -------- METRIC PARSER --------

def _parse_num(s):
    try:
        return float(re.search(r"[-+]?[0-9]*\.?[0-9]+", s).group()) if s else None
    except:
        return None


def build_metrics(results):
    return {
        "temperature_c": _parse_num(results.get("Temperature")),
        "moisture_pct": _parse_num(results.get("Moisture")),
        "ec_us_cm": _parse_num(results.get("Electric Conductivity")),
        "acidity_ph": _parse_num(results.get("Acidity")),
        "nitrogen": _parse_num(results.get("Nitrogen")),
        "phosphorus": _parse_num(results.get("Phosphorus")),
        "potassium": _parse_num(results.get("Potassium")),
    }


# -------- DATA VALIDATION --------

def validate_metrics(metrics, sensor_name):
    """Validate extracted metrics are reasonable"""
    issues = []
    
    temp = metrics.get('temperature_c')
    if temp is not None and (temp < -40 or temp > 60):
        issues.append(f"Temperature {temp}°C seems unrealistic")
    
    moisture = metrics.get('moisture_pct')
    if moisture is not None and (moisture < 0 or moisture > 100):
        issues.append(f"Moisture {moisture}% is out of range")
    
    ec = metrics.get('ec_us_cm')
    if ec is not None and (ec < 0 or ec > 5000):
        issues.append(f"EC {ec} µS/cm seems extreme")
    
    ph = metrics.get('acidity_ph')
    if ph is not None and (ph <= 0 or ph > 14):
        issues.append(f"pH {ph} is out of valid range")
    
    if issues:
        print(f"   ⚠️  Validation warnings for {sensor_name}:")
        for issue in issues:
            print(f"      - {issue}")
        return False
    return True


# -------- CSV SAVE --------

def save_to_csv(sensor_name, metrics):
    file_exists = os.path.isfile(CSV_FILE)
    
    # Validate before saving
    is_valid = validate_metrics(metrics, sensor_name)
    
    with open(CSV_FILE, mode='a', newline='') as f:
        writer = csv.writer(f)
        
        if not file_exists:
            writer.writerow([
                'timestamp_iso', 'sensor', 'temperature_c', 'moisture_pct',
                'ec_us_cm', 'ph', 'nitrogen', 'phosphorus', 'potassium',
                'temperature_status', 'moisture_status',
                'ec_status', 'ph_status', 'overall_status'
            ])
        
        temp = metrics.get('temperature_c')
        moisture = metrics.get('moisture_pct')
        ec = metrics.get('ec_us_cm')
        ph = metrics.get('acidity_ph')
        nitrogen = metrics.get('nitrogen')
        phosphorus = metrics.get('phosphorus')
        potassium = metrics.get('potassium')
        
        # Determine status
        temp_status = 'OK'
        if temp is not None:
            if temp < TEMP_CRITICAL_LOW or temp > TEMP_CRITICAL_HIGH:
                temp_status = 'CRITICAL'
        
        moisture_status = 'OK' if moisture is not None else 'NA'
        ec_status = 'OK' if ec is not None else 'NA'
        ph_status = 'OK' if ph is not None else 'NA'
        
        statuses = [temp_status, moisture_status, ec_status, ph_status]
        overall_status = 'CRITICAL' if 'CRITICAL' in statuses else 'OK'
        
        writer.writerow([
            datetime.now().strftime('%Y-%m-%dT%H:%M:%S'),
            sensor_name,
            temp if temp is not None else 'NA',
            moisture if moisture is not None else 'NA',
            ec if ec is not None else 'NA',
            ph if ph is not None else 'NA',
            nitrogen if nitrogen is not None else 'NA',
            phosphorus if phosphorus is not None else 'NA',
            potassium if potassium is not None else 'NA',
            temp_status,
            moisture_status,
            ec_status,
            ph_status,
            overall_status
        ])
    
    status_badge = '✓' if is_valid else '⚠️'
    print(f"   {status_badge} Saved to {CSV_FILE}")


# -------- TERMINAL DISPLAY --------

def display_terminal(sensor, results, metrics):
    print("\n" + "-"*50)
    print(f"📊 {sensor}")
    print("-"*50)

    # Data quality indicator
    data_quality = results.pop('_data_quality', 'GOOD')
    quality_icon = '✓' if data_quality == 'GOOD' else '⚠️'
    print(f"{quality_icon} Data Quality: {data_quality}")
    print()

    for k, v in results.items():
        print(f"{k:25}: {v}")
    
    # Highlight NPK extraction status with validation
    print("\n🌱 NPK Status:")
    npk_complete = all(results.get(x, 'N/A') != 'N/A' for x in ['Nitrogen', 'Phosphorus', 'Potassium'])
    npk_icon = '✓' if npk_complete else '⚠️'
    print(f"   {npk_icon} Nitrogen (N):   {results.get('Nitrogen', 'N/A')}")
    print(f"   {npk_icon} Phosphorus (P): {results.get('Phosphorus', 'N/A')}")
    print(f"   {npk_icon} Potassium (K):  {results.get('Potassium', 'N/A')}")

    print("\n📈 Parsed numeric values:")
    for k, v in metrics.items():
        check = '✓' if v is not None else '✗'
        print(f"   {check} {k:23}: {v}")

    print("-"*50)


# -------- MAIN --------

def run_single_check():
    print("\n" + "="*60)
    print("GRAFANA MONITOR")
    print("="*60)

    for sensor_name, url in DASHBOARDS.items():
        page_text = get_dashboard_data(url, sensor_name)
        results = extract_parameters(page_text)
        metrics = build_metrics(results)
        display_terminal(sensor_name, results, metrics)
        save_to_csv(sensor_name, metrics)


def run_watch_mode(interval, duration_minutes=None):
    """
    Run scraping at specified interval indefinitely (24/7 mode).
    
    Args:
        interval: Minutes between each scrape
        duration_minutes: Optional - if set, stops after this duration (for testing)
    """
    start_time = time.time()
    end_time = start_time + (duration_minutes * 60) if duration_minutes else None
    run_count = 0
    
    print(f"\n🚀 Starting auto-scrape mode (24/7)")
    print(f"   Interval: every {interval} minutes")
    if duration_minutes:
        stop_at = datetime.now() + timedelta(minutes=duration_minutes)
        print(f"   TEST MODE: Will stop at {stop_at.strftime('%H:%M:%S')}")
    else:
        print(f"   Running indefinitely until process restarts")
    
    while True:
        if end_time and time.time() >= end_time:
            print(f"\n✅ Test duration completed ({run_count} scrape(s)).")
            break
            
        run_count += 1
        print(f"\n⏱️  Run #{run_count} | Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        try:
            run_single_check()
        except Exception as e:
            print(f"❌ Error during scrape: {e}")
            print("   Will retry at next interval...")
        
        print(f"\n💤 Sleeping for {interval} minutes...")
        time.sleep(interval * 60)


if __name__ == "__main__":
    try:
        print("="*60)
        print("MONITOR STARTING UP")
        print("="*60)
        
        parser = argparse.ArgumentParser()
        parser.add_argument("--watch", "-w", action="store_true", help="Run in watch mode (auto-scrape 24/7)")
        parser.add_argument("--interval", "-i", type=int, default=POLL_INTERVAL_MINUTES, help="Minutes between scrapes (default: 10)")
        parser.add_argument("--duration", "-d", type=int, default=None, help="Optional: Total duration in minutes (for testing only)")
        args = parser.parse_args()
        
        print(f"Arguments parsed: watch={args.watch}, interval={args.interval}, duration={args.duration}")

        if args.watch:
            run_watch_mode(args.interval, args.duration)
        else:
            run_single_check()
    except Exception as e:
        print(f"FATAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        raise
