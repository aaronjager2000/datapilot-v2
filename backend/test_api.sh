#!/bin/bash

# Datapilot API Testing Script
# Make sure the server is running on http://localhost:8001

BASE_URL="http://localhost:8001"
API_URL="${BASE_URL}/api/v1"

echo "========================================="
echo "Datapilot API Testing Protocol"
echo "========================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Test 1: Health Check
echo -e "${BLUE}Test 1: Health Check${NC}"
echo "GET ${BASE_URL}/health"
curl -s "${BASE_URL}/health" | jq '.'
echo ""
echo ""

# Test 2: Register a new user (creates organization)
echo -e "${BLUE}Test 2: Register New User${NC}"
echo "POST ${API_URL}/auth/register"
TIMESTAMP=$(date +%s)
REGISTER_RESPONSE=$(curl -s -X POST "${API_URL}/auth/register" \
  -H "Content-Type: application/json" \
  -d "{
    \"email\": \"test${TIMESTAMP}@example.com\",
    \"password\": \"SecurePass123!\",
    \"full_name\": \"Test User\",
    \"organization_name\": \"Test Organization ${TIMESTAMP}\"
  }")

echo "$REGISTER_RESPONSE" | jq '.'
ACCESS_TOKEN=$(echo "$REGISTER_RESPONSE" | jq -r '.access_token')
REFRESH_TOKEN=$(echo "$REGISTER_RESPONSE" | jq -r '.refresh_token')
echo ""
echo -e "${GREEN}Access Token: ${ACCESS_TOKEN:0:50}...${NC}"
echo ""
echo ""

# Test 3: Get current user info
echo -e "${BLUE}Test 3: Get Current User Info (/auth/me)${NC}"
echo "GET ${API_URL}/auth/me"
curl -s "${API_URL}/auth/me" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" | jq '.'
echo ""
echo ""

# Test 4: Login with existing user
echo -e "${BLUE}Test 4: Login with Superuser${NC}"
echo "POST ${API_URL}/auth/login"
LOGIN_RESPONSE=$(curl -s -X POST "${API_URL}/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@datapilot.com",
    "password": "changethis"
  }')

echo "$LOGIN_RESPONSE" | jq '.'
ADMIN_TOKEN=$(echo "$LOGIN_RESPONSE" | jq -r '.access_token')
echo ""
echo -e "${GREEN}Admin Access Token: ${ADMIN_TOKEN:0:50}...${NC}"
echo ""
echo ""

# Test 5: Refresh token
echo -e "${BLUE}Test 5: Refresh Access Token${NC}"
echo "POST ${API_URL}/auth/refresh"
REFRESH_RESPONSE=$(curl -s -X POST "${API_URL}/auth/refresh" \
  -H "Content-Type: application/json" \
  -d "{
    \"refresh_token\": \"${REFRESH_TOKEN}\"
  }")

echo "$REFRESH_RESPONSE" | jq '.'
NEW_ACCESS_TOKEN=$(echo "$REFRESH_RESPONSE" | jq -r '.access_token')
echo ""
echo -e "${GREEN}New Access Token: ${NEW_ACCESS_TOKEN:0:50}...${NC}"
echo ""
echo ""

# Test 6: Get current organization
echo -e "${BLUE}Test 6: Get Current Organization${NC}"
echo "GET ${API_URL}/organizations/me"
curl -s "${API_URL}/organizations/me" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" | jq '.'
echo ""
echo ""

# Test 7: List users in organization
echo -e "${BLUE}Test 7: List Users in Organization${NC}"
echo "GET ${API_URL}/users"
curl -s "${API_URL}/users" \
  -H "Authorization: Bearer ${ADMIN_TOKEN}" | jq '.'
echo ""
echo ""

# Test 8: Get specific user
echo -e "${BLUE}Test 8: Get Current User Details${NC}"
echo "GET ${API_URL}/auth/me"
USER_RESPONSE=$(curl -s "${API_URL}/auth/me" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}")
echo "$USER_RESPONSE" | jq '.'
USER_ID=$(echo "$USER_RESPONSE" | jq -r '.id')
echo ""
echo ""

# Test 9: Update user profile
echo -e "${BLUE}Test 9: Update User Profile${NC}"
echo "PUT ${API_URL}/users/${USER_ID}"
curl -s -X PUT "${API_URL}/users/${USER_ID}" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "full_name": "Test User Updated"
  }' | jq '.'
echo ""
echo ""

# Test 10: Update organization settings
echo -e "${BLUE}Test 10: Update Organization Settings${NC}"
ORG_RESPONSE=$(curl -s "${API_URL}/organizations/me" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}")
ORG_ID=$(echo "$ORG_RESPONSE" | jq -r '.id')

echo "PUT ${API_URL}/organizations/${ORG_ID}"
curl -s -X PUT "${API_URL}/organizations/${ORG_ID}" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test Organization Updated"
  }' | jq '.'
echo ""
echo ""

# Test 11: Test invalid token
echo -e "${BLUE}Test 11: Test Invalid Token (Should Fail)${NC}"
echo "GET ${API_URL}/auth/me"
curl -s "${API_URL}/auth/me" \
  -H "Authorization: Bearer invalid_token_here" | jq '.'
echo ""
echo ""

# Test 12: Logout
echo -e "${BLUE}Test 12: Logout (Revoke Tokens)${NC}"
echo "POST ${API_URL}/auth/logout"
curl -s -X POST "${API_URL}/auth/logout" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" | jq '.'
echo ""
echo ""

# Test 13: Try to use token after logout (should fail)
echo -e "${BLUE}Test 13: Try Using Token After Logout (Should Fail)${NC}"
echo "GET ${API_URL}/auth/me"
curl -s "${API_URL}/auth/me" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" | jq '.'
echo ""
echo ""

echo -e "${GREEN}=========================================${NC}"
echo -e "${GREEN}Testing Complete!${NC}"
echo -e "${GREEN}=========================================${NC}"
