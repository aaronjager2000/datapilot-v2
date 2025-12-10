# Datapilot API Testing Guide

## Quick Start

### Option 1: Automated Testing Script
```bash
cd backend
./test_api.sh
```

### Option 2: Manual Testing

## Prerequisites
- Server running on http://localhost:8001
- `jq` installed for JSON formatting (optional): `brew install jq`

---

## Test Protocol

### 1. Health Check
```bash
curl http://localhost:8001/health | jq '.'
```

**Expected Response:**
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "service": "datapilot-api"
}
```

---

### 2. Register New User (Creates Organization)
```bash
curl -X POST http://localhost:8001/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "SecurePass123!",
    "full_name": "Test User",
    "organization_name": "Test Organization"
  }' | jq '.'
```

**Expected Response:**
```json
{
  "access_token": "eyJhbGc...",
  "refresh_token": "eyJhbGc...",
  "token_type": "bearer",
  "user": {
    "id": "uuid",
    "email": "test@example.com",
    "full_name": "Test User",
    "is_active": true,
    "organization_id": "uuid"
  }
}
```

**Save the access_token for next requests:**
```bash
export ACCESS_TOKEN="<your_access_token_here>"
```

---

### 3. Login with Superuser
```bash
curl -X POST http://localhost:8001/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@datapilot.com",
    "password": "admin123"
  }' | jq '.'
```

---

### 4. Get Current User Info
```bash
curl http://localhost:8001/api/v1/auth/me \
  -H "Authorization: Bearer $ACCESS_TOKEN" | jq '.'
```

**Expected Response:**
```json
{
  "id": "uuid",
  "email": "test@example.com",
  "full_name": "Test User",
  "is_active": true,
  "is_superuser": false,
  "organization_id": "uuid",
  "created_at": "2024-01-01T00:00:00Z"
}
```

---

### 5. Get Current Organization
```bash
curl http://localhost:8001/api/v1/organizations/me \
  -H "Authorization: Bearer $ACCESS_TOKEN" | jq '.'
```

**Expected Response:**
```json
{
  "id": "uuid",
  "name": "Test Organization",
  "slug": "test-organization",
  "subscription_tier": "FREE",
  "is_active": true
}
```

---

### 6. List Users in Organization
```bash
curl http://localhost:8001/api/v1/users \
  -H "Authorization: Bearer $ACCESS_TOKEN" | jq '.'
```

---

### 7. Update User Profile
```bash
# First get your user ID from /auth/me
export USER_ID="<your_user_id>"

curl -X PUT http://localhost:8001/api/v1/users/$USER_ID \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "full_name": "Test User Updated"
  }' | jq '.'
```

---

### 8. Update Organization
```bash
# First get your org ID from /organizations/me
export ORG_ID="<your_org_id>"

curl -X PUT http://localhost:8001/api/v1/organizations/$ORG_ID \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "My Updated Organization"
  }' | jq '.'
```

---

### 9. Refresh Access Token
```bash
# Save your refresh token from registration/login
export REFRESH_TOKEN="<your_refresh_token>"

curl -X POST http://localhost:8001/api/v1/auth/refresh \
  -H "Content-Type: application/json" \
  -d "{
    \"refresh_token\": \"$REFRESH_TOKEN\"
  }" | jq '.'
```

---

### 10. Logout (Revoke Tokens)
```bash
curl -X POST http://localhost:8001/api/v1/auth/logout \
  -H "Authorization: Bearer $ACCESS_TOKEN" | jq '.'
```

**Expected Response:**
```
HTTP 204 No Content
```

---

### 11. Test Invalid Token (Should Fail)
```bash
curl http://localhost:8001/api/v1/auth/me \
  -H "Authorization: Bearer invalid_token" | jq '.'
```

**Expected Response:**
```json
{
  "detail": "Could not validate credentials"
}
```

---

## Testing Error Handling

### Test Validation Errors
```bash
# Missing required fields
curl -X POST http://localhost:8001/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com"
  }' | jq '.'
```

### Test Duplicate Email
```bash
curl -X POST http://localhost:8001/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@datapilot.com",
    "password": "password",
    "full_name": "Test",
    "organization_name": "Test"
  }' | jq '.'
```

### Test Invalid Login
```bash
curl -X POST http://localhost:8001/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "wrongpassword"
  }' | jq '.'
```

---

## Rate Limiting Test

Run this multiple times rapidly to test rate limiting:
```bash
for i in {1..150}; do
  echo "Request $i"
  curl -s http://localhost:8001/health
done
```

After ~100 requests in 60 seconds, you should see:
```json
{
  "detail": "Rate limit exceeded. Please try again later."
}
```

---

## API Documentation

Visit the interactive API docs:
- **Swagger UI**: http://localhost:8001/api/v1/docs
- **ReDoc**: http://localhost:8001/api/v1/redoc

---

## Expected Superuser Credentials

From your `.env` file:
- **Email**: `admin@datapilot.com`
- **Password**: `admin123`

---

## Common Issues

### 1. Connection Refused
- Make sure the server is running: `uvicorn app.main:app --reload --port 8001`

### 2. 401 Unauthorized
- Check that your token is valid and not expired
- Make sure you're including `Bearer ` prefix in Authorization header

### 3. 422 Unprocessable Entity
- Check your request body matches the schema
- Verify all required fields are included

### 4. 429 Too Many Requests
- You've exceeded the rate limit
- Wait 60 seconds and try again
