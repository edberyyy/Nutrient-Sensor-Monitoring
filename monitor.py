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
        'Potassium': 'N/A'
    }

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
        
        # Grafana layout: N, K, [N_val], [K_val], [P_val], P
        # Map values based on position and labels
        if len(mg_values) >= 3:
            # First value after N/K is typically N
            results['Nitrogen'] = f"{mg_values[0]} mg/kg"
            # Third value (before P label) is typically P
            results['Phosphorus'] = f"{mg_values[2]} mg/kg"
            # Second value is typically K
            results['Potassium'] = f"{mg_values[1]} mg/kg"
        elif len(mg_values) == 2:
            results['Nitrogen'] = f"{mg_values[0]} mg/kg"
            results['Phosphorus'] = f"{mg_values[1]} mg/kg"
        elif len(mg_values) == 1:
            results['Nitrogen'] = f"{mg_values[0]} mg/kg"

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


# -------- CSV SAVE --------

def save_to_csv(sensor_name, metrics):
    file_exists = os.path.isfile(CSV_FILE)
    
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
    
    print(f"💾 Saved to {CSV_FILE}")


# -------- TERMINAL DISPLAY --------

def display_terminal(sensor, results, metrics):
    print("\n" + "-"*40)
    print(f"📊 {sensor}")
    print("-"*40)

    for k, v in results.items():
        print(f"{k:25}: {v}")
    
    # Highlight NPK extraction status
    print("\n🌱 NPK Status:")
    print(f"   Nitrogen (N):   {results.get('Nitrogen', 'N/A')}")
    print(f"   Phosphorus (P): {results.get('Phosphorus', 'N/A')}")
    print(f"   Potassium (K):  {results.get('Potassium', 'N/A')}")

    print("\nParsed numeric values:")
    for k, v in metrics.items():
        print(f"{k:25}: {v}")

    print("-"*40)


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


def run_watch_mode(interval, duration_minutes=60):
    """
    Run scraping at specified interval and stop after duration.
    
    Args:
        interval: Minutes between each scrape
        duration_minutes: Total runtime in minutes (default: 60 = 1 hour)
    """
    start_time = time.time()
    end_time = start_time + (duration_minutes * 60)
    run_count = 0
    stop_at = datetime.now() + timedelta(minutes=duration_minutes)
    
    print(f"\n🚀 Starting auto-scrape mode")
    print(f"   Interval: every {interval} minutes")
    print(f"   Duration: {duration_minutes} minutes (will stop at {stop_at.strftime('%H:%M:%S')})")
    
    while time.time() < end_time:
        run_count += 1
        remaining = (end_time - time.time()) / 60
        print(f"\n⏱️  Run #{run_count} | Time remaining: {remaining:.1f} minutes")
        
        run_single_check()
        
        # Check if there's enough time for another run
        if time.time() + (interval * 60) >= end_time:
            print(f"\n✅ Completed {run_count} scrape(s). Duration limit reached.")
            break
            
        print(f"\n💤 Sleeping for {interval} minutes...")
        time.sleep(interval * 60)
    
    print(f"\n🏁 Auto-scrape finished! Total runs: {run_count}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--watch", "-w", action="store_true", help="Run in watch mode (auto-scrape)")
    parser.add_argument("--interval", "-i", type=int, default=POLL_INTERVAL_MINUTES, help="Minutes between scrapes")
    parser.add_argument("--duration", "-d", type=int, default=60, help="Total duration in minutes (default: 60)")
    args = parser.parse_args()

    if args.watch:
        run_watch_mode(args.interval, args.duration)
    else:
        run_single_check()
