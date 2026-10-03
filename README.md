# FastAPI Starter Template

A production-ready FastAPI backend starter template with best practices, testing, and comprehensive documentation.

## Features

- **FastAPI Framework**: Modern, fast (high-performance) web framework
- **Pydantic v2**: Data validation using Python type annotations
- **Environment-based Configuration**: Easy configuration management with `.env` files
- **RESTful API Structure**: Well-organized API endpoints with versioning
- **Comprehensive Testing**: pytest setup with test coverage
- **Code Quality Tools**: Black, Ruff, and MyPy for formatting and linting
- **CORS Middleware**: Pre-configured for cross-origin requests
- **Health Checks**: Built-in health and readiness endpoints
- **API Documentation**: Auto-generated OpenAPI (Swagger) docs

## Project Structure

```
.
├── app/
│   ├── api/
│   │   └── v1/
│   │       ├── endpoints/
│   │       │   ├── health.py      # Health check endpoints
│   │       │   └── items.py       # Example CRUD endpoints
│   │       └── api.py             # API router configuration
│   ├── core/
│   │   └── config.py              # Application settings
│   ├── models/
│   │   └── item.py                # Data models
│   ├── schemas/
│   │   └── item.py                # Pydantic schemas
│   ├── services/
│   │   └── item_service.py        # Business logic
│   └── main.py                    # Application entry point
├── tests/
│   ├── api/
│   │   └── v1/
│   │       ├── test_health.py
│   │       └── test_items.py
│   └── conftest.py
├── .env.example                   # Environment variables template
├── requirements.txt               # Python dependencies
├── pyproject.toml                 # Project configuration
├── Makefile                       # Common commands
└── README.md
```

## Getting Started

### Prerequisites

- Python 3.11 or higher
- pip or poetry

### Installation

1. Clone the repository:
```bash
git clone <your-repo-url>
cd ai-builder/be
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
make install
# or
pip install -r requirements.txt
```

4. Copy the example environment file and configure:
```bash
cp .env.example .env
# Edit .env with your configuration
```

### Running the Application

#### Development Mode

```bash
make run
# or
python -m app.main
# or
uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000`

#### API Documentation

Once running, visit:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

### Testing

Run all tests:
```bash
make test
# or
pytest
```

Run tests with coverage:
```bash
make test-cov
# or
pytest --cov=app --cov-report=html --cov-report=term
```

### Code Quality

Format code:
```bash
make format
# or
black app tests
ruff check --fix app tests
```

Run linter:
```bash
make lint
# or
ruff check app tests
mypy app
```

## API Endpoints

### Health Checks

- `GET /api/v1/health` - Health check endpoint
- `GET /api/v1/ready` - Readiness check endpoint

### Items (Example CRUD)

- `POST /api/v1/items` - Create a new item
- `GET /api/v1/items` - Get list of items (with pagination)
- `GET /api/v1/items/{item_id}` - Get item by ID
- `PUT /api/v1/items/{item_id}` - Update an item
- `DELETE /api/v1/items/{item_id}` - Delete an item

## Configuration

Configuration is managed through environment variables. See `.env.example` for all available options:

- `APP_NAME`: Application name
- `APP_VERSION`: Application version
- `APP_ENV`: Environment (development/production)
- `DEBUG`: Enable debug mode
- `API_V1_PREFIX`: API version prefix
- `SECRET_KEY`: Secret key for security
- `HOST`: Server host
- `PORT`: Server port
- `ALLOWED_ORIGINS`: CORS allowed origins
- `LOG_LEVEL`: Logging level

## Development

### Adding New Endpoints

1. Create a new router in `app/api/v1/endpoints/`
2. Define schemas in `app/schemas/`
3. Add business logic in `app/services/`
4. Register the router in `app/api/v1/api.py`
5. Write tests in `tests/api/v1/`

### Using Poetry (Alternative)

If you prefer using Poetry:

```bash
# Install dependencies
poetry install

# Activate virtual environment
poetry shell

# Run application
poetry run python -m app.main

# Run tests
poetry run pytest
```

## Best Practices

- Follow the repository structure for consistency
- Write tests for all new endpoints
- Use Pydantic schemas for request/response validation
- Keep business logic in services, not in endpoints
- Use type hints throughout the codebase
- Follow REST API naming conventions
- Document all endpoints with docstrings

## Common Commands

```bash
make help       # Show all available commands
make install    # Install dependencies
make run        # Run the application
make test       # Run tests
make test-cov   # Run tests with coverage
make lint       # Run linter
make format     # Format code
make clean      # Clean up cache files
```

## Environment Variables

Create a `.env` file based on `.env.example`:

```bash
cp .env.example .env
```

Key variables:
- `SECRET_KEY`: Change this in production
- `ALLOWED_ORIGINS`: Update with your frontend URLs
- `DATABASE_URL`: Add when using a database

## Next Steps

- [ ] Add database integration (PostgreSQL, MongoDB, etc.)
- [ ] Implement authentication and authorization
- [ ] Add caching layer (Redis)
- [ ] Set up CI/CD pipeline
- [ ] Add logging and monitoring
- [ ] Implement rate limiting
- [ ] Add WebSocket support if needed
- [ ] Set up Docker deployment

## License

MIT License - feel free to use this template for your projects.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
