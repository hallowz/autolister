# Deploy AutoLister to Raspberry Pi

This guide will help you deploy AutoLister to your Raspberry Pi (192.168.5.8).

## Prerequisites

1. **SSH Access** - You need SSH access to your Raspberry Pi
2. **GitHub Account** - You'll need a GitHub account to host the repository
3. **Raspberry Pi Requirements**:
   - Docker and Docker Compose installed
   - Internet connection

## Step 1: Initialize Git Repository

Open Command Prompt or PowerShell in the AutoLister directory and run:

```cmd
git init
git add .
git commit -m "Initial commit - AutoLister application"
```

## Step 2: Create GitHub Repository

1. Go to https://github.com/new
2. Repository name: `autolister`
3. Make it Public or Private (your choice)
4. Click "Create repository"

## Step 3: Push to GitHub

Replace `YOUR_USERNAME` with your GitHub username:

```cmd
git remote add origin https://github.com/YOUR_USERNAME/autolister.git
git branch -M main
git push -u origin main
```

## Step 4: Test SSH Connection

```cmd
ssh lane@192.168.5.8 "echo 'Connection successful'"
```

If this fails, check:
- Raspberry Pi is powered on
- SSH is enabled on Raspberry Pi
- Username and password are correct

## Step 5: Prepare Raspberry Pi

SSH into your Raspberry Pi and install Docker:

```bash
ssh lane@192.168.5.8
sudo apt-get update
sudo apt-get install -y git docker.io docker-compose
sudo usermod -aG docker $USER
```

## Step 6: Clone Repository on Raspberry Pi

```bash
cd ~
git clone https://github.com/YOUR_USERNAME/autolister.git
cd autolister
```

## Step 7: Create Configuration File

```bash
cp .env.example .env
nano .env
```

Edit the `.env` file with your API keys:
- Google Custom Search API key and CX
- Bing Search API key
- Etsy API credentials

Save with `Ctrl+O`, then `Ctrl+X`.

## Step 8: Start Docker Containers

```bash
cd docker
docker-compose up -d
```

## Step 9: Check Service Status

```bash
docker-compose ps
```

You should see:
- `autolister` (running)
- `autolister-redis` (running)
- `autolister-celery` (running)
- `autolister-beat` (running)

## Step 10: Access the Dashboard

Open your browser and go to:
```
http://192.168.5.8:8000/dashboard
```

## Useful Commands

### View Logs
```bash
cd ~/autolister/docker
docker-compose logs -f autolister
```

### Stop Services
```bash
cd ~/autolister/docker
docker-compose down
```

### Restart Services
```bash
cd ~/autolister/docker
docker-compose restart
```

### Update Application
```bash
cd ~/autolister
git pull
cd docker
docker-compose down
docker-compose up -d --build
```

### View Database
```bash
sqlite3 ~/autolister/data/autolister.db
```

## Troubleshooting

### Container won't start
```bash
docker-compose logs autolister
```

### Port already in use
Edit `.env` on Raspberry Pi:
```env
DASHBOARD_PORT=8001
```

### Database errors
```bash
rm ~/autolister/data/autolister.db
```

The database will be recreated on next start.

## Next Steps

1. Configure your API keys in the `.env` file
2. Access the dashboard at http://192.168.5.8:8000/dashboard
3. Test the scraping functionality
4. Process some manuals and create test listings
