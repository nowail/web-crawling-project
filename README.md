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

### 📸 Testing Screenshots & Documentation
The `images/` folder contains comprehensive testing screenshots and documentation:
- **Successful crawler run** - Screenshots showing the web crawler successfully extracting book data
- **Successful scheduler run** - Screenshots demonstrating the change detection system working properly
- **End-to-end workflow** - Complete testing flow with change logs and API responses
- **API documentation** - Screenshots of the FastAPI Swagger UI and API endpoint testing results

All testing has been completed and documented with visual proof of the system's functionality.

### 📚 Documentation Structure
This project includes separate README files for each major component:
- **`README_API.md`** - FastAPI REST API documentation and endpoints
- **`README_DAEMON.md`** - Scheduler daemon setup and management
- **`README.md`** - This main documentation file

Here are the highlights of each part. For more details, visit the related README file:

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
python3 manage_daemon.py stop
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

### Part 3: API testing

#### Basic Usage
```bash
python3 run_api.py
```

## 🗄️ MongoDB Document Structure

The system uses MongoDB with the following collections and document structures:

### 📚 Books Collection (`books`)

**Primary collection storing book data from books.toscrape.com**

```json
{
  "_id": "ObjectId('...')",
  "name": "A Light in the Attic",
  "description": "It's hard to imagine a world without A Light in the Attic. This now-classic collection of poetry and drawings from Shel Silverstein celebrates its 20th anniversary...",
  "category": "Poetry",
  "price_including_tax": 51.77,
  "price_excluding_tax": 51.77,
  "availability": "In stock",
  "number_of_reviews": 0,
  "image_url": "https://books.toscrape.com/media/cache/2c/da/2cdad67c44b002e7ead0cc35693c0e8.jpg",
  "rating": 3,
  "source_url": "https://books.toscrape.com/catalogue/a-light-in-the-attic_1000/index.html",
  "crawl_timestamp": "2024-01-15T10:30:00Z",
  "status": "completed",
  "raw_html": "<html>...</html>",
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T10:30:00Z"
}
```

**Field Descriptions:**
- `name` (string): Book title
- `description` (string): Book description/summary
- `category` (string): Book category/genre
- `price_including_tax` (decimal): Price with tax included
- `price_excluding_tax` (decimal): Price without tax
- `availability` (string): Stock status ("In stock" or "Out of stock")
- `number_of_reviews` (integer): Number of customer reviews
- `image_url` (string): URL to book cover image
- `rating` (integer): Star rating (1-5, null if no rating)
- `source_url` (string): Original book page URL
- `crawl_timestamp` (datetime): When the book was crawled
- `status` (string): Crawl status ("completed", "failed")
- `raw_html` (string): Raw HTML snapshot for fallback
- `created_at` (datetime): Document creation timestamp
- `updated_at` (datetime): Last update timestamp

### 🔍 Fingerprints Collection (`fingerprints`)

**Stores content fingerprints for efficient change detection**

```json
{
  "_id": "ObjectId('...')",
  "book_id": "book_c8cb1d10209c6fbed02788a1b7ba5cba",
  "source_url": "https://books.toscrape.com/catalogue/a-light-in-the-attic_1000/index.html",
  "content_hash": "dcf6c1d6714a25680d3c4ed4c224b174b2a9b9021111ffaf3fd9958fcbc81363",
  "price_hash": "d78875cf1bdf1b2dbce7cf1aa1b752374c48024f4c8ee63bd53a97f934cc3dd2",
  "availability_hash": "bbc0d7d42e2bf1213a132608a85a8e3df9259883ed71126f52b6f044665683a0",
  "metadata_hash": "c1403ff7a4b69d28b4085283b77a56fdf86063df1074c55b69d83b9a230df652",
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T10:30:00Z"
}
```

**Field Descriptions:**
- `book_id` (string): Unique book identifier (SHA-256 hash of source_url)
- `source_url` (string): Book page URL (unique)
- `content_hash` (string): SHA-256 hash of all book fields
- `price_hash` (string): SHA-256 hash of price fields only
- `availability_hash` (string): SHA-256 hash of availability and reviews
- `metadata_hash` (string): SHA-256 hash of description, category, rating, image
- `created_at` (datetime): Fingerprint creation timestamp
- `updated_at` (datetime): Last fingerprint update timestamp

### 📝 Change Logs Collection (`change_logs`)

**Records all detected changes with detailed information**

```json
{
  "_id": "ObjectId('...')",
  "change_id": "change_xyz789",
  "book_id": "book_abc123",
  "source_url": "https://books.toscrape.com/catalogue/book_1000/index.html",
  "change_type": "price_change",
  "severity": "high",
  "old_value": 51.77,
  "new_value": 49.99,
  "field_name": "price_including_tax",
  "change_summary": "price_including_tax changed from '51.77' to '49.99'",
  "detected_at": "2024-01-15T10:30:00Z",
  "confidence_score": 1.0
}
```

**Field Descriptions:**
- `change_id` (string): Unique change identifier (UUID)
- `book_id` (string): Associated book identifier
- `source_url` (string): Book page URL
- `change_type` (string): Type of change (price_change, availability_change, etc.)
- `severity` (string): Change severity (low, medium, high)
- `old_value` (mixed): Previous field value
- `new_value` (mixed): New field value
- `field_name` (string): Name of the changed field
- `change_summary` (string): Human-readable change description
- `detected_at` (datetime): When the change was detected
- `confidence_score` (float): Confidence in the change detection (0.0-1.0)

### 📊 Daily Reports Collection (`daily_reports`)

**Stores daily change detection summaries**

```json
{
  "_id": "ObjectId('...')",
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
    "description_change": 1,
    "reviews_change": 2,
    "rating_change": 1
  },
  "changes_by_severity": {
    "high": 8,
    "medium": 5,
    "low": 2
  },
  "system_health_score": 0.95,
  "detection_duration_seconds": 45.2,
  "average_book_processing_time": 0.045
}
```

**Field Descriptions:**
- `report_id` (string): Unique report identifier
- `report_date` (datetime): Date the report covers
- `generated_at` (datetime): When the report was generated
- `total_books_in_system` (integer): Total books in database
- `books_checked` (integer): Number of books checked for changes
- `changes_detected` (integer): Total changes detected
- `new_books_added` (integer): New books discovered
- `books_updated` (integer): Books with changes
- `books_removed` (integer): Books no longer available
- `changes_by_type` (object): Breakdown of changes by type
- `changes_by_severity` (object): Breakdown of changes by severity
- `system_health_score` (float): Overall system health (0.0-1.0)
- `detection_duration_seconds` (float): Time taken for detection
- `average_book_processing_time` (float): Average time per book

### 🔍 Detection Results Collection (`detection_results`)

**Stores metadata about each change detection run**

```json
{
  "_id": "ObjectId('...')",
  "detection_id": "detection_abc123",
  "run_timestamp": "2024-01-15T02:00:00Z",
  "total_books_checked": 1000,
  "changes_detected": 15,
  "new_books": 2,
  "updated_books": 12,
  "removed_books": 1,
  "detection_duration_seconds": 45.2,
  "average_book_processing_time": 0.045,
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
  "success": true,
  "errors": []
}
```

### 🗂️ MongoDB Indexes

**Optimized indexes for efficient querying:**

#### Books Collection Indexes:
- `source_url` (unique) - Deduplication and fast lookups
- `category` - Category filtering
- `availability` - Availability filtering  
- `price_including_tax` - Price range queries
- `rating` - Rating filtering
- `crawl_timestamp` - Time-based queries
- `created_at` - Creation time queries
- `updated_at` - Update time queries

#### Fingerprints Collection Indexes:
- `book_id` (unique) - Fast fingerprint lookups
- `source_url` - URL-based lookups
- `updated_at` - Time-based queries

#### Change Logs Collection Indexes:
- `change_id` (unique) - Deduplication
- `book_id` - Book-specific change queries
- `detected_at` - Time-based change queries
- `change_type` - Change type filtering
- `severity` - Severity filtering
- `source_url` - URL-based queries

#### Daily Reports Collection Indexes:
- `report_id` (unique) - Report deduplication
- `report_date` - Date-based queries
- `generated_at` - Generation time queries

#### Detection Results Collection Indexes:
- `detection_id` (unique) - Run deduplication
- `run_timestamp` - Time-based queries

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