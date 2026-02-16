# Docker Deployment Fixes

## Issues Fixed

### 1. Celery App Loading Error
**Error**: `AttributeError: module 'app' has no attribute 'tasks'`

**Cause**: Celery was trying to load `app.tasks` as a Celery app, but the module didn't define a Celery app instance.

**Fix**: Added a Celery app instance to `app/tasks/__init__.py`:
```python
from celery import Celery
from app.config import get_settings

settings = get_settings()

# Create Celery app instance
celery_app = Celery(
    'autolister',
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=['app.tasks.jobs']
)
```

**Updated Files**:
- `app/tasks/__init__.py` - Added `celery_app` instance
- `docker/docker-compose.yml` - Updated Celery commands to use `app.tasks.celery_app`

### 2. Environment Variable Parsing Error
**Error**: `pydantic_settings.sources.SettingsError: error parsing value for field "additional_image_pages" from source "EnvSettingsSource"`

**Cause**: The `ADDITIONAL_IMAGE_PAGES` environment variable was set as `2,3,4` (comma-separated) but Pydantic was trying to parse it as JSON.

**Fix**: Changed the configuration to:
1. Store `additional_image_pages` as a string in settings
2. Added a property `additional_image_pages_list` that parses both JSON array (`[2,3,4]`) and comma-separated (`2,3,4`) formats
3. Updated all code to use the property instead of the raw field

**Updated Files**:
- `app/config.py` - Changed field type to `str` and added `additional_image_pages_list` property
- `app/processors/pdf_processor.py` - Updated to use `settings.additional_image_pages_list`
- `.env.example` - Updated to use comma-separated format

## How to Redeploy

### Option 1: Using the Deployment Script
1. Make sure you have SSH access to your Raspberry Pi
2. Run the deployment script from Windows:
   ```powershell
   powershell -ExecutionPolicy Bypass -File DEPLOY_TO_PI.ps1
   ```
3. Enter your Raspberry Pi IP when prompted
4. The script will upload the updated files and restart the containers

### Option 2: Manual Deployment
1. SSH into your Raspberry Pi:
   ```bash
   ssh pi@192.168.5.8
   ```
2. Navigate to the project directory:
   ```bash
   cd ~/autolister
   ```
3. Pull the latest changes (if using git) or upload the updated files
4. Stop the containers:
   ```bash
   docker-compose down
   ```
5. Rebuild and start the containers:
   ```bash
   docker-compose build
   docker-compose up -d
   ```

### Option 3: Test Locally First
If you want to test the fixes before deploying:

1. Install Python 3.11+ on Windows
2. Create a virtual environment:
   ```bash
   python -m venv venv
   venv\Scripts\activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Copy `.env.example` to `.env`:
   ```bash
   copy .env.example .env
   ```
5. Initialize the database:
   ```bash
   python -c "from app.database import init_db; init_db()"
   ```
6. Run the app:
   ```bash
   python -m uvicorn app.main:app --reload
   ```
7. Access the dashboard at `http://localhost:8000/dashboard`

## Verification

After deployment, verify the containers are running:

```bash
docker ps
```

You should see:
- `autolister` - Main FastAPI application
- `autolister-redis` - Redis server
- `autolister-celery` - Celery worker
- `autolister-beat` - Celery beat scheduler

Check the logs for any errors:

```bash
docker logs autolister-celery
docker logs autolister-beat
```

## Configuration Notes

The `ADDITIONAL_IMAGE_PAGES` environment variable now supports both formats:

**Comma-separated (recommended)**:
```
ADDITIONAL_IMAGE_PAGES=2,3,4
```

**JSON array**:
```
ADDITIONAL_IMAGE_PAGES=[2,3,4]
```

Both formats will be parsed correctly by the application.

## Next Steps

1. **Deploy the fixes** using one of the methods above
2. **Verify the containers are running** without errors
3. **Access the dashboard** at `http://<pi-ip>:8000/dashboard`
4. **Test the application** by:
   - Running a scraping job
   - Approving/rejecting manuals
   - Downloading and processing PDFs
   - Creating file listings

## Troubleshooting

If you still encounter errors:

1. Check the container logs:
   ```bash
   docker logs autolister-celery
   docker logs autolister-beat
   docker logs autolister
   ```

2. Verify the `.env` file exists and has the correct format:
   ```bash
   cat .env
   ```

3. Check Redis is running:
   ```bash
   docker logs autolister-redis
   ```

4. Restart the containers:
   ```bash
   docker-compose restart
   ```

5. Rebuild from scratch if needed:
   ```bash
   docker-compose down
   docker-compose build --no-cache
   docker-compose up -d
   ```
