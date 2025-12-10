#!/bin/bash

echo "=== Simple API Test ==="
echo ""

# Test 1: Health Check
echo "1. Health Check:"
curl -s http://localhost:8001/health | jq '.'
echo ""

# Test 2: Register (this will be slow due to bcrypt)
echo "2. Registering new user (this may take 10-20 seconds due to bcrypt)..."
REGISTER_RESPONSE=$(curl -s -X POST http://localhost:8001/api/v1/auth/register \
  -H 'Content-Type: application/json' \
  -d @- <<'EOF'
{
  "email": "newuser@test.com",
  "password": "SecurePass123",
  "full_name": "New Test User",
  "organization_name": "Test Company"
}
EOF
)

echo "$REGISTER_RESPONSE" | jq '.'

# Extract token if registration succeeded
ACCESS_TOKEN=$(echo "$REGISTER_RESPONSE" | jq -r '.access_token // empty')

if [ -n "$ACCESS_TOKEN" ] && [ "$ACCESS_TOKEN" != "null" ]; then
  echo ""
  echo "3. Testing authenticated endpoint /auth/me:"
  curl -s http://localhost:8001/api/v1/auth/me \
    -H "Authorization: Bearer $ACCESS_TOKEN" | jq '.'
else
  echo ""
  echo "Registration failed or no token returned"
fi

echo ""
echo "Done!"
