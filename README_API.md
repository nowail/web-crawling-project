# FilersKeepers REST API

A comprehensive RESTful API built with FastAPI for managing and monitoring book data with change detection capabilities.

## 🚀 Features

- **Book Management**: Browse, search, and filter books with advanced querying
- **Change Tracking**: Monitor price changes, availability updates, and new books
- **Authentication**: API key-based authentication system
- **Rate Limiting**: 100 requests per hour per API key
- **Pagination**: Efficient pagination for large datasets
- **OpenAPI Documentation**: Interactive Swagger UI and ReDoc
- **Health Monitoring**: Built-in health checks and statistics

## 📋 API Endpoints

### Books
- `GET /books` - List books with filtering and pagination
- `GET /books/{book_id}` - Get book details by ID

### Changes
- `GET /changes` - View recent updates and changes

### System
- `GET /health` - Health check (no auth required)

## 🔧 Installation

1. **Install Dependencies**:
   ```bash
   pip install -r requirements-api.txt
   ```

2. **Environment Setup**:
   Create a `.env` file with your configuration:
   ```env
   API_HOST=0.0.0.0
   API_PORT=8000
   API_DEBUG=false
   API_MONGODB_URL=mongodb://localhost:27017
   API_MONGODB_DATABASE=filers_keepers
   API_SECRET_KEY=your-secret-key-here
   ```

3. **Run the API**:
   ```bash
   python run_api.py
   ```

   Or directly with uvicorn:
   ```bash
   uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
   ```

## 🔐 Authentication

All endpoints (except `/health`) require API key authentication.

### API Key Configuration

API keys are configured via environment variables for security. Copy `env.example` to `.env` and configure your API keys:

```bash
# Copy the example configuration
cp env.example .env

# Edit .env file
nano .env
```

**Configure API Keys in `.env`:**
```bash
# Comma-separated list of valid API keys
API_KEYS=fk_wSahdItxXh5e3oooff3AVn0mXS4hG3GKM5T8XdtNLMg,fk_your_second_key_here
```

**Start the API:**
```bash
# With environment variables
API_KEYS="fk_wSahdItxXh5e3oooff3AVn0mXS4hG3GKM5T8XdtNLMg" python run_api.py

# Or with .env file
python run_api.py
```

### Using API Keys

Include your API key in the Authorization header:

```bash
curl -H "Authorization: Bearer your_api_key_here" \
  "http://localhost:8000/books"
```

## 📖 API Usage Examples

### Get Books with Filtering

```bash
# Get books in "Fiction" category, sorted by rating
curl -H "Authorization: Bearer your_api_key" \
  "http://localhost:8000/books?category=Fiction&sort_by=rating&sort_order=desc&page=1&per_page=10"

# Get books with price range
curl -H "Authorization: Bearer your_api_key" \
  "http://localhost:8000/books?min_price=10&max_price=50&rating=4"

# Get books by rating
curl -H "Authorization: Bearer your_api_key" \
  "http://localhost:8000/books?rating=5&sort_by=reviews&sort_order=desc"
```

### Get Book Details

```bash
# Get book by MongoDB ObjectId
curl -H "Authorization: Bearer your_api_key" \
  "http://localhost:8000/books/507f1f77bcf86cd799439011"

# Get book by source URL
curl -H "Authorization: Bearer your_api_key" \
  "http://localhost:8000/books/https://books.toscrape.com/catalogue/a-light-in-the-attic_1000/index.html"
```

### Get Recent Changes

```bash
# Get all recent changes
curl -H "Authorization: Bearer your_api_key" \
  "http://localhost:8000/changes?page=1&per_page=20"

# Get price changes only
curl -H "Authorization: Bearer your_api_key" \
  "http://localhost:8000/changes?change_type=price_change&severity=high"

# Get changes since a specific date
curl -H "Authorization: Bearer your_api_key" \
  "http://localhost:8000/changes?since=2025-09-21T00:00:00Z"
```


## 📊 Query Parameters

### Books Endpoint (`GET /books`)

| Parameter | Type | Description | Example |
|-----------|------|-------------|---------|
| `category` | string | Filter by category | `category=Fiction` |
| `min_price` | float | Minimum price | `min_price=10.0` |
| `max_price` | float | Maximum price | `max_price=50.0` |
| `rating` | integer | Filter by rating (1-5) | `rating=4` |
| `sort_by` | string | Sort field | `sort_by=rating` |
| `sort_order` | string | Sort order (asc/desc) | `sort_order=desc` |
| `page` | integer | Page number | `page=1` |
| `per_page` | integer | Items per page (1-100) | `per_page=20` |

**Sort Fields**: `name`, `rating`, `price`, `reviews`, `created_at`, `updated_at`

### Changes Endpoint (`GET /changes`)

| Parameter | Type | Description | Example |
|-----------|------|-------------|---------|
| `book_id` | string | Filter by book ID | `book_id=book_123` |
| `change_type` | string | Filter by change type | `change_type=price_change` |
| `severity` | string | Filter by severity | `severity=high` |
| `since` | string | Changes since date (ISO) | `since=2025-09-21T00:00:00Z` |
| `page` | integer | Page number | `page=1` |
| `per_page` | integer | Items per page (1-100) | `per_page=20` |

**Change Types**: `price_change`, `availability_change`, `rating_change`, `new_book`, `book_removed`, `description_change`, `category_change`

**Severity Levels**: `low`, `medium`, `high`, `critical`

## 🚦 Rate Limiting

- **Limit**: 100 requests per hour per API key
- **Headers**: Rate limit information is included in response headers:
  - `X-RateLimit-Limit`: Total requests allowed per hour
  - `X-RateLimit-Remaining`: Remaining requests in current hour
  - `X-RateLimit-Reset`: Unix timestamp when limit resets

## 📚 Documentation

Once the API is running, visit:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI JSON**: http://localhost:8000/openapi.json

## 🔍 Health Monitoring

### Health Check
```bash
curl http://localhost:8000/health
```


## 🛠️ Development

### Running in Development Mode
```bash
uvicorn api.main:app --reload --log-level debug
```

### Testing
```bash
# Install test dependencies
pip install pytest pytest-asyncio httpx

# Run tests
pytest tests/
```

## 🚀 Production Deployment

### Using Gunicorn
```bash
pip install gunicorn
gunicorn api.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

### Using Docker
```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements-api.txt .
RUN pip install -r requirements-api.txt

COPY . .
EXPOSE 8000

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

## 🔧 Configuration

All configuration can be set via environment variables with the `API_` prefix:

- `API_HOST`: Server host (default: 0.0.0.0)
- `API_PORT`: Server port (default: 8000)
- `API_DEBUG`: Debug mode (default: false)
- `API_MONGODB_URL`: MongoDB connection URL
- `API_MONGODB_DATABASE`: Database name
- `API_SECRET_KEY`: Secret key for JWT tokens
- `API_DEFAULT_RATE_LIMIT`: Default rate limit (default: 100)

## 📝 Response Format

All API responses follow a consistent format:

### Success Response
```json
{
  "books": [...],
  "total": 1000,
  "page": 1,
  "per_page": 20,
  "total_pages": 50,
  "has_next": true,
  "has_prev": false
}
```

### Error Response
```json
{
  "error": "Error message",
  "detail": "Additional error details",
  "status_code": 400
}
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License.
