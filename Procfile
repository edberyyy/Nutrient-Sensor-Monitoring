web: gunicorn -w 1 -b 0.0.0.0 --timeout 120 server:app
worker: python monitor.py --watch
