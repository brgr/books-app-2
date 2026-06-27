# README

## Superuser Setup

The application runs in single-user mode and does not expose a public registration endpoint.  
Create the sole account with the management command:

```bash
uv run manage.py create-superuser
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

Type checking, linting, tests:

```bash
cd books-backend
uv run ty check    # type checking
uv run ruff check  # linting
uv run pytest      # run the tests
```

## Google Books API key setup

The Books API expects each request to identify your application using an API key.

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
