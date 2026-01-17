# Books Management Application

A full-stack web application for managing your personal book collection and tracking your reading progress.

## Overview

This application allows users to:
- Create an account and authenticate securely
- Manage a collection of books (create, read, update, delete)
- Track reading status for each book (want to read, started, finished, abandoned)
- Add personal notes and timestamps for books
- Browse books with pagination

## Architecture

The application consists of two main components:

- **Backend**: FastAPI (Python) REST API with SQLite database
- **Frontend**: Vue.js 3 (TypeScript) single-page application

## Features

### User Management
- User registration with password hashing (Argon2)
- OAuth2 password flow with JWT Bearer tokens
- Secure password storage

### Book Management
- Full CRUD operations for books
- Book attributes: title, author, ISBN, description, price, published date, page count
- Pagination support for book listings

### Reading Status Tracking
- Track reading status: want to read, started, finished, abandoned
- Automatic timestamp tracking (started_at, finished_at)
- Personal notes for each book
- Per-user reading lists

## Prerequisites

### Backend
- Python 3.12 or higher
- uv (Python package manager) - recommended, or pip

### Frontend
- Node.js 18+ and npm

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

### Key Endpoints

#### Authentication
- `POST /token` - OAuth2 password flow login (returns access + refresh tokens)
- `POST /auth/refresh` - Refresh access token
- `GET /users/me` - Get current user info (requires auth)

#### Books
- `GET /books` - List all books (paginated)
- `GET /books/{book_id}` - Get a specific book
- `POST /books` - Create a new book
- `PUT /books/{book_id}` - Update a book
- `DELETE /books/{book_id}` - Delete a book

#### Reading Status
- `PUT /books/{book_id}/status` - Set/update reading status for a book
- `DELETE /books/{book_id}/status` - Remove a book from reading list

## Development

### Backend Development

Type checking:
```bash
cd books-backend
uv run ty check
```

Linting:
```bash
cd books-backend
uv run ruff check
```

Run tests:
```bash
cd books-backend
uv run pytest
```

### Frontend Development

Build for production:
```bash
cd books-frontend
npm run build
```

Type checking:
```bash
npm run build  # Includes type checking
```

Preview production build:
```bash
npm run preview
```

## Environment Variables

### Backend (.env)
```env
DATABASE_URL=sqlite:///./books.db
APP_NAME=Books API
DEBUG=False
ALLOWED_ORIGINS=http://localhost:5173
```

## TODO

See books-backend/app/models.py:32 - Support for multiple authors per book is planned.
