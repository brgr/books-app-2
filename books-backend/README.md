# README

## Superuser Setup

The application runs in single-user mode and does not expose a public registration endpoint.  
Create the sole account with the management command:

```bash
# Probably use uv instead of python directly: uv run manage.py create-superuser
python manage.py create-superuser
```

You will be prompted for a username and password unless you pass them via flags:

```bash
python manage.py create-superuser --username alice
python manage.py create-superuser --username alice --password secretpass
```

The command uses the same `DATABASE_URL` configuration as the API.  
If an account already exists, the command aborts, and you must delete the user record manually before creating another
one.

## Development

Run type checks with Ty:

```bash
uv run ty check
```

Run lint checks with Ruff:

```bash
uv run ruff check
```

Run the API locally with FastAPI's dev server (binds to all interfaces so you can test from your phone):

```bash
uv run fastapi dev main.py --host 0.0.0.0 --port 8000
```

## Google Books API key setup

The Books API expects each request to identify your application using an API key. For this app, an API key is enough.

Create and enable a key:

1. Create or select a Google Cloud project, then enable the Google Books API for that project in the API Library.
2. Create an API key in the Cloud Console Credentials page.
3. Restrict the key before using it in production (recommended).

Console entry points (paste in your browser):

```
https://console.cloud.google.com/apis/library
https://console.cloud.google.com/apis/credentials
```

Add the key to `.env`:

```
GOOGLE_BOOKS_API_KEY=your-key-here
```
