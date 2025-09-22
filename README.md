# FilersKeepers Assessment - Web Crawler & Change Detection System

A comprehensive web crawling and change detection system for books.toscrape.com with advanced scheduling, monitoring, and alerting capabilities.

## 📋 Requirements

### Python Version
- Python 3.8 or higher

### Dependencies
See `requirements.txt` for complete dependency list with versions:
- `httpx` - Async HTTP client
- `pydantic` - Data validation and serialization
- `motor` - Async MongoDB driver
- `beautifulsoup4` - HTML parsing
- `structlog` - Structured logging
- `pytest` - Testing framework

## 🛠️ Setup Instructions

### 1. Clone and Navigate

### 2. Create Virtual Environment
```bash
python -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip3 install -r requirements.txt
```

### 4. MongoDB Setup
Install and start MongoDB:
```bash
# macOS with Homebrew
brew install mongodb-community
brew services start mongodb-community


### 5. Environment Configuration
Copy the example environment file:
```bash
cp env.example .env
```

Edit `.env` with your configuration:

## 🏃‍♂️ Running the System

### Part 1: Web Crawler

#### Basic Usage
```bash
python3 main.py
```

### Part 2: Scheduler & Change Detection

To start the scheduler:
#### Start the Scheduler Service
```bash
python3 manage_daemon.py start
```

To stop the scheduler:
```bash
python3 manage_daemon.py start
```

#### Configuration
The scheduler can be configured via environment variables (see `env.example`):

```bash
# Scheduling
SCHEDULE_HOUR=2          # Run at 2 AM
SCHEDULE_MINUTE=0        # Run at 2:00 AM
TIMEZONE=UTC

# Change Detection
ENABLE_CHANGE_DETECTION=true
MAX_CONCURRENT_BOOKS=50
BATCH_SIZE=100

# Alerting
EMAIL_ENABLED=false      # Set to true for email alerts
LOG_ENABLED=true
MIN_SEVERITY_FOR_EMAIL=medium

# Reporting
GENERATE_DAILY_REPORTS=true
REPORT_FORMAT=json       # or csv
```

### Part 1: Book Data Schema
Each book document contains:

```json
{
  "name": "A Light in the Attic",
  "description": "It's hard to imagine a world without A Light in the Attic...",
  "category": "Poetry",
  "price_including_tax": 51.77,
  "price_excluding_tax": 51.77,
  "availability": "In stock",
  "number_of_reviews": 22,
  "image_url": "https://books.toscrape.com/media/cache/2c/da/2cdad67c44b002e7ead0cc35693c0e8.jpg",
  "rating": 3,
  "source_url": "https://books.toscrape.com/catalogue/a-light-in-the-attic_1000/index.html",
  "crawl_timestamp": "2024-01-15T10:30:00Z",
  "status": "completed",
  "raw_html": "<html>...</html>"
}
```

### Part 2: Change Detection Schema

#### Content Fingerprint
```json
{
  "book_id": "book_abc123",
  "source_url": "https://books.toscrape.com/catalogue/book_1000/index.html",
  "content_hash": "sha256_hash_of_content",
  "price_hash": "sha256_hash_of_price",
  "availability_hash": "sha256_hash_of_availability",
  "metadata_hash": "sha256_hash_of_metadata",
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T10:30:00Z"
}
```

#### Change Log
```json
{
  "change_id": "change_xyz789",
  "book_id": "book_abc123",
  "source_url": "https://books.toscrape.com/catalogue/book_1000/index.html",
  "change_type": "price_change",
  "severity": "high",
  "old_value": 51.77,
  "new_value": 49.99,
  "field_name": "price_including_tax",
  "change_summary": "Price changed from £51.77 to £49.99",
  "detected_at": "2024-01-15T10:30:00Z",
  "confidence_score": 1.0
}
```

#### Daily Report
```json
{
  "report_id": "report_20240115",
  "report_date": "2024-01-15T00:00:00Z",
  "generated_at": "2024-01-15T02:30:00Z",
  "total_books_in_system": 1000,
  "books_checked": 1000,
  "changes_detected": 15,
  "new_books_added": 2,
  "books_updated": 12,
  "books_removed": 1,
  "changes_by_type": {
    "price_change": 8,
    "availability_change": 3,
    "description_change": 1
  },
  "changes_by_severity": {
    "high": 8,
    "medium": 5,
    "low": 2
  },
  "system_health_score": 0.95
}
```

### MongoDB Indexes
Optimized indexes for efficient querying:
- `source_url` (unique) - Deduplication
- `category` - Category filtering
- `availability` - Availability filtering
- `price_including_tax` - Price range queries
- `rating` - Rating filtering
- `crawl_timestamp` - Time-based queries
- Compound indexes for complex queries

## 🧪 Testing

### Run All Tests
```bash
pytest -m tests/
```

## 🔧 Configuration Options

### Crawler Settings
- `MAX_CONCURRENT_REQUESTS`: Number of concurrent HTTP requests (1-50)
- `REQUEST_TIMEOUT`: HTTP request timeout in seconds (5-300)
- `RETRY_ATTEMPTS`: Number of retry attempts (0-10)
- `RETRY_DELAY`: Base delay between retries in seconds
- `RATE_LIMIT_PER_SECOND`: Requests per second limit (0.1-10)

### Logging Settings
- `LOG_LEVEL`: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- `LOG_FORMAT`: Output format (json, console)
- `LOG_FILE`: Optional log file path

### Database Settings
- `MONGODB_URL`: MongoDB connection URL
- `MONGODB_DATABASE`: Database name
- `MONGODB_COLLECTION`: Collection name

## 🔍 Monitoring and Logging

### Log Formats
- **JSON**: Structured logs for production monitoring
- **Console**: Human-readable logs for development

### Log Files
Logs are written to `logs/crawler.log` by default, with automatic log rotation and cleanup.

## 📊 Expected Results

After successful crawling, you should see:
- All books from books.toscrape.com stored in MongoDB
- Comprehensive logs in `logs/crawler.log`
- Crawl state saved in `crawl_state.json`

## 📄 License

This project is part of the FilersKeepers Assessment and is for evaluation purposes