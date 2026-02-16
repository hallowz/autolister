# Raspberry Pi Setup Guide for AutoLister

Complete step-by-step guide to deploy AutoLister on Raspberry Pi.

## Prerequisites

- Raspberry Pi 4 or newer (recommended for better performance)
- Raspberry Pi OS (64-bit recommended)
- Internet connection
- SSH access (for remote setup)
- At least 16GB SD card (32GB+ recommended)

---

## Step 1: Prepare Raspberry Pi

### 1.1 Update System

```bash
sudo apt update && sudo apt upgrade -y
```

### 1.2 Install Required Packages

```bash
sudo apt install -y git curl docker.io docker-compose python3-pip
```

### 1.3 Enable Docker (if not already enabled)

```bash
sudo usermod -aG docker $USER
newgrp docker
```

### 1.4 Verify Docker Installation

```bash
docker --version
docker-compose --version
```

---

## Step 2: Clone or Transfer Repository

### Option A: Clone from Git (if code is on GitHub)

```bash
cd ~
git clone https://github.com/YOUR_USERNAME/AutoLister.git
cd AutoLister
```

### Option B: Transfer from Windows PC

**On Windows (in PowerShell):**
```powershell
# Compress the AutoLister folder
Compress-Archive -Path "e:\Programs\repos\hallowz\AutoLister" -DestinationPath "AutoLister.zip"
```

**Transfer to Raspberry Pi via SCP:**
```bash
# On Windows, in PowerShell
scp AutoLister.zip pi@192.168.5.8:~/

# On Raspberry Pi
unzip AutoLister.zip
cd AutoLister
```

---

## Step 3: Configure Environment Variables

### 3.1 Copy Example Environment File

```bash
cp .env.example .env
```

### 3.2 Edit Configuration

```bash
nano .env
```

**Minimum required settings:**

```env
# Application
APP_NAME=AutoLister
APP_VERSION=1.0.0
DEBUG=false

# Dashboard
DASHBOARD_HOST=0.0.0.0
DASHBOARD_PORT=8000

# Database
DATABASE_PATH=./data/autolister.db

# Processing
MAX_PDF_SIZE_MB=50
IMAGE_DPI=150
IMAGE_FORMAT=jpeg

# Etsy (required for listing creation)
ETSY_API_KEY=your_api_key_here
ETSY_API_SECRET=your_api_secret_here
ETSY_ACCESS_TOKEN=your_access_token_here
ETSY_ACCESS_TOKEN_SECRET=your_access_token_secret_here
ETSY_SHOP_ID=your_shop_id_here
ETSY_DEFAULT_PRICE=4.99
ETSY_DEFAULT_QUANTITY=9999

# Redis (for Celery)
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

# Scraping (optional - for testing without API keys)
SCRAPING_INTERVAL_HOURS=6
MAX_RESULTS_PER_SEARCH=20
REQUEST_TIMEOUT=30
USER_AGENT=AutoLister/1.0
```

Press `Ctrl+X`, then `Y`, then `Enter` to save and exit.

---

## Step 4: Etsy Account Setup

### 4.1 Create Etsy Shop Name

**Recommended Shop Names for Manual Sales:**

Choose a name that:
- Is clear and descriptive
- Sounds professional
- Indicates what you sell
- Is easy to remember

**Examples:**
- `ManualsHub`
- `EquipmentManuals`
- `ServiceManualsDirect`
- `ManualMaster`
- `TechManuals`
- `EquipmentDocs`
- `RepairManuals`
- `ManualLibrary`
- `ManualsArchive`
- `DigitalManuals`

**Tips:**
- Avoid using brand names (e.g., "HondaManuals") to avoid trademark issues
- Use generic terms like "Manuals", "Guides", "Documentation"
- Keep it short and memorable
- Check if the name is available on Etsy

### 4.2 Get Etsy API Credentials

1. Go to [Etsy Developers](https://www.etsy.com/developers)
2. Click "Create an App"
3. Fill in the form:
   - **App Name**: AutoLister (or your shop name)
   - **App Description**: Automated manual listing tool
   - **App URL**: Your dashboard URL (e.g., `http://your-pi-ip:8000`)
   - **Callback URL**: Same as App URL
4. Choose permissions:
   - `listings_r` - Read listings
   - `listings_w` - Write listings
   - `listings_d` - Delete listings
5. Click "Create App"
6. Copy your **API Key** and **Shared Secret**
7. Generate **Access Token** and **Access Token Secret**

### 4.3 Get Your Shop ID

1. Log into Etsy
2. Go to Your Shop → Settings → Info & Appearance
3. Your Shop ID is displayed in the URL or in settings
4. Copy the numeric Shop ID

### 4.4 Update .env with Etsy Credentials

Add the credentials to your `.env` file:

```env
ETSY_API_KEY=your_actual_api_key
ETSY_API_SECRET=your_actual_api_secret
ETSY_ACCESS_TOKEN=your_actual_access_token
ETSY_ACCESS_TOKEN_SECRET=your_actual_access_token_secret
ETSY_SHOP_ID=123456789
```

---

## Step 5: Build and Start with Docker

### 5.1 Build Docker Images

```bash
cd docker
docker-compose build
```

This may take 10-20 minutes on Raspberry Pi.

### 5.2 Start All Services

```bash
docker-compose up -d
```

### 5.3 Check Service Status

```bash
docker-compose ps
```

You should see 4 services running:
- `autolister` - Main application
- `autolister-redis` - Redis database
- `autolister-celery` - Background worker
- `autolister-beat` - Task scheduler

### 5.4 View Logs

```bash
# View all logs
docker-compose logs -f

# View specific service logs
docker-compose logs -f autolister
```

---

## Step 6: Access the Dashboard

### 6.1 Find Your Raspberry Pi IP

```bash
hostname -I
```

### 6.2 Access Dashboard

Open your web browser and navigate to:
```
http://YOUR_PI_IP:8000/dashboard
```

For example: `http://192.168.5.8:8000/dashboard`

You should see the AutoLister dashboard with statistics.

---

## Step 7: Initial Setup

### 7.1 Initialize Database

The database is automatically created on first run, but you can verify:

```bash
docker exec -it autolister python -c "from app.database import init_db; init_db()"
```

### 7.2 Test API Health Check

```bash
curl http://localhost:8000/health
```

Should return: `{"status":"healthy"}`

---

## Step 8: Configure Scraping (Optional)

### 8.1 Get Google Custom Search API Key

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project
3. Enable "Custom Search API"
4. Create credentials → API Key
5. Go to [Google Custom Search](https://programmablesearchengine.google.com/)
6. Create a Custom Search Engine
7. Copy the **CX ID**

### 8.2 Get Bing Search API Key (Optional)

1. Go to [Azure Portal](https://portal.azure.com/)
2. Create a "Bing Search" resource
3. Get your API key

### 8.3 Update .env with Search API Keys

```env
GOOGLE_API_KEY=your_google_api_key
GOOGLE_CX=your_google_cx_id
BING_API_KEY=your_bing_api_key
```

---

## Step 9: Start Scraping

### 9.1 Manual Scraping Test

You can trigger a scraping job manually:

```bash
docker exec -it autolister python -c "from app.tasks import run_scraping_job; run_scraping_job()"
```

### 9.2 Automatic Scraping

The Celery beat scheduler will automatically run scraping jobs based on the interval set in `.env` (default: every 6 hours).

---

## Step 10: Monitor and Manage

### 10.1 Access Dashboard

Use the web dashboard to:
- Approve/reject pending manuals
- Download PDFs
- Process manuals
- Create Etsy listings
- Monitor statistics

### 10.2 View Logs

```bash
docker-compose logs -f autolister
```

### 10.3 Restart Services

```bash
docker-compose restart
```

### 10.4 Stop Services

```bash
docker-compose down
```

---

## Troubleshooting

### Issue: Docker build fails

**Solution**: Ensure you have enough disk space and swap:

```bash
# Check disk space
df -h

# Add swap if needed (2GB)
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

### Issue: Services won't start

**Solution**: Check logs for errors:

```bash
docker-compose logs autolister
```

### Issue: Can't access dashboard

**Solution**: Check if firewall is blocking port 8000:

```bash
sudo ufw allow 8000
```

### Issue: Out of memory errors

**Solution**: Reduce Docker memory usage or add more swap:

```bash
# Check memory
free -h
```

### Issue: Etsy API errors

**Solution**: Verify your credentials are correct and your shop is active:

1. Check API keys in `.env`
2. Verify shop is not suspended
3. Check Etsy API status page

---

## Performance Optimization

### For Raspberry Pi 4 (4GB+ RAM)

The default configuration should work well.

### For Raspberry Pi 4 (2GB RAM) or Pi 3

Consider these optimizations:

1. **Reduce image processing DPI** in `.env`:
```env
IMAGE_DPI=100
```

2. **Limit concurrent tasks** in Celery:
```bash
# Edit docker-compose.yml
command: celery -A app.tasks worker --concurrency=1 --loglevel=info
```

3. **Use lighter base image**:
```dockerfile
FROM python:3.11-slim
```

---

## Security Recommendations

1. **Change default port** if exposing to internet:
```env
DASHBOARD_PORT=8443
```

2. **Use HTTPS** with reverse proxy (nginx)
3. **Restrict access** to dashboard via firewall
4. **Keep API keys secure** - never commit to git
5. **Regular updates**:
```bash
cd ~/AutoLister
git pull
cd docker
docker-compose build
docker-compose up -d
```

---

## Backup and Restore

### Backup Data

```bash
# Backup database and files
tar -czf autolister-backup-$(date +%Y%m%d).tar.gz data/
```

### Restore Data

```bash
tar -xzf autolister-backup-YYYYMMDD.tar.gz
```

---

## Next Steps

1. Test the scraping functionality
2. Approve some manuals
3. Process PDFs
4. Create test listings on Etsy
5. Monitor performance and adjust settings as needed

---

## Support

For issues or questions:
- Check logs: `docker-compose logs`
- Review documentation: `README.md`
- Check architecture: `plans/architecture.md`
