#!/bin/bash
#
# Push Client Image to Harbor as latest-alpha
# Usage: ./scripts/push-client-alpha.sh [VERSION]
#   VERSION: Optional version string (will be prompted if not provided)
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Harbor configuration
HARBOR_HOST="harbor.vm.kumpeapps.com"
HARBOR_PROJECT="managed-nebula"
IMAGE_NAME="client"
FULL_IMAGE="${HARBOR_HOST}/${HARBOR_PROJECT}/${IMAGE_NAME}"

echo -e "${BLUE}=== Push Client Image to Harbor as latest-alpha ===${NC}"
echo

# Get version
if [ -n "$1" ]; then
    VERSION="$1"
    echo -e "${GREEN}Using provided version: ${VERSION}${NC}"
else
    # Prompt for version
    echo -e "${YELLOW}Enter the client version (e.g., 1.5.0alpha1, 1.5.0beta1):${NC}"
    echo -e "${YELLOW}This will tag the image as latest-alpha'${NC}"
    read -p "Version: " VERSION
    
    if [ -z "$VERSION" ]; then
        echo -e "${RED}Error: Version is required${NC}"
        exit 1
    fi
    
    echo -e "${GREEN}Version set to: ${VERSION}${NC}"
fi

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo -e "${RED}Error: Docker is not running${NC}"
    exit 1
fi

# Check if logged into Harbor
echo -e "${YELLOW}Checking Harbor login status...${NC}"
if ! docker login ${HARBOR_HOST} --get-login; then
    echo -e "${YELLOW}Not logged into Harbor. Please login:${NC}"
    docker login ${HARBOR_HOST}
fi

# Confirm before proceeding
echo
echo -e "${YELLOW}About to build and push:${NC}"
echo -e "  Image: ${FULL_IMAGE}:latest-alpha"
echo -e "  Build context: ../client"
echo -e "  Platforms: linux/amd64,linux/arm64"
echo
read -p "Continue? (y/N) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${RED}Aborted${NC}"
    exit 1
fi

# Set up Docker Buildx if not already configured
echo -e "${BLUE}Setting up Docker Buildx...${NC}"
if ! docker buildx inspect multiarch > /dev/null 2>&1; then
    docker buildx create --name multiarch --driver docker-container --use
    docker buildx inspect --bootstrap
else
    docker buildx use multiarch
fi

# Build and push
echo -e "${BLUE}Building and pushing client image...${NC}"
docker buildx build --push \
    --build-arg VERSION="${VERSION}" \
    --tag "${FULL_IMAGE}:latest-alpha" \
    --cache-from type=registry,ref="${FULL_IMAGE}:latest-alpha" \
    --cache-to type=inline \
    --provenance=false \
    --platform linux/amd64,linux/arm64 \
    ../client

echo
echo -e "${GREEN}✓ Successfully pushed client images:${NC}"
echo -e "  ${FULL_IMAGE}:latest-alpha"
echo
echo -e "${BLUE}To pull the image:${NC}"
echo -e "  docker pull ${FULL_IMAGE}:latest-alpha"
echo
echo -e "${BLUE}To use in docker-compose:${NC}"
echo -e "  image: ${FULL_IMAGE}:latest-alpha"
