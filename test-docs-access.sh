#!/bin/bash
# Test script to verify API documentation endpoints are accessible

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
COMPOSE_FILE="${1:-development-docker-compose-server.yml}"
FRONTEND_URL="https://localhost:4200"
SERVER_URL="http://localhost:8080"

if [ "$COMPOSE_FILE" = "docker-compose-server.yml" ]; then
    FRONTEND_URL="https://localhost"
fi

echo "Testing API documentation access..."
echo "Using compose file: $COMPOSE_FILE"
echo "Frontend URL: $FRONTEND_URL"
echo "Server URL: $SERVER_URL"
echo ""

# Function to test an endpoint
test_endpoint() {
    local url=$1
    local description=$2
    local expect_json=$3
    
    echo -n "Testing $description... "
    
    # Make request and capture HTTP status code
    http_code=$(curl -s -k -o /tmp/test_response.txt -w "%{http_code}" "$url" || echo "000")
    
    if [ "$http_code" = "200" ]; then
        # Additional validation for JSON endpoints
        if [ "$expect_json" = "true" ]; then
            if grep -q "openapi" /tmp/test_response.txt 2>/dev/null || \
               grep -q "swagger" /tmp/test_response.txt 2>/dev/null || \
               grep -q "<!DOCTYPE html>" /tmp/test_response.txt 2>/dev/null; then
                echo -e "${GREEN}✓ PASSED${NC} (HTTP $http_code)"
                return 0
            else
                echo -e "${YELLOW}⚠ WARNING${NC} (HTTP $http_code but unexpected content)"
                return 1
            fi
        else
            echo -e "${GREEN}✓ PASSED${NC} (HTTP $http_code)"
            return 0
        fi
    elif [ "$http_code" = "000" ]; then
        echo -e "${RED}✗ FAILED${NC} (Connection error - is the service running?)"
        return 1
    else
        echo -e "${RED}✗ FAILED${NC} (HTTP $http_code)"
        return 1
    fi
}

# Check if containers are running
echo "Checking if containers are running..."
if ! docker compose -f "$COMPOSE_FILE" ps | grep -q "Up"; then
    echo -e "${YELLOW}Warning: Containers may not be running${NC}"
    echo "Start them with: docker compose -f $COMPOSE_FILE up -d"
    echo ""
fi

# Test direct server access (should work in dev mode)
if [ "$COMPOSE_FILE" = "development-docker-compose-server.yml" ]; then
    echo "=== Testing Direct Server Access ==="
    test_endpoint "$SERVER_URL/docs" "Direct Swagger UI" "true"
    test_endpoint "$SERVER_URL/redoc" "Direct ReDoc" "true"
    test_endpoint "$SERVER_URL/openapi.json" "Direct OpenAPI JSON" "true"
    echo ""
fi

# Test frontend proxy access
echo "=== Testing Frontend Proxy Access ==="
test_endpoint "$FRONTEND_URL/api/docs" "Proxied Swagger UI" "true"
test_endpoint "$FRONTEND_URL/api/redoc" "Proxied ReDoc" "true"
test_endpoint "$FRONTEND_URL/api/openapi.json" "Proxied OpenAPI JSON" "true"
echo ""

# Test that regular API still works
echo "=== Testing Regular API Endpoints ==="
test_endpoint "$FRONTEND_URL/api/v1/healthz" "Health check endpoint" "false"
echo ""

# Summary
echo "=== Test Summary ==="
echo "All configured documentation endpoints have been tested."
echo ""
echo "To access the documentation:"
echo "  Swagger UI: $FRONTEND_URL/api/docs"
echo "  ReDoc:      $FRONTEND_URL/api/redoc"
echo "  OpenAPI:    $FRONTEND_URL/api/openapi.json"
echo ""
echo "For more information, see DOCS_ACCESS.md"

# Cleanup
rm -f /tmp/test_response.txt
