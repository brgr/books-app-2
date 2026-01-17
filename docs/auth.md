# Auth

## Overview
The backend uses the OAuth2 password flow with JWT Bearer access tokens and longer-lived refresh tokens.
Clients authenticate with `Authorization: Bearer <access_token>`.

## Endpoints
- `POST /token`
  - Body: `application/x-www-form-urlencoded` (`username`, `password`)
  - Response: `{ "access_token", "refresh_token", "expires_in", "refresh_expires_in" }`
- `POST /auth/refresh`
  - Body: `{ "refresh_token": "..." }`
  - Response: `{ "access_token", "expires_in" }`

## Configuration
Set these environment variables in production:
- `JWT_SECRET`: a long random string used to sign tokens
- `JWT_ALGORITHM`: defaults to `HS256`
- `JWT_ACCESS_TOKEN_EXP_MINUTES`: default `60`
- `JWT_REFRESH_TOKEN_EXP_MINUTES`: default `43200` (30 days)

Recommendation: generate a 32+ byte random secret and keep it private.
