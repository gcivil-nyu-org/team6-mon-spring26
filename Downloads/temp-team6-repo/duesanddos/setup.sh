#!/bin/bash

# Setup colors
GREEN='\033[0;32m'
NC='\033[0m' # No Color

echo -e "${GREEN}Starting installation for Dues & Do's...${NC}"

# Backend Setup
echo -e "\n${GREEN}Setting up Backend...${NC}"
cd backend
if [ ! -d ".venv" ]; then
    python3 -m venv .venv
fi
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
cd ..

# Frontend Setup
echo -e "\n${GREEN}Setting up Frontend...${NC}"
cd frontend
npm install
cd ..

echo -e "\n${GREEN}Installation complete!${NC}"
echo -e "To start the development servers:"
echo -e "1. Backend: cd backend && source .venv/bin/activate && python manage.py runserver"
echo -e "2. Frontend: cd frontend && npm run dev"
