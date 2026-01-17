# Auth

OAuth2 password flow with JWT tokens. Uses **HttpOnly cookies** (browser clients) or `Authorization: Bearer` header (API clients/Swagger).

## Endpoints

| Endpoint | Description |
|----------|-------------|
| `POST /token` | Login (form: `username`, `password`) - sets cookies |
| `POST /auth/refresh` | Refresh access token (reads from cookie or body) |
| `POST /auth/logout` | Clears cookies |

## Production Configuration (Required)

```bash
# Generate secret: python -c "import secrets; print(secrets.token_urlsafe(32))"
JWT_SECRET=<your-random-secret>
ALLOWED_ORIGINS='["https://yourdomain.com"]'
```

**Defaults `change-me` and `["*"]` are insecure - must change for production.**

## All Options

| Variable | Default | Description |
|----------|---------|-------------|
| `JWT_SECRET` | `change-me` | Secret for signing JWTs |
| `JWT_ACCESS_TOKEN_EXP_MINUTES` | `60` | Access token expiry |
| `JWT_REFRESH_TOKEN_EXP_MINUTES` | `43200` | Refresh token expiry (30 days) |
| `ALLOWED_ORIGINS` | `["*"]` | CORS allowed origins |
| `COOKIE_SECURE` | `true` | HTTPS-only cookies (set `false` for local network HTTP) |
| `COOKIE_SAMESITE` | `lax` | Cookie SameSite attribute |
