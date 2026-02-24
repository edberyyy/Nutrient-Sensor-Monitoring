"""
Debug script to capture raw page content from Grafana dashboards
This helps identify what data is actually available vs. what's being extracted
"""

from playwright.sync_api import sync_playwright
import time

DASHBOARDS = {
    "Sensor 1": "https://solisolcap.grafana.net/public-dashboards/5f813ad60cfd4d5495ee33fbac349c34",
    "Sensor 2": "https://solisolcap.grafana.net/public-dashboards/36aa33cfd13c44d5a43422afa6fa1235",
}

def capture_dashboard(url, name="Dashboard"):
    """Capture raw page text and save to file"""
    print(f"\n📡 Capturing {name}...")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1920, "height": 1080})
        
        try:
            page.goto(url, timeout=60000)
            print(f"   ✓ Page loaded")
            
            try:
                page.wait_for_load_state("networkidle", timeout=45000)
            except:
                page.wait_for_load_state("domcontentloaded", timeout=20000)
                page.wait_for_timeout(3000)
            
            print(f"   ⏳ Waiting for rendering...")
            time.sleep(10)
            
            try:
                for _ in range(5):
                    page.evaluate("window.scrollBy(0, document.body.scrollHeight)")
                    time.sleep(1)
                    page.wait_for_load_state("networkidle")
            except:
                pass
            
            # Get full page text
            all_text = page.locator("body").inner_text()
            
            # Save to file for inspection
            filename = f"debug_{name.replace(' ', '_').lower()}_raw.txt"
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(all_text)
            
            print(f"   ✓ Saved raw content to {filename}")
            print(f"   📊 Content length: {len(all_text)} characters")
            print(f"\n   📋 Preview (first 1500 chars):")
            print("   " + "-" * 60)
            for line in all_text[:1500].split('\n')[:20]:
                if line.strip():
                    print(f"   {line[:70]}")
            print("   " + "-" * 60)
            
            # Look for specific metrics
            print(f"\n   🔍 Searching for key metrics:")
            
            keywords = ['Temperature', 'Moisture', 'Nitrogen', 'Phosphorus', 'Potassium', 
                       'EC', 'pH', 'Acidity', 'mg/L', 'mg/kg', '%', '°C']
            
            found = {}
            for keyword in keywords:
                if keyword.lower() in all_text.lower():
                    # Find context around keyword
                    idx = all_text.lower().find(keyword.lower())
                    context = all_text[max(0, idx-50):min(len(all_text), idx+100)]
                    found[keyword] = context.replace('\n', ' ')
            
            for kw, context in sorted(found.items()):
                print(f"      ✓ {kw:15} → ...{context}...")
            
            browser.close()
            return all_text
            
        except Exception as e:
            print(f"   ❌ Error: {e}")
            browser.close()
            return None

if __name__ == "__main__":
    print("="*70)
    print("GRAFANA DASHBOARD DEBUG - CAPTURING RAW CONTENT")
    print("="*70)
    
    for sensor_name, url in DASHBOARDS.items():
        capture_dashboard(url, sensor_name)
    
    print("\n" + "="*70)
    print("✅ Debug files created:")
    print("   - debug_sensor_1_raw.txt")
    print("   - debug_sensor_2_raw.txt")
    print("\nReview these files to see exactly what's on the Grafana dashboard")
    print("="*70)
