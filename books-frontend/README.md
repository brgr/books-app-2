# Books Frontend

A Vue 3 frontend for managing your book collection.

## Setup

1. Install dependencies:
   ```bash
   npm install
   ```

2. Create a `.env` file (copy from `.env.example`):
   ```bash
   cp .env.example .env
   ```

3. Configure the API URL in `.env`:
   ```
   VITE_API_URL=http://localhost:8000
   ```

If you want to test from another device on your network (e.g., your phone):

- Start the backend so it listens on all interfaces: `uv run fastapi dev main.py --host 0.0.0.0 --port 8000` (from
  `books-backend/`).
- Set `VITE_API_URL` to your machine's LAN IP, e.g. `VITE_API_URL=http://<your-lan-ip>:8000`.
- In the backend `.env`, set `COOKIE_SECURE=false` (required for HTTP on local network IPs).
- In the backend `.env`, set `ALLOWED_ORIGINS` to include your frontend URL, e.g. `ALLOWED_ORIGINS='["http://<your-lan-ip>:5173"]'`.
- Run the frontend dev server bound to all interfaces: `npm run dev -- --host 0.0.0.0`.

## Development

Run the development server:

```bash
npm run dev
```

The application will be available at `http://localhost:5173`

## Building for Production

Build the application:

```bash
npm run build
```
