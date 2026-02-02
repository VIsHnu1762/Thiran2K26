# 🚀 BillAgent Pro - Complete Setup Guide

This guide walks you through setting up BillAgent Pro from scratch for both development and deployment.

---

## 📋 Table of Contents

1. [Prerequisites](#prerequisites)
2. [Local Development Setup](#local-development-setup)
3. [Project Cleanup](#project-cleanup)
4. [GitHub Upload](#github-upload)
5. [Deployment](#deployment)
6. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### System Requirements

**Minimum:**
- RAM: 4GB
- Storage: 2GB
- OS: Windows/Mac/Linux

**Recommended:**
- RAM: 8GB+
- Storage: 5GB+
- GPU: NVIDIA (for faster OCR)

### Required Software

1. **Node.js** (v18 or higher)
   - Download: https://nodejs.org
   - Verify: `node --version` & `npm --version`

2. **Python** (v3.10 or higher)
   - Download: https://www.python.org
   - Verify: `python --version`

3. **Git** (for version control)
   - Download: https://git-scm.com
   - Verify: `git --version`

---

## Local Development Setup

### Step 1: Clone Repository

```bash
git clone https://github.com/yourusername/billagent-pro.git
cd billagent-pro
```

### Step 2: Python Virtual Environment

```bash
# Create virtual environment
python -m venv venv

# Activate it
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate
```

**Verify activation:** You should see `(venv)` in your terminal prompt.

### Step 3: Install Backend Dependencies

```bash
pip install -r backend/requirements.txt
```

**First run only:** EasyOCR will download ~500MB of models.

### Step 4: Install Frontend Dependencies

```bash
npm install
```

### Step 5: Start Backend (Terminal 1)

```bash
python -m uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

**Expected output:**
```
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     Application startup complete
```

### Step 6: Start Frontend (Terminal 2)

```bash
npm run dev
```

**Expected output:**
```
VITE v6.x.x ready in xxx ms
➜  Local:   http://localhost:3000/
```

### Step 7: Access Application

Open browser: **http://localhost:3000**

---

## Project Cleanup

Before uploading to GitHub, clean up these files:

### Remove Large Directories

```bash
# Windows PowerShell
Remove-Item -Recurse -Force node_modules
Remove-Item -Recurse -Force venv
Remove-Item -Recurse -Force dist
Remove-Item -Recurse -Force __pycache__

# macOS/Linux
rm -rf node_modules venv dist
find . -type d -name __pycache__ -exec rm -r {} +
```

### Remove Environment Files

```bash
# Windows
del .env.local
del .env.*.local

# macOS/Linux
rm .env.local .env.*.local
```

### Remove Cache & Build Files

```bash
# Clear npm cache
npm cache clean --force

# Remove pip cache
pip cache purge

# Remove Python cache
find . -name "*.pyc" -delete
find . -name "*.pyo" -delete
```

### Verify Cleanup

Your project should only have:
- ✅ Source code files
- ✅ Configuration files (package.json, tsconfig.json, etc)
- ✅ README.md
- ✅ .gitignore
- ✅ backend/ folder (no __pycache__)
- ✅ components/ folder
- ✅ services/ folder

Size should be < 50MB

---

## GitHub Upload

### Step 1: Initialize Git (if not cloned)

```bash
git init
git add .
git commit -m "Initial commit: BillAgent Pro"
```

### Step 2: Create GitHub Repository

1. Go to https://github.com/new
2. Name: `billagent-pro`
3. Description: "AI-powered bill digitization system"
4. Public/Private: Your choice
5. Click "Create repository"

### Step 3: Push to GitHub

```bash
git remote add origin https://github.com/yourusername/billagent-pro.git
git branch -M main
git push -u origin main
```

### Step 4: Verify Upload

Visit your repository URL:
```
https://github.com/yourusername/billagent-pro
```

Check that:
- ✅ README.md displays properly
- ✅ All source code visible
- ✅ node_modules NOT included
- ✅ venv NOT included
- ✅ .env.local NOT included

---

## Deployment

### Option 1: AWS EC2 (Recommended)

**Advantages:** Affordable, full control, scalable

#### Setup

```bash
# SSH into EC2 instance
ssh -i key.pem ubuntu@your-instance-ip

# Install dependencies
sudo apt update && sudo apt upgrade -y
sudo apt install python3.11 python3-pip nodejs npm git -y

# Clone repo
git clone https://github.com/yourusername/billagent-pro.git
cd billagent-pro

# Setup
python3 -m venv venv
source venv/bin/activate
pip install -r backend/requirements.txt
npm install && npm run build

# Start with PM2 (keeps app running)
sudo npm install -g pm2
pm2 start "python -m uvicorn backend.main:app --bind 0.0.0.0:8000"
pm2 start "npm run dev"
pm2 save
pm2 startup
```

**Security:**
- Use security groups to allow ports 3000, 8000
- Enable HTTPS with SSL certificate
- Use environment variables for secrets

### Option 2: Heroku

**Advantages:** Easiest deployment, no server management

#### Setup

```bash
# Install Heroku CLI
# https://devcenter.heroku.com/articles/heroku-cli

# Login
heroku login

# Create app
heroku create billagent-pro

# Add buildpacks
heroku buildpacks:add heroku/python
heroku buildpacks:add heroku/nodejs

# Set config variables
heroku config:set FLASK_ENV=production

# Deploy
git push heroku main

# Open app
heroku open
```

### Option 3: Docker

**Advantages:** Consistent environment, easy scaling

#### Dockerfile

```dockerfile
FROM node:18-alpine AS frontend-build
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM python:3.11-slim
WORKDIR /app

# Install Node for any runtime needs
RUN apt-get update && apt-get install -y nodejs npm && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend ./backend
COPY --from=frontend-build /app/dist ./frontend

EXPOSE 8000 3000

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

#### Build & Run

```bash
docker build -t billagent-pro .
docker run -p 3000:3000 -p 8000:8000 billagent-pro
```

### Option 4: Google Cloud Run

**Advantages:** Serverless, pay-per-use

```bash
gcloud run deploy billagent-pro \
  --source . \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated
```

---

## Troubleshooting

### Port Already in Use

```bash
# Find process using port 8000
# Windows:
netstat -ano | findstr :8000

# macOS/Linux:
lsof -i :8000

# Kill process
# Windows:
taskkill /PID <PID> /F
# macOS/Linux:
kill -9 <PID>
```

### EasyOCR Models Download Failed

```bash
# Models cache location
# Windows: C:\Users\<username>\.EasyOCR
# macOS: ~/.EasyOCR
# Linux: ~/.EasyOCR

# Delete and retry
rm -rf ~/.EasyOCR
```

### CORS Error

Ensure `.env.local` has:
```env
VITE_BACKEND_URL=http://localhost:8000
```

### Module Not Found

```bash
# Frontend
npm install --legacy-peer-deps

# Backend
pip install --force-reinstall -r backend/requirements.txt
```

---

## Performance Optimization

### Frontend

```bash
# Enable Gzip compression
npm install compression

# Build with minification
npm run build

# Check bundle size
npm install --save-dev webpack-bundle-analyzer
```

### Backend

```bash
# Use Gunicorn for production
pip install gunicorn
gunicorn -w 4 backend.main:app

# Enable caching
pip install aioredis
```

---

## Security Checklist

- [ ] Remove all API keys from code
- [ ] Use environment variables for secrets
- [ ] Enable HTTPS
- [ ] Add rate limiting
- [ ] Implement JWT authentication
- [ ] Validate all inputs
- [ ] Use secure headers (CSP, HSTS)
- [ ] Regular security updates
- [ ] Database encryption
- [ ] Backup strategy

---

## Monitoring & Logging

### Frontend Errors

```typescript
// Add error tracking (e.g., Sentry)
import * as Sentry from "@sentry/react";

Sentry.init({
  dsn: "your-dsn-here",
  environment: "production",
});
```

### Backend Logs

```python
import logging

logger = logging.getLogger(__name__)
logger.info("Bill analyzed successfully")
logger.error("OCR failed", exc_info=True)
```

---

## Maintenance

### Regular Updates

```bash
# Frontend
npm update
npm audit fix

# Backend
pip list --outdated
pip install --upgrade [package_name]
```

### Database Backup

```bash
# If using PostgreSQL
pg_dump database_name > backup.sql
```

---

## Support Resources

- **Documentation:** See main README.md
- **Issues:** GitHub Issues
- **Community:** GitHub Discussions
- **Email:** support@yourdomain.com

---

**Last Updated:** February 2026
