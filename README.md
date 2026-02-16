# AutoLister

Automatic PDF Manual Scraper and Etsy Lister for Raspberry Pi

## Overview

AutoLister is a Python-based application that automatically scrapes PDF manuals for equipment (ATVs, lawnmowers, tractors, generators, etc.), processes them for Etsy listings, and creates listings with digital download capabilities.

## Features

- **Multi-Source Scraping**: Search engines (DuckDuckGo/Google/Bing), equipment forums, and manual-specific websites
  - **DuckDuckGo**: Free search engine, no API key required
  - **Google/Bing**: Optional API-based search for better results
- **Approval Workflow**: Web dashboard for manual review and approval before download
- **PDF Processing**: Extract text, generate images, and create listing summaries
- **File-Based Listings**: Create listing files for manual Etsy upload (no API required)
- **Background Tasks**: Automated scraping and processing with Celery
- **Docker Support**: Easy deployment on Raspberry Pi

## Technology Stack

- **Backend**: Python 3.11+ with FastAPI
- **Database**: SQLite (can be upgraded to PostgreSQL)
- **Task Queue**: Celery + Redis
- **Scraping**: BeautifulSoup4, Scrapy, Selenium/Playwright
- **PDF Processing**: PyPDF2, pdfplumber, Pillow
- **Etsy API**: Etsy Open API Python SDK

## Project Structure

```
AutoLister/
├── app/
│   ├── api/              # API routes and schemas
│   ├── scrapers/         # Web scrapers
│   ├── processors/       # PDF processing
│   ├── etsy/            # Etsy integration
│   ├── tasks/           # Background jobs
│   ├── static/          # Dashboard frontend
│   ├── config.py        # Configuration
│   ├── database.py      # Database models
│   └── main.py         # FastAPI application
├── config/              # Configuration files
├── data/                # Data storage (PDFs, images, database)
├── docker/              # Docker configuration
├── tests/               # Test files
├── requirements.txt     # Python dependencies
└── README.md           # This file
```

## Installation

### Prerequisites

- Python 3.11 or higher
- Docker and Docker Compose (for containerized deployment)
- Redis (for Celery task queue)

### Local Development Setup

1. Clone the repository:
```bash
git clone https://github.com/yourusername/AutoLister.git
cd AutoLister
```

**Note**: This app now works WITHOUT Etsy API credentials. You can create file-based listings that can be manually uploaded to Etsy.

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Copy the example environment file and configure:
```bash
cp .env.example .env
```

Edit `.env` with your API keys and configuration:

**Required for Basic Functionality:**
- None! The app works out of the box with DuckDuckGo (free, no API key)

**Optional for Enhanced Search:**
- Google Custom Search API key and CX (for better Google results)
- Bing Search API key (for better Bing results)

**Optional for Etsy API Integration:**
- Etsy API credentials (for direct listing creation)

**Other Settings:**
- Scraping intervals, PDF limits, image settings, etc.

5. Initialize the database:
```bash
python -c "from app.database import init_db; init_db()"
```

6. Run the application:
```bash
python -m uvicorn app.main:app --reload
```

The dashboard will be available at `http://localhost:8000/dashboard`

### Docker Deployment (Raspberry Pi)

1. Build and start the containers:
```bash
cd docker
docker-compose up -d
```

2. View logs:
```bash
docker-compose logs -f autolister
```

3. Stop the containers:
```bash
docker-compose down
```

## Configuration

### Environment Variables

See [`.env.example`](.env.example) for all available configuration options.

Key settings:
- `SCRAPING_INTERVAL_HOURS`: How often to run scraping jobs
- `MAX_RESULTS_PER_SEARCH`: Maximum results per search query
- `MAX_PDF_SIZE_MB`: Maximum PDF file size
- `ETSY_DEFAULT_PRICE`: Default listing price
- `DASHBOARD_PORT`: Dashboard web server port

### Search Terms

Edit [`config/search_terms.yaml`](config/search_terms.yaml) to customize:
- Equipment categories
- Brands
- Types
- Keywords

## Usage

### Dashboard

Access the web dashboard at `http://localhost:8000/dashboard` (or your Raspberry Pi's IP address).

The dashboard provides:
- System statistics
- Pending manual approval
- Manual management
- Etsy listing management

### API Endpoints

**Manual Management API**:
- `GET /api/stats` - System statistics
- `GET /api/pending` - Pending manuals for approval
- `POST /api/pending/{id}/approve` - Approve a manual
- `POST /api/pending/{id}/reject` - Reject a manual
- `POST /api/manuals/{id}/download` - Download a PDF
- `POST /api/manuals/{id}/process` - Process a PDF

**File-Based Listing API** (No Etsy API Required):
- `GET /api/files/listings` - Get all file listings
- `GET /api/files/listings/{id}` - Get specific listing details
- `GET /api/files/listings/{id}/files` - Get listing files
- `POST /api/files/listings` - Create a new file listing
- `PUT /api/files/listings/{id}/status` - Update listing status
- `DELETE /api/files/listings/{id}` - Delete a listing
- `GET /api/files/export/csv` - Export listings to CSV
- `GET /api/files/download/{filename}` - Download a file from listings directory
- `GET /api/files/statistics` - Get listing statistics

### Background Tasks

Run scraping jobs:
```python
from app.tasks import run_scraping_job
run_scraping_job()
```

Process approved manuals:
```python
from app.tasks import process_approved_manuals
process_approved_manuals()
```

Create Etsy listings:
```python
from app.tasks import create_etsy_listings
create_etsy_listings()
```

## Etsy API Setup

### Get Etsy API Credentials

1. Go to [Etsy Developers](https://www.etsy.com/developers)
2. Create a new app
3. Get your API key and secret
4. Generate access tokens

### Configure Etsy Integration

Add your credentials to `.env`:
```
ETSY_API_KEY=your_api_key
ETSY_API_SECRET=your_api_secret
ETSY_ACCESS_TOKEN=your_access_token
ETSY_ACCESS_TOKEN_SECRET=your_access_token_secret
ETSY_SHOP_ID=your_shop_id
```

### Important Note

**Two Modes of Operation**:

1. **Etsy API Mode** (Optional):
   - Requires Etsy API credentials
   - Creates listings directly on Etsy
   - Uploads images automatically
   - Digital file upload may require manual action due to API limitations

2. **File-Based Mode** (Default - No API Required):
   - Creates listing files in `data/listings/` directory
   - Each listing has its own folder with PDF, images, and README.txt
   - Includes upload instructions for Etsy
   - No API credentials required
   - Works offline and can be used with any marketplace
   - Each listing has its own folder with PDF and images
   - Includes a README.txt with upload instructions
   - You manually upload files to Etsy through the dashboard
   - No API credentials required
   - Works offline and can be used with any marketplace

The app supports both modes. Use file-based mode if you don't want to deal with Etsy API setup or rate limits.

## Development

### Running Tests

```bash
pytest tests/
```

### Code Style

This project follows PEP 8 style guidelines.

### Adding New Scrapers

1. Create a new scraper in `app/scrapers/`
2. Inherit from `BaseScraper`
3. Implement the `search()` method
4. Register in `app/scrapers/__init__.py`

## Troubleshooting

### Common Issues

**Database locked error**: Ensure only one process is accessing the database at a time.

**Scraping fails**: Check your API keys and internet connection.

**Etsy API errors**: Verify your credentials and ensure your shop is properly configured.

**PDF processing fails**: Check that the PDF is valid and not corrupted.

### Logs

Check logs in the `logs/` directory or Docker logs:
```bash
docker-compose logs -f autolister
```

## License

This project is provided as-is for educational purposes.

## Disclaimer

This tool is for educational purposes only. Always respect:
- Website terms of service
- Copyright laws
- Etsy seller policies
- Rate limiting and fair use

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Support

For issues and questions, please open an issue on GitHub.
