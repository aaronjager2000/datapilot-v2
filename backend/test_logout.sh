#!/bin/bash

cd "/Users/aarongrant/datapilot grind/datapilot/backend"

echo "1. Login and get token..."
TOKEN=$(curl -s -X POST http://localhost:8001/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email": "admin@datapilot.com", "password": "changethis"}' | jq -r '.access_token')

echo "Token: ${TOKEN:0:50}..."
echo ""

echo "2. Test token BEFORE logout..."
curl -s http://localhost:8001/api/v1/auth/me \
  -H "Authorization: Bearer $TOKEN" | jq '.email'
echo ""

echo "3. Logout (revoke token)..."
curl -s -X POST http://localhost:8001/api/v1/auth/logout \
  -H "Authorization: Bearer $TOKEN"
echo ""
echo ""

echo "4. Test token AFTER logout (should fail)..."
curl -s http://localhost:8001/api/v1/auth/me \
  -H "Authorization: Bearer $TOKEN" | jq '.'
