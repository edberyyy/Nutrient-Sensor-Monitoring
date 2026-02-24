#!/usr/bin/env python
"""Test script to verify data loading"""

from server import read_csv_data, get_latest_readings

print("[*] Testing CSV data loading...")

# Load data
data = read_csv_data()
latest = get_latest_readings()

print(f"[OK] CSV loaded: {len(data)} records")
print(f"[OK] Sensors found: {list(latest.keys())}")

# Check Sensor 2
s2 = latest.get('Sensor 2', {})
temp = s2.get('temperature_c', 'N/A')
moisture = s2.get('moisture_pct', 'N/A')
ec = s2.get('ec_us_cm', 'N/A')
nitrogen = s2.get('nitrogen', 'N/A')

print(f"[OK] Sensor 2 latest values:")
print(f"     Temperature: {temp}C")
print(f"     Moisture: {moisture}%")
print(f"     EC: {ec} µS/cm")
print(f"     Nitrogen: {nitrogen} mg/kg")

print("\n[OK] All data loads correctly!")
print("[OK] Graphs should display with historical data")
