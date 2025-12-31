# API Testing Guide

Complete guide for testing the Similarity Intelligence Platform API.

## Table of Contents

- [Quick Start](#quick-start)
- [Setup](#setup)
- [Authentication](#authentication)
- [API Endpoints](#api-endpoints)
- [Testing Workflows](#testing-workflows)
- [Postman Collection](#postman-collection)
- [Troubleshooting](#troubleshooting)

## Quick Start

### 1. Start the Server

```bash
# Start services
docker-compose up -d postgres redis

# Run migrations
alembic upgrade head

# Seed test data
python scripts/seed_test_data.py

# Start API server
uvicorn app.main:app --reload
```

### 2. Access Documentation

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/health

### 3. Test Credentials

After running the seed script, use these credentials:

**Organization 1 - Acme News Corp (Free Tier)**
- Admin: `admin@acmenews.com` / `admin123!`
- Member: `editor@acmenews.com` / `editor123!`

**Organization 2 - TechInsight Media (Pro Tier)**
- Admin: `cto@techinsight.io` / `cto123!`
- Member: `researcher@techinsight.io` / `research123!`
- Viewer: `intern@techinsight.io` / `intern123!`

**Superuser**
- `superuser@platform.com` / `super123!`

---

## Setup

### Prerequisites

```bash
# Python 3.11+
python --version

# Install dependencies
pip install -r requirements.txt

# Set environment variables
cp .env.example .env

# Edit .env and set:
# - SECRET_KEY (generate with: openssl rand -hex 32)
# - DATABASE_URL
# - YOUTUBE_API_KEY (optional, for YouTube similarity checks)
```

### Database Setup

```bash
# Create database
createdb similarity_platform

# Run migrations
alembic upgrade head

# Seed test data
python scripts/seed_test_data.py
```

---

## Authentication

The API supports two authentication methods:

### 1. JWT Tokens (User Management)

For user/organization management endpoints.

**Login Flow:**

```bash
# 1. Register new user + organization
curl -X POST http://localhost:8000/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "username": "testuser",
    "password": "SecurePass123!",
    "full_name": "Test User",
    "organization_name": "Test Corp"
  }'

# 2. Login (returns JWT token)
curl -X POST http://localhost:8000/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@acmenews.com",
    "password": "admin123!"
  }'

# Response:
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "expires_in": 3600,
  "user": {
    "id": "...",
    "email": "admin@acmenews.com",
    "username": "acme_admin",
    "role": "admin",
    ...
  }
}

# 3. Use token in subsequent requests
curl -X GET http://localhost:8000/v1/users \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIs..."
```

### 2. API Keys (Similarity Checks)

For similarity checking endpoints.

**Create API Key:**

```bash
# 1. Login to get JWT token (see above)

# 2. Create API key
curl -X POST http://localhost:8000/v1/organizations/current/api-keys \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "My Test Key",
    "rate_limit_per_minute": 60,
    "expires_in_days": 90
  }'

# Response (API key shown ONLY on creation):
{
  "id": "...",
  "name": "My Test Key",
  "key_prefix": "sk_live_abc",
  "api_key": "sk_test_YOUR_API_KEY_HERE_REPLACE_ME",  # SAVE THIS!
  "is_active": true,
  ...
}

# 3. Use API key for similarity checks
curl -X POST http://localhost:8000/v1/check \
  -H "X-API-Key: sk_test_YOUR_API_KEY_HERE_REPLACE_ME" \
  -H "Content-Type: application/json" \
  -d '{
    "article_text": "Your article content...",
    "sources": ["articles", "youtube"]
  }'
```

---

## API Endpoints

### Authentication (`/v1/auth`)

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| POST | `/v1/auth/register` | Register new user + organization | None |
| POST | `/v1/auth/login` | Login and get JWT token | None |
| GET | `/v1/auth/me` | Get current user info | JWT |
| POST | `/v1/auth/change-password` | Change password | JWT |
| POST | `/v1/auth/logout` | Logout (client-side token deletion) | None |

### User Management (`/v1/users`)

| Method | Endpoint | Description | Auth | Role |
|--------|----------|-------------|------|------|
| GET | `/v1/users` | List organization users | JWT | Admin |
| POST | `/v1/users` | Create new user | JWT | Admin |
| GET | `/v1/users/{id}` | Get user by ID | JWT | Admin/Self |
| PATCH | `/v1/users/{id}` | Update user | JWT | Admin |
| DELETE | `/v1/users/{id}` | Delete user | JWT | Admin |

### Organization Management (`/v1/organizations`)

| Method | Endpoint | Description | Auth | Role |
|--------|----------|-------------|------|------|
| GET | `/v1/organizations/current` | Get current organization | JWT | Any |
| PATCH | `/v1/organizations/current` | Update current organization | JWT | Admin |
| GET | `/v1/organizations/current/api-keys` | List API keys | JWT | Admin |
| POST | `/v1/organizations/current/api-keys` | Create API key | JWT | Admin |
| DELETE | `/v1/organizations/current/api-keys/{id}` | Delete API key | JWT | Admin |
| GET | `/v1/organizations` | List all organizations | JWT | Superuser |
| POST | `/v1/organizations` | Create organization | JWT | Superuser |
| GET | `/v1/organizations/{id}` | Get organization by ID | JWT | Superuser |
| PATCH | `/v1/organizations/{id}` | Update organization | JWT | Superuser |
| DELETE | `/v1/organizations/{id}` | Delete organization | JWT | Superuser |

### Similarity Checks (`/v1/check`)

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| POST | `/v1/check` | Submit similarity check | API Key |
| GET | `/v1/check/{id}` | Get check results | API Key |

### Usage Stats (`/v1/usage`)

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| GET | `/v1/usage` | Get usage statistics | API Key |

---

## Testing Workflows

### Workflow 1: Complete Registration Flow

```bash
# 1. Register
REGISTER_RESPONSE=$(curl -s -X POST http://localhost:8000/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "newuser@example.com",
    "username": "newuser",
    "password": "SecurePass123!",
    "full_name": "New User",
    "organization_name": "New Corp"
  }')

echo $REGISTER_RESPONSE | jq '.'

# Extract token
TOKEN=$(echo $REGISTER_RESPONSE | jq -r '.access_token')

# 2. Get user info
curl -X GET http://localhost:8000/v1/auth/me \
  -H "Authorization: Bearer $TOKEN" | jq '.'

# 3. Get organization
curl -X GET http://localhost:8000/v1/organizations/current \
  -H "Authorization: Bearer $TOKEN" | jq '.'

# 4. Create API key
API_KEY_RESPONSE=$(curl -s -X POST http://localhost:8000/v1/organizations/current/api-keys \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Production Key",
    "rate_limit_per_minute": 100
  }')

echo $API_KEY_RESPONSE | jq '.'

# Extract API key
API_KEY=$(echo $API_KEY_RESPONSE | jq -r '.api_key')
echo "🔑 Your API Key: $API_KEY"

# 5. Run similarity check
curl -X POST http://localhost:8000/v1/check \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "article_text": "Machine learning is transforming how we process data. Neural networks can identify patterns in large datasets.",
    "sources": ["articles", "youtube"],
    "sensitivity": "medium"
  }' | jq '.'
```

### Workflow 2: User Management

```bash
# Login as admin
LOGIN_RESPONSE=$(curl -s -X POST http://localhost:8000/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@acmenews.com",
    "password": "admin123!"
  }')

TOKEN=$(echo $LOGIN_RESPONSE | jq -r '.access_token')

# List users
curl -X GET http://localhost:8000/v1/users \
  -H "Authorization: Bearer $TOKEN" | jq '.'

# Create new user
curl -X POST http://localhost:8000/v1/users \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "junior@acmenews.com",
    "username": "junior_editor",
    "password": "JuniorPass123!",
    "full_name": "Junior Editor",
    "role": "member"
  }' | jq '.'

# Update user (get ID from previous response)
curl -X PATCH http://localhost:8000/v1/users/{USER_ID} \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "role": "admin",
    "is_active": true
  }' | jq '.'
```

### Workflow 3: API Key Management

```bash
# Login
TOKEN=$(curl -s -X POST http://localhost:8000/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@acmenews.com", "password": "admin123!"}' \
  | jq -r '.access_token')

# List existing API keys
curl -X GET http://localhost:8000/v1/organizations/current/api-keys \
  -H "Authorization: Bearer $TOKEN" | jq '.'

# Create new API key
curl -X POST http://localhost:8000/v1/organizations/current/api-keys \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Development Key",
    "rate_limit_per_minute": 30,
    "expires_in_days": 30
  }' | jq '.'

# Delete API key
curl -X DELETE http://localhost:8000/v1/organizations/current/api-keys/{KEY_ID} \
  -H "Authorization: Bearer $TOKEN"
```

### Workflow 4: Similarity Check

```bash
# Use seeded API key
API_KEY="YOUR_API_KEY_FROM_SEED_SCRIPT"

# Submit check
CHECK_RESPONSE=$(curl -s -X POST http://localhost:8000/v1/check \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "article_text": "Artificial intelligence and machine learning are revolutionizing technology. Neural networks enable computers to learn from data without explicit programming. Deep learning models can process vast amounts of information and identify complex patterns.",
    "sources": ["articles", "youtube"],
    "sensitivity": "medium",
    "metadata": {
      "title": "AI Revolution Article",
      "author": "Test User"
    }
  }')

echo $CHECK_RESPONSE | jq '.'

# Extract check ID
CHECK_ID=$(echo $CHECK_RESPONSE | jq -r '.check_id')

# Poll for results (async processing)
sleep 5

curl -X GET http://localhost:8000/v1/check/$CHECK_ID \
  -H "X-API-Key: $API_KEY" | jq '.'

# Get usage stats
curl -X GET http://localhost:8000/v1/usage \
  -H "X-API-Key: $API_KEY" | jq '.'
```

---

## Postman Collection

### Import into Postman

1. Create a new collection: "Similarity Platform API"
2. Add environment variables:
   - `BASE_URL`: `http://localhost:8000`
   - `JWT_TOKEN`: (will be set automatically)
   - `API_KEY`: (will be set automatically)

3. Import these requests:

**Register**
```json
POST {{BASE_URL}}/v1/auth/register
Content-Type: application/json

{
  "email": "test@example.com",
  "username": "testuser",
  "password": "Test123!",
  "organization_name": "Test Corp"
}

Tests (auto-save token):
pm.environment.set("JWT_TOKEN", pm.response.json().access_token);
```

**Login**
```json
POST {{BASE_URL}}/v1/auth/login
Content-Type: application/json

{
  "email": "admin@acmenews.com",
  "password": "admin123!"
}

Tests:
pm.environment.set("JWT_TOKEN", pm.response.json().access_token);
```

**Create API Key**
```json
POST {{BASE_URL}}/v1/organizations/current/api-keys
Authorization: Bearer {{JWT_TOKEN}}
Content-Type: application/json

{
  "name": "Test Key",
  "rate_limit_per_minute": 60
}

Tests:
pm.environment.set("API_KEY", pm.response.json().api_key);
```

**Similarity Check**
```json
POST {{BASE_URL}}/v1/check
X-API-Key: {{API_KEY}}
Content-Type: application/json

{
  "article_text": "Your article here...",
  "sources": ["articles", "youtube"]
}
```

---

## Troubleshooting

### Common Issues

**1. "Invalid authentication credentials"**
- Check token is in `Authorization: Bearer <token>` format
- Token may have expired (default 1 hour)
- Re-login to get new token

**2. "API key is required"**
- Similarity endpoints need `X-API-Key` header
- Create API key first via `/organizations/current/api-keys`

**3. "Monthly check limit exceeded"**
- Check usage: `GET /v1/usage`
- Upgrade tier or wait for monthly reset
- Superusers can update limits via `/organizations/{id}`

**4. "Access denied" / 403 errors**
- Check user role (admin/member/viewer permissions)
- Some endpoints require admin or superuser role
- Use correct organization context

**5. Database connection errors**
- Ensure PostgreSQL is running: `docker-compose up -d postgres`
- Check `DATABASE_URL` in `.env`
- Run migrations: `alembic upgrade head`

**6. Celery tasks not processing**
- Ensure Redis is running: `docker-compose up -d redis`
- Start Celery worker: `celery -A app.tasks.celery_app worker -l info`

### Debug Mode

Enable debug logging:

```bash
# In .env
DEBUG=true
ENVIRONMENT=development

# Restart server
uvicorn app.main:app --reload --log-level debug
```

### Reset Database

```bash
# Drop and recreate
dropdb similarity_platform
createdb similarity_platform

# Run migrations
alembic upgrade head

# Reseed
python scripts/seed_test_data.py
```

---

## Examples by Role

### Admin User

Can do everything in their organization:

```bash
TOKEN="<admin_jwt_token>"

# Manage users
curl -X GET http://localhost:8000/v1/users -H "Authorization: Bearer $TOKEN"
curl -X POST http://localhost:8000/v1/users -H "Authorization: Bearer $TOKEN" -d '...'

# Manage API keys
curl -X GET http://localhost:8000/v1/organizations/current/api-keys -H "Authorization: Bearer $TOKEN"
curl -X POST http://localhost:8000/v1/organizations/current/api-keys -H "Authorization: Bearer $TOKEN" -d '...'

# Update organization
curl -X PATCH http://localhost:8000/v1/organizations/current -H "Authorization: Bearer $TOKEN" -d '...'
```

### Member User

Can use API, view own profile:

```bash
TOKEN="<member_jwt_token>"

# View own profile
curl -X GET http://localhost:8000/v1/auth/me -H "Authorization: Bearer $TOKEN"

# Change password
curl -X POST http://localhost:8000/v1/auth/change-password -H "Authorization: Bearer $TOKEN" -d '...'

# Cannot manage users or API keys (403 error)
```

### Viewer User

Read-only access:

```bash
TOKEN="<viewer_jwt_token>"

# Can view own profile
curl -X GET http://localhost:8000/v1/auth/me -H "Authorization: Bearer $TOKEN"

# Cannot modify anything (403 errors)
```

### Superuser

Can manage all organizations:

```bash
TOKEN="<superuser_jwt_token>"

# List all organizations
curl -X GET http://localhost:8000/v1/organizations -H "Authorization: Bearer $TOKEN"

# Create organization
curl -X POST http://localhost:8000/v1/organizations -H "Authorization: Bearer $TOKEN" -d '...'

# Update any organization
curl -X PATCH http://localhost:8000/v1/organizations/{id} -H "Authorization: Bearer $TOKEN" -d '...'

# Change tier/limits
curl -X PATCH http://localhost:8000/v1/organizations/{id} \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"tier": "enterprise", "monthly_check_limit": 10000}'
```

---

## OpenAPI Schema

Access the full OpenAPI schema:

```bash
# JSON format
curl http://localhost:8000/openapi.json

# Interactive UI
open http://localhost:8000/docs
```

---

## Further Reading

- [Main README](../README.md)
- [API Documentation](http://localhost:8000/docs) (when server running)
- [Architecture Overview](./ARCHITECTURE.md)
- [Deployment Guide](./DEPLOYMENT.md)
