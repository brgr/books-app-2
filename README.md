# Books App

A full-stack web application for managing your personal book collection and tracking your reading progress.

The application consists of two main components:

- **Backend**: FastAPI (Python) REST API with SQLite database
- **Frontend**: Vue.js 3 (TypeScript) single-page application

## Installation

### Backend Setup

1. Navigate to the backend directory:

```bash
cd books-backend
```

2. Install dependencies using uv:

```bash
uv sync
```

Or using pip:

```bash
pip install -e .
```

3. Set up the database:

```bash
# Initialize Alembic migrations (if needed)
uv run alembic upgrade head
```

4. Run the development server:

```bash
uv run fastapi dev main.py
```

The API will be available at `http://localhost:8000`

### Frontend Setup

1. Navigate to the frontend directory:

```bash
cd books-frontend
```

2. Install dependencies:

```bash
npm install
```

3. Run the development server:

```bash
npm run dev
```

The frontend will be available at `http://localhost:5173`

## Running with Docker

Build and run the backend container:

```bash
cd books-backend
docker build -t books-backend .
docker run -p 80:80 books-backend
```

## API Documentation

Once the backend is running, visit `http://localhost:8000/docs` for interactive API documentation (Swagger UI).

## Development

### Git Hooks

This repo includes a versioned pre-commit hook that runs backend type checking, linting, and tests plus frontend type
checking.

To enable it on your machine:

```bash
cp .githooks/pre-commit .git/hooks/pre-commit
```

### Backend Development

Type checking, linting, tests:

```bash
cd books-backend
uv run ty check    # type checking
uv run ruff check  # linting
uv run pytest      # run the tests
```

### Frontend Development

Build for production (includes type checking):

```bash
cd books-frontend
npm run build
```

## Environment Variables

### Backend (.env)

```env
DATABASE_URL=sqlite:///./books.db
APP_NAME=Books API
DEBUG=False
ALLOWED_ORIGINS=http://localhost:5173
```
