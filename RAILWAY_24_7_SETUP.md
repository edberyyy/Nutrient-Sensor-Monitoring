# 🚀 24/7 Railway Deployment Guide

## What Your System Does

Your **Sensor Monitoring System** will run continuously in the cloud:

- **Dashboard Server** - Serves your interactive web dashboard publicly  
- **Web Scraper** - Continuously scrapes Grafana dashboards every 10 minutes  
- **Data Storage** - CSV files grow with readings (persisted automatically)  

---

## 📋 Prerequisites

✅ GitHub account (free at github.com)  
✅ Railway account (free at railway.app)  
✅ Your code ready to push

---

## 🎯 Step-by-Step Deployment

### Step 1: Push Code to GitHub

Open PowerShell and run:

```powershell
cd "C:\Users\Edber John\Programming\Web Scrap"
git add .
git commit -m "Sensor monitoring system - 24/7 deployment ready"
git push origin main
```

*(Your code should already be on GitHub from recent commits)*

### Step 2: Create Railway Account

1. Go to **https://railway.app**
2. Click **"Sign Up with GitHub"**
3. Authorize Railway to access your GitHub account
4. You're logged in!

### Step 3: Deploy Your App

1. In Railway dashboard, click **"New Project"**
2. Select **"Deploy from GitHub repo"**
3. Search for **`web-scrap`** repository
4. Click **"Deploy"**

Railway automatically:
- ✅ Reads your `Procfile` (tells it how to run)
- ✅ Installs Python packages from `requirements.txt`
- ✅ Starts both processes simultaneously
- ✅ Assigns a public URL to your dashboard

### Step 4: Get Your Live URL

After deployment completes (2-3 minutes):
1. Click on your project
2. In the **"Deployments"** tab, find your URL
3. Example: `https://web-scrap-production.up.railway.app`
4. **This is your live dashboard!** 🎉

---

## 🔄 How Your System Runs 24/7

Your **Procfile** contains two processes:

```procfile
web: python server.py          # Flask dashboard
worker: python monitor.py --watch  # Scraper (infinite loop)
```

### Web Process
- Runs Python Flask server
- Serves dashboard on the assigned port
- Handles 3 API endpoints:
  - `/api/latest` - Get most recent readings
  - `/api/history` - Get all data
  - `/api/history/<sensor>` - Get specific sensor data

### Worker Process  
- Runs in an infinite loop
- Every 10 minutes: scrapes both Grafana dashboards
- Extracts: Temperature, Moisture, EC, pH, Nitrogen, Phosphorus, Potassium
- Saves data to `readings_history.csv`
- Stores latest values in `last_readings.json`

**Both run simultaneously and continuously!**

---

## 📊 Data Persistence

Your CSV file is stored in Railway's **persistent volume**:
- Survives app restarts
- Grows continuously with new readings
- Can export anytime from Railway dashboard

---

## 🔍 Monitor Your App

### View Real-Time Logs
1. Go to Railway dashboard → Your project
2. Click **"Logs"** tab
3. See live output from both processes

### What You'll See
```
🌐 SENSOR DASHBOARD SERVER        ← server.py started
⏱️  Run #1 | Time: 2026-02-20 14:05:00   ← scraper running
📡 Loading Sensor 1...
📡 Loading Sensor 2...
💾 Saved to readings_history.csv   ← data saved
💤 Sleeping for 10 minutes...      ← waiting for next cycle
```

### Check System Status
- **Green dot** = ✅ All healthy
- **Yellow** = ⏳ Starting/restarting  
- **Red** = ❌ Error (check logs)

---

## 🛠️ Troubleshooting

### Problem: Deployment Failed
**Check:**
- All files pushed to GitHub (`git status` should show clean)
- `Procfile` exists and is correct
- No syntax errors in Python files
- `requirements.txt` has correct package names

**Fix:**
```powershell
git add .
git commit -m "Fix deployment"
git push origin main
```

### Problem: Scraper Not Running (Worker)
**Check:**
- Railway logs show: `python monitor.py --watch`
- No "ModuleNotFoundError" messages
- Grafana URLs are still accessible

**Restart:**
- Click restart button in Railway dashboard

### Problem: Dashboard Shows "Cannot GET /"
**Cause:** Dockerfile or deployment config issue

**Solution:**
- Check that `dashboard.html` exists in repository
- Make sure no `.gitignore` excludes critical files

---

## 🎮 Common Tasks

### Change Scrape Interval (default: 10 minutes)

Edit `Procfile`:
```
worker: python monitor.py --watch --interval 20
```

Then:
```powershell
git add Procfile
git commit -m "Change scrape interval to 20 minutes"
git push origin main
```

Railroad auto-redeploys with new interval.

### View Historical Data

1. Visit your dashboard: `https://your-railway-url.com`
2. Click on sensor names to see history
3. Download CSV for analysis

### Manually Trigger Scrape (Testing)

Log into Railway terminal and run:
```bash
python monitor.py
```

This runs one scrape immediately (useful for testing new code).

---

## 💡 Free Tier Details

### What's Included
- **500 hours/month** per project (more than enough for 24/7)
- **100 GB** storage (your data is only a few MB)
- **Unlimited** dashboard requests
- **Automatic SSL** (HTTPS enabled)
- **Auto-restart** on crashes

### Cost: **$0/month** ✅

---

## 📈 Future Improvements

Once running:

1. **Add Email Alerts** - Alert you if temperature goes critical
2. **Database** - Store in PostgreSQL instead of CSV
3. **Webhook** - Send data to external service
4. **Custom Domain** - Use your own domain name

All configurable in Railway without code changes!

---

## ✅ Quick Deployment Checklist

- [ ] Code pushed to GitHub main branch
- [ ] Railway account created
- [ ] Project deployed from GitHub
- [ ] Deployment shows green/healthy status
- [ ] Can see logs in Railway
- [ ] Dashboard URL is accessible
- [ ] CSV file created with first readings

**Once all checked: Your system runs 24/7 automatically!** 🎉

---

## 🆘 Need Help?

- **Railway Docs**: https://docs.railway.app
- **Your GitHub Repo**: Check file structure
- **Grafana Dashboards**: Verify they're still public
- **Community**: Railway Discord at https://railway.app/community

Your system is ready to monitor sensors 24/7! 🌿📊
