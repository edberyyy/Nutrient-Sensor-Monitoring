# Railway Deployment Guide

## Steps to Deploy to Railway (24/7 Free):

1. **Create GitHub Account** (if you don't have one)
   - Go to https://github.com and sign up

2. **Push Your Code to GitHub**:
   ```powershell
   cd "C:\Users\Edber John\Programming\Web Scrap"
   git init
   git add .
   git commit -m "Initial commit"
   git remote add origin https://github.com/YOUR_USERNAME/web-scrap.git
   git branch -M main
   git push -u origin main
   ```

3. **Deploy to Railway**:
   - Go to https://railway.app
   - Sign up with GitHub
   - Click "New Project" → "Deploy from GitHub"
   - Select your `web-scrap` repository
   - Railway auto-deploys! ✅

4. **Access Your Dashboard**:
   - Railway gives you a free URL like: `https://web-scrap-production.up.railway.app`
   - Your dashboard is live 24/7!

5. **Monitor & View Logs**:
   - All logs visible in Railway dashboard
   - Automatic restarts if crashes

## What Gets Deployed:
- **server.py** - Flask dashboard (web process)
- **monitor.py** - Data scraper (worker process)
- **Procfile** - Tells Railway how to run both

## Cost:
- **FREE forever** with Railway's free tier
- Unlimited projects
- 24/7 uptime

Your data collection runs continuously in the cloud! 🚀
