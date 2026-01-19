#!/bin/bash

# Production deployment script for PUNCHLINE API

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m' # No Color

echo -e "${GREEN}Starting PUNCHLINE API deployment...${NC}"

# Load environment variables
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

# Login to ECR
echo -e "${GREEN}Logging in to AWS ECR...${NC}"
aws ecr get-login-password --region ap-southeast-2 | docker login --username AWS --password-stdin 533267128891.dkr.ecr.ap-southeast-2.amazonaws.com

# Pull latest image
echo -e "${GREEN}Pulling latest Docker image...${NC}"
docker-compose -f docker-compose.prod.yml pull

# Stop existing container
echo -e "${GREEN}Stopping existing container...${NC}"
docker-compose -f docker-compose.prod.yml down

# Start new container
echo -e "${GREEN}Starting new container...${NC}"
docker-compose -f docker-compose.prod.yml up -d

# Check if container is running
sleep 5
if docker ps | grep -q punchline-api; then
    echo -e "${GREEN}PUNCHLINE API is running successfully!${NC}"
    echo -e "${GREEN}Health check: http://localhost:8060/health${NC}"
    docker logs punchline-api --tail 20
else
    echo -e "${RED}Failed to start PUNCHLINE API${NC}"
    docker logs punchline-api --tail 50
    exit 1
fi