# AutoLister Deployment Guide

This guide explains how to deploy and update AutoLister on your Raspberry Pi using the provided deployment scripts.

## Initial Setup (One-Time)

To avoid entering your password multiple times during deployments, set up SSH key authentication:

### Windows (PowerShell)

```powershell
.\deploy_and_update_pi.ps1 -RaspberryPiIP <YOUR_PI_IP> -SetupKeys
```

### Linux/Mac (Bash)

```bash
./deploy_and_update_pi.sh <YOUR_PI_IP> --setup-keys
```

You will be prompted for your password **ONE TIME ONLY**. After this, all future deployments will be passwordless.

## Deployment Options

### Full Deployment (Recommended for Code Changes)

Pulls latest code, rebuilds Docker images, regenerates database, and restarts services.

**Windows:**
```powershell
.\deploy_and_update_pi.ps1 -RaspberryPiIP <YOUR_PI_IP>
```

**Linux/Mac:**
```bash
./deploy_and_update_pi.sh <YOUR_PI_IP>
```

### Quick Restart (For Configuration Changes Only)

Restarts the Docker container without rebuilding. Use this when you've made changes that don't require a rebuild (like config file updates).

**Windows:**
```powershell
.\deploy_and_update_pi.ps1 -RaspberryPiIP <YOUR_PI_IP> -QuickRestart
```

**Linux/Mac:**
```bash
./deploy_and_update_pi.sh <YOUR_PI_IP> --quick
```

## What the Scripts Do

### Full Deployment Steps:
1. **Pull latest changes** - `git pull origin main`
2. **Stop containers** - `docker-compose down`
3. **Rebuild images** - `docker-compose build`
4. **Regenerate database** - Creates fresh database schema
5. **Start services** - `docker-compose up -d`
6. **Check status** - `docker-compose ps`

### Quick Restart Steps:
1. **Restart autolister container** - `docker-compose restart autolister`
2. **Check status** - `docker-compose ps`

## Troubleshooting

### SSH Connection Failed

If you see "SSH connection failed":
1. Verify your Raspberry Pi is powered on and connected to your network
2. Check the IP address is correct
3. Ensure SSH is enabled on the Raspberry Pi (`sudo raspi-config` → Interface Options → SSH)
4. Verify the username is correct (default: `lane`)

### Password Still Required

If you're still being prompted for a password after setting up SSH keys:
1. Verify SSH keys were created: Check `~/.ssh/id_ed25519` exists
2. Try running the setup command again: `--setup-keys`
3. Manually test: `ssh lane@<YOUR_PI_IP>`

### Docker Build Failed

If the Docker build fails:
1. Check for syntax errors in your code
2. Ensure all dependencies are in `requirements.txt`
3. Check Docker has enough disk space: `docker system df`

### Database Issues

If you encounter database issues:
1. The full deployment automatically regenerates the database
2. To manually regenerate: Connect to the Pi and run:
   ```bash
   cd ~/autolister/docker
   docker-compose run --rm autolister python -c 'from app.database import regenerate_db; regenerate_db()'
   ```

## Manual Deployment (If Scripts Fail)

If the automated scripts don't work, you can deploy manually:

```bash
# Connect to your Raspberry Pi
ssh lane@<YOUR_PI_IP>

# Navigate to project
cd ~/autolister

# Pull latest code
git pull origin main

# Stop containers
cd docker
docker-compose down

# Rebuild
docker-compose build

# Regenerate database
docker-compose run --rm autolister python -c 'from app.database import regenerate_db; regenerate_db()'

# Start services
docker-compose up -d

# Check status
docker-compose ps
```

## Accessing the Application

After successful deployment:
- **Dashboard**: http://<YOUR_PI_IP>:8000/dashboard
- **Scrape Queue**: http://<YOUR_PI_IP>:8000/scrape-queue
- **Health Check**: http://<YOUR_PI_IP>:8000/health
- **API Docs**: http://<YOUR_PI_IP>:8000/docs

## Environment Variables

The application uses environment variables from the `.env` file. Make sure this file exists in the project root on your Raspberry Pi with your configuration:

```env
# Etsy API Credentials
ETSY_API_KEY=your_api_key
ETSY_SHARED_SECRET=your_shared_secret
ETSY_ACCESS_TOKEN=your_access_token
ETSY_ACCESS_TOKEN_SECRET=your_token_secret

# Groq API (for AI features)
GROQ_API_KEY=your_groq_api_key

# Database
DATABASE_URL=sqlite:///./data/autolister.db

# Other settings...
```

## Logs

To view application logs:

```bash
# Connect to Pi
ssh lane@<YOUR_PI_IP>

# View container logs
cd ~/autolister/docker
docker-compose logs -f autolister

# View all services
docker-compose logs -f
```
