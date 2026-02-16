# Windows Setup Guide for AutoLister

This guide will help you set up and run AutoLister on Windows.

## Prerequisites

1. **Install Python 3.11 or higher**
   - Download from: https://www.python.org/downloads/
   - During installation, **check "Add Python to PATH"**
   - Verify installation by opening Command Prompt and running: `python --version`

2. **Install Redis (for Celery background tasks)**
   - Download from: https://github.com/microsoftarchive/redis/releases
   - Or use Windows Subsystem for Linux (WSL) with Redis
   - For testing, you can skip Redis and run without Celery

## Quick Start (Without Redis/Celery)

This is the simplest way to run the app for testing.

### Step 1: Create Virtual Environment

Open Command Prompt in the AutoLister directory and run:

```cmd
python -m venv venv
```

### Step 2: Activate Virtual Environment

```cmd
venv\Scripts\activate
```

You should see `(venv)` in your command prompt.

### Step 3: Install Dependencies

```cmd
pip install -r requirements.txt
```

### Step 4: Create Configuration File

```cmd
copy .env.example .env
```

Edit `.env` with a text editor (Notepad, VS Code, etc.) and add at minimum:

```env
APP_NAME=AutoLister
APP_VERSION=1.0.0
DEBUG=true
DASHBOARD_HOST=0.0.0.0
DASHBOARD_PORT=8000
```

### Step 5: Initialize Database

```cmd
python -c "from app.database import init_db; init_db()"
```

### Step 6: Run the Application

```cmd
python -m uvicorn app.main:app --reload
```

The dashboard will be available at: http://localhost:8000/dashboard

## Full Setup (With Redis/Celery)

For production use with background tasks.

### Step 1: Install Redis

Option A - Using Windows Redis:
1. Download Redis for Windows
2. Extract and run `redis-server.exe`

Option B - Using WSL:
```cmd
wsl
sudo apt-get update
sudo apt-get install redis-server
sudo service redis-server start
```

### Step 2: Update .env File

Add Redis configuration:
```env
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
```

### Step 3: Run Celery Worker (New Terminal Window)

```cmd
venv\Scripts\activate
celery -A app.tasks worker --loglevel=info
```

### Step 4: Run Celery Beat (Another New Terminal Window)

```cmd
venv\Scripts\activate
celery -A app.tasks beat --loglevel=info
```

### Step 5: Run the Main App (Original Terminal)

```cmd
python -m uvicorn app.main:app --reload
```

## Troubleshooting

### Python not found

If you get "Python is not recognized", you need to add Python to your PATH:
1. Search for "Environment Variables" in Windows
2. Click "Edit the system environment variables"
3. Click "Environment Variables"
4. Under "System variables", find "Path" and click "Edit"
5. Add paths like:
   - `C:\Users\YourName\AppData\Local\Programs\Python\Python311`
   - `C:\Users\YourName\AppData\Local\Programs\Python\Python311\Scripts`

### Module not found errors

Make sure you've activated the virtual environment and installed requirements:
```cmd
venv\Scripts\activate
pip install -r requirements.txt
```

### Redis connection errors

If you don't need background tasks, you can run without Redis. Just skip the Celery commands.

### Port already in use

If port 8000 is already in use, change it in `.env`:
```env
DASHBOARD_PORT=8001
```

## Testing the Application

1. Open http://localhost:8000/dashboard in your browser
2. You should see the dashboard with statistics
3. The API is available at http://localhost:8000/api

## Next Steps

1. Configure API keys in `.env` (Google, Bing, Etsy)
2. Test the scraping functionality
3. Process some manuals and create test listings

## Stopping the Application

Press `Ctrl+C` in each terminal window to stop the services.

To deactivate the virtual environment:
```cmd
deactivate
```
