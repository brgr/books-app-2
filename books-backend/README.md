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

Run type checks with the ty:

```bash
uv run ty check
```
