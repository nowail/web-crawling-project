# FilersKeepers Assessment - Web Crawler & Change Detection System

A comprehensive web crawling and change detection system for books.toscrape.com with advanced scheduling, monitoring, and alerting capabilities.

## 📋 Project Overview

This project consists of two main parts:
- **Part 1**: Robust web crawler with async operations and MongoDB integration
- **Part 2**: Scheduler and change detection system with alerting and reporting

## 🚀 Features

### Part 1: Web Crawler
- **Async Web Crawling**: High-performance async crawling using `httpx`
- **Robust Error Handling**: Retry logic with exponential backoff
- **Resumable Operations**: Save/restore crawl state for fault tolerance
- **MongoDB Integration**: Efficient NoSQL storage with optimized indexing
- **Data Validation**: Pydantic models for type safety and validation
- **Comprehensive Logging**: Structured logging with multiple output formats
- **Rate Limiting**: Respectful crawling with configurable rate limits
- **HTML Snapshots**: Store raw HTML as fallback for data recovery

### Part 2: Scheduler & Change Detection
- **Daily Scheduling**: Automated daily change detection using APScheduler
- **Content Fingerprinting**: SHA-256 hashing for efficient change detection
- **Change Classification**: Automatic classification of changes by type and severity
- **Alerting System**: Email and log-based notifications for significant changes
- **Report Generation**: Daily reports in JSON and CSV formats
- **Performance Monitoring**: Real-time metrics and system health tracking
- **Rate Limiting**: Configurable alert rate limiting and cooldown periods
- **Data Persistence**: Complete audit trail of all changes and detections

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
```bash
cd /Users/dev/Desktop/Assessments/FilersKeepersAssessment
```

### 2. Create Virtual Environment
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. MongoDB Setup
Install and start MongoDB:
```bash
# macOS with Homebrew
brew install mongodb-community
brew services start mongodb-community

# Or use Docker
docker run -d -p 27017:27017 --name mongodb mongo:latest
```

### 5. Environment Configuration
Copy the example environment file:
```bash
cp env.example .env
```

Edit `.env` with your configuration:
```env
# MongoDB Configuration
MONGODB_URL=mongodb://localhost:27017
MONGODB_DATABASE=filers_keepers
MONGODB_COLLECTION=books

# Crawler Configuration
BASE_URL=https://books.toscrape.com
MAX_CONCURRENT_REQUESTS=10
REQUEST_TIMEOUT=30
RETRY_ATTEMPTS=3
RETRY_DELAY=1
RATE_LIMIT_PER_SECOND=2

# Logging Configuration
LOG_LEVEL=INFO
LOG_FORMAT=json
LOG_FILE=logs/crawler.log

# Crawl State Management
STATE_FILE=crawl_state.json
RESUME_ON_FAILURE=true

# Development/Testing
DEBUG=false
TEST_MODE=false
```

## 🏃‍♂️ Running the System

### Part 1: Web Crawler

#### Basic Usage
```bash
python main.py
```

#### Development Mode
```bash
DEBUG=true LOG_FORMAT=console python main.py
```

#### Test Mode (Limited Crawling)
```bash
TEST_MODE=true python main.py
```

### Part 2: Scheduler & Change Detection

#### Start the Scheduler Service
```bash
python scheduler_main.py
```

#### Test the Scheduler (Manual Run)
```bash
python test_scheduler.py
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

## 📊 Data Structure

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
pytest
```

### Run with Coverage
```bash
pytest --cov=crawler --cov=utilities
```

### Run Specific Test Files
```bash
pytest tests/test_models.py
pytest tests/test_crawler.py
```

### Run with Verbose Output
```bash
pytest -v
```

## 📁 Project Structure

```
FilersKeepersAssessment/
├── README.md                 # This file
├── requirements.txt          # Python dependencies
├── env.example              # Environment configuration template
├── main.py                  # Part 1: Main crawler entry point
├── scheduler_main.py        # Part 2: Scheduler service entry point
├── test_scheduler.py        # Part 2: Scheduler testing script
├── crawler/                 # Part 1: Crawler module
│   ├── __init__.py
│   ├── book_crawler.py      # Main crawler implementation
│   ├── models.py            # Pydantic data models
│   └── database.py          # MongoDB operations
├── scheduler/               # Part 2: Scheduler and change detection
│   ├── __init__.py
│   ├── models.py            # Scheduler data models
│   ├── fingerprinting.py    # Content fingerprinting system
│   ├── change_detector.py   # Change detection engine
│   ├── alerting.py          # Alerting and notification system
│   ├── report_generator.py  # Report generation system
│   └── scheduler_service.py # Main scheduler service
├── utilities/               # Utility modules
│   ├── __init__.py
│   ├── config.py            # Configuration management
│   └── logger.py            # Logging system
├── tests/                   # Test suite
│   ├── __init__.py
│   ├── conftest.py          # Pytest configuration
│   ├── test_models.py       # Model tests
│   ├── test_crawler.py      # Crawler tests
│   └── test_scheduler.py    # Scheduler tests
├── reports/                 # Generated reports (created at runtime)
└── logs/                    # Log files (created at runtime)
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

## 🚨 Error Handling

The crawler implements comprehensive error handling:

- **Network Errors**: Automatic retry with exponential backoff
- **Parsing Errors**: Graceful handling of malformed HTML
- **Database Errors**: Connection recovery and duplicate handling
- **Rate Limiting**: Automatic throttling to respect server limits
- **State Recovery**: Resume from last successful crawl point

## 📈 Performance Features

- **Async Operations**: Concurrent processing for maximum speed
- **Batch Database Operations**: Efficient bulk inserts
- **Connection Pooling**: Reuse HTTP connections
- **Memory Management**: Streaming processing for large datasets
- **Optimized Indexing**: Fast database queries

## 🔍 Monitoring and Logging

### Log Formats
- **JSON**: Structured logs for production monitoring
- **Console**: Human-readable logs for development

### Log Levels
- **DEBUG**: Detailed debugging information
- **INFO**: General operational information
- **WARNING**: Warning messages for non-critical issues
- **ERROR**: Error messages for failed operations
- **CRITICAL**: Critical errors that may cause system failure

### Log Files
Logs are written to `logs/crawler.log` by default, with automatic log rotation and cleanup.

## 🛡️ Security Features

- **Rate Limiting**: Prevents overwhelming the target server
- **User Agent**: Identifies the crawler as educational assessment
- **Input Validation**: Pydantic models validate all input data
- **Error Sanitization**: Sensitive information is not logged
- **Environment Variables**: Secure configuration management

## 📝 Example Usage

### Basic Crawling
```python
from crawler.database import MongoDBManager
from crawler.book_crawler import BookCrawler

# Initialize database manager
db_manager = MongoDBManager(
    connection_url="mongodb://localhost:27017",
    database_name="filers_keepers",
    collection_name="books"
)

# Connect to database
await db_manager.connect()

# Initialize and run crawler
crawler = BookCrawler(db_manager)
result = await crawler.crawl_all_books()

print(f"Crawled {result.books_crawled} books in {result.duration_seconds} seconds")
```

### Querying Data
```python
# Get books by category
poetry_books = await db_manager.get_books_by_category("Poetry")

# Get book by URL
book = await db_manager.get_book_by_url("https://books.toscrape.com/catalogue/...")

# Get database statistics
stats = await db_manager.get_database_stats()
```

## 🐛 Troubleshooting

### Common Issues

1. **MongoDB Connection Failed**
   - Ensure MongoDB is running: `brew services start mongodb-community`
   - Check connection URL in `.env` file
   - Verify MongoDB is accessible on port 27017

2. **Import Errors**
   - Ensure virtual environment is activated
   - Install dependencies: `pip install -r requirements.txt`
   - Check Python path in `main.py`

3. **Rate Limiting Issues**
   - Reduce `RATE_LIMIT_PER_SECOND` in configuration
   - Increase `RETRY_DELAY` for more conservative crawling

4. **Memory Issues**
   - Reduce `MAX_CONCURRENT_REQUESTS`
   - Enable garbage collection in Python

### Debug Mode
Run with debug mode for detailed logging:
```bash
DEBUG=true LOG_LEVEL=DEBUG python main.py
```

## 📊 Expected Results

After successful crawling, you should see:
- All books from books.toscrape.com stored in MongoDB
- Comprehensive logs in `logs/crawler.log`
- Crawl state saved in `crawl_state.json`
- Database statistics showing total books and categories

## 🔄 Next Steps

This completes Part 1 of the FilersKeepers Assessment. The crawler is ready for:
- Part 2: Scheduler implementation
- Part 3: RESTful API development
- Part 4: Testing and deployment

## 📄 License

This project is part of the FilersKeepers Assessment and is for educational purposes only.
