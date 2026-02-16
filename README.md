# AutoLister

Automatic PDF Manual Scraper and Etsy Lister for Raspberry Pi

## Overview

AutoLister is a Python-based application that automatically scrapes PDF manuals for equipment (ATVs, lawnmowers, tractors, generators, etc.), processes them for Etsy listings, and creates listings with digital download capabilities.

## Features

- **Multi-Source Scraping**: Search engines (Google/Bing), equipment forums, and manual-specific websites
- **Approval Workflow**: Web dashboard for manual review and approval before download
- **PDF Processing**: Extract text, generate images, and create listing summaries
- **Etsy Integration**: Create listings with images and digital downloads
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
- Google Custom Search API key and CX
- Bing Search API key
- Etsy API credentials
- Other settings as needed

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

- `GET /api/stats` - System statistics
- `GET /api/pending` - Pending manuals for approval
- `POST /api/pending/{id}/approve` - Approve a manual
- `POST /api/pending/{id}/reject` - Reject a manual
- `POST /api/manuals/{id}/download` - Download a PDF
- `POST /api/manuals/{id}/process` - Process a PDF
- `POST /api/manuals/{id}/list` - Create Etsy listing
- `GET /api/listings` - List all Etsy listings
- `POST /api/listings/{id}/activate` - Activate a listing
- `POST /api/listings/{id}/deactivate` - Deactivate a listing

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

The Etsy Open API has limitations:
- Digital file uploads may not be supported via API
- You may need to manually upload PDFs through the Etsy dashboard
- The app will create listings with images, but you'll need to attach the digital file manually

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
