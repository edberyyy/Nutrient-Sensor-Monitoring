# Launcher script to run both website and scraper in separate terminals
import subprocess
import os
import sys

# Get the directory where this script is located
script_dir = os.path.dirname(os.path.abspath(__file__))
python_exe = sys.executable

print("="*50)
print("🚀 LAUNCHING SENSOR MONITORING SYSTEM")
print("="*50)

# Command to activate venv and run server
server_cmd = f'cd "{script_dir}"; & "{python_exe}" server.py'
scraper_cmd = f'cd "{script_dir}"; & "{python_exe}" monitor.py --watch'

# Open new PowerShell windows for each process
subprocess.Popen([
    'powershell', '-NoExit', '-Command',
    f'$Host.UI.RawUI.WindowTitle = "Dashboard Server"; {server_cmd}'
])

subprocess.Popen([
    'powershell', '-NoExit', '-Command',
    f'$Host.UI.RawUI.WindowTitle = "Web Scraper"; {scraper_cmd}'
])

print("\n✅ Started 2 terminals:")
print("   1. Dashboard Server - http://localhost:5000")
print("   2. Web Scraper - scraping every 10 minutes")
print("\nYou can close this window.")
