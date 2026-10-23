# Caller ID Monitor

A professional, white-label caller ID monitoring tool built with FastAPI and modern web technologies.

## Features

- Modern, responsive UI built with Tailwind CSS
- Real-time phone number monitoring using callerapi.com
- Easy API key configuration
- Professional phone number management
- Enterprise-ready architecture following SOLID principles
- White-label ready for customization

## Tech Stack

- FastAPI - Modern, fast web framework for building APIs
- SQLAlchemy - SQL toolkit and ORM
- Tailwind CSS - Utility-first CSS framework
- Jinja2 - Template engine
- SQLite - Database (can be easily switched to PostgreSQL for production)

## Setup

1. Clone the repository:
```bash
git clone <repository-url>
cd caller-id-monitor
```

2. Create a virtual environment and activate it:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Create a `.env` file in the root directory:
```bash
cp .env.example .env
```

5. Set `SESSION_SECRET` in the `.env` file. Use a random value of at least 32 characters. The app does not start without it. To make a value, run:
```bash
python -c 'import secrets; print(secrets.token_urlsafe(48))'
```

6. Apply the database migrations:
```bash
alembic upgrade head
```

7. Run the application:
```bash
uvicorn app.main:app --reload
```

8. Open your browser and navigate to `http://localhost:8000`. Each user signs in with their own API key. The app keeps the numbers of each user separate and monitors them with the key of their owner.

## Project Structure

```
caller_id_monitor/
├── app/
│   ├── api/            # API endpoints
│   ├── core/           # Core configuration
│   ├── db/             # Database configuration
│   ├── models/         # SQLAlchemy models
│   ├── schemas/        # Pydantic schemas
│   ├── services/       # Business logic
│   └── templates/      # HTML templates
├── static/             # Static files
├── tests/              # Test suite
├── .env.example        # Environment variables example
└── requirements.txt    # Python dependencies
```

## API Documentation

Once the application is running, you can access:
- Interactive API documentation: `http://localhost:8000/docs`
- Alternative API documentation: `http://localhost:8000/redoc`

## Development

To run the development server with auto-reload:
```bash
uvicorn app.main:app --reload
```

To run the tests:
```bash
pip install -r requirements-dev.txt
pytest
```

## Production Deployment

For production deployment:

1. Use a production-grade database (e.g., PostgreSQL)
2. Set up proper environment variables. `SESSION_SECRET` is required.
3. Run `alembic upgrade head` before you start a new version
4. Use a production ASGI server (e.g., Gunicorn with Uvicorn workers)
5. Set up proper security measures (HTTPS, rate limiting, etc.)
6. Configure proper logging

Example production command:
```bash
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker
```

## White Labeling

The application is designed to be easily white-labeled:

1. Customize the branding in `app/templates/base.html`
2. Modify the color scheme in the Tailwind configuration
3. Add your logo and custom styles
4. Update text and messaging throughout the templates

## Support

For support, please contact https://callerapi.com/contact